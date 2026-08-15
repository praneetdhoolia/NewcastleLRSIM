package citysim;

import org.matsim.core.config.Config;
import org.matsim.core.config.ReflectiveConfigGroup;

/**
 * The `telemetry` config module: how often the run publishes what it is doing.
 *
 * <p>Values here are written by {@code build_matsim_run_inputs.py} from
 * {@code config/registry/<city>/RUN_execution.json}. Nothing is typed into a
 * script.
 *
 * <p>Declaring it as a real {@link ReflectiveConfigGroup} rather than letting
 * MATSim absorb an unknown module buys the same two things the `parking` module
 * buys: an unrecognised parameter fails the run instead of being ignored, and
 * the module lands in the output config dump, so a run carries the telemetry
 * regime that produced it.
 *
 * <p>The module is <em>absent</em> from a config that does not want telemetry,
 * and {@link RunTelemetry} is then never installed — the same on/off shape the
 * parking price file uses.
 */
public final class TelemetryConfigGroup extends ReflectiveConfigGroup {

    public static final String NAME = "telemetry";

    /**
     * Sentinel meaning "the config never set it", NOT a usable interval.
     *
     * <p>This field held {@code 3600.0} — exactly the value
     * {@code RUN.telemetry.live_interval_s} declares. A Java default that
     * EQUALS its registry value is this repository's signature defect in its
     * worst form: it is right by accident, every test passes, and it silently
     * stops being right the moment anyone sweeps the field, because a config
     * that failed to write the parameter would run on this number and report
     * success. {@link #checkConsistency} now refuses that run instead.
     */
    private static final double UNSET = -1.0;

    private double liveIntervalS = UNSET;

    public TelemetryConfigGroup() {
        super(NAME);
    }

    /**
     * Simulated seconds between live snapshots.
     *
     * <p>The boundary is <em>simulated</em> time, never wall clock, so a run
     * writes the same snapshots in the same places every time it is repeated —
     * the determinism rule in CLAUDE.md applies to an observer as much as to a
     * build script.
     *
     * <p>3600 puts one snapshot per simulated hour, which at the measured sweep
     * rate (a 30 h day in about 15 s of wall clock) is roughly one every half
     * second: frequent enough to watch the peak build, cheap enough that the
     * write is not part of the run's cost. Lowering it does not lose data — the
     * file carries the accumulating profile of the day, not a single instant —
     * it only refines the bins.
     */
    @StringGetter("liveIntervalS")
    public double getLiveIntervalS() {
        return this.liveIntervalS;
    }

    @StringSetter("liveIntervalS")
    public void setLiveIntervalS(final double value) {
        this.liveIntervalS = value;
    }

    /**
     * Refuse a telemetry module that carries no interval.
     *
     * <p>The config is BUILT from the registry by
     * {@code src/registry/param_config.py}, so a missing parameter means the
     * binding was lost — and the one thing that must not happen then is for the
     * run to continue on a number nobody chose.
     */
    @Override
    public void checkConsistency(final Config config) {
        super.checkConsistency(config);
        if (this.liveIntervalS <= 0.0) {
            throw new IllegalStateException(
                    "telemetry.liveIntervalS was never set. It is declared as "
                    + "RUN.telemetry.live_interval_s and written into the config "
                    + "by src/registry/param_config.py; this class keeps no "
                    + "usable default, because a default equal to the declared "
                    + "value is right by accident.");
        }
    }
}
