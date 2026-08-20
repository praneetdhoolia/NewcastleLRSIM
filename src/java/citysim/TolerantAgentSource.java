package citysim;

import com.google.inject.Inject;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.population.Leg;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Population;
import org.matsim.core.config.groups.QSimConfigGroup;
import org.matsim.core.mobsim.framework.AgentSource;
import org.matsim.core.mobsim.framework.MobsimAgent;
import org.matsim.core.mobsim.qsim.QSim;
import org.matsim.core.mobsim.qsim.agents.AgentFactory;
import org.matsim.core.mobsim.qsim.interfaces.Netsim;
import org.matsim.core.mobsim.qsim.qnetsimengine.QVehicleFactory;
import org.matsim.core.population.routes.NetworkRoute;
import org.matsim.core.router.TripStructureUtils;
import org.matsim.vehicles.Vehicle;
import org.matsim.vehicles.VehicleUtils;

/**
 * The population agent source, tolerant of a main-mode leg whose route is not
 * a network route (DECISIONS.md 9.54).
 *
 * <p>MATSim's own {@code PopulationAgentSource} casts EVERY main-mode leg's
 * route to a {@link NetworkRoute} while parking the mode vehicles — and once
 * {@code walk} is a qsim main mode, that cast dies on the transit router's
 * access/egress and direct-walk legs, which carry mode {@code walk} with a
 * GENERIC route (measured: 9,466 such legs in a 1% day, every one with
 * {@code routingMode=pt}). Those legs are teleported stubs by design and are
 * claimed at departure by {@link GenericRouteTeleporter}; this source simply
 * does not demand a vehicle for them.
 *
 * <p>This is a REIMPLEMENTATION for the one configuration this model
 * declares, and it refuses any other rather than half-supporting it:
 * {@code vehiclesSource=modeVehicleTypesFromVehiclesData}, where
 * PrepareForSim has already created every (person x main mode) vehicle in the
 * scenario. For each person it parks each main mode's vehicle at the mode's
 * first network-routed leg's start link (people with no such leg get the
 * vehicle at their first activity's link, where it stays unused), writes the
 * vehicle id into each network route exactly as the original does, and
 * inserts the agent.
 */
public final class TolerantAgentSource implements AgentSource {

    private final Population population;
    private final AgentFactory agentFactory;
    private final QVehicleFactory qVehicleFactory;
    private final Netsim qsim;

    @Inject
    TolerantAgentSource(final Population population,
                        final AgentFactory agentFactory,
                        final QVehicleFactory qVehicleFactory,
                        final Netsim qsim) {
        this.population = population;
        this.agentFactory = agentFactory;
        this.qVehicleFactory = qVehicleFactory;
        this.qsim = qsim;
        final QSimConfigGroup.VehiclesSource source =
                qsim.getScenario().getConfig().qsim().getVehiclesSource();
        if (source != QSimConfigGroup.VehiclesSource
                .modeVehicleTypesFromVehiclesData) {
            throw new IllegalStateException(
                    "TolerantAgentSource supports exactly the declared "
                    + "qsim.vehiclesSource=modeVehicleTypesFromVehiclesData "
                    + "(RUN.qsim.vehicles_source); got " + source
                    + ". Supporting another source silently would be the "
                    + "right-by-accident defect class.");
        }
    }

    @Override
    public void insertAgentsIntoMobsim() {
        final Set<String> mainModes = new HashSet<>(
                this.qsim.getScenario().getConfig().qsim().getMainModes());
        for (final Person person : this.population.getPersons().values()) {
            final MobsimAgent agent =
                    this.agentFactory.createMobsimAgentFromPerson(person);
            insertVehicles(person, mainModes);
            this.qsim.insertAgentIntoMobsim(agent);
        }
    }

    private void insertVehicles(final Person person, final Set<String> mainModes) {
        final List<Leg> legs =
                TripStructureUtils.getLegs(person.getSelectedPlan());
        final Set<String> parked = new HashSet<>();
        for (final Leg leg : legs) {
            final String mode = leg.getMode();
            if (!mainModes.contains(mode)) {
                continue;
            }
            if (!(leg.getRoute() instanceof NetworkRoute)) {
                // a teleported stub wearing a main-mode name (the transit
                // router's walk legs): no vehicle, no cast, no crash -
                // GenericRouteTeleporter moves it at departure
                continue;
            }
            final NetworkRoute route = (NetworkRoute) leg.getRoute();
            final Id<Vehicle> vehicleId =
                    VehicleUtils.getVehicleId(person, mode);
            route.setVehicleId(vehicleId);
            if (parked.contains(mode)) {
                continue;
            }
            parked.add(mode);
            final Vehicle vehicle = this.qsim.getScenario().getVehicles()
                    .getVehicles().get(vehicleId);
            if (vehicle == null) {
                throw new IllegalStateException(
                        "no vehicle " + vehicleId + " for main mode '" + mode
                        + "' - PrepareForSim creates one per person and mode "
                        + "under modeVehicleTypesFromVehiclesData, so its "
                        + "absence means the vehicles file lost the type");
            }
            ((QSim) this.qsim).addParkedVehicle(
                    this.qVehicleFactory.createQVehicle(vehicle),
                    route.getStartLinkId());
        }
    }
}
