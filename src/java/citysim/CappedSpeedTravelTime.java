package citysim;

import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.population.Person;
import org.matsim.core.router.util.TravelTime;
import org.matsim.vehicles.Vehicle;

/**
 * Router travel time for a network-simulated unmotorised mode (DECISIONS.md
 * 9.54): a walker or cyclist traverses a link at the LOWER of the link's free
 * speed and their own physical speed, unaffected by motor congestion — a
 * pedestrian on the footpath beside a jammed road still walks at walking
 * pace. The cap is the mode's declared speed, read from the same vehicle type
 * the qsim itself loads, so the router's estimate and the mobsim's physics
 * cannot drift apart: one declared value, two consumers, byte-equal.
 *
 * <p>Nothing here is a behavioural weight — the disutility of the time this
 * returns is priced by the mode's own scoring parameters, exactly as before.
 */
public final class CappedSpeedTravelTime implements TravelTime {

    private final double capMetresPerSecond;

    public CappedSpeedTravelTime(final double capMetresPerSecond) {
        if (!(capMetresPerSecond > 0.0)) {
            throw new IllegalArgumentException(
                    "a network-simulated mode needs a positive speed cap; got "
                    + capMetresPerSecond + ". The caps are declared in the "
                    + "registry and carried by the vehicles file.");
        }
        this.capMetresPerSecond = capMetresPerSecond;
    }

    @Override
    public double getLinkTravelTime(final Link link, final double time,
                                    final Person person, final Vehicle vehicle) {
        return link.getLength()
                / Math.min(link.getFreespeed(time), this.capMetresPerSecond);
    }
}
