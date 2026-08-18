package citysim;

import com.google.inject.Singleton;
import java.io.File;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.controler.Controler;
import org.matsim.core.population.algorithms.PermissibleModesCalculator;
import org.matsim.core.scenario.ScenarioUtils;

/**
 * The project's MATSim entry point. Identical to
 * {@code org.matsim.core.controler.Controler} except for the two rebindings and
 * the one added module below.
 *
 * <p><b>1. Mode availability.</b> {@link PermissibleModesCalculator} is rebound
 * so `ride` can be withheld from a person who has nobody to drive them
 * (DECISIONS.md 9.11), `bike` from a person drawn without one (DECISIONS.md
 * 9.39, issue #29), and so an agent carrying `lockedMode` — a through-traffic
 * vehicle anchored on an observed road count — keeps the mode it is defined by
 * (DECISIONS.md 9.41, issue #20).
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
 * <p><b>3. Parking charges (DECISIONS.md 9.31, issue #33).</b> The package has
 * declared a parking price since P1 and no script read it, so a car has always
 * parked for free — in a study about city-centre access, where parking price is
 * the prime competitive lever between car and public transport. When the
 * `parking` module carries a price file, {@link ParkingChargeHandler} is
 * installed and bills a car for the time it stands still. The module is absent
 * from a config that does not want it, and the handler is then never built.
 *
 * <p><b>4. Ride pairing, Tier 1 (DECISIONS.md 9.44, issue #31).</b> The note
 * above says ride experiences congestion without causing it, "which is correct
 * only insofar as every ride trip is paired with a driver trip, and it is not".
 * {@link RidePairingEngine} is what makes that pairing exist: at the
 * BeforeMobsim boundary each `ride` leg looks up a household member whose `car`
 * leg it could be inside, and a paired passenger then takes THAT DRIVER's
 * realised travel time rather than its own routed one. The module is absent
 * from a config that does not want it, and `ridePairing.enabled = false`
 * restores exactly the previous behaviour for comparison within one build.
 *
 * <p><b>5. Live telemetry.</b> When the `telemetry` module is present,
 * {@link RunTelemetry} publishes what is moving, of what kind and where it is
 * piling up, <em>while the mobsim runs</em>. It needs no change to
 * {@code writeEventsInterval}: a registered handler receives the full event
 * stream on every iteration regardless of whether that stream is also being
 * written to disk. It is an observer and cannot alter a result.
 *
 * <p>Run exactly as the stock main was:
 * <pre>java -cp pt2matsim-shaded.jar;classes citysim.CitysimControler config.xml</pre>
 *
 * <p>The pinned toolchain is untouched: this ADDS a compiled artefact alongside
 * the shaded jar rather than replacing it, so the JDK, pt2matsim and SUMO
 * digests in .tools/toolchain.json are unchanged. The artefact is built from
 * committed source by the pinned javac, which is what makes it reproducible.
 */
public final class CitysimControler {

    private CitysimControler() {
    }

    public static void main(final String[] args) {
        if (args.length != 1) {
            System.err.println("usage: citysim.CitysimControler <config.xml>");
            System.exit(2);
        }
        final ParkingConfigGroup parking = new ParkingConfigGroup();
        final TelemetryConfigGroup telemetry = new TelemetryConfigGroup();
        final RidePairingConfigGroup ridePairing = new RidePairingConfigGroup();
        final Config config =
                ConfigUtils.loadConfig(args[0], parking, telemetry, ridePairing);
        // The price file is written beside the config, like the network and the
        // schedule, so it is named relatively there and resolved here. MATSim
        // resolves its own input paths against the config's directory; this
        // module is ours, so it does its own.
        if (!parking.getPriceFile().isEmpty()) {
            final File declared = new File(parking.getPriceFile());
            if (!declared.isAbsolute()) {
                final File base = new File(args[0]).getAbsoluteFile().getParentFile();
                parking.setPriceFile(new File(base, parking.getPriceFile()).getPath());
            }
        }
        final Controler controler = new Controler(ScenarioUtils.loadScenario(config));
        controler.addOverridingModule(new AbstractModule() {
            @Override
            public void install() {
                bind(PermissibleModesCalculator.class)
                        .to(AvailabilityModesCalculator.class);
                // Issue #28: without these, `ride` routes on free-flow times.
                addTravelTimeBinding(TransportMode.ride)
                        .to(networkTravelTime());
                addTravelDisutilityFactoryBinding(TransportMode.ride)
                        .to(carTravelDisutilityFactoryKey());
            }
        });
        if (!parking.getPriceFile().isEmpty()) {
            controler.addOverridingModule(new AbstractModule() {
                @Override
                public void install() {
                    // One instance serving both roles: it accumulates as an
                    // event handler and emits as a controler listener.
                    bind(ParkingChargeHandler.class).in(Singleton.class);
                    addEventHandlerBinding().to(ParkingChargeHandler.class);
                    addControllerListenerBinding().to(ParkingChargeHandler.class);
                }
            });
        }
        if (ridePairing.isEnabled()) {
            controler.addOverridingModule(new AbstractModule() {
                @Override
                public void install() {
                    // One instance in two roles: it accumulates the drivers'
                    // realised times as an event handler, and makes the pairing
                    // as a controler listener at the BeforeMobsim boundary.
                    bind(RidePairingEngine.class).in(Singleton.class);
                    addEventHandlerBinding().to(RidePairingEngine.class);
                    addControllerListenerBinding().to(RidePairingEngine.class);
                }
            });
        }
        if (config.getModules().containsKey(TelemetryConfigGroup.NAME)) {
            controler.addOverridingModule(new AbstractModule() {
                @Override
                public void install() {
                    // One instance in three roles: it accumulates as an event
                    // handler, flushes live as a mobsim listener, and closes the
                    // iteration as a controler listener.
                    bind(RunTelemetry.class).in(Singleton.class);
                    addEventHandlerBinding().to(RunTelemetry.class);
                    addMobsimListenerBinding().to(RunTelemetry.class);
                    addControllerListenerBinding().to(RunTelemetry.class);
                }
            });
        }
        controler.run();
    }
}
