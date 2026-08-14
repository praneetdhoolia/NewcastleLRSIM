package citysim;

import com.google.inject.Inject;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.events.LinkEnterEvent;
import org.matsim.api.core.v01.events.LinkLeaveEvent;
import org.matsim.api.core.v01.events.PersonArrivalEvent;
import org.matsim.api.core.v01.events.PersonDepartureEvent;
import org.matsim.api.core.v01.events.PersonStuckEvent;
import org.matsim.api.core.v01.events.TransitDriverStartsEvent;
import org.matsim.api.core.v01.events.VehicleEntersTrafficEvent;
import org.matsim.api.core.v01.events.VehicleLeavesTrafficEvent;
import org.matsim.api.core.v01.events.handler.LinkEnterEventHandler;
import org.matsim.api.core.v01.events.handler.LinkLeaveEventHandler;
import org.matsim.api.core.v01.events.handler.PersonArrivalEventHandler;
import org.matsim.api.core.v01.events.handler.PersonDepartureEventHandler;
import org.matsim.api.core.v01.events.handler.PersonStuckEventHandler;
import org.matsim.api.core.v01.events.handler.TransitDriverStartsEventHandler;
import org.matsim.api.core.v01.events.handler.VehicleEntersTrafficEventHandler;
import org.matsim.api.core.v01.events.handler.VehicleLeavesTrafficEventHandler;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.controler.OutputDirectoryHierarchy;
import org.matsim.core.controler.events.IterationEndsEvent;
import org.matsim.core.controler.events.IterationStartsEvent;
import org.matsim.core.controler.listener.IterationEndsListener;
import org.matsim.core.controler.listener.IterationStartsListener;
import org.matsim.core.mobsim.framework.events.MobsimAfterSimStepEvent;
import org.matsim.core.mobsim.framework.listeners.MobsimAfterSimStepListener;
import org.matsim.vehicles.Vehicle;

/**
 * Live per-iteration telemetry: what is moving, of what kind, and where it is
 * piling up — published while the mobsim runs rather than after it.
 *
 * <p><b>Why this exists rather than a config change.</b> The obvious way to see
 * inside a run is to write the event stream every iteration
 * ({@code writeEventsInterval = 1}). That is the expensive way and it is not
 * needed. MATSim's {@code EventsManager} fires every event to every registered
 * handler on <em>every</em> iteration; {@code writeEventsInterval} governs only
 * whether {@code EventWriterXML} — itself just another handler — is among them.
 * The package proves it: a completed 250-iteration run holds <b>26</b> event
 * files and <b>251</b> leg histograms, and the histogram is built by a handler.
 * So this class sees 100% of events on 100% of iterations at no disk cost, and
 * {@code RUN.controler.write_events_interval} stays where it is.
 *
 * <p><b>Why it is live.</b> Handlers are called <em>as the mobsim advances</em>,
 * in simulated-time order. A snapshot flushed on a simulated-time boundary is
 * therefore a real reading of the run in flight, not a replay of it afterwards.
 *
 * <p><b>What it emits.</b> Two files under the run's output directory, both
 * outside {@code ITERS/} so {@code prune_run.py} never removes them:
 * <ul>
 *   <li>{@code telemetry_live.json} — rewritten every
 *       {@code live_interval_s} <em>simulated</em> seconds. It carries the
 *       accumulating per-bin profile of the day so far, not a single instant, so
 *       a reader polling at any rate misses nothing between two polls. At the
 *       measured cadence the mobsim sweeps a 30 h day in about 15 s of wall
 *       clock, so an instant-only file would be unreadable.</li>
 *   <li>{@code telemetry.jsonl} — one line appended per iteration, holding the
 *       iteration totals and the per-link congestion payload the hotspot map
 *       colours.</li>
 * </ul>
 *
 * <p><b>Determinism.</b> The flush boundary is <em>simulated</em> time, never
 * wall clock, so the same run writes the same number of snapshots with the same
 * contents every time (CLAUDE.md: no wall-clock dependence). Wall-clock readings
 * that do appear in the payload are labelled and are elapsed-time only.
 *
 * <p><b>It is an observer.</b> It emits no event, holds no lock and mutates no
 * model state, so a run observed is byte-for-byte a run unobserved. Its output
 * is a diagnostic and is <em>not</em> a result: mode counts here are legs in
 * flight during one iteration, which is neither the mode agents chose
 * ({@code modestats.csv}) nor the trips that completed
 * ({@code _metrics.json}) — see DECISIONS.md 9.12. Nothing reportable comes
 * from this file.
 *
 * <p><b>What the hotspot payload can and cannot show.</b> Delay is measured from
 * {@code LinkEnter}/{@code LinkLeave} pairs, so it covers exactly the vehicles
 * that traverse network links: {@code car} and the transit fleet. {@code walk}
 * and {@code bike} are teleported and never enter a link. {@code ride} routes on
 * the network but adds no vehicle to the mobsim (issue #31), so it experiences
 * congestion without causing it. A map drawn from this is therefore
 * <em>vehicular</em> congestion, and the page must say so.
 */
public final class RunTelemetry implements
        PersonDepartureEventHandler, PersonArrivalEventHandler,
        PersonStuckEventHandler, LinkEnterEventHandler, LinkLeaveEventHandler,
        VehicleEntersTrafficEventHandler, VehicleLeavesTrafficEventHandler,
        TransitDriverStartsEventHandler, MobsimAfterSimStepListener,
        IterationStartsListener, IterationEndsListener {

    /** Simulated seconds between live snapshots. One per simulated hour matches
     *  MATSim's own QSim log line, which is about 0.5 s of wall clock apart at
     *  the measured sweep rate — frequent enough to watch, cheap enough to
     *  ignore. */
    private final double liveIntervalS;

    private final Network network;
    private final Scenario scenario;
    private final OutputDirectoryHierarchy io;

    /** Free-flow traversal time per link, precomputed once. */
    private final Map<Id<Link>, Double> freeflow = new HashMap<>();

    /** Person legs in flight, by leg mode. Covers teleported modes too, which
     *  the link events cannot see. */
    private final Map<String, Integer> enRouteByMode = new TreeMap<>();
    private final Map<String, Integer> departuresByMode = new TreeMap<>();
    private final Map<String, Integer> arrivalsByMode = new TreeMap<>();
    private final Map<String, Integer> stuckByMode = new TreeMap<>();

    /** Transit vehicle id -> its declared type (Bus, Rail, Tram, Ferry). The
     *  passenger's leg mode is `pt` for all four, so the split the light rail
     *  study needs cannot come from leg mode and comes from the fleet instead. */
    private final Map<Id<Vehicle>, String> transitType = new HashMap<>();
    private final Map<String, Integer> enRouteByVehicleType = new TreeMap<>();

    /** Open link traversals, keyed by vehicle: entry time awaiting a leave. */
    private final Map<Id<Vehicle>, LinkEntry> open = new HashMap<>();

    /** Cumulative over the whole iteration - the day's picture, written at the end. */
    private final Map<Id<Link>, LinkLoad> load = new HashMap<>();

    /** The CURRENT window only, cleared at every live flush. A live map has to
     *  answer "what is congested now", and a cumulative day mean cannot: it
     *  converges as the day proceeds and stops moving, so the peak would build
     *  and then never dissipate. This is what makes the map live rather than
     *  merely frequent. */
    private final Map<Id<Link>, LinkLoad> window = new HashMap<>();
    private double windowStart = 0.0;

    private final List<Bin> profile = new ArrayList<>();

    /** Windows holds a file against replacement while a reader has it open, and
     *  the live view polls twice a second, so a collision is routine rather than
     *  exceptional. */
    private static final int MOVE_ATTEMPTS = 5;
    private static final long MOVE_BACKOFF_MS = 4L;

    /** Frames lost to IO. Reported, never thrown. */
    private int writeFailures = 0;

    private int iteration = -1;
    private double nextFlush = Double.NEGATIVE_INFINITY;
    private double lastTime = 0.0;
    private long iterationStartedMs = 0L;

    private static final class LinkEntry {
        private final Id<Link> link;
        private final double time;

        private LinkEntry(final Id<Link> link, final double time) {
            this.link = link;
            this.time = time;
        }
    }

    /** Volume and cumulative traversal time for one link over one iteration. */
    private static final class LinkLoad {
        private int volume;
        private double travelTimeSum;
    }

    /** One simulated-time bin of the accumulating day profile. */
    private static final class Bin {
        private final double t;
        private final Map<String, Integer> modes;
        private final Map<String, Integer> vehicleTypes;
        private final int total;

        private Bin(final double t, final Map<String, Integer> modes,
                    final Map<String, Integer> vehicleTypes, final int total) {
            this.t = t;
            this.modes = new TreeMap<>(modes);
            this.vehicleTypes = new TreeMap<>(vehicleTypes);
            this.total = total;
        }
    }

    @Inject
    RunTelemetry(final Network network, final Scenario scenario,
                 final OutputDirectoryHierarchy io) {
        this.network = network;
        this.scenario = scenario;
        this.io = io;
        final TelemetryConfigGroup cfg = (TelemetryConfigGroup) scenario.getConfig()
                .getModules().get(TelemetryConfigGroup.NAME);
        this.liveIntervalS = cfg == null ? 3600.0 : cfg.getLiveIntervalS();
        for (final Link link : network.getLinks().values()) {
            final double v = link.getFreespeed();
            freeflow.put(link.getId(), v > 0 ? link.getLength() / v : 0.0);
        }
    }

    // ---- lifecycle ----

    @Override
    public void notifyIterationStarts(final IterationStartsEvent event) {
        iteration = event.getIteration();
        iterationStartedMs = System.currentTimeMillis();
        reset();
    }

    @Override
    public void reset(final int iteration) {
        reset();
    }

    private void reset() {
        enRouteByMode.clear();
        departuresByMode.clear();
        arrivalsByMode.clear();
        stuckByMode.clear();
        enRouteByVehicleType.clear();
        transitType.clear();
        open.clear();
        load.clear();
        profile.clear();
        nextFlush = Double.NEGATIVE_INFINITY;
        lastTime = 0.0;
    }

    // ---- person legs, every mode including the teleported ones ----

    @Override
    public void handleEvent(final PersonDepartureEvent event) {
        bump(enRouteByMode, event.getLegMode(), 1);
        bump(departuresByMode, event.getLegMode(), 1);
        lastTime = event.getTime();
    }

    @Override
    public void handleEvent(final PersonArrivalEvent event) {
        bump(enRouteByMode, event.getLegMode(), -1);
        bump(arrivalsByMode, event.getLegMode(), 1);
        lastTime = event.getTime();
    }

    @Override
    public void handleEvent(final PersonStuckEvent event) {
        // An agent the mobsim gave up on. Rising counts here mean the network is
        // gridlocked or broken, which is the one live reading that says a run
        // should be killed rather than waited out.
        bump(stuckByMode, event.getLegMode(), 1);
        bump(enRouteByMode, event.getLegMode(), -1);
    }

    // ---- transit fleet: the bus / train / light rail / ferry split ----

    @Override
    public void handleEvent(final TransitDriverStartsEvent event) {
        final Vehicle v = scenario.getTransitVehicles().getVehicles()
                .get(event.getVehicleId());
        if (v != null && v.getType() != null) {
            transitType.put(event.getVehicleId(), v.getType().getId().toString());
        }
    }

    @Override
    public void handleEvent(final VehicleEntersTrafficEvent event) {
        final String t = transitType.get(event.getVehicleId());
        if (t != null) {
            bump(enRouteByVehicleType, t, 1);
        }
    }

    @Override
    public void handleEvent(final VehicleLeavesTrafficEvent event) {
        final String t = transitType.get(event.getVehicleId());
        if (t != null) {
            bump(enRouteByVehicleType, t, -1);
        }
    }

    // ---- per-link load: volume, and the delay the hotspot map colours ----

    @Override
    public void handleEvent(final LinkEnterEvent event) {
        open.put(event.getVehicleId(),
                 new LinkEntry(event.getLinkId(), event.getTime()));
        lastTime = event.getTime();
    }

    @Override
    public void handleEvent(final LinkLeaveEvent event) {
        final LinkEntry e = open.remove(event.getVehicleId());
        lastTime = event.getTime();
        if (e == null || !e.link.equals(event.getLinkId())) {
            return;
        }
        final double tt = event.getTime() - e.time;
        final LinkLoad l = load.computeIfAbsent(e.link, k -> new LinkLoad());
        l.volume++;
        l.travelTimeSum += tt;
        final LinkLoad w = window.computeIfAbsent(e.link, k -> new LinkLoad());
        w.volume++;
        w.travelTimeSum += tt;
    }

    // ---- live flush, on a SIMULATED-time boundary ----

    @Override
    public void notifyMobsimAfterSimStep(final MobsimAfterSimStepEvent event) {
        try {
            publishStep(event.getSimulationTime());
        } catch (final RuntimeException e) {
            // Last line of defence. Nothing this class does may stop a run.
            writeFailures++;
        }
    }

    private void publishStep(final double simTime) {
        final double now = simTime;
        lastTime = now;
        if (nextFlush == Double.NEGATIVE_INFINITY) {
            nextFlush = Math.floor(now / liveIntervalS) * liveIntervalS;
        }
        if (now < nextFlush) {
            return;
        }
        int total = 0;
        for (final int n : enRouteByMode.values()) {
            total += Math.max(0, n);
        }
        profile.add(new Bin(nextFlush, enRouteByMode, enRouteByVehicleType, total));
        final double wStart = windowStart;
        while (now >= nextFlush) {
            nextFlush += liveIntervalS;
        }
        writeLive(now, false);
        // The map moves with the clock: the congestion of the window that just
        // closed, published before the next one starts filling.
        writeLinks(window, wStart, now, false);
        window.clear();
        windowStart = now;
    }

    @Override
    public void notifyIterationEnds(final IterationEndsEvent event) {
        try {
            publishIterationEnd();
        } catch (final RuntimeException e) {
            writeFailures++;
        }
    }

    private void publishIterationEnd() {
        writeLive(lastTime, true);
        appendIterationLine();
        // The whole day, replacing the last live window: once the mobsim has
        // ended, the useful reading is the iteration's own picture.
        writeLinks(load, 0.0, lastTime, true);
        window.clear();
        windowStart = 0.0;
    }

    // ---- emit ----

    private void writeLive(final double now, final boolean mobsimDone) {
        final StringBuilder b = new StringBuilder(1 << 16);
        b.append('{');
        b.append("\"iteration\":").append(iteration);
        b.append(",\"sim_time_s\":").append(fmt(now));
        b.append(",\"sim_clock\":\"").append(clock(now)).append('"');
        b.append(",\"mobsim_done\":").append(mobsimDone);
        b.append(",\"iteration_elapsed_s\":")
         .append(fmt((System.currentTimeMillis() - iterationStartedMs) / 1000.0));
        b.append(",\"live_interval_s\":").append(fmt(liveIntervalS));
        b.append(",\"write_failures\":").append(writeFailures);
        b.append(",\"en_route\":");
        jsonCounts(b, enRouteByMode);
        b.append(",\"en_route_vehicle_type\":");
        jsonCounts(b, enRouteByVehicleType);
        b.append(",\"departures\":");
        jsonCounts(b, departuresByMode);
        b.append(",\"arrivals\":");
        jsonCounts(b, arrivalsByMode);
        b.append(",\"stuck\":");
        jsonCounts(b, stuckByMode);
        b.append(",\"profile\":[");
        for (int i = 0; i < profile.size(); i++) {
            final Bin bin = profile.get(i);
            if (i > 0) {
                b.append(',');
            }
            b.append("{\"t\":").append(fmt(bin.t));
            b.append(",\"clock\":\"").append(clock(bin.t)).append('"');
            b.append(",\"total\":").append(bin.total);
            b.append(",\"modes\":");
            jsonCounts(b, bin.modes);
            b.append(",\"vehicle_types\":");
            jsonCounts(b, bin.vehicleTypes);
            b.append('}');
        }
        b.append("]}");
        atomicWrite("telemetry_live.json", b.toString());
    }

    private void appendIterationLine() {
        final StringBuilder b = new StringBuilder(1 << 20);
        b.append('{');
        b.append("\"iteration\":").append(iteration);
        b.append(",\"wall_s\":")
         .append(fmt((System.currentTimeMillis() - iterationStartedMs) / 1000.0));
        b.append(",\"departures\":");
        jsonCounts(b, departuresByMode);
        b.append(",\"arrivals\":");
        jsonCounts(b, arrivalsByMode);
        b.append(",\"stuck\":");
        jsonCounts(b, stuckByMode);
        b.append(",\"profile\":[");
        for (int i = 0; i < profile.size(); i++) {
            final Bin bin = profile.get(i);
            if (i > 0) {
                b.append(',');
            }
            b.append("{\"t\":").append(fmt(bin.t))
             .append(",\"total\":").append(bin.total)
             .append(",\"modes\":");
            jsonCounts(b, bin.modes);
            b.append(",\"vehicle_types\":");
            jsonCounts(b, bin.vehicleTypes);
            b.append('}');
        }
        b.append(']');
        // Whatever is still counted as in flight once the mobsim has ended is
        // NOT en route - it is a leg the mobsim never terminated. Measured on a
        // 1% probe, departures = arrivals + stuck EXACTLY for car, bike, ride
        // and walk, and `pt` left a residual of 305: passengers still waiting at
        // a stop at 30:00:00, for whom MATSim emits no terminal event. Naming it
        // is the point. Folded into `en_route` it would read as traffic, and the
        // conservation identity below would silently not close.
        b.append(",\"unresolved\":");
        jsonCounts(b, enRouteByMode);
        b.append(",\"unresolved_vehicle_type\":");
        jsonCounts(b, enRouteByVehicleType);
        b.append('}');
        append("telemetry.jsonl", b.toString() + System.lineSeparator());
    }

    /**
     * The hotspot payload — the congestion of one window of simulated time.
     *
     * <p>Called on every live boundary with the window that just closed, and
     * once more at iteration end with the whole day. Written to its own file and
     * <b>overwritten</b> rather than appended. Measured on a 1% probe: the
     * per-link array is 1.14 MB for a full day against a 6 KB summary — 99.5% of
     * the bytes — so appending it would put 1.2 GB on disk over a 1000-iteration
     * run at 1%. Overwriting costs nothing on disk, and a live window is far
     * smaller than a day because only the links moving in that hour appear.
     *
     * <p>Only links that carried something are written: a link with no volume
     * has no congestion to colour.
     *
     * @param src   the accumulator to publish — the live window, or the day
     * @param from  window start, simulated seconds
     * @param to    window end, simulated seconds
     * @param whole true when this is the iteration's whole-day picture
     */
    private void writeLinks(final Map<Id<Link>, LinkLoad> src, final double from,
                            final double to, final boolean whole) {
        final StringBuilder b = new StringBuilder(1 << 22);
        b.append("{\"iteration\":").append(iteration);
        b.append(",\"scope\":\"").append(whole ? "iteration" : "window").append('"');
        b.append(",\"window_from_s\":").append(fmt(from));
        b.append(",\"window_to_s\":").append(fmt(to));
        b.append(",\"window_from\":\"").append(clock(from)).append('"');
        b.append(",\"window_to\":\"").append(clock(to)).append('"');
        b.append(",\"metric\":\"delay_ratio = mean observed traversal / free-flow"
                 + " traversal; volume = vehicle traversals\"");
        b.append(",\"covers\":\"car and the transit fleet only - walk and bike are"
                 + " teleported and never enter a link, and ride adds no vehicle"
                 + " to the mobsim (issue #31)\"");
        b.append(",\"links\":[");
        boolean first = true;
        for (final Map.Entry<Id<Link>, LinkLoad> e : src.entrySet()) {
            final LinkLoad l = e.getValue();
            if (l.volume <= 0) {
                continue;
            }
            final Double ff = freeflow.get(e.getKey());
            final double mean = l.travelTimeSum / l.volume;
            // Below one free-flow traversal there is no delay to report; the
            // ratio is clamped at 1.0 so the ramp starts at "flowing".
            final double ratio = ff == null || ff <= 0 ? 1.0
                    : Math.max(1.0, mean / ff);
            if (!first) {
                b.append(',');
            }
            first = false;
            b.append("[\"").append(e.getKey()).append("\",")
             .append(l.volume).append(',').append(fmt(ratio)).append(']');
        }
        b.append("]}");
        atomicWrite("telemetry_links.json", b.toString());
    }

    // ---- helpers ----

    private static void bump(final Map<String, Integer> m, final String k,
                             final int d) {
        if (k == null) {
            return;
        }
        m.merge(k, d, Integer::sum);
    }

    private static void jsonCounts(final StringBuilder b,
                                   final Map<String, Integer> m) {
        b.append('{');
        boolean first = true;
        int total = 0;
        for (final Map.Entry<String, Integer> e : m.entrySet()) {
            final int n = Math.max(0, e.getValue());
            total += n;
            if (!first) {
                b.append(',');
            }
            first = false;
            b.append('"').append(e.getKey()).append("\":").append(n);
        }
        if (!first) {
            b.append(',');
        }
        b.append("\"total\":").append(total).append('}');
    }

    /** Simulated seconds as a 24 h clock. MATSim days run past 24:00, so the
     *  hour is not wrapped: 30:15:00 is a real and meaningful reading. */
    private static String clock(final double t) {
        final long s = (long) Math.max(0, t);
        return String.format(Locale.ROOT, "%02d:%02d:%02d",
                             s / 3600, (s % 3600) / 60, s % 60);
    }

    private static String fmt(final double v) {
        if (v == Math.rint(v) && !Double.isInfinite(v)) {
            return Long.toString((long) v);
        }
        return String.format(Locale.ROOT, "%.4f", v);
    }

    /**
     * Replace via a temporary file so a reader never sees a half-written page.
     *
     * <p><b>An observer must never be able to stop the thing it observes.</b>
     * This class claims that a run observed is byte-for-byte a run unobserved,
     * and the first version broke that claim outright: on Windows a
     * {@code Files.move} with {@code REPLACE_EXISTING} throws
     * {@code FileSystemException: The process cannot access the file because it
     * is being used by another process} whenever a reader has the target open —
     * and the live view polls this file twice a second. The exception
     * propagated out of the mobsim and <b>killed the run</b>. Reproduced at
     * iteration 5 of a 10-iteration probe.
     *
     * <p>So: retry briefly for the ordinary case of a reader mid-read, then fall
     * back to writing in place, and if even that fails give up silently and
     * count it. Telemetry is a diagnostic; losing a frame of it is a
     * non-event, and losing the run is not.
     */
    private void atomicWrite(final String name, final String body) {
        final Path out = Paths.get(io.getOutputFilename(name));
        final Path tmp = Paths.get(io.getOutputFilename(name + ".tmp"));
        final byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        try {
            Files.write(tmp, bytes);
        } catch (final IOException e) {
            writeFailures++;
            return;
        }
        for (int attempt = 0; attempt < MOVE_ATTEMPTS; attempt++) {
            try {
                Files.move(tmp, out, StandardCopyOption.REPLACE_EXISTING);
                return;
            } catch (final IOException held) {
                try {
                    Thread.sleep(MOVE_BACKOFF_MS);
                } catch (final InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
        // A reader has held it for the whole backoff. Write in place rather than
        // lose the frame; a reader that catches a partial parse simply retries.
        try {
            Files.write(out, bytes);
            Files.deleteIfExists(tmp);
        } catch (final IOException e) {
            writeFailures++;
        }
    }

    private void append(final String name, final String body) {
        try {
            Files.write(Paths.get(io.getOutputFilename(name)),
                        body.getBytes(StandardCharsets.UTF_8),
                        java.nio.file.StandardOpenOption.CREATE,
                        java.nio.file.StandardOpenOption.APPEND);
        } catch (final IOException e) {
            writeFailures++;
        }
    }
}
