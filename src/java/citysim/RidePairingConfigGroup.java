package citysim;

import org.matsim.core.config.Config;
import org.matsim.core.config.ReflectiveConfigGroup;

/**
 * The `ridePairing` config module: how a car passenger names the household
 * member who drives them.
 *
 * <p>Every value here is written by {@code build_matsim_run_inputs.py} from
 * {@code cities/<city>/registry/B_demand.json}. None of them may be typed into
 * a script, and none of them is a place: the pairing is decided on link
 * identity and clock time, both of which come out of the agents' own plans.
 * Java does no spatial work at all.
 *
 * <p>Declaring this as a real {@link ReflectiveConfigGroup} rather than letting
 * MATSim absorb an unknown module buys what the `parking` and `telemetry`
 * modules buy: an unrecognised parameter fails the run instead of being
 * ignored, and the module lands in the output config dump, so a result carries
 * the pairing regime that produced it.
 *
 * <p>See DECISIONS.md 9.44 and issue #31.
 */
public final class RidePairingConfigGroup extends ReflectiveConfigGroup {

    public static final String NAME = "ridePairing";

    /**
     * Sentinel meaning "the config never set it", NOT a usable value.
     *
     * <p>The lesson {@link TelemetryConfigGroup} records applies here in full: a
     * Java default that EQUALS its registry value is right by accident, passes
     * every test, and silently stops being right the moment anyone sweeps the
     * field. {@link #checkConsistency} refuses such a run instead.
     */
    private static final double UNSET = -1.0;

    /** The four rules {@code B.ride.pairing_rule} may take. */
    public static final String RULE_BOTH_LINKS = "both_links";
    public static final String RULE_ORIGIN_LINK = "origin_link";
    public static final String RULE_DEST_LINK = "dest_link";
    public static final String RULE_WINDOW_ONLY = "window_only";

    private boolean enabled = false;
    private boolean physicalBoarding = false;
    private double windowMinutes = UNSET;
    private String rule = "";
    private double pickupDwellSeconds = UNSET;
    private int maxPassengersPerVehicle = -1;

    public RidePairingConfigGroup() {
        super(NAME);
    }

    /**
     * Whether a ride leg may name a driver at all.
     *
     * <p>False restores exactly the behaviour of every run made before this
     * class existed — a teleported passenger on their own routed time — so the
     * two are comparable within one build, which is what
     * {@code B.population.ride_requires_household_driver} does for the
     * availability rule. The default is false for the same reason the parking
     * price file defaults to empty: an absent binding must not switch a
     * mechanism on.
     */
    @StringGetter("enabled")
    public boolean isEnabled() {
        return this.enabled;
    }

    @StringSetter("enabled")
    public void setEnabled(final boolean value) {
        this.enabled = value;
    }

    /**
     * Whether a PAIRED passenger physically boards the driver's vehicle
     * (DECISIONS.md 9.53, issue #48) instead of inheriting its clock.
     *
     * <p>With this on, {@link JointRideEngine} claims the ride departure of
     * every booked passenger whose driver's car is parked at their shared
     * origin link, boards them (a real {@code PersonEntersVehicleEvent}), and
     * alights them when the car reaches their shared destination link. A
     * booked passenger whose car has ALREADY LEFT falls back to Tier 1's
     * teleport-on-the-driver's-clock, counted and reported — never hidden.
     * False restores Tier 1 exactly (DECISIONS.md 9.44).
     */
    @StringGetter("physicalBoarding")
    public boolean isPhysicalBoarding() {
        return this.physicalBoarding;
    }

    @StringSetter("physicalBoarding")
    public void setPhysicalBoarding(final boolean value) {
        this.physicalBoarding = value;
    }

    /**
     * How far apart the passenger's and the driver's planned departures may be
     * and still be one trip, in minutes.
     *
     * <p>This is the tolerance the pairing is allowed, NOT a modelled waiting
     * time: Tier 1 does not move the passenger's departure, because shifting it
     * would cascade through the rest of that person's day and the blast radius
     * of this change is deliberately bounded (DECISIONS.md 9.44). The
     * unmodelled sub-window adjustment is a stated limitation, and
     * {@link #getPickupDwellSeconds()} is the only friction that is priced.
     */
    @StringGetter("windowMinutes")
    public double getWindowMinutes() {
        return this.windowMinutes;
    }

    @StringSetter("windowMinutes")
    public void setWindowMinutes(final double value) {
        this.windowMinutes = value;
    }

    /**
     * Which endpoints of the driver's leg must coincide with the passenger's.
     *
     * <p>{@link #RULE_BOTH_LINKS} is the only rule under which handing the
     * driver's realised travel time to the passenger is CORRECT rather than
     * merely closer: the two are then the same trip. The looser rules exist so
     * the sweep can measure what a laxer assumption would buy, and a run made
     * under one of them is a sensitivity, not a result.
     */
    @StringGetter("rule")
    public String getRule() {
        return this.rule;
    }

    @StringSetter("rule")
    public void setRule(final String value) {
        this.rule = value == null ? "" : value.trim();
    }

    /**
     * Seconds added to a paired passenger's travel time for being picked up.
     *
     * <p>DELIBERATELY NEUTRAL BY DEFAULT. The measured car-minus-ride residual
     * this whole lane exists to remove is about 5 s at 25% and 13 s at 10%
     * (NEXT_AGENT_BRIEF.md 2), so a one-minute pickup friction would be five to
     * twelve times the entire quantity it was supposed to explain. Sizing one
     * to close that gap is calibration wearing a mechanism's clothes and was
     * REFUSED (DECISIONS.md 9.44). This field exists so the question can be
     * SWEPT — no local observation of pickup dwell exists — and its value is
     * never fitted.
     */
    @StringGetter("pickupDwellSeconds")
    public double getPickupDwellSeconds() {
        return this.pickupDwellSeconds;
    }

    @StringSetter("pickupDwellSeconds")
    public void setPickupDwellSeconds(final double value) {
        this.pickupDwellSeconds = value;
    }

    /**
     * How many passengers one driver's leg may carry.
     *
     * <p>Without a cap one driver would serve every passenger their household
     * offered, which is the same unbounded-supply defect
     * {@code rideAvail} removed on the availability side.
     */
    @StringGetter("maxPassengersPerVehicle")
    public int getMaxPassengersPerVehicle() {
        return this.maxPassengersPerVehicle;
    }

    @StringSetter("maxPassengersPerVehicle")
    public void setMaxPassengersPerVehicle(final int value) {
        this.maxPassengersPerVehicle = value;
    }

    /**
     * Refuse a pairing module that is switched on and carries no regime.
     *
     * <p>The config is BUILT from the registry by
     * {@code src/registry/param_config.py}, so a missing parameter means the
     * binding was lost — and the one thing that must not then happen is for the
     * run to continue on a number nobody chose.
     */
    @Override
    public void checkConsistency(final Config config) {
        super.checkConsistency(config);
        if (!this.enabled) {
            return;
        }
        require(this.windowMinutes >= 0.0, "windowMinutes", "B.ride.pairing_window_min");
        require(this.pickupDwellSeconds >= 0.0, "pickupDwellSeconds",
                "B.ride.pickup_dwell_s");
        require(this.maxPassengersPerVehicle >= 1, "maxPassengersPerVehicle",
                "B.ride.max_passengers_per_vehicle");
        require(!this.rule.isEmpty(), "rule", "B.ride.pairing_rule");
        if (!RULE_BOTH_LINKS.equals(this.rule) && !RULE_ORIGIN_LINK.equals(this.rule)
                && !RULE_DEST_LINK.equals(this.rule)
                && !RULE_WINDOW_ONLY.equals(this.rule)) {
            throw new IllegalStateException(
                    "ridePairing.rule is '" + this.rule + "', which is not one of "
                    + RULE_BOTH_LINKS + ", " + RULE_ORIGIN_LINK + ", "
                    + RULE_DEST_LINK + ", " + RULE_WINDOW_ONLY
                    + ". The rule is declared as B.ride.pairing_rule.");
        }
    }

    private static void require(final boolean ok, final String param,
                                final String field) {
        if (!ok) {
            throw new IllegalStateException(
                    "ridePairing." + param + " was never set, but ridePairing is "
                    + "enabled. It is declared as " + field + " and written into "
                    + "the config by src/registry/param_config.py; this class "
                    + "keeps no usable default, because a default equal to the "
                    + "declared value is right by accident.");
        }
    }
}
