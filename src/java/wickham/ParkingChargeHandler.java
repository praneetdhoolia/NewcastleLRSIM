package wickham;

import com.google.inject.Inject;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.events.ActivityStartEvent;
import org.matsim.api.core.v01.events.PersonArrivalEvent;
import org.matsim.api.core.v01.events.PersonDepartureEvent;
import org.matsim.api.core.v01.events.PersonMoneyEvent;
import org.matsim.api.core.v01.events.handler.ActivityStartEventHandler;
import org.matsim.api.core.v01.events.handler.PersonArrivalEventHandler;
import org.matsim.api.core.v01.events.handler.PersonDepartureEventHandler;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.population.Person;
import org.matsim.core.api.experimental.events.EventsManager;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.events.AfterMobsimEvent;
import org.matsim.core.controler.listener.AfterMobsimListener;
import org.matsim.core.router.TripStructureUtils;

/**
 * Charges a car for the time it stands parked, as a {@link PersonMoneyEvent}.
 *
 * <p><b>Why this exists.</b> Parking price is the prime competitive lever
 * between car and public transport for a city-centre trip, and this study is
 * about city-centre access. The package has carried a parking price layer since
 * P1 - {@code A5_parking_facilities.csv} declares {@code is_priced},
 * {@code price_aud_hr} and a sweep on both - and no script read any of it, so
 * the model has always parked for free. Issue #33; DECISIONS.md 9.31.
 *
 * <p><b>What is charged.</b> A car occupies a space from the moment it arrives
 * until the <em>next car departure</em>, not merely for the activity that
 * follows it. An agent who parks, shops, walks to a cafe and then drives home
 * has occupied the space for the whole spell, and charging only the first
 * activity would under-count it. The charge is
 *
 * <pre>price(link) x min(overlap(spell, chargedWindow), maxStay)</pre>
 *
 * <p>and is emitted as a negative amount, matching the sign convention
 * {@code monetaryDistanceRate} already uses.
 *
 * <p><b>What is not charged.</b> Only modes in
 * {@link ParkingConfigGroup#getChargedModes()} - `car` - open a spell: a
 * passenger does not pay to park the vehicle they are riding in. Activity types
 * in {@link ParkingConfigGroup#getExemptActivityTypes()} - `home` - cancel one:
 * charging an agent to park at their own home would levy the max-stay cap every
 * night on everyone who lives in a dense zone, which is a standing penalty on
 * city-centre residence rather than a price on a travel choice.
 *
 * <p><b>Why the money events are deferred to {@code notifyAfterMobsim}.</b>
 * Emitting an event from inside an event handler re-enters the events manager
 * while it is draining its own queue. MATSim's roadpricing contrib accumulates
 * during the mobsim and emits afterwards for exactly this reason, and scoring
 * still sees them because {@code EventsToScore} finishes at the scoring
 * listener, which fires after {@code afterMobsim}. roadpricing itself is not in
 * the pinned jar - only its DTD ships - so the pattern is reproduced here
 * rather than reused.
 *
 * <p><b>No spatial work happens here.</b> The link-to-price table is built by
 * {@code build_matsim_run_inputs.py} by joining the run network to the city's
 * own job-density surface. This class reads a two-column file. A place name, a
 * coordinate or an extent in this file would be the defect CLAUDE.md forbids.
 */
public final class ParkingChargeHandler implements PersonArrivalEventHandler,
        PersonDepartureEventHandler, ActivityStartEventHandler, AfterMobsimListener {

    /** Purpose string carried on every emitted PersonMoneyEvent. */
    public static final String PURPOSE = "parking";
    /** Deliberately generic: naming an operator here would name a place. */
    public static final String PARTNER = "parkingOperator";

    private final EventsManager events;
    private final Map<Id<Link>, Double> priceByLink;
    private final Set<String> chargedModes;
    private final Set<String> exemptActivities;
    private final double windowStart;
    private final double windowEnd;
    private final double maxStaySeconds;

    private final Map<Id<Person>, Spell> open = new HashMap<>();
    private final List<Charge> pending = new ArrayList<>();
    private double lastEventTime = 0.0;

    /** One car parked at one link, from arrival until the next car departure. */
    private static final class Spell {
        private final Id<Link> link;
        private final double start;
        private boolean resolved;
        private boolean charged;

        private Spell(final Id<Link> link, final double start) {
            this.link = link;
            this.start = start;
        }
    }

    /** A crystallised charge, held until the mobsim is done. */
    private static final class Charge {
        private final Id<Person> person;
        private final double time;
        private final double amount;
        private final Id<Link> link;

        private Charge(final Id<Person> person, final double time, final double amount,
                       final Id<Link> link) {
            this.person = person;
            this.time = time;
            this.amount = amount;
            this.link = link;
        }
    }

    @Inject
    public ParkingChargeHandler(final Config config, final EventsManager events) {
        final ParkingConfigGroup cfg = ConfigUtils.addOrGetModule(config, ParkingConfigGroup.class);
        this.events = events;
        this.priceByLink = readPrices(cfg.getPriceFile());
        this.chargedModes = split(cfg.getChargedModes());
        this.exemptActivities = split(cfg.getExemptActivityTypes());
        this.windowStart = cfg.getChargedStartHour() * 3600.0;
        this.windowEnd = cfg.getChargedEndHour() * 3600.0;
        this.maxStaySeconds = cfg.getMaxStayMinutes() * 60.0;
    }

    private static Set<String> split(final String csv) {
        final Set<String> out = new HashSet<>();
        if (csv == null || csv.isEmpty()) {
            return out;
        }
        for (final String part : csv.split(",")) {
            final String trimmed = part.trim();
            if (!trimmed.isEmpty()) {
                out.add(trimmed);
            }
        }
        return out;
    }

    private static Map<Id<Link>, Double> readPrices(final String path) {
        final Map<Id<Link>, Double> out = new HashMap<>();
        if (path == null || path.isEmpty()) {
            return out;
        }
        try (BufferedReader in = Files.newBufferedReader(Paths.get(path), StandardCharsets.UTF_8)) {
            String line = in.readLine();          // header
            if (line == null) {
                throw new IOException("parking price file is empty: " + path);
            }
            while ((line = in.readLine()) != null) {
                if (line.isEmpty()) {
                    continue;
                }
                final int tab = line.indexOf('\t');
                if (tab < 0) {
                    throw new IOException("parking price file row is not tab separated: " + line);
                }
                out.put(Id.createLinkId(line.substring(0, tab)),
                        Double.valueOf(line.substring(tab + 1)));
            }
        } catch (final IOException e) {
            throw new UncheckedIOException("cannot read parking price file " + path, e);
        }
        return out;
    }

    // -- events ------------------------------------------------------------
    @Override
    public void handleEvent(final PersonArrivalEvent event) {
        this.lastEventTime = Math.max(this.lastEventTime, event.getTime());
        if (!this.chargedModes.contains(event.getLegMode())) {
            return;
        }
        if (this.priceByLink.containsKey(event.getLinkId())) {
            this.open.put(event.getPersonId(), new Spell(event.getLinkId(), event.getTime()));
        }
    }

    @Override
    public void handleEvent(final ActivityStartEvent event) {
        this.lastEventTime = Math.max(this.lastEventTime, event.getTime());
        final Spell spell = this.open.get(event.getPersonId());
        if (spell == null || spell.resolved) {
            return;                       // a later activity in the same spell
        }
        // `routing.accessEgressType` is `accessEgressModeToLink` by MATSim's
        // own default, so the activity that immediately follows a car arrival
        // is the synthetic `car interaction`, not the real destination. Reading
        // that as the destination made the `home` exemption match nothing and
        // charged every agent to park at their own house - measured, not
        // supposed: 267 of 641 charges in the first smoke run were at a link
        // where the person's real activity was home. Skip stage activities and
        // wait for the destination that follows.
        if (TripStructureUtils.isStageActivityType(event.getActType())) {
            return;
        }
        spell.resolved = true;
        spell.charged = !this.exemptActivities.contains(baseType(event.getActType()));
        if (!spell.charged) {
            this.open.remove(event.getPersonId());
        }
    }

    @Override
    public void handleEvent(final PersonDepartureEvent event) {
        this.lastEventTime = Math.max(this.lastEventTime, event.getTime());
        if (!this.chargedModes.contains(event.getLegMode())) {
            return;
        }
        final Spell spell = this.open.remove(event.getPersonId());
        if (spell != null && spell.charged) {
            accrue(event.getPersonId(), spell, event.getTime());
        }
    }

    /**
     * MATSim appends a duration suffix to activity types in some setups
     * (`home_43200`). Matching on the stem keeps the exemption working if that
     * is ever switched on, and is a no-op while it is not.
     */
    private static String baseType(final String actType) {
        final int cut = actType.lastIndexOf('_');
        if (cut <= 0) {
            return actType;
        }
        final String tail = actType.substring(cut + 1);
        for (int i = 0; i < tail.length(); i++) {
            if (!Character.isDigit(tail.charAt(i))) {
                return actType;
            }
        }
        return tail.isEmpty() ? actType : actType.substring(0, cut);
    }

    private void accrue(final Id<Person> person, final Spell spell, final double end) {
        final double overlap = Math.min(end, this.windowEnd) - Math.max(spell.start, this.windowStart);
        if (overlap <= 0.0) {
            return;
        }
        final double seconds = Math.min(overlap, this.maxStaySeconds);
        if (seconds <= 0.0) {
            return;
        }
        final double price = this.priceByLink.get(spell.link);
        this.pending.add(new Charge(person, end, -price * seconds / 3600.0, spell.link));
    }

    @Override
    public void notifyAfterMobsim(final AfterMobsimEvent event) {
        // A car still parked when the mobsim stops is charged to that moment,
        // capped like any other spell. Most of these are the day's last
        // activity; `home` among them has already been dropped as exempt.
        for (final Map.Entry<Id<Person>, Spell> entry : this.open.entrySet()) {
            if (entry.getValue().charged) {
                accrue(entry.getKey(), entry.getValue(), this.lastEventTime);
            }
        }
        this.open.clear();
        for (final Charge charge : this.pending) {
            this.events.processEvent(new PersonMoneyEvent(
                    charge.time, charge.person, charge.amount, PURPOSE, PARTNER,
                    charge.link.toString()));
        }
        this.pending.clear();
    }

    @Override
    public void reset(final int iteration) {
        this.open.clear();
        this.pending.clear();
        this.lastEventTime = 0.0;
    }

    /** Logged once at startup, so a run's console says what it charged. */
    @Override
    public String toString() {
        return "parking: " + this.priceByLink.size() + " priced links, modes "
                + new TreeSet<>(this.chargedModes) + ", window "
                + this.windowStart / 3600.0 + "-" + this.windowEnd / 3600.0
                + " h, max stay " + this.maxStaySeconds / 60.0 + " min, exempt "
                + new TreeSet<>(this.exemptActivities);
    }
}
