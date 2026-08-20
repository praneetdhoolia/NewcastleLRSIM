package citysim;

import com.google.inject.Inject;
import java.util.Comparator;
import java.util.PriorityQueue;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.network.Link;
import org.matsim.core.mobsim.framework.MobsimAgent;
import org.matsim.core.mobsim.qsim.InternalInterface;
import org.matsim.core.mobsim.qsim.interfaces.DepartureHandler;
import org.matsim.core.mobsim.qsim.interfaces.MobsimEngine;
import org.matsim.core.population.routes.NetworkRoute;
import org.matsim.core.utils.misc.OptionalTime;

/**
 * Teleports the main-mode legs that carry no network route (DECISIONS.md
 * 9.54): the transit router's access/egress and direct-walk legs keep mode
 * {@code walk} with a generic beeline route, and once walk is a qsim main
 * mode the vehicular machinery would otherwise claim and crash on them
 * (measured - the 9.54 probe died in {@code PopulationAgentSource} exactly
 * there). MAIN walk trips carry network routes and never reach this class:
 * it claims a departure only when the leg's route is NOT a network route, so
 * everything physical stays physical.
 *
 * <p>The teleport itself is MATSim's own semantics: arrive at the route's
 * travel time. A generic main-mode leg without a travel time is refused
 * loudly - inventing a duration here would be a silent modelling choice.
 */
public final class GenericRouteTeleporter implements MobsimEngine, DepartureHandler {

    private static final Logger LOG =
            LogManager.getLogger(GenericRouteTeleporter.class);

    /** The qsim components name this engine registers under. */
    public static final String COMPONENT = "citysimGenericRouteTeleporter";

    private InternalInterface internalInterface;

    private static final class Pending {
        final double arrival;
        final MobsimAgent agent;
        final Id<Link> destination;
        final long seq;

        Pending(final double arrival, final MobsimAgent agent,
                final Id<Link> destination, final long seq) {
            this.arrival = arrival;
            this.agent = agent;
            this.destination = destination;
            this.seq = seq;
        }
    }

    /** Ordered by arrival, then insertion order - deterministic. */
    private final PriorityQueue<Pending> queue = new PriorityQueue<>(
            Comparator.<Pending>comparingDouble(p -> p.arrival)
                    .thenComparingLong(p -> p.seq));
    private long seq;
    private int teleported;

    @Inject
    GenericRouteTeleporter() {
    }

    @Override
    public boolean handleDeparture(final double now, final MobsimAgent agent,
                                   final Id<Link> linkId) {
        final org.matsim.core.mobsim.framework.PlanAgent planAgent =
                (org.matsim.core.mobsim.framework.PlanAgent) agent;
        final Object element = planAgent.getCurrentPlanElement();
        if (!(element instanceof org.matsim.api.core.v01.population.Leg)) {
            return false;
        }
        final org.matsim.api.core.v01.population.Leg leg =
                (org.matsim.api.core.v01.population.Leg) element;
        if (leg.getRoute() == null || leg.getRoute() instanceof NetworkRoute) {
            return false;                    // physical - the netsim's business
        }
        if (!this.internalInterface.getMobsim().getScenario().getConfig()
                .qsim().getMainModes().contains(leg.getMode())) {
            return false;                    // the teleportation engine's business
        }
        final OptionalTime time = leg.getRoute().getTravelTime();
        if (!time.isDefined()) {
            throw new IllegalStateException(
                    "generic-route main-mode leg with no travel time for agent "
                    + agent.getId() + " (" + leg.getMode() + "): refusing to "
                    + "invent a duration (DECISIONS.md 9.54)");
        }
        this.queue.add(new Pending(now + time.seconds(), agent,
                                   agent.getDestinationLinkId(), this.seq++));
        return true;
    }

    @Override
    public void doSimStep(final double now) {
        while (!this.queue.isEmpty() && this.queue.peek().arrival <= now) {
            final Pending p = this.queue.poll();
            p.agent.notifyArrivalOnLinkByNonNetworkMode(p.destination);
            p.agent.endLegAndComputeNextState(now);
            this.internalInterface.arrangeNextAgentState(p.agent);
            this.teleported++;
        }
    }

    @Override
    public void beforeMobsim() {
        this.queue.clear();
        this.seq = 0L;
        this.teleported = 0;
    }

    @Override
    public void afterMobsim() {
        int aborted = 0;
        while (!this.queue.isEmpty()) {
            final Pending p = this.queue.poll();
            p.agent.setStateToAbort(this.internalInterface.getMobsim()
                    .getSimTimer().getTimeOfDay());
            this.internalInterface.arrangeNextAgentState(p.agent);
            aborted++;
        }
        LOG.info("genericRouteTeleporter: teleported={} abortedAtSimEnd={}",
                 this.teleported, aborted);
    }

    @Override
    public void setInternalInterface(final InternalInterface internalInterface) {
        this.internalInterface = internalInterface;
    }
}
