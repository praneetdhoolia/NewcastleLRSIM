#!/usr/bin/env python
"""Measure the light-vehicle day-type factors from the classified hourly counts.

Three demand-generation quantities were assumed for want of this measurement,
and DECISIONS.md 9.61 replaces them with it (deliverable 0b): the
Saturday-to-Sunday level split inside the weekend (the weekend-to-weekday
LEVEL was already measured in C2; the split within it was not), the external
boundary tier's weekend scaling, and the weekend departure-time shift. The
same raw download that measured the freight profile (9.49) carries LIGHT
VEHICLES classified hourly rows for the study slice, so all three are
measurable by exactly the method ``extract_freight_profile.py`` proved.

Outputs, both consumed by ``src/build/build_activity_chains.py``:

* ``data/processed/observed/light_hourly_profile.csv`` -
  ``day_type,hour,share``: the share of a day's light volume moving in each
  hour, per day type. Shares sum to 1 within a day type.
* ``data/processed/observed/light_day_factors.csv`` -
  ``day_type,factor,depart_shift_h,stations,station_days``: light daily
  volume relative to the same station's weekday mean (WEEKDAY = 1.0 by
  identity; median across stations of each station's own ratio), and the
  integer-hour circular shift of that day type's hourly profile that best
  matches the weekday profile (the measured counterpart of the assumed
  weekend departure shift).

Selection rules follow the freight extraction verbatim, all definitional:
LIGHT VEHICLES classification resolved through the observed
``classification_seq`` pairing; stations restricted to the study slice;
public holidays excluded; complete days only; no year filter.

Deterministic: pure aggregation of a hashed raw download, no randomness.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', '..', 'src'))
import city as _city  # noqa: E402

import zipfile

import numpy as np
import pandas as pd

RAW_ZIP = _city.path('data/raw/counts/rms_hourly_permanent.zip')
STATIONS = _city.path('data/processed/observed/traffic_count_stations_newcastle.csv')
AADT = _city.path('data/processed/observed/traffic_aadt.csv')
OUT_PROFILE = _city.path('data/processed/observed/light_hourly_profile.csv')
OUT_FACTORS = _city.path('data/processed/observed/light_day_factors.csv')

HOUR_COLS = ['hour_%02d' % h for h in range(24)]
# The model's service week (cities/<city>/city.json day_types) named over
# ISO day-of-week, which the raw data carries as 1=Monday..7=Sunday.
DAY_TYPE_OF_DOW = {1: 'WEEKDAY', 2: 'WEEKDAY', 3: 'WEEKDAY', 4: 'WEEKDAY',
                   5: 'WEEKDAY', 6: 'SAT', 7: 'SUN'}


def light_seq():
    """The classification code for LIGHT VEHICLES, read from the AADT slice."""
    a = pd.read_csv(AADT, usecols=['classification_seq', 'classification_type'])
    m = a.drop_duplicates()
    m = m[m.classification_type == 'LIGHT VEHICLES']
    if len(m) != 1:
        raise SystemExit('expected exactly one LIGHT VEHICLES classification '
                         'code in %s, found %d' % (AADT, len(m)))
    return int(m.classification_seq.iloc[0])


def load_light_days():
    seq = light_seq()
    slice_keys = set(pd.read_csv(STATIONS, usecols=['station_key'])
                     .station_key.astype(str))
    usecols = (['station_key', 'classification_seq', 'day_of_week',
                'public_holiday', 'daily_total'] + HOUR_COLS)
    z = zipfile.ZipFile(RAW_ZIP)
    frames = []
    for name in sorted(z.namelist()):
        df = pd.read_csv(z.open(name), usecols=usecols)
        df = df[(df.classification_seq == seq)
                & df.station_key.astype(str).isin(slice_keys)
                & (~df.public_holiday.astype(bool))]
        if len(df):
            frames.append(df)
    if not frames:
        raise SystemExit('no classified light-vehicle hourly rows found for '
                         'the study slice - the raw download or the slice '
                         'changed')
    df = pd.concat(frames, ignore_index=True)
    hours = df[HOUR_COLS].fillna(0.0)
    complete = hours.sum(axis=1).round(0) == df.daily_total.fillna(-1).round(0)
    df = df[complete & (df.daily_total > 0)].reset_index(drop=True)
    df[HOUR_COLS] = df[HOUR_COLS].fillna(0.0)
    df['day_type'] = df.day_of_week.map(DAY_TYPE_OF_DOW)
    return df


def best_shift(weekday_profile, day_profile):
    """Integer-hour circular shift of `day_profile` best matching the weekday.

    argmax over shifts of the dot product of the weekday profile with the
    day profile rolled LATER by the shift - i.e. how many hours later the
    weekend day moves to look most like a weekday. Ties break to the
    smallest shift, and the search covers the full circle so nothing about
    the answer is presumed.
    """
    w = np.asarray(weekday_profile, dtype=float)
    p = np.asarray(day_profile, dtype=float)
    scores = [float(np.dot(w, np.roll(p, -s))) for s in range(24)]
    return int(np.argmax(scores))


def main():
    df = load_light_days()
    day_types = sorted(df.day_type.unique())

    profiles = {}
    rows = []
    for dt in day_types:
        d = df[df.day_type == dt]
        hour_sums = d[HOUR_COLS].sum()
        share = (hour_sums / hour_sums.sum()).to_numpy()
        profiles[dt] = share
        for h in range(24):
            rows.append(dict(day_type=dt, hour=h, share=round(float(share[h]), 6)))
    pd.DataFrame(rows).to_csv(OUT_PROFILE, index=False)

    per_station = (df.groupby(['station_key', 'day_type'])
                   .daily_total.mean().unstack())
    out = []
    for dt in day_types:
        if dt == 'WEEKDAY':
            factor, n_st = 1.0, int(per_station['WEEKDAY'].notna().sum())
        else:
            both = per_station[[dt, 'WEEKDAY']].dropna()
            ratio = both[dt] / both['WEEKDAY']
            factor, n_st = float(ratio.median()), len(both)
        shift = 0 if dt == 'WEEKDAY' else best_shift(profiles['WEEKDAY'],
                                                     profiles[dt])
        out.append(dict(day_type=dt, factor=round(factor, 4),
                        depart_shift_h=shift, stations=n_st,
                        station_days=int((df.day_type == dt).sum())))
    pd.DataFrame(out).to_csv(OUT_FACTORS, index=False)

    f = {r['day_type']: r for r in out}
    sat, sun = f.get('SAT', {}), f.get('SUN', {})
    print('light day factors: ' + '  '.join(
        '%s=%.4f (shift %dh, %d stations)' % (r['day_type'], r['factor'],
                                              r['depart_shift_h'],
                                              r['stations'])
        for r in out))
    if sat and sun and sun['factor'] > 0:
        print('SAT:SUN split = %.4f (was assumed 1.1875)'
              % (sat['factor'] / sun['factor']))
    print('wrote %s and %s' % (OUT_PROFILE, OUT_FACTORS))


if __name__ == '__main__':
    main()
