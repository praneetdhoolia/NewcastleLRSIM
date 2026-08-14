package citysim;

import org.matsim.core.config.ReflectiveConfigGroup;

/**
 * The `parking` config module: what a car is charged to stand still.
 *
 * <p>Every value here is written by {@code build_matsim_run_inputs.py} from
 * {@code config/registry/<city>/A_supply.json}. None of them may be typed into
 * a script, and none is a place: the price of a <em>link</em> is looked up in
 * {@link #getPriceFile()}, which the build produces by joining the run network
 * to the city's own job-density surface. Java does no spatial work at all.
 *
 * <p>Declaring this as a real {@link ReflectiveConfigGroup} rather than letting
 * MATSim absorb an unknown module has two consequences worth having: an
 * unrecognised parameter fails the run instead of being silently ignored, and
 * the module is written into the output config dump, so a result carries the
 * parking regime that produced it.
 *
 * <p>See DECISIONS.md 9.31 and issue #33.
 */
public final class ParkingConfigGroup extends ReflectiveConfigGroup {

    public static final String GROUP_NAME = "parking";

    private String priceFile = "";
    private double maxStayMinutes = 0.0;
    private double chargedStartHour = 0.0;
    private double chargedEndHour = 0.0;
    private String chargedModes = "car";
    private String exemptActivityTypes = "";

    public ParkingConfigGroup() {
        super(GROUP_NAME);
    }

    /**
     * Tab-separated {@code link_id\tprice_aud_hr}, one row per PRICED link.
     * A link absent from the file is free, so the file holds roughly 22k rows
     * of the run network's ~144k car links rather than all of them. Empty
     * disables parking charging entirely.
     */
    @StringGetter("priceFile")
    public String getPriceFile() {
        return this.priceFile;
    }

    @StringSetter("priceFile")
    public void setPriceFile(final String value) {
        this.priceFile = value == null ? "" : value.trim();
    }

    /**
     * The charge cap, in minutes: a spell is charged for
     * {@code min(duration, maxStayMinutes)}. This UNDER-charges a long stay,
     * which is a declared modelling choice - representing over-stay properly
     * needs an infringement rate nobody has measured here.
     */
    @StringGetter("maxStayMinutes")
    public double getMaxStayMinutes() {
        return this.maxStayMinutes;
    }

    @StringSetter("maxStayMinutes")
    public void setMaxStayMinutes(final double value) {
        this.maxStayMinutes = value;
    }

    /** Start of the charged window, in hours after midnight. */
    @StringGetter("chargedStartHour")
    public double getChargedStartHour() {
        return this.chargedStartHour;
    }

    @StringSetter("chargedStartHour")
    public void setChargedStartHour(final double value) {
        this.chargedStartHour = value;
    }

    /**
     * End of the charged window, in hours after midnight. An end at or before
     * the start means nothing is charged on this day type - which is how a
     * free Sunday is expressed, rather than by a separate flag.
     */
    @StringGetter("chargedEndHour")
    public double getChargedEndHour() {
        return this.chargedEndHour;
    }

    @StringSetter("chargedEndHour")
    public void setChargedEndHour(final double value) {
        this.chargedEndHour = value;
    }

    /**
     * Comma-separated leg modes that occupy a parking space. `car` only: a
     * passenger does not pay to park the vehicle they are riding in, and
     * charging `ride` as well would bill the same vehicle twice.
     */
    @StringGetter("chargedModes")
    public String getChargedModes() {
        return this.chargedModes;
    }

    @StringSetter("chargedModes")
    public void setChargedModes(final String value) {
        this.chargedModes = value == null ? "" : value.trim();
    }

    /**
     * Comma-separated activity types at which a parked car is not charged.
     * `home` by default - see DECISIONS.md 9.31 for why charging it would be a
     * standing levy on living in a dense zone rather than a price on travel.
     */
    @StringGetter("exemptActivityTypes")
    public String getExemptActivityTypes() {
        return this.exemptActivityTypes;
    }

    @StringSetter("exemptActivityTypes")
    public void setExemptActivityTypes(final String value) {
        this.exemptActivityTypes = value == null ? "" : value.trim();
    }
}
