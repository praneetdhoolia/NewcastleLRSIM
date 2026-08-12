package wickham;

import org.matsim.api.core.v01.TransportMode;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.controler.Controler;
import org.matsim.core.population.algorithms.PermissibleModesCalculator;
import org.matsim.core.scenario.ScenarioUtils;

/**
 * The project's MATSim entry point. Identical to
 * {@code org.matsim.core.controler.Controler} except for two rebindings.
 *
 * <p><b>1. Ride availability.</b> {@link PermissibleModesCalculator} is rebound
 * so `ride` can be withheld from a person who has nobody to drive them
 * (DECISIONS.md 9.11).
 *
 * <p><b>2. Ride travel time (DECISIONS.md 9.26, issue #28).</b> `ride` is listed
 * in {@code routing.networkModes} but is not the qsim {@code mainMode}, so
 * MATSim routes it over the network and — with no events of its own to learn
 * from — hands it <em>free-flow</em> link times. Measured over a completed
 * 250-iteration run that made a car passenger arrive 13% faster than the car
 * carrying them: ride realised 55.7 km/h against car's 49.3. The two bindings
 * below point `ride` at the congested car travel time and the car disutility, so
 * a passenger now experiences exactly the traffic the driver does.
 *
 * <p>Note what this deliberately does <em>not</em> do: it does not add a ride
 * vehicle to the mobsim. A passenger travels in a car that is already there, so
 * a second vehicle would double-count the traffic. Ride therefore
 * <em>experiences</em> congestion without <em>causing</em> it — which is correct
 * only insofar as every ride trip is paired with a driver trip, and it is not.
 * That is issue #31, and it is open.
 *
 * <p>Run exactly as the stock main was:
 * <pre>java -cp pt2matsim-shaded.jar;classes wickham.WickhamControler config.xml</pre>
 *
 * <p>The pinned toolchain is untouched: this ADDS a compiled artefact alongside
 * the shaded jar rather than replacing it, so the JDK, pt2matsim and SUMO
 * digests in .tools/toolchain.json are unchanged. The artefact is built from
 * committed source by the pinned javac, which is what makes it reproducible.
 */
public final class WickhamControler {

    private WickhamControler() {
    }

    public static void main(final String[] args) {
        if (args.length != 1) {
            System.err.println("usage: wickham.WickhamControler <config.xml>");
            System.exit(2);
        }
        final Config config = ConfigUtils.loadConfig(args[0]);
        final Controler controler = new Controler(ScenarioUtils.loadScenario(config));
        controler.addOverridingModule(new AbstractModule() {
            @Override
            public void install() {
                bind(PermissibleModesCalculator.class)
                        .to(RideAvailabilityModesCalculator.class);
                // Issue #28: without these, `ride` routes on free-flow times.
                addTravelTimeBinding(TransportMode.ride)
                        .to(networkTravelTime());
                addTravelDisutilityFactoryBinding(TransportMode.ride)
                        .to(carTravelDisutilityFactoryKey());
            }
        });
        controler.run();
    }
}
