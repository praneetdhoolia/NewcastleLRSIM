# Point-to-point (taxi + rideshare) mode — evidence dossier and task definition

*18 August 2026. The "no separate taxi/rideshare mode" decision (STATUS declined
table; DECISIONS.md) was **re-opened by the project owner on 18 Aug 2026 on new
evidence**: IPART now surveys Newcastle and Hunter as its own point-to-point
region, and the passenger service levy means every p2p trip in NSW is counted.
Owner direction: infer inputs from open sources (labelled, swept), do not lodge
data requests. The formal DECISIONS.md entry is written when the mode is built.*

**Nothing below is observed for this study area unless marked measured. Every
inferred value carries its band and enters the registry with a sweep.**

## What open sources give

| Quantity | Value | Grade | Source |
|---|---|---|---|
| Taxi fleet, greater Newcastle | ~175 vehicles (13cabs, the largest Hunter provider); 6,164 licences state-wide | literature | 13cabs company statements; TfNSW taxi licensing review, Mar 2026 |
| Rideshare fleet | unpublished anywhere | — | would be assumed + swept (fleet size barely matters for a teleported mode) |
| Taxi fares (urban max, from 1 Jul 2025) | flagfall $5.17; $2.61/km first 12 km then $2.37/km; night $3.10/$2.82 | **measured** | TfNSW Point to Point Transport (Fares) Order 2025 |
| Rideshare fares, Newcastle | base ~$1.80–2.10; ~$1.40–1.60/km; per-minute and booking fee unresolved; surge unknowable | literature | aggregator estimates; sweep wide |
| P2P use incidence, state-wide 2025 | 48% used rideshare, 39% taxi in past 6 months; taxis ahead of rideshare in regional areas; Newcastle rideshare grew ~18%/yr (2018 survey) | literature | IPART annual p2p survey 2025 (Newcastle & Hunter regional table in the full paper — PDF fetch timed out, extract on next pass) |

## Derived volume constraint (inference, wide band)

Study-area adults ≈ 490k. If 40–50% use p2p within 6 months and active users
average 2–4 trips/month (state-pattern assumption, NOT yet confirmed for the
region), daily p2p trips ≈ **10,000–35,000**, i.e. **~0.5–1.5% of the 2.3M
daily trips** — consistent with fitting inside the HTS "Other" bucket (3.2%
incl. motorcycles). This band is the placeholder **constraint** until the IPART
regional table tightens it. The levy trip counts remain the gold source if ever
requested.

## How the mode enters (when built)

- **Teleported priced mode** — car-like travel time, fare disutility from the
  measured taxi schedule / literature rideshare rates, no parking charge. No
  fleet simulation (a DRT contrib is a §14 toolchain change, unjustified at ~1%
  of trips).
- Every value declared in `cities/newcastle/registry/` with provenance grade and
  sweep; regenerate the reference docs; `check_hardcoding --strict` stays 0.
- Validated against the derived volume band as a **constraint, never a target**
  — the pre-registered 67/143 split cannot grow.
- **Sequenced after the calibrated base (task 4.4)**: a ~1% refinement must not
  precede the measured 10–20 pp defects (ride, walk, counts). Its later
  relevance is real: p2p competes with the light rail for exactly the short CBD
  and night-time trips the footfall hypotheses examine.

## Sources

- TfNSW Point to Point Transport (Fares) Order, June 2025 —
  https://www.transport.nsw.gov.au/system/files/media/documents/2025/Point-to-Point-Transport-Fares-Order-June-2025.pdf
- TfNSW rank-and-hail fares page — https://transportnsw.info/travel-info/ways-to-get-around/taxi-hire-vehicle/rank-hail-taxi-fares-charges
- IPART Information Paper, Survey of Point to Point Transport Use 2025 —
  https://www.ipart.nsw.gov.au/sites/default/files/cm9_documents/Information-Paper-Survey-of-Point-to-Point-Transport-Use-2025-(1).PDF
- IPART media release, 20 Feb 2026 —
  https://www.ipart.nsw.gov.au/sites/default/files/cm9_documents/Media-Release-Point-to-Point-Transport-Use-Survey-20-February-2026.PDF
- TfNSW taxi licensing amendments statutory review discussion paper, Mar 2026 —
  https://hdp-au-prod-app-nsw-haveyoursay-files.s3.ap-southeast-2.amazonaws.com/8217/7448/3600/tax-licensing-amendments-statutory-review-discussion-paper-march-2026.pdf
- 13cabs Newcastle fleet statements — https://www.13cabs.com.au/locations/newcastle/
- Newcastle Herald on the IPART survey (rideshare +18%/yr) —
  https://www.theherald.com.au/story/5828274/ridesharing-use-on-the-move-in-newcastle-ipart-survey-shows/
