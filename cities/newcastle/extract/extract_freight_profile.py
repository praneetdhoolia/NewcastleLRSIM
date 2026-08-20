#!/usr/bin/env python
"""Measure the heavy-vehicle temporal profile from the classified hourly counts.

The freight background layer (issue #24, DECISIONS.md 9.49) needs two temporal
facts: WHEN heavy vehicles move within a day, and HOW MUCH lighter weekend
freight is than weekday freight. Both are MEASURED here rather than assumed -
the RMS permanent hourly counts carry a HEAVY VEHICLES classification, and the
study slice holds classified rows for stations inside the study area.

Outputs, both consumed by ``src/build/build_activity_chains.py``:

* ``data/processed/observed/freight_hourly_profile.csv`` -
  ``day_type,hour,share``: the share of a day's heavy volume departing in each
  hour, per day type. Shares sum to 1 within a day type.
* ``data/processed/observed/freight_day_factors.csv`` -
  ``day_type,factor,stations,station_days``: heavy daily volume relative to the
  same station's weekday mean (WEEKDAY = 1.0 by identity). The factor is the
  median across stations of each station's own SAT/SUN-to-weekday ratio, so a
  station that counts more days does not dominate the level.

Selection rules, all definitional rather than tuned:

* HEAVY VEHICLES classification only, resolved through the
  ``classification_seq -> classification_type`` pairing observed in the AADT
  slice - the hourly file carries only the code.
* Stations restricted to the study slice (``traffic_count_stations_newcastle``).
* Public holidays excluded: the model's day types are typical WEEKDAY/SAT/SUN
  and a public-holiday Monday is none of them.
* Only complete days are used: rows whose 24 hourly cells sum to their own
  ``daily_total`` (blank hourly cells are zero counts in this format; a row
  whose hours do not reconcile is a partial day).
* No year filter: every classified year in the raw download contributes. A
  cutoff would be an undeclared modelling choice; the profile is a SHAPE, and
  the volume it scales is declared and swept elsewhere
  (``B.freight.trip_ratio``).

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

import pandas as pd

RAW_ZIP = _city.path('data/raw/counts/rms_hourly_permanent.zip')
STATIONS = _city.path('data/processed/observed/traffic_count_stations_newcastle.csv')
AADT = _city.path('data/processed/observed/traffic_aadt.csv')
OUT_PROFILE = _city.path('data/processed/observed/freight_hourly_profile.csv')
OUT_FACTORS = _city.path('data/processed/observed/freight_day_factors.csv')

HOUR_COLS = ['hour_%02d' % h for h in range(24)]
# The model's service week (cities/<city>/city.json day_types) named over
# ISO day-of-week, which the raw data carries as 1=Monday..7=Sunday.
DAY_TYPE_OF_DOW = {1: 'WEEKDAY', 2: 'WEEKDAY', 3: 'WEEKDAY', 4: 'WEEKDAY',
                   5: 'WEEKDAY', 6: 'SAT', 7: 'SUN'}


def heavy_seq():
    """The classification code for HEAVY VEHICLES, read from the AADT slice.

    The hourly file carries only ``classification_seq``; the AADT slice carries
    both the code and its label, so the mapping is observed rather than typed.
    """
    a = pd.read_csv(AADT, usecols=['classification_seq', 'classification_type'])
    pairs = a.drop_duplicates()
    m = pairs[pairs.classification_type == 'HEAVY VEHICLES']
    if len(m) != 1:
        raise SystemExit('expected exactly one HEAVY VEHICLES classification code '
                         'in %s, found %d' % (AADT, len(m)))
    return int(m.classification_seq.iloc[0])


def load_heavy_days():
    seq = heavy_seq()
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
        raise SystemExit('no classified heavy-vehicle hourly rows found for the '
                         'study slice - the raw download or the slice changed')
    df = pd.concat(frames, ignore_index=True)
    hours = df[HOUR_COLS].fillna(0.0)
    # complete days only: the hourly cells must reconcile with the row's own
    # daily total (blank cells are zeros in this format; a mismatch is a
    # partial day, not a rounding artefact - both sides are integer counts)
    complete = hours.sum(axis=1).round(0) == df.daily_total.fillna(-1).round(0)
    df = df[complete & (df.daily_total > 0)].reset_index(drop=True)
    df[HOUR_COLS] = df[HOUR_COLS].fillna(0.0)
    df['day_type'] = df.day_of_week.map(DAY_TYPE_OF_DOW)
    return df


def main():
    df = load_heavy_days()
    day_types = sorted(df.day_type.unique())

    # hourly shape: total heavy volume per hour over total heavy volume,
    # per day type - a volume-weighted profile, which is what a background
    # load samples departures from
    rows = []
    for dt in day_types:
        d = df[df.day_type == dt]
        hour_sums = d[HOUR_COLS].sum()
        total = float(hour_sums.sum())
        for h in range(24):
            rows.append(dict(day_type=dt, hour=h,
                             share=round(float(hour_sums.iloc[h]) / total, 6)))
    profile = pd.DataFrame(rows)

    # day factors: each station's own SAT/SUN mean daily heavy volume over its
    # own weekday mean, median across stations - paired within station so the
    # mix of large and small stations cancels
    per = (df.groupby(['station_key', 'day_type']).daily_total.mean()
             .unstack('day_type'))
    per = per[per.get('WEEKDAY', pd.Series(dtype=float)).notna()]
    factors = []
    for dt in day_types:
        if dt == 'WEEKDAY':
            factors.append(dict(day_type=dt, factor=1.0,
                                stations=int(per.WEEKDAY.notna().sum()),
                                station_days=int((df.day_type == dt).sum())))
            continue
        ratio = (per[dt] / per.WEEKDAY).dropna()
        factors.append(dict(day_type=dt, factor=round(float(ratio.median()), 4),
                            stations=int(ratio.size),
                            station_days=int((df.day_type == dt).sum())))
    factors = pd.DataFrame(factors)

    profile.to_csv(OUT_PROFILE, index=False, lineterminator='\n')
    factors.to_csv(OUT_FACTORS, index=False, lineterminator='\n')
    print('freight_hourly_profile.csv: %d rows from %d station-days at %d stations'
          % (len(profile), len(df), df.station_key.nunique()))
    print('freight_day_factors.csv:')
    print(factors.to_string(index=False))
    peak = profile[profile.day_type == 'WEEKDAY'].nlargest(3, 'share')
    print('weekday peak hours: %s'
          % ', '.join('%02d:00 %.1f%%' % (r.hour, 100 * r.share)
                      for r in peak.itertuples()))


if __name__ == '__main__':
    main()
