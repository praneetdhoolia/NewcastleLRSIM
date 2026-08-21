package citysim;

import com.google.inject.Inject;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.events.PersonArrivalEvent;
import org.matsim.api.core.v01.events.PersonDepartureEvent;
import org.matsim.api.core.v01.events.handler.PersonArrivalEventHandler;
import org.matsim.api.core.v01.events.handler.PersonDepartureEventHandler;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.Leg;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.PlanElement;
import org.matsim.api.core.v01.population.Route;
import org.matsim.core.controler.OutputDirectoryHierarchy;
import org.matsim.core.controler.events.BeforeMobsimEvent;
import org.matsim.core.controler.listener.BeforeMobsimListener;
import org.matsim.core.router.StageActivityTypeIdentifier;
import org.matsim.core.utils.misc.OptionalTime;

/**
 * Tier 1 of the ride pairing: a car passenger NAMES a household driver, and
 * takes that driver's realised travel time instead of their own routed one.
 *
 * <h2>Why a lookup and not joint plans</h2>
 *
 * <p>What makes boarding a bus cheap in MATSim is that the timetable is fixed
 * before routing, so the passenger does a lookup rather than a search. A
 * household car can work the same way: a passenger leg only ever needs to NAME
 * a driver, and the candidate set is the household — never more than nine
 * people, ~1.5 licensed adults on average. A full socnetsim joint-plans
 * implementation was built against this scenario and measured at roughly ten
 * times the cost of the whole mobsim, all of it inside
 * {@code CourtesyEventsGenerator}'s joint-ACTIVITY machinery, which answers a
 * different research question. It was reverted by owner instruction; this class
 * is what replaced it (DECISIONS.md 9.44).
 *
 * <h2>Where the pairing happens, and why that is sound</h2>
 *
 * <p>MATSim's loop is {@code replan -> all plans final -> mobsim}. At
 * {@link BeforeMobsimListener} every selected plan is stable and nothing will
 * move until the mobsim runs. THAT is our timetable. A pairing made there is
 * valid for that iteration and re-made the next, exactly as a public-transport
 * connection is re-found on every re-route.
 *
 * <p>This dissolves the objection that sent the previous attempt to socnetsim: a
 * pairing baked into PLANS is destroyed by {@code SubtourModeChoice}, which
 * carries `ride` in its mode list; a pairing made AFTER replanning is not.
 *
 * <h2>How a passenger takes the driver's time without a mobsim change</h2>
 *
 * <p>`ride` is in {@code routing.networkModes} but is not the qsim
 * {@code mainMode}, so MATSim routes it over the network and then TELEPORTS it.
 * {@code DefaultTeleportationEngine.handleDeparture} asks the agent for
 * {@code getExpectedTravelTime()}, which is
 * {@code TimeInterpretation.decideOnLegTravelTime(leg)}, which is exactly
 * {@code route.getTravelTime().or(leg.getTravelTime())} — verified against the
 * pinned jar's bytecode, not assumed from the API.
 *
 * <p>The ROUTE's time therefore wins, and both routing modules
 * ({@code NetworkRoutingModule}, {@code NetworkRoutingInclAccessEgressModule})
 * set the leg's and the route's time TOGETHER. So this class writes only the
 * ROUTE's time and never the leg's. That single choice buys three things at
 * once and needs no bookkeeping of its own:
 *
 * <ul>
 *   <li>the router's own estimate survives untouched in
 *       {@code leg.getTravelTime()}, so it is the baseline;</li>
 *   <li>an UNPAIRED leg is restored to exactly that baseline, which is the
 *       guarantee that an unpaired leg behaves exactly as it does today;</li>
 *   <li>the baseline refreshes itself whenever the router re-routes the leg,
 *       and survives the plan-copying that replanning does, because it lives in
 *       the plan rather than in a side map.</li>
 * </ul>
 *
 * <p>Note what this deliberately does NOT do. It does not put a passenger
 * vehicle in the mobsim: a passenger travels in a car that is already there, so
 * a second vehicle would double-count the traffic. It does not move the
 * passenger's departure time, which would cascade through the rest of that
 * person's day; the pairing window is a tolerance, and the sub-window
 * adjustment is a STATED limitation. Binding the passenger physically into the
 * vehicle, with seats constraining flow, is Tier 2 and an increment on this,
 * not a prerequisite for it.
 *
 * <h2>The driver's realised time</h2>
 *
 * <p>Realised means realised in the mobsim, which is where the sample-dependent
 * queueing lives that a teleported passenger is structurally immune to — the
 * mechanism behind the fraction-dependent car/ride margin the convergence
 * pilots flagged and could not explain. It is necessarily the PREVIOUS
 * iteration's realisation, because at BeforeMobsim the current one has not
 * happened; that is the same one-iteration lag every travel time in MATSim
 * carries. Before the first mobsim, and for a driver leg with no realised
 * counterpart, the driver's own routed time is used instead and the fallback is
 * counted in the diagnostic.
 *
 * <h2>What it reports, and why the report is the point</h2>
 *
 * <p>The unpaired share, SPLIT BY DIRECTION, is written every iteration to
 * {@code ride_pairing.csv}. Return trips pair INDEPENDENTLY of outbound ones —
 * `ride` is correctly not a chain-based mode, a passenger owns no vehicle to
 * bring home, and forcing symmetry would MANUFACTURE car trips, which is the
 * direction of error this project is most exposed to. The obligation that
 * creates is to report the asymmetry rather than to remove it: a large unpaired
 * share is a finding about the DEMAND, not about this class.
 */
public final class RidePairingEngine implements BeforeMobsimListener,
        PersonDepartureEventHandler, PersonArrivalEventHandler {

    /** Person attribute written by build_matsim_plans.py; absent on the
     *  household-less external and through boundary tiers. */
    public static final String HOUSEHOLD_ATTRIBUTE = "householdId";
    /** Person attribute written by build_matsim_plans.py from the B2
     *  non-household lift bindings (DECISIONS.md 9.60): the household id of
     *  the DRIVER whose re-targeted escort tour serves this person, so the
     *  pairing may search that household's car legs in addition to the
     *  person's own. The binding is an eligibility, not a guarantee - the
     *  driver's leg must still match under the declared rule and window. */
    public static final String LIFT_HOUSEHOLD_ATTRIBUTE = "liftHousehold";
    /** Written by build_matsim_plans.py, and already consumed by
     *  {@link AvailabilityModesCalculator}'s sibling attributes. */
    public static final String LICENCE_ATTRIBUTE = "hasLicense";
    public static final String LICENCE_YES = "yes";

    private static final String OUT_FILE = "ride_pairing.csv";
    private static final String HEADER =
            "iteration,ride_legs,paired,unpaired,pair_rate,"
            + "paired_outbound,paired_return,paired_intermediate,"
            + "unpaired_outbound,unpaired_return,unpaired_intermediate,"
            + "total_outbound,total_return,total_intermediate,"
            + "car_legs,occupancy_from_pairings,"
            + "driver_time_realised,driver_time_routed,"
            + "mean_driver_minus_baseline_s,capacity_refusals,"
            + "households_with_ride,ride_legs_no_household,elapsed_ms\n";

    private final Scenario scenario;
    private final OutputDirectoryHierarchy io;
    private final RidePairingConfigGroup cfg;

    /** Household id per person, resolved once: membership never changes. */
    private final Map<Id<Person>, String> household = new HashMap<>();
    /** Lift-driver household per bound passenger (9.60), resolved once. */
    private final Map<Id<Person>, String> liftHousehold = new HashMap<>();
    /** Licence holding per person, resolved once, for the same reason. */
    private final Map<Id<Person>, Boolean> licensed = new HashMap<>();
    private boolean indexed = false;
    /** Population membership does not change during a run, so the id-ordered
     *  traversal that makes the pairing deterministic is built once. */
    private List<Person> ordered = null;

    /** Realised car-leg durations from the mobsim that is running now. */
    /**
     * This iteration's physical-boarding bookings (DECISIONS.md 9.53): for a
     * paired ride, which driver's vehicle the passenger should be aboard.
     * Written here at BeforeMobsim, consumed by {@link JointRideEngine} on the
     * qsim thread after this listener has finished — never concurrently.
     */
    private final Map<Id<Person>, List<Booking>> bookings = new HashMap<>();

    /** One paired ride leg's claim on a driver's vehicle. */
    public static final class Booking {
        final Id<Link> from;
        final Id<Link> to;
        final double plannedDeparture;
        final Id<Person> driver;

        Booking(final Id<Link> from, final Id<Link> to,
                final double plannedDeparture, final Id<Person> driver) {
            this.from = from;
            this.to = to;
            this.plannedDeparture = plannedDeparture;
            this.driver = driver;
        }

        public Id<Link> destination() {
            return this.to;
        }

        public Id<Person> driver() {
            return this.driver;
        }
    }

    /**
     * The booking for this passenger departing this link now, or null. The
     * booking is CONSUMED: a person with two paired ride legs from the same
     * link holds two bookings, each redeemable once, nearest planned
     * departure first.
     */
    public Booking claimBooking(final Id<Person> person, final Id<Link> link,
                                final double now) {
        final List<Booking> list = this.bookings.get(person);
        if (list == null) {
            return null;
        }
        Booking best = null;
        for (final Booking b : list) {
            if (!b.from.equals(link)) {
                continue;
            }
            if (best == null || Math.abs(b.plannedDeparture - now)
                    < Math.abs(best.plannedDeparture - now)) {
                best = b;
            }
        }
        if (best != null) {
            list.remove(best);
        }
        return best;
    }

    private Map<Id<Person>, List<Realised>> current = new HashMap<>();
    /** ... and from the one that has finished, which is what pairing reads. */
    private Map<Id<Person>, List<Realised>> previous = new HashMap<>();
    /** Car legs in flight, one per person at a time. */
    private final Map<Id<Person>, Realised> inFlight = new HashMap<>();

    private boolean headerWritten = false;
    private int writeFailures = 0;

    /** One realised car leg: where it ran, when it left, how long it took. */
    private static final class Realised {
        private final Id<Link> from;
        private Id<Link> to;
        private final double departure;
        private double duration = Double.NaN;

        Realised(final Id<Link> from, final double departure) {
            this.from = from;
            this.departure = departure;
        }
    }

    /** One candidate driver leg, taken from a selected plan. */
    private static final class DriverLeg {
        private final Id<Person> person;
        private final Id<Link> from;
        private final Id<Link> to;
        private final double departure;
        private final double routedTravelTime;
        private int carrying = 0;

        DriverLeg(final Id<Person> person, final Id<Link> from, final Id<Link> to,
                  final double departure, final double routedTravelTime) {
            this.person = person;
            this.from = from;
            this.to = to;
            this.departure = departure;
            this.routedTravelTime = routedTravelTime;
        }
    }

    /** One ride leg awaiting a driver, with the plan handles needed to retime it. */
    private static final class RideLeg {
        private final Id<Person> person;
        private final Leg leg;
        private final Route route;
        private final Id<Link> from;
        private final Id<Link> to;
        private final double departure;
        private final String direction;

        RideLeg(final Id<Person> person, final Leg leg, final Route route,
                final Id<Link> from, final Id<Link> to, final double departure,
                final String direction) {
            this.person = person;
            this.leg = leg;
            this.route = route;
            this.from = from;
            this.to = to;
            this.departure = departure;
            this.direction = direction;
        }
    }

    @Inject
    RidePairingEngine(final Scenario scenario, final OutputDirectoryHierarchy io) {
        this.scenario = scenario;
        this.io = io;
        this.cfg = (RidePairingConfigGroup) scenario.getConfig().getModules()
                .get(RidePairingConfigGroup.NAME);
    }

    // ---- the mobsim's own record of what actually happened ----------------

    @Override
    public void handleEvent(final PersonDepartureEvent event) {
        if (!enabled() || !TransportMode.car.equals(event.getLegMode())) {
            return;
        }
        inFlight.put(event.getPersonId(),
                     new Realised(event.getLinkId(), event.getTime()));
    }

    @Override
    public void handleEvent(final PersonArrivalEvent event) {
        if (!enabled() || !TransportMode.car.equals(event.getLegMode())) {
            return;
        }
        final Realised r = inFlight.remove(event.getPersonId());
        if (r == null) {
            return;
        }
        r.to = event.getLinkId();
        r.duration = event.getTime() - r.departure;
        current.computeIfAbsent(event.getPersonId(), k -> new ArrayList<>(2)).add(r);
    }

    /**
     * Deliberately NOT overriding {@code reset(int)}.
     *
     * <p>MATSim resets event handlers immediately before the mobsim, which is
     * AFTER {@link #notifyBeforeMobsim} — so a reset that cleared the realised
     * times would clear exactly the data the pairing had just been about to
     * read, and would do it silently. The buffers are swapped explicitly in
     * {@link #notifyBeforeMobsim} instead, where the ordering is visible.
     */

    // ---- the pairing ------------------------------------------------------

    @Override
    public void notifyBeforeMobsim(final BeforeMobsimEvent event) {
        if (!enabled()) {
            return;
        }
        final long started = System.currentTimeMillis();
        // The mobsim that is about to run fills `current`; the one that has
        // finished is what the pairing may read. Swapping here, rather than in
        // reset(), is what makes the ordering auditable.
        previous = current;
        current = new HashMap<>();
        inFlight.clear();
        bookings.clear();

        index();

        final double window = cfg.getWindowMinutes() * 60.0;
        final String rule = cfg.getRule();
        final int capacity = cfg.getMaxPassengersPerVehicle();
        final double dwell = cfg.getPickupDwellSeconds();

        final Map<String, List<DriverLeg>> driversByHousehold = new HashMap<>();
        final List<RideLeg> rides = new ArrayList<>();
        int carLegs = 0;
        int noHousehold = 0;

        // Persons in id order, so the pairing does not depend on map iteration
        // order. Determinism is a hard constraint here, not a nicety: the same
        // seed must produce the same run.
        for (final Person person : ordered) {
            final Plan plan = person.getSelectedPlan();
            if (plan == null) {
                continue;
            }
            final String hh = household.get(person.getId());
            final List<PlanElement> elements = plan.getPlanElements();
            double clock = Double.NaN;
            String previousActivity = null;
            for (int i = 0; i < elements.size(); i++) {
                final PlanElement pe = elements.get(i);
                if (pe instanceof Activity) {
                    final Activity act = (Activity) pe;
                    final OptionalTime end = act.getEndTime();
                    if (end.isDefined()) {
                        clock = end.seconds();
                    }
                    // A ride trip under routing.accessEgressType is
                    // walk -> `ride interaction` -> ride -> `ride interaction`
                    // -> walk, so the activity ADJACENT to the ride leg is a
                    // stage activity, never the real one. Reading it as the
                    // real one classified every leg `intermediate` and made the
                    // direction split - the whole obligation this diagnostic
                    // carries - silently all-zero.
                    if (!StageActivityTypeIdentifier.isStageActivity(act.getType())) {
                        previousActivity = act.getType();
                    }
                    continue;
                }
                final Leg leg = (Leg) pe;
                final double departure = legDeparture(leg, clock);
                final double travel = definedOr(leg.getTravelTime(), 0.0);
                if (!Double.isNaN(clock)) {
                    clock = departure + travel;
                }
                final Route route = leg.getRoute();
                if (route == null) {
                    continue;
                }
                if (TransportMode.car.equals(leg.getMode())) {
                    carLegs++;
                    if (hh != null && Boolean.TRUE.equals(licensed.get(person.getId()))) {
                        driversByHousehold
                                .computeIfAbsent(hh, k -> new ArrayList<>(2))
                                .add(new DriverLeg(person.getId(),
                                                   route.getStartLinkId(),
                                                   route.getEndLinkId(),
                                                   departure, travel));
                    }
                } else if (TransportMode.ride.equals(leg.getMode())) {
                    if (hh == null) {
                        // An external or through boundary agent has no household
                        // by construction, so it can never pair. It keeps
                        // today's behaviour and is counted, not hidden.
                        noHousehold++;
                        restore(leg, route);
                        continue;
                    }
                    rides.add(new RideLeg(person.getId(), leg, route,
                                          route.getStartLinkId(),
                                          route.getEndLinkId(), departure,
                                          direction(previousActivity,
                                                    nextActivity(elements, i))));
                }
            }
        }

        // Candidate order must be deterministic too. Person id, then departure.
        for (final List<DriverLeg> legs : driversByHousehold.values()) {
            legs.sort(Comparator.<DriverLeg, Id<Person>>comparing(d -> d.person)
                              .thenComparingDouble(d -> d.departure));
        }
        rides.sort(Comparator.<RideLeg, Id<Person>>comparing(r -> r.person)
                           .thenComparingDouble(r -> r.departure));

        final Map<String, int[]> paired = new HashMap<>();
        final Map<String, int[]> unpaired = new HashMap<>();
        int nPaired = 0;
        int remoded = 0;
        int fromRealised = 0;
        int fromRouted = 0;
        int capacityRefusals = 0;
        double deltaSum = 0.0;

        for (final RideLeg ride : rides) {
            List<DriverLeg> candidates =
                    driversByHousehold.getOrDefault(household.get(ride.person),
                                                    Collections.emptyList());
            // DECISIONS.md 9.60: a bound lift widens the search to the
            // driver's household - own household first, so the binding can
            // never displace an intra-household pairing at equal gap.
            final String lift = liftHousehold.get(ride.person);
            if (lift != null) {
                final List<DriverLeg> liftCandidates = driversByHousehold
                        .getOrDefault(lift, Collections.emptyList());
                if (!liftCandidates.isEmpty()) {
                    final List<DriverLeg> merged = new ArrayList<>(
                            candidates.size() + liftCandidates.size());
                    merged.addAll(candidates);
                    merged.addAll(liftCandidates);
                    candidates = merged;
                }
            }
            DriverLeg best = null;
            double bestGap = Double.MAX_VALUE;
            boolean refusedForCapacity = false;
            for (final DriverLeg driver : candidates) {
                if (driver.person.equals(ride.person)) {
                    continue;                       // you cannot drive yourself
                }
                final double gap = Math.abs(driver.departure - ride.departure);
                if (gap > window) {
                    continue;
                }
                if (!endpointsMatch(rule, driver, ride)) {
                    continue;
                }
                if (driver.carrying >= capacity) {
                    refusedForCapacity = true;
                    continue;
                }
                if (gap < bestGap) {
                    bestGap = gap;
                    best = driver;
                }
            }
            if (best == null) {
                if (refusedForCapacity) {
                    capacityRefusals++;
                }
                unpaired.computeIfAbsent(ride.direction, k -> new int[1])[0]++;
                if (cfg.isPhysicalBoarding() && cfg.isRemodeUnpaired()) {
                    // DECISIONS.md 9.55: a ride trip no household driver can
                    // physically serve is not a ride trip - it WALKS, on the
                    // network, this iteration (the car route's links are
                    // traversed at walking speed; ReRoute re-routes it as
                    // walk next innovation). A long forced walk scores
                    // terribly, so co-evolution reassigns the tour, and ride
                    // becomes emergent: only what the driver supply carries
                    // survives. No parameter invented; the constraint is the
                    // price.
                    ride.leg.setMode(TransportMode.walk);
                    org.matsim.core.router.TripStructureUtils.setRoutingMode(
                            ride.leg, TransportMode.walk);
                    // the car route may traverse walk-excluded links, and
                    // PersonPrepareForSim refuses a route inconsistent with
                    // link modes (measured). A null route makes it re-route
                    // the leg as WALK on the walk network before the mobsim -
                    // properly walked from its first iteration.
                    ride.leg.setRoute(null);
                    remoded++;
                    continue;
                }
                restore(ride.leg, ride.route);
                continue;
            }
            best.carrying++;
            nPaired++;
            paired.computeIfAbsent(ride.direction, k -> new int[1])[0]++;

            final double realised = realisedDuration(best);
            final double driverTime;
            if (Double.isNaN(realised)) {
                driverTime = best.routedTravelTime;
                fromRouted++;
            } else {
                driverTime = realised;
                fromRealised++;
            }
            final double baseline = definedOr(ride.leg.getTravelTime(),
                                              definedOr(ride.route.getTravelTime(), 0.0));
            deltaSum += driverTime - baseline;
            // ONLY the route's travel time is written. The leg keeps the
            // router's own estimate, which is what makes an unpaired leg
            // restorable to exactly today's behaviour.
            ride.route.setTravelTime(driverTime + dwell);
            if (cfg.isPhysicalBoarding()) {
                // The booking JointRideEngine redeems at the qsim's own
                // departure (DECISIONS.md 9.53). The route time written above
                // stays: it is exactly what a MISSED boarding falls back to,
                // so the fallback is Tier 1 verbatim rather than a third
                // behaviour.
                bookings.computeIfAbsent(ride.person, k -> new ArrayList<>(2))
                        .add(new Booking(ride.from, ride.to, ride.departure,
                                         best.person));
            }
        }

        write(event.getIteration(), rides.size(), nPaired, paired, unpaired,
              carLegs, fromRealised, fromRouted,
              nPaired == 0 ? 0.0 : deltaSum / nPaired, capacityRefusals,
              driversByHousehold.size(), noHousehold,
              System.currentTimeMillis() - started);
        if (cfg.isPhysicalBoarding() && cfg.isRemodeUnpaired()) {
            org.apache.logging.log4j.LogManager.getLogger(RidePairingEngine.class)
                    .info("ridePairing: {} unpaired ride legs re-moded to "
                          + "network walk (DECISIONS.md 9.55)", remoded);
        }
    }

    // ---- the rules --------------------------------------------------------

    private static boolean endpointsMatch(final String rule, final DriverLeg driver,
                                          final RideLeg ride) {
        switch (rule) {
            case RidePairingConfigGroup.RULE_BOTH_LINKS:
                return equalId(driver.from, ride.from) && equalId(driver.to, ride.to);
            case RidePairingConfigGroup.RULE_ORIGIN_LINK:
                return equalId(driver.from, ride.from);
            case RidePairingConfigGroup.RULE_DEST_LINK:
                return equalId(driver.to, ride.to);
            case RidePairingConfigGroup.RULE_WINDOW_ONLY:
                return true;
            default:
                // checkConsistency has already refused anything else; reaching
                // here would mean the config group was bypassed.
                throw new IllegalStateException("unknown ridePairing.rule " + rule);
        }
    }

    private static boolean equalId(final Id<Link> a, final Id<Link> b) {
        return a != null && a.equals(b);
    }

    /**
     * The driver's realised duration for THIS leg, or NaN if the last mobsim
     * holds no counterpart for it.
     *
     * <p>Matched on the driver's own endpoints and then on the closest
     * departure, because a person may run the same origin-destination pair more
     * than once in a day and the two realisations differ by exactly the
     * congestion this class exists to transmit.
     */
    private double realisedDuration(final DriverLeg driver) {
        final List<Realised> done = previous.get(driver.person);
        if (done == null) {
            return Double.NaN;
        }
        double best = Double.NaN;
        double bestGap = Double.MAX_VALUE;
        for (final Realised r : done) {
            if (!equalId(r.from, driver.from) || !equalId(r.to, driver.to)) {
                continue;
            }
            final double gap = Math.abs(r.departure - driver.departure);
            if (gap < bestGap) {
                bestGap = gap;
                best = r.duration;
            }
        }
        return best;
    }

    /**
     * A ride leg's direction, which is what the unpaired share must be split by.
     *
     * <p>Outbound leaves home, return arrives home, and anything else is an
     * intermediate leg of a tour. Nothing about this is a place: `home` is an
     * activity type the demand builder writes, and any city has one.
     */
    private static String direction(final String before, final String after) {
        if ("home".equals(before)) {
            return "outbound";
        }
        if ("home".equals(after)) {
            return "return";
        }
        return "intermediate";
    }

    /** The next REAL activity, stepping over the router's stage activities. */
    private static String nextActivity(final List<PlanElement> elements, final int at) {
        for (int i = at + 1; i < elements.size(); i++) {
            if (elements.get(i) instanceof Activity) {
                final String type = ((Activity) elements.get(i)).getType();
                if (!StageActivityTypeIdentifier.isStageActivity(type)) {
                    return type;
                }
            }
        }
        return null;
    }

    /** Give an unpaired leg back the router's own estimate — today's behaviour. */
    private static void restore(final Leg leg, final Route route) {
        final OptionalTime baseline = leg.getTravelTime();
        if (baseline.isDefined()) {
            route.setTravelTime(baseline.seconds());
        }
    }

    private static double legDeparture(final Leg leg, final double clock) {
        final OptionalTime declared = leg.getDepartureTime();
        if (declared.isDefined()) {
            return declared.seconds();
        }
        return Double.isNaN(clock) ? 0.0 : clock;
    }

    private static double definedOr(final OptionalTime t, final double fallback) {
        return t != null && t.isDefined() ? t.seconds() : fallback;
    }

    private boolean enabled() {
        return cfg != null && cfg.isEnabled();
    }

    /** Household and licence are properties of the person, not of the iteration. */
    private void index() {
        if (indexed) {
            return;
        }
        for (final Person person : scenario.getPopulation().getPersons().values()) {
            final Object hh = person.getAttributes().getAttribute(HOUSEHOLD_ATTRIBUTE);
            if (hh != null) {
                household.put(person.getId(), hh.toString());
            }
            final Object lift = person.getAttributes()
                    .getAttribute(LIFT_HOUSEHOLD_ATTRIBUTE);
            if (lift != null) {
                liftHousehold.put(person.getId(), lift.toString());
            }
            final Object lic = person.getAttributes().getAttribute(LICENCE_ATTRIBUTE);
            licensed.put(person.getId(), lic != null && LICENCE_YES.equals(lic.toString()));
        }
        ordered = new ArrayList<>(scenario.getPopulation().getPersons().values());
        ordered.sort(Comparator.comparing(Person::getId));
        indexed = true;
    }

    // ---- the diagnostic ---------------------------------------------------

    private void write(final int iteration, final int rideLegs, final int nPaired,
                       final Map<String, int[]> paired, final Map<String, int[]> unpaired,
                       final int carLegs, final int fromRealised, final int fromRouted,
                       final double meanDelta, final int capacityRefusals,
                       final int households, final int noHousehold,
                       final long elapsedMs) {
        final StringBuilder b = new StringBuilder(256);
        if (!headerWritten) {
            b.append(HEADER);
            headerWritten = true;
        }
        b.append(iteration).append(',').append(rideLegs).append(',').append(nPaired)
                .append(',').append(rideLegs - nPaired).append(',')
                .append(rate(nPaired, rideLegs)).append(',')
                .append(count(paired, "outbound")).append(',')
                .append(count(paired, "return")).append(',')
                .append(count(paired, "intermediate")).append(',')
                .append(count(unpaired, "outbound")).append(',')
                .append(count(unpaired, "return")).append(',')
                .append(count(unpaired, "intermediate")).append(',')
                .append(count(paired, "outbound") + count(unpaired, "outbound")).append(',')
                .append(count(paired, "return") + count(unpaired, "return")).append(',')
                .append(count(paired, "intermediate") + count(unpaired, "intermediate"))
                .append(',').append(carLegs).append(',')
                .append(rate(nPaired, carLegs)).append(',')
                .append(fromRealised).append(',').append(fromRouted).append(',')
                .append(String.format(java.util.Locale.ROOT, "%.3f", meanDelta))
                .append(',').append(capacityRefusals).append(',').append(households)
                .append(',').append(noHousehold).append(',').append(elapsedMs)
                .append('\n');
        try {
            Files.write(Paths.get(io.getOutputFilename(OUT_FILE)),
                        b.toString().getBytes(StandardCharsets.UTF_8),
                        java.nio.file.StandardOpenOption.CREATE,
                        java.nio.file.StandardOpenOption.APPEND);
        } catch (final IOException e) {
            // An observer may never stop a run.
            writeFailures++;
        }
    }

    private static int count(final Map<String, int[]> m, final String key) {
        final int[] v = m.get(key);
        return v == null ? 0 : v[0];
    }

    private static String rate(final int n, final int of) {
        return of == 0 ? "0.0000"
                : String.format(java.util.Locale.ROOT, "%.4f", (double) n / of);
    }

    int getWriteFailures() {
        return writeFailures;
    }
}
