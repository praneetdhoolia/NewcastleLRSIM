package citysim;

import com.google.inject.Inject;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.events.PersonEntersVehicleEvent;
import org.matsim.api.core.v01.events.PersonLeavesVehicleEvent;
import org.matsim.api.core.v01.network.Link;
import org.matsim.core.api.experimental.events.EventsManager;
import org.matsim.core.mobsim.framework.MobsimAgent;
import org.matsim.core.mobsim.framework.PassengerAgent;
import org.matsim.core.mobsim.qsim.InternalInterface;
import org.matsim.core.mobsim.qsim.QSim;
import org.matsim.core.mobsim.qsim.interfaces.DepartureHandler;
import org.matsim.core.mobsim.qsim.interfaces.MobsimEngine;
import org.matsim.core.mobsim.qsim.interfaces.MobsimVehicle;
import org.matsim.core.mobsim.qsim.qnetsimengine.QVehicle;
import org.matsim.vehicles.Vehicle;

/**
 * Physical boarding for paired car passengers (DECISIONS.md 9.53, issue #48):
 * a booked passenger ENTERS the household driver's vehicle, rides every link
 * the car traverses, and alights at their shared destination link. No
 * teleportation — the passenger's realised times are the vehicle's own, and
 * the events stream carries a real {@link PersonEntersVehicleEvent} /
 * {@link PersonLeavesVehicleEvent} pair, so occupancy is measurable from the
 * run rather than inferred.
 *
 * <h2>The contract with {@link RidePairingEngine}</h2>
 *
 * <p>Pairing stays where it was: at BeforeMobsim, on stable plans, in
 * {@link RidePairingEngine} (DECISIONS.md 9.44). When
 * {@code ridePairing.physicalBoarding} is on, each paired ride leg becomes a
 * {@link RidePairingEngine.Booking} naming the driver. This engine redeems
 * bookings at the qsim's own departures:
 *
 * <ul>
 *   <li><b>Board</b>: the passenger departs on a ride leg, holds a booking
 *       from this link, and the driver's car is STILL PARKED HERE — then the
 *       passenger enters it and this handler claims the departure.</li>
 *   <li><b>Miss</b>: the car has already left, was never here, or is full —
 *       the departure is NOT claimed, so the leg falls through to the
 *       teleportation engine carrying the driver's realised time that
 *       {@link RidePairingEngine} already wrote into the route. A miss is
 *       Tier 1 verbatim, never a third behaviour, and it is counted.</li>
 *   <li><b>Alight</b>: each sim step, a passenger whose vehicle has moved off
 *       the boarding link and now stands on (or traverses) their destination
 *       link leaves it, ends the leg at the real clock, and continues their
 *       plan.</li>
 * </ul>
 *
 * <h2>What this deliberately does not do</h2>
 *
 * <p>It never delays the driver (the blast-radius rule of 9.44: an unpaired
 * or unboarded world must be byte-comparable to Tier 1), never moves a
 * departure time, and never invents a pairing — bookings come only from the
 * declared regime. The driver-departs-first miss is the measured ×6.9 window
 * layer of the realisation gap wearing its physical face; closing it is a
 * replanning question (joint departure times), not a boarding one, and it is
 * reported per iteration rather than papered over.
 */
public final class JointRideEngine implements MobsimEngine, DepartureHandler {

    private static final Logger LOG = LogManager.getLogger(JointRideEngine.class);

    /** The qsim components name this engine registers under. */
    public static final String COMPONENT = "citysimJointRide";

    private final RidePairingEngine pairing;
    private final EventsManager events;

    private InternalInterface internalInterface;
    private QSim qsim;

    /** Passengers currently aboard, in boarding order (determinism). */
    private final Map<MobsimAgent, Riding> riding = new LinkedHashMap<>();

    /** Passengers standing at the meeting point (DECISIONS.md 9.60). */
    private final Map<MobsimAgent, Waiting> waiting = new LinkedHashMap<>();

    private RidePairingConfigGroup cfg;

    private int boarded;
    private int alighted;
    private int missedVehicleGone;
    private int missedVehicleAbsent;
    private int missedFull;
    private int waitBoarded;
    private int waitTimeouts;
    private int abortedAtSimEnd;

    private static final class Riding {
        final MobsimVehicle vehicle;
        final Id<Link> boardedAt;
        final Id<Link> destination;
        boolean underway;

        Riding(final MobsimVehicle vehicle, final Id<Link> boardedAt,
               final Id<Link> destination) {
            this.vehicle = vehicle;
            this.boardedAt = boardedAt;
            this.destination = destination;
        }
    }

    private static final class Waiting {
        final Id<Link> linkId;
        final Id<org.matsim.api.core.v01.population.Person> driver;
        final double deadline;
        final double fallbackTravelTime;
        /** Set on timeout: the Tier-1 clock, counted from the timeout. */
        double arriveAt = Double.NaN;

        Waiting(final Id<Link> linkId,
                final Id<org.matsim.api.core.v01.population.Person> driver,
                final double deadline, final double fallbackTravelTime) {
            this.linkId = linkId;
            this.driver = driver;
            this.deadline = deadline;
            this.fallbackTravelTime = fallbackTravelTime;
        }
    }

    @Inject
    JointRideEngine(final RidePairingEngine pairing, final EventsManager events) {
        this.pairing = pairing;
        this.events = events;
    }

    // ---- DepartureHandler --------------------------------------------------

    @Override
    public boolean handleDeparture(final double now, final MobsimAgent agent,
                                   final Id<Link> linkId) {
        if (!TransportMode.ride.equals(agent.getMode())) {
            return false;
        }
        final RidePairingEngine.Booking booking =
                this.pairing.claimBooking(agent.getId(), linkId, now);
        if (booking == null) {
            return false;                       // unpaired: Tier 1 as before
        }
        // The car vehicle of a person carries the person's own id, bare -
        // measured from the events, where trucks are `<person>_truck` but car
        // vehicles are `<person>` (MATSim suffixes only the non-car modes).
        // The suffixed form is kept as a fallback so an upstream change in
        // that convention degrades to a counted miss, not a wrong boarding.
        final MobsimVehicle vehicle = vehicleOf(booking.driver());
        if (vehicle == null || !linkId.equals(vehicle.getCurrentLinkId())) {
            if (this.cfg != null && this.cfg.isWaitForDriver()) {
                // DECISIONS.md 9.60: the passenger physically WAITS at the
                // meeting point for the booked car, bounded by the same
                // declared window the booking was made under. The fallback
                // travel time is captured now, so a timeout completes the leg
                // on the Tier-1 clock counted from the moment of giving up -
                // waiting costs what waiting costs.
                this.waiting.put(agent, new Waiting(linkId, booking.driver(),
                        now + this.cfg.getWindowMinutes() * 60.0,
                        fallbackTravelTime(agent)));
                return true;
            }
            if (vehicle == null) {
                this.missedVehicleAbsent++;
            } else {
                // the driver has already left (or parks elsewhere): the
                // measured window layer of the realisation gap, physically
                // manifest
                this.missedVehicleGone++;
            }
            return false;
        }
        if (!vehicle.addPassenger((PassengerAgent) agent)) {
            this.missedFull++;
            return false;
        }
        board(now, agent, vehicle, linkId);
        this.boarded++;
        return true;
    }

    private void board(final double now, final MobsimAgent agent,
                       final MobsimVehicle vehicle, final Id<Link> linkId) {
        ((PassengerAgent) agent).setVehicle(vehicle);
        this.events.processEvent(
                new PersonEntersVehicleEvent(now, agent.getId(),
                                             vehicle.getId()));
        this.riding.put(agent, new Riding(vehicle, linkId,
                                          agent.getDestinationLinkId()));
    }

    /** The current ride leg's routed travel time - the Tier-1 clock. */
    private static double fallbackTravelTime(final MobsimAgent agent) {
        if (agent instanceof org.matsim.core.mobsim.framework.PlanAgent) {
            final org.matsim.api.core.v01.population.PlanElement e =
                    ((org.matsim.core.mobsim.framework.PlanAgent) agent)
                            .getCurrentPlanElement();
            if (e instanceof org.matsim.api.core.v01.population.Leg) {
                final org.matsim.api.core.v01.population.Route route =
                        ((org.matsim.api.core.v01.population.Leg) e).getRoute();
                if (route != null
                        && route.getTravelTime().isDefined()) {
                    return route.getTravelTime().seconds();
                }
            }
        }
        return 0.0;
    }

    private MobsimVehicle vehicleOf(
            final Id<org.matsim.api.core.v01.population.Person> driver) {
        MobsimVehicle vehicle = this.qsim.getVehicles().get(
                Id.create(driver.toString(), Vehicle.class));
        if (vehicle == null) {
            vehicle = this.qsim.getVehicles().get(
                    Id.create(driver.toString() + "_" + TransportMode.car,
                              Vehicle.class));
        }
        return vehicle;
    }

    // ---- MobsimEngine ------------------------------------------------------

    @Override
    public void doSimStep(final double now) {
        if (!this.waiting.isEmpty()) {
            serveWaiting(now);
        }
        if (this.riding.isEmpty()) {
            return;
        }
        final List<MobsimAgent> done = new ArrayList<>(0);
        for (final Map.Entry<MobsimAgent, Riding> e : this.riding.entrySet()) {
            final Riding r = e.getValue();
            final Id<Link> at = r.vehicle.getCurrentLinkId();
            if (!r.underway && at != null && !at.equals(r.boardedAt)) {
                r.underway = true;
            }
            if (r.underway && r.destination.equals(at)) {
                done.add(e.getKey());
            }
        }
        for (final MobsimAgent agent : done) {
            final Riding r = this.riding.remove(agent);
            r.vehicle.removePassenger((PassengerAgent) agent);
            ((PassengerAgent) agent).setVehicle(null);
            this.events.processEvent(new PersonLeavesVehicleEvent(
                    now, agent.getId(), r.vehicle.getId()));
            agent.notifyArrivalOnLinkByNonNetworkMode(r.destination);
            agent.endLegAndComputeNextState(now);
            this.internalInterface.arrangeNextAgentState(agent);
            this.alighted++;
        }
    }

    /** Board waiting passengers whose car has arrived; time the rest out. */
    private void serveWaiting(final double now) {
        final List<MobsimAgent> done = new ArrayList<>(0);
        for (final Map.Entry<MobsimAgent, Waiting> e : this.waiting.entrySet()) {
            final Waiting w = e.getValue();
            if (!Double.isNaN(w.arriveAt)) {
                if (now >= w.arriveAt) {
                    done.add(e.getKey());       // timed out earlier; arrive now
                }
                continue;
            }
            final MobsimVehicle vehicle = vehicleOf(w.driver);
            if (vehicle != null && w.linkId.equals(vehicle.getCurrentLinkId())
                    && vehicle.addPassenger((PassengerAgent) e.getKey())) {
                board(now, e.getKey(), vehicle, w.linkId);
                this.waitBoarded++;
                done.add(e.getKey());
                continue;
            }
            if (now >= w.deadline) {
                // give up: Tier-1 completion, clocked from the timeout
                w.arriveAt = now + w.fallbackTravelTime;
                this.waitTimeouts++;
            }
        }
        for (final MobsimAgent agent : done) {
            final Waiting w = this.waiting.remove(agent);
            if (w != null && !Double.isNaN(w.arriveAt)) {
                agent.notifyArrivalOnLinkByNonNetworkMode(
                        agent.getDestinationLinkId());
                agent.endLegAndComputeNextState(now);
                this.internalInterface.arrangeNextAgentState(agent);
            }
        }
    }

    @Override
    public void beforeMobsim() {
        this.riding.clear();
        this.waiting.clear();
        this.boarded = 0;
        this.alighted = 0;
        this.missedVehicleGone = 0;
        this.missedVehicleAbsent = 0;
        this.missedFull = 0;
        this.waitBoarded = 0;
        this.waitTimeouts = 0;
        this.abortedAtSimEnd = 0;
    }

    @Override
    public void afterMobsim() {
        // A passenger still aboard when the mobsim ends is stuck honestly:
        // aborted through the standard path, so the run's stuck accounting
        // sees them (a run whose accounting does not close is not relaxed).
        final double now = this.internalInterface.getMobsim().getSimTimer()
                .getTimeOfDay();
        for (final Iterator<Map.Entry<MobsimAgent, Riding>> it =
             this.riding.entrySet().iterator(); it.hasNext();) {
            final Map.Entry<MobsimAgent, Riding> e = it.next();
            e.getValue().vehicle.removePassenger((PassengerAgent) e.getKey());
            this.events.processEvent(new PersonLeavesVehicleEvent(
                    now, e.getKey().getId(), e.getValue().vehicle.getId()));
            e.getKey().setStateToAbort(now);
            this.internalInterface.arrangeNextAgentState(e.getKey());
            this.abortedAtSimEnd++;
            it.remove();
        }
        // A passenger still waiting at a meeting point at sim end is stuck
        // honestly too, through the same standard path.
        for (final Iterator<Map.Entry<MobsimAgent, Waiting>> it =
             this.waiting.entrySet().iterator(); it.hasNext();) {
            final Map.Entry<MobsimAgent, Waiting> e = it.next();
            e.getKey().setStateToAbort(now);
            this.internalInterface.arrangeNextAgentState(e.getKey());
            this.abortedAtSimEnd++;
            it.remove();
        }
        LOG.info("jointRide: boarded={} alighted={} missed(gone={} absent={} "
                 + "full={}) waited(boarded={} timedOut={}) abortedAtSimEnd={}",
                 this.boarded, this.alighted, this.missedVehicleGone,
                 this.missedVehicleAbsent, this.missedFull,
                 this.waitBoarded, this.waitTimeouts, this.abortedAtSimEnd);
    }

    @Override
    public void setInternalInterface(final InternalInterface internalInterface) {
        this.internalInterface = internalInterface;
        this.qsim = (QSim) internalInterface.getMobsim();
        this.cfg = (RidePairingConfigGroup) this.qsim.getScenario().getConfig()
                .getModules().get(RidePairingConfigGroup.NAME);
    }
}
