package citysim;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Node;
import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.Leg;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.PlanElement;
import org.matsim.core.config.Config;
import org.matsim.core.config.groups.ReplanningConfigGroup.StrategySettings;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.population.PopulationUtils;

/**
 * Pins every activity to a link its person can actually use (DECISIONS.md 9.58).
 *
 * <p>MATSim assigns an activity's link by nearest distance over the whole
 * network, and the router silently starts a leg's route at the nearest link of
 * the LEG's mode when the activity's link does not carry it — while the qsim
 * inserts the vehicle at the ACTIVITY's link. With {@code accessEgressType =
 * none} there is no access leg to bridge the two, so the first hop of the route
 * is a topological break, {@code DefaultTurnAcceptanceLogic} refuses it, and the
 * agent wedges at the junction until the stuck timeout ABORTS it mid-day.
 * Measured on the first all-physical arm (25%): 491,349 refusals over 135
 * iterations — 478,360 walk and 12,989 bike — from ~11.6k broken legs per
 * iteration; 6.8% of activities sat on links carrying no walk.
 *
 * <p>The rule: an activity's link must carry every network mode its person can
 * put on an adjacent leg. That set is derived from the run's own config, not
 * declared anew: the person's existing leg modes, plus — for a subpopulation
 * whose strategy settings include SubtourModeChoice — everything mode innovation
 * could choose ({@code subtourModeChoice.modes ∩ routing.networkModes}). A
 * boundary agent whose modes are locked (external, freight — 9.58 withholds
 * SubtourModeChoice from both) therefore keeps its cordon gate link: its
 * needed set is exactly the mode it arrived with, which the gate link carries.
 *
 * <p>Runs once, on the loaded scenario, before the Controler exists — so
 * PrepareForSim's own XY2Links finds every activity already linked and assigns
 * nothing. Deterministic: nearest-link per MATSim's own quadtree over a
 * subnetwork built in file order. An activity without a coordinate keeps
 * whatever link it has; interaction activities do not exist at load time.
 */
final class ActivityLinkAssigner {

    private static final Logger LOG =
            LogManager.getLogger(ActivityLinkAssigner.class);

    private ActivityLinkAssigner() {
    }

    static void run(final Scenario scenario) {
        final Config config = scenario.getConfig();
        final Set<String> networkModes =
                new HashSet<>(config.routing().getNetworkModes());
        final Set<String> choiceModes = new HashSet<>(
                Arrays.asList(config.subtourModeChoice().getModes()));
        choiceModes.retainAll(networkModes);
        final Set<String> innovating = new HashSet<>();
        for (final StrategySettings s
                : config.replanning().getStrategySettings()) {
            if ("SubtourModeChoice".equals(s.getStrategyName())) {
                innovating.add(s.getSubpopulation());
            }
        }
        final Set<String> transitModes =
                new HashSet<>(config.transit().getTransitModes());

        final Map<Set<String>, Network> subnetOf = new HashMap<>();
        long kept = 0;
        long reassigned = 0;
        long assigned = 0;
        long coordless = 0;
        for (final Person person
                : scenario.getPopulation().getPersons().values()) {
            final Set<String> needed = new TreeSet<>();
            for (final Plan plan : person.getPlans()) {
                for (final PlanElement e : plan.getPlanElements()) {
                    if (e instanceof Leg) {
                        final String mode = ((Leg) e).getMode();
                        if (networkModes.contains(mode)) {
                            needed.add(mode);
                        } else if (transitModes.contains(mode)
                                && networkModes.contains(
                                        org.matsim.api.core.v01
                                                .TransportMode.walk)) {
                            // A transit trip the raptor cannot serve falls
                            // back to a NETWORK walk leg from this activity
                            // (measured: three external pt commuters at
                            // motorway gate links wedged exactly here), so a
                            // person with transit legs can always be handed
                            // walk.
                            needed.add(org.matsim.api.core.v01
                                    .TransportMode.walk);
                        }
                    }
                }
            }
            if (innovating.contains(PopulationUtils.getSubpopulation(person))) {
                needed.addAll(choiceModes);
            }
            if (needed.isEmpty()) {
                continue;
            }
            final Network subnet = subnetOf.computeIfAbsent(
                    new HashSet<>(needed),
                    modes -> subnetwork(scenario.getNetwork(), modes));
            for (final Plan plan : person.getPlans()) {
                for (final PlanElement e : plan.getPlanElements()) {
                    if (!(e instanceof Activity)) {
                        continue;
                    }
                    final Activity act = (Activity) e;
                    if (act.getLinkId() != null) {
                        final Link current = scenario.getNetwork().getLinks()
                                .get(act.getLinkId());
                        if (current != null
                                && current.getAllowedModes().containsAll(needed)) {
                            kept++;
                            continue;
                        }
                    }
                    final Coord coord = act.getCoord();
                    if (coord == null) {
                        coordless++;
                        continue;
                    }
                    final Link nearest = NetworkUtils.getNearestLink(subnet, coord);
                    if (nearest == null) {
                        throw new IllegalStateException(
                                "no link carries all of " + needed
                                + " - the network cannot host person "
                                + person.getId());
                    }
                    if (nearest.getId().equals(act.getLinkId())) {
                        kept++;
                    } else if (act.getLinkId() == null) {
                        assigned++;
                        act.setLinkId(nearest.getId());
                    } else {
                        reassigned++;
                        act.setLinkId(nearest.getId());
                    }
                }
            }
        }
        LOG.info("activityLinkAssigner: {} kept, {} newly assigned, {} moved "
                 + "off a link missing a usable mode, {} without coordinates "
                 + "left untouched (DECISIONS.md 9.58)",
                 kept, assigned, reassigned, coordless);
    }

    /** Links carrying ALL of {@code modes}, with their nodes, in file order. */
    private static Network subnetwork(final Network full,
                                      final Set<String> modes) {
        final Network out = NetworkUtils.createNetwork();
        final List<Link> links = new ArrayList<>(full.getLinks().values());
        for (final Link link : links) {
            if (!link.getAllowedModes().containsAll(modes)) {
                continue;
            }
            for (final Node n
                    : new Node[] {link.getFromNode(), link.getToNode()}) {
                if (!out.getNodes().containsKey(n.getId())) {
                    out.addNode(out.getFactory()
                            .createNode(n.getId(), n.getCoord()));
                }
            }
            final Link copy = out.getFactory().createLink(link.getId(),
                    out.getNodes().get(link.getFromNode().getId()),
                    out.getNodes().get(link.getToNode().getId()));
            copy.setAllowedModes(link.getAllowedModes());
            copy.setLength(link.getLength());
            out.addLink(copy);
        }
        if (out.getLinks().isEmpty()) {
            throw new IllegalStateException(
                    "no link in the network carries all of " + modes);
        }
        return out;
    }
}
