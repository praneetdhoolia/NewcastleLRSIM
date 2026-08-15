package citysim;

import com.google.inject.Inject;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Person;
import org.matsim.core.config.Config;
import org.matsim.core.population.algorithms.PermissibleModesCalculator;
import org.matsim.core.population.algorithms.PermissibleModesCalculatorImpl;

/**
 * Per-person mode availability, from attributes the plans builder derives or
 * declares. Successor to {@code RideAvailabilityModesCalculator}, which handled
 * `ride` alone.
 *
 * <p><b>`rideAvail`</b> (derived): MATSim's standard treatment lets any agent
 * become a car passenger on any trip. DECISIONS.md 9.7 and 9.10 measure what
 * that costs here: `ride` reaches 0.72 of legs against an observed 0.206,
 * putting 5.9 people in every car. A person may ride only if their B1 household
 * holds a vehicle AND contains another licence holder.
 *
 * <p><b>`bikeAvail`</b> (assumed, {@code B.population.bike_available_rate},
 * swept): until this existed, car was the only mode whose ownership was
 * modelled while bike was silently available to everyone — a structural bias
 * against car in the choice set itself, undeclared anywhere (issue #29,
 * DECISIONS.md 9.39).
 *
 * <p><b>`lockedMode`</b> (declared per agent tier): an agent whose demand is
 * anchored on an observed quantity of a specific mode — a through-traffic
 * vehicle seeded from a cordon road count (issue #20, DECISIONS.md 9.41) — must
 * not be handed a different mode by replanning, or the anchoring quantity
 * silently leaks. For such an agent the permissible set is the locked mode
 * alone.
 *
 * <p>Core MATSim can restrict `car` per person, through the `carAvail`
 * attribute honoured by {@link PermissibleModesCalculatorImpl}, but has no
 * equivalent for the others, and `subtourModeChoice.modes` is global. Absent
 * attributes mean available, so this class is inert on a population that does
 * not carry them.
 *
 * <p><b>What this does not do.</b> It makes a mode available or not for a
 * person. It does NOT bind a passenger to a specific driver on a specific trip
 * at a specific time, so the model can still produce more passengers than there
 * are drivers to carry them at any given hour. That is what the socnetsim joint
 * plans contrib does (Dubernet and Axhausen), which is absent from the pinned
 * jar and out of scope. The residual is stated rather than hidden (issue #31).
 */
public final class AvailabilityModesCalculator implements PermissibleModesCalculator {

    /** Person attributes written by build_matsim_plans.py. */
    public static final String RIDE_ATTRIBUTE = "rideAvail";
    public static final String BIKE_ATTRIBUTE = "bikeAvail";
    public static final String LOCKED_ATTRIBUTE = "lockedMode";
    /** The one value that removes a mode; anything else leaves it available. */
    public static final String NEVER = "never";
    public static final String RIDE = "ride";
    public static final String BIKE = "bike";

    private final PermissibleModesCalculator delegate;

    @Inject
    public AvailabilityModesCalculator(final Config config) {
        this.delegate = new PermissibleModesCalculatorImpl(config);
    }

    private static boolean never(final Person person, final String attribute) {
        final Object flag = person.getAttributes().getAttribute(attribute);
        return flag != null && NEVER.equals(flag.toString());
    }

    @Override
    public Collection<String> getPermissibleModes(final Plan plan) {
        final Collection<String> modes = this.delegate.getPermissibleModes(plan);
        final Person person = plan.getPerson();
        if (person == null) {
            return modes;
        }
        final Object locked = person.getAttributes().getAttribute(LOCKED_ATTRIBUTE);
        if (locked != null) {
            final String mode = locked.toString();
            // the locked mode even if the delegate would deny it: the lock is
            // the agent's definition, not a preference
            return Collections.singletonList(mode);
        }
        final boolean noRide = never(person, RIDE_ATTRIBUTE);
        final boolean noBike = never(person, BIKE_ATTRIBUTE);
        if (!noRide && !noBike) {
            return modes;
        }
        final Collection<String> out = new ArrayList<>(modes.size());
        for (final String mode : modes) {
            if ((noRide && RIDE.equals(mode)) || (noBike && BIKE.equals(mode))) {
                continue;
            }
            out.add(mode);
        }
        return out;
    }
}
