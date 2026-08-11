package wickham;

import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.controler.Controler;
import org.matsim.core.population.algorithms.PermissibleModesCalculator;
import org.matsim.core.scenario.ScenarioUtils;

/**
 * The project's MATSim entry point. Identical to
 * {@code org.matsim.core.controler.Controler} except that it rebinds
 * {@link PermissibleModesCalculator} so `ride` can be withheld from a person who
 * has nobody to drive them.
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
            }
        });
        controler.run();
    }
}
