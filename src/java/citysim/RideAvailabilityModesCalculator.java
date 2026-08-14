package citysim;

import com.google.inject.Inject;
import java.util.ArrayList;
import java.util.Collection;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Person;
import org.matsim.core.config.Config;
import org.matsim.core.population.algorithms.PermissibleModesCalculator;
import org.matsim.core.population.algorithms.PermissibleModesCalculatorImpl;

/**
 * Removes `ride` from the choice set of a person who has nobody to drive them.
 *
 * <p>MATSim's standard treatment lets any agent become a car passenger on any
 * trip. Riding as a passenger should only be available when another agent is
 * driving the same trip at the same time, but it is usually modelled without
 * that requirement and teleported through the network. DECISIONS.md 9.7 and
 * 9.10 measure what that costs here: `ride` reaches 0.72 of legs against an
 * observed 0.206, unchanged by a tenfold increase in sample size, putting 5.9
 * people in every car.
 *
 * <p>Core MATSim can restrict `car` per person, through the `carAvail`
 * attribute honoured by {@link PermissibleModesCalculatorImpl}, but has no
 * equivalent for `ride`, and `subtourModeChoice.modes` is global. So this is the
 * smallest structural fix available: a per-person availability flag, derived
 * from the synthetic household rather than assumed.
 *
 * <p><b>What this does not do.</b> It makes `ride` available or not for a
 * person. It does NOT bind a passenger to a specific driver on a specific trip
 * at a specific time, so the model can still produce more passengers than there
 * are drivers to carry them at any given hour. That is what the socnetsim joint
 * plans contrib does (Dubernet and Axhausen), which is absent from the pinned
 * jar and out of scope. The residual is stated rather than hidden.
 *
 * <p>The attribute is written by build_matsim_plans.py from B1 household
 * composition and licence holding. Absent attribute means available, so this
 * class is inert on a population that does not carry it.
 */
public final class RideAvailabilityModesCalculator implements PermissibleModesCalculator {

    /** Person attribute written by build_matsim_plans.py. */
    public static final String ATTRIBUTE = "rideAvail";
    /** The one value that removes the mode; anything else leaves it available. */
    public static final String NEVER = "never";
    public static final String RIDE = "ride";

    private final PermissibleModesCalculator delegate;

    @Inject
    public RideAvailabilityModesCalculator(final Config config) {
        this.delegate = new PermissibleModesCalculatorImpl(config);
    }

    @Override
    public Collection<String> getPermissibleModes(final Plan plan) {
        final Collection<String> modes = this.delegate.getPermissibleModes(plan);
        final Person person = plan.getPerson();
        if (person == null) {
            return modes;
        }
        final Object flag = person.getAttributes().getAttribute(ATTRIBUTE);
        if (flag == null || !NEVER.equals(flag.toString())) {
            return modes;
        }
        final Collection<String> out = new ArrayList<>(modes.size());
        for (final String mode : modes) {
            if (!RIDE.equals(mode)) {
                out.add(mode);
            }
        }
        return out;
    }
}
