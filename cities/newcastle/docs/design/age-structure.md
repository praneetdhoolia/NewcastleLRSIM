# Age structure and the tasks each age group is simulated doing

*Evidence dossier and fix specification, 18 August 2026. Written for tasks
4.2.5/4.2.6 ([`STATUS.md`](../STATUS.md) §"The plan") against the project goal:
whether the twin predicts the correct ridership **per mode** — and ridership per
mode is not answerable if the population making the trips has the wrong age
structure, the wrong employment, or children who never co-locate with the
parent escorting them. Everything quantitative below is measured from tables
already in the committed package or reproduced from the built synthetic
population; the external figures are cross-checks, not inputs.*

---

## 1. What each age group does in this model — the classification

The model's activity vocabulary is six tour purposes (HW work, HE education,
HS shopping, HO social/personal, WB work business, HX serve-passenger) plus
being carried as a car passenger (`ride`). Which purposes a person can draw is
decided by five person attributes, all set in B1
([`build_population.py`](../../../../src/build/build_population.py)):
`employment_status`, `student_status`, `licence_holder`, `car_available`, `age`
itself. The table states, per age group, what the attributes should be — with
the census table that grounds each column — and therefore which tasks the
group is simulated doing.

| age | employed (G46, stated basis) | FT share of employed (G46) | attending education (G01) | licence ([lit.](../../registry/B_demand.json), `B.population.licence_rate_by_age_band`) | tasks simulated |
|---|---:|---:|---:|---:|---|
| 0–4 | 0 (definition) | — | **32.0%** (childcare/preschool) | 0 | HE tour when attending (escorted in practice); otherwise home. Cannot escort, cannot drive |
| 5–14 | 0 under 15 (definition) | — | **94.9%** (school) | 0 | HE on school days; secondary tours thinned to `child_tour_retention` under 12 |
| 15–19 | **54.5%** | **24.0%** | **72.6%** (school → tertiary transition) | 0 under 17, then band rate | School dominates; employment is overwhelmingly part-time alongside study. Youth unemployment 12.3% of the LF — the highest of any band |
| 20–24 | **77.8%** | **50.2%** | **37.9%** (tertiary) | 0.62 | Work and study mix; the crossover band from HE to HW |
| 25–34 | **82.5%** | **65.9%** | 5.5% | 0.88 | HW dominant; HX begins (parenthood) |
| 35–44 | **83.8%** | **65.4%** | 5.5% | 0.93 | HW + the peak school-run (HX) years |
| 45–54 | **80.3%** | **67.6%** | 5.5% | 0.94 | HW dominant |
| 55–64 | **60.7%** | **59.6%** | 5.5% | 0.93 | Transition to retirement begins — a fifth of the band has already left the LF |
| 65–74 | **16.1%** | **35.7%** | 5.5% | 0.88 | Mostly retired: HS/HO daytime travel, and the cohort that *rides* rather than drives |
| 75–84 | **2.4%** | **16.4%** | 5.5% | 0.72 | Almost none employed. HS/HO only; licence holding falls with the NSW ≥75 annual medical assessment |
| 85+ | **0.3%** | — | 5.5% | 0.45 | HS/HO at reduced rates; the largest `ride`-dependent group per capita |

Employment rates are **of persons with a stated labour-force status** (G46
`P_Tot_LF + P_Not_in_LF`), computed over the 1,500 core SA1s; attendance rates
are G01 attendees over the band population, same extent. The G01 age groups are
coarser than single years, so the rate is flat *within* a group — stated as a
limitation in §5.

### Cross-checks against published figures (checks, not inputs)

- **Older employment**: AIHW reports 65+ workforce participation at **15%** in
  April 2021 — the G46-derived 16.1% (65–74) / 2.4% (75–84) bracket it exactly
  ([AIHW, Older Australians: employment and work](https://www.aihw.gov.au/reports/older-people/older-australians/contents/employment-and-work)).
- **Tertiary attendance**: ABS reports **42.3% of 18–24-year-olds** attending
  tertiary education in 2021; the local G01 20–24 rate is 37.9% and 15–19 is
  72.6% (school-inclusive), consistent for a region with lower university
  density than the capitals ([ABS, Education in Australia](https://www.abs.gov.au/articles/education-australia-abc-bs-and-cs)).
- **Older licence holding**: NSW licence retention at age 75 measured at
  74.5–81.1% around the 2008 licensing reform; the declared 0.72 for 75–84 sits
  inside it ([Impacts of the 2008 NSW older driver licensing reform](https://www.sciencedirect.com/science/article/abs/pii/S2214140525001173)).
- **Age-mode direction**: TfNSW reports PT/walk concentrated under 30 and
  car reliance rising over 60 ([HTS](https://www.transport.nsw.gov.au/data-and-research/data-and-insights/surveys/household-travel-survey-hts)) —
  which is why an inflated elderly *commuter* count contaminates exactly the
  mode split this project exists to test.

---

## 2. The three defects, measured (18 August 2026)

Measured on the pre-fix `B1_synthetic_population.csv` against the census
tables before anything was changed — the numbers are the built file's own, not
the handover brief's. The post-fix rates are a committed artefact:
`_population_report.json` now carries `by_abs_age_band` so every rebuild
states its realised age-conditional rates beside the census they were drawn
from.

### D1 — the 75+ population mostly does not exist

`age_sex_dist()` reads single-year columns `Age_yr_<N>_<sex>`, which G04 stops
publishing at 79: ages 80–99 are in grouped columns (`Age_yr_80_84_*`,
`85_89`, `90_94`, `95_99`) the loop never touches. Only 100+ survives via its
special case.

| band | synthetic | census (G01) | error |
|---|---:|---:|---|
| 65–74 | 77,854 | 66,300 | +17% (absorbs redistributed mass) |
| 75–84 | 26,285 | 38,507 | **−32%** (only 75–79 present) |
| 85+ | **186** | **15,151** | **−98.8%** (only 100+ present) |

≈**27,000 people aged 75+ are missing** — the most ride- and PT-dependent
cohort in the population — and their probability mass is redistributed across
every younger band, inflating each by 13–19%.

### D2 — one flat employment rate makes ~40,000 phantom elderly workers

The docstring claims age-conditional labour force status (G46); the code
applies one flat G43 15+ rate to every adult, one flat FT share, and a flat
6% unemployment residual:

| band | synthetic employed | G46 observed | synthetic FT share | G46 FT share |
|---|---:|---:|---:|---:|
| 15–19 | 58.8% | 54.5% | 0.563 | **0.240** |
| 25–34 | 59.1% | **82.5%** | 0.576 | 0.659 |
| 35–44 | 60.0% | **83.8%** | 0.575 | 0.654 |
| 65–74 | **52.2%** | **16.1%** | 0.556 | 0.357 |
| 75–84 | **47.8%** | **2.4%** | 0.558 | 0.164 |
| 85+ | 29.0% | 0.3% | 0.611 | 0.159 |

Two errors in opposite directions: the elderly get ~40,000 phantom commuters
(53,299 employed 65+ against a census-implied ≈13,200 at the synthetic band
sizes), while prime working age is understated by >20 pp — so the model
simultaneously over-generates elderly HW tours and under-generates prime-age
ones. G46A/B (employment status × age × sex, SA1) has been in the package
since P1 and was loaded (`r46`) but never read.

### D3 — every under-18 is a full-time student, including all 22,115 aged 0–4

`student_status` is `full_time` for 100% of under-18s. G01 measures education
attendance at **32.0%** for 0–4 (childcare/preschool), **94.9%** for 5–14 and
**72.6%** for 15–19. For 18–24 a flat 0.35 was assumed against an observed
37.9% attendance (× a full-time share); for 25+ full-time study was
impossible (observed: 5.5% attendance).

---

## 3. The fix, as implemented

All in [`build_population.py`](../../../../src/build/build_population.py); the
tour-selection priority in
[`build_activity_chains.py`](../../../../src/build/build_activity_chains.py).

1. **Ages** (D1): `age_sex_dist()` also consumes the grouped 80–84 / 85–89 /
   90–94 / 95–99 columns, apportioning each to the model band containing it
   (80–84 → 75–84; 85–99 → 85+). Within-band single-year ages stay uniform.
2. **Employment** (D2): per person, from the person's own SA1 row of G46A/B by
   sex and ABS age band — P(employed | stated status), then FT/PT from the
   band's own FT share, then P(unemployed | not employed) from the band's own
   unemployment. A SA1×band×sex cell with no population (7.4% of cells) falls
   back to the core-region band×sex aggregate. No assumed scalar remains: the
   flat `emp_rate`, `ft_share`, and the 0.06 unemployment literal are deleted.
3. **Students** (D3): per person, from the person's own SA1 row of G01 by age
   group (0–4, 5–14, 15–19, 20–24, 25+; regional fallback as above). Attendees
   under 18 are `full_time` (school is full-time by definition). Attendees 18+
   split full/part-time by `B.population.tertiary_ft_share` — **assumed and
   swept**, because the table that measures it (G15, full/part-time student
   status by age) is not in the package. Declared in the registry with the
   non-acquisition reason; a G15 harvest is a deliverable-0b candidate, not a
   silent assumption.
4. **Work/study priority** (consequence of 2+3, in B2): the tour draw was
   `employed → HW, elif full-time student → HE`, which sent every employed
   full-time student to work. It becomes: full-time **employed** → HW;
   otherwise full-time **student** → HE; otherwise part-time employed → HW.
   A 16-year-old with a part-time job now goes to school on a weekday. The
   B2 rate solve uses the same reclassified fractions, so the realised trip
   rate stays calibrated to the observed HTS 3.473 trips/person/day.

**What this changes downstream, stated in advance:** employment falls from
50.4% to ≈44% of persons (the census level), so HW tours fall and the
secondary purposes absorb the difference through the existing rate solve;
students rise at 18+, fall sharply at 0–4; ≈27,000 persons move into 75+
bands, where licence holding (0.72/0.45) and employment (≈0) make them
HS/HO travellers with high `ride` dependence. Mode share is expected to move;
that is the point, and it is measured on the next run rather than predicted
here.

---

## 4. Escort coupling (task 4.2.5, summarised — decision record in DECISIONS.md §9.46)

The same evidence pass measures **0.104% of ride trips sharing an OD with a
household car trip**, traced to `HX` escort tours drawing their destination
from the education attractor *distribution* and their hour from the profile,
never from the escorted person's actual trip. The binding (a parent's HX tour
takes an actual household member's drawn destination and departure) is
specified and recorded in `DECISIONS.md` §9.46 — it retargets existing HX
tours and adds none, because the HX rate is already calibrated to the observed
`Serve passenger` 10–19.5%.

The age-structure fix is sequenced with it because the *escorted* population
(children attending education, elderly non-drivers) is exactly the population
D1–D3 distorts.

---

## 5. Deliberately not done, and why

- **Age-conditional secondary tour rates** (retirees shop more, teens travel
  socially more): no HTS age dimension exists in the held LGA extracts, so any
  rates would be invented. The uniform Poisson rates stay, stated.
- **G15 harvest** for the tertiary full/part-time split: consumable but
  second-order (it decides HE tour-making for the ≈38%-attending 20–24 band
  only within its full-time fraction). Declared as an assumed, swept field
  instead — owner directive: do one thing right, do not harvest ahead of need.
- **Within-group attendance shape** (a 15-year-old vs a 19-year-old): G01
  publishes 15–19 as one group; splitting it by single year would be invention.
  The flat group rate is stated as a limitation.
- **Occupation/income by age** (G60/G17 are age-conditional too): neither
  drives tour generation; not touched.
- **Aged-care/institutional population**: G01 counts persons in non-private
  dwellings, the synthesis houses everyone in private dwellings. Some of the
  restored 85+ band would in reality travel less than the tour rates imply;
  the mobility-impairment ramp (5%→30% by age 100) is the only brake. Stated,
  not fixed — no local observation separates the two.

## 6. Sources

Package (measured): `census2021_G46A/B_SA1.csv`, `census2021_G01_SA1.csv`,
`census2021_G04A/B_SA1.csv`, `demand/population/B1_synthetic_population.csv`.
External (cross-checks only):
[AIHW Older Australians — employment](https://www.aihw.gov.au/reports/older-people/older-australians/contents/employment-and-work) ·
[ABS Education in Australia](https://www.abs.gov.au/articles/education-australia-abc-bs-and-cs) ·
[ABS Education and training: Census 2021](https://www.abs.gov.au/statistics/people/education/education-and-training-census/latest-release) ·
[ABS 2021 Census dictionary, TYSTAP](https://www.abs.gov.au/census/guide-census-data/census-dictionary/2021/variables-topic/education-and-training/educational-institution-attendee-status-tystap) ·
[NSW older-driver licensing reform study](https://www.sciencedirect.com/science/article/abs/pii/S2214140525001173) ·
[TfNSW Household Travel Survey](https://www.transport.nsw.gov.au/data-and-research/data-and-insights/surveys/household-travel-survey-hts).
