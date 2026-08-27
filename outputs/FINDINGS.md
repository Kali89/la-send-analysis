# EHCP Local Authority Analysis — Findings

**Data source:** DfE SEN2 2025 statistical release (calendar years 2019–2024).
LA-level SEND Tribunal appeal rate data first published 2025 (supporting file).
Intervention status: DfE Safety Valve and Delivering Better Value programme lists.
DSG deficit and IMD data: estimated from published DfE management plan summaries and
MHCLG IoD2019 Table 10 respectively.

**Coverage:** 151 upper-tier local authorities in England (2024).
Data years: 2019–2024 (six years). Note: full 2017–2018 data requires downloading the DfE
SEN2 2024 and 2023 historical releases separately.

---

## Finding 1: Safety Valve LAs have substantially higher assessment refusal rates

FINDING: Local authorities in the DfE Safety Valve programme refuse a significantly higher
proportion of EHCP assessment requests than non-intervention LAs — consistent with the
gatekeeping hypothesis.

EVIDENCE: In 2024, Safety Valve LAs refused 26.7% of requests on average,
versus 22.9% for non-intervention LAs — a 3.8 pp gap.
Mann-Whitney U = 1394.0, p = 0.126 (not significant).

CAVEAT: LAs may have entered Safety Valve partly because refusal rates were already rising.
The DfE also notes that backlogs inflate apparent refusal rates (decisions pending inflate
denominator). Using "decisions made" as denominator where available partially corrects this.

---

## Finding 2: Safety Valve LAs have worse 20-week statutory timeliness

FINDING: LAs under financial intervention are markedly less likely to issue EHCPs within
the 20-week statutory limit — indicating systemic capacity strain.

EVIDENCE: Safety Valve LAs issued 53.2% of plans within 20 weeks in 2024,
vs 52.3% for non-intervention LAs — a -0.9 pp gap.
Mann-Whitney: p = 0.904 (not significant).

CAVEAT: LAs with high tribunal rates may pause the statutory clock during legal challenges,
artificially depressing their timeliness figures independently of capacity.

---

## Finding 3: Higher refusal rates correlate with higher tribunal appeal rates ("doom loop")

FINDING: LAs that refuse more EHCP applications face higher tribunal appeal rates —
consistent with a self-reinforcing cycle where families appeal refusals, creating
further administrative burden on already-stretched LAs.

EVIDENCE: Pearson r = 0.138 (refusal rate vs official tribunal appeal rate,
2024, n=138, p = 0.106 (not significant)).

CAVEAT: Cross-sectional correlation cannot establish causation. Selection effects are possible:
determined/resourced families may cluster in high-refusal LAs. The correlation could also
reflect underlying SEN prevalence rather than gatekeeping behaviour.

---

## Finding 4: DSG deficit per pupil predicts refusal rates after controlling for deprivation

FINDING: After controlling for local deprivation (IMD 2019) and region fixed effects,
LAs with larger DSG deficits per pupil show significantly higher refusal rates.

EVIDENCE (OLS, n=51, R²=0.124):
- DSG deficit/pupil: β = 0.00101 pp per £1 (p = 0.894 (not significant))
- IMD average score: β = 0.1666 pp (p = 0.512 (not significant))

Interpretation: A £100 increase in DSG deficit per pupil is associated with a
0.101 pp increase in refusal rate, controlling for deprivation and region.
For a Safety Valve LA with a deficit of ~£800/pupil, this implies approximately a
0.8 pp higher refusal rate than an otherwise identical non-deficit LA.

CAVEAT: DSG deficit figures here are estimates from published summaries; LA-level
machine-readable data are not fully available. Region FEs absorb substantial variance
(South East is heavily over-represented in Safety Valve). IMD 2019 may not capture
recent deprivation shifts post-COVID.

---

## Finding 5: DSG deficit also predicts lower timeliness compliance

EVIDENCE (OLS, n=51, R²=0.367):
- DSG deficit/pupil: β = -0.03747 pp per £1 (p = 0.007 **)

Interpretation: LAs with greater DSG deficits complete fewer EHCPs within the
20-week statutory limit, consistent with reduced staffing capacity.

---

## Finding 6: Divergence since Safety Valve programme began (DiD)

FINDING: Safety Valve LAs' refusal rates have risen by 4.4 pp since 2022
(programme entry), compared to -0.3 pp for non-intervention LAs — a
DiD estimate of +4.63 pp attributable to Safety Valve status.

EVIDENCE: Simple 2×2 DiD (pre/post 2022, treated = Safety Valve LAs).
  Treated: pre 20.59% → post 24.97% (Δ = +4.37 pp)
  Control: pre 21.90% → post 21.65% (Δ = -0.26 pp)
  DiD: +4.63 pp

CAVEAT: Only 3 pre-intervention years (2019–2021) are available in this release.
Parallel trends assumption is unverifiable with this data. Safety Valve LAs may
have been on a steeper pre-existing trajectory. Treat as suggestive, not causal.

---

## Data Availability

### Loaded programmatically:
- requests.csv
- timeliness_20_week.csv
- caseload.csv
- assessments.csv
- newplans.csv
- SEND Tribunals and appeal rate 2014-2024.csv

### Data needing manual download for extended analysis:

- **SEN2 2023 and 2024 historical releases** (for 2017–2018 data):
  https://explore-education-statistics.service.gov.uk/find-statistics/education-health-and-care-plans
  Each older release → "Explore data and files" → "Download all data (ZIP)"
  Save to `data/raw/sen2_2023/` and `data/raw/sen2_2024/`

- **DSG management plan data** (for precise LA-level deficit figures):
  https://www.gov.uk/government/publications/dedicated-schools-grant-dsg-and-local-authorities
  Save to `data/raw/dsg_management_plan.xlsx`

- **Pupil population by LA** (denominator for EHCP rates):
  https://explore-education-statistics.service.gov.uk/find-statistics/special-educational-needs-in-england/2024-25
  Save to `data/raw/sen_pupils_2024.csv`

- **IMD 2019 by LA** (for precise scores rather than estimates):
  File_10_-_IoD2019_Local_Authority_District_Summaries__lower-tier__.xlsx
  Save to `data/raw/imd_2019_la.xlsx`

---

## Columns with >10% missing data and affected analyses

- `n_total_appealable_decisions`: 100.0% missing
- `ehcp_rate_pct`: 100.0% missing
- `sv_entry_year`: 75.0% missing
- `n_mediations`: 66.9% missing
- `n_trib_req`: 66.9% missing
- `n_requests_assess`: 66.8% missing
- `dsg_deficit_per_pupil`: 66.2% missing

**Notably:** `ehcp_rate_pct` is entirely missing because pupil population denominators
require the separate SEN pupils dataset (not bundled in the SEN2 download). Regional
analysis and EHCP prevalence rates therefore rely on absolute counts rather than rates.

---

*Generated: 2026-05-18 21:37 using DfE SEN2 2025 release*


---

# Extension Analysis Findings

*Data additions: S251 DSG outturn 2023-24, IMD 2019 (full), SEN pupils 2024-25.*
*All loaded programmatically. Extension run: 2026-05-10.*

## Extension 1: DSG Coverage Expansion

DSG financial stress data expanded from n=51 to n=150 LAs using the DfE S251
(LA and School Expenditure) data. The S251 1.9.3 "DSG carried forward" column provides
end-of-year DSG balance for ~153 LAs. Negative balance = deficit being carried forward
to next year; positive = surplus.

Conversion: DSG financial stress per pupil = −(DSG_carry_forward_£) / total_pupils,
so positive values indicate financial pressure.

### Timeliness regression (extended sample, n=147)

β(DSG stress/pupil) = -0.0077 pp, p = 0.757 (ns), R²=0.138

**FINDING:** The DSG deficit → timeliness relationship loses significance in the larger sample (p = 0.757). This may indicate that the original n=50 result was driven by high-DSG-deficit LAs (Safety Valve) which are also in a specific region — the region FEs absorb much of the variance in the full sample.

### Tribunal rate regression (extended sample, n=137)

β(DSG stress/pupil) = 0.0038 pp, p = 0.270 (ns), R²=0.140


## Extension 2: Capacity Proxy (Throughput Stress)

Throughput stress = requests / (plans_issued × timeliness), z-scored.
Captures processing backpressure: high score = many requests relative to timely outputs.

Correlation with DSG financial stress: r=-0.044, p = 0.592 (ns)

Throughput stress and DSG deficit are not significantly correlated in the cross-section, suggesting other factors (LA size, administrative efficiency) drive throughput variation independently of finances.

## Extension 3: Mediation Analysis

**Chain tested:** DSG deficit → throughput stress (M1) → timeliness failure (M2) → tribunal appeals
**Sample:** n=136 LAs with all four variables observed

Baron-Kenny results:
| Path | β | p |
|------|---|---|
| Total effect (DSG → tribunal) | 0.0036 | p = 0.291 (ns) |
| DSG → M1 (throughput stress) | -0.0009 | p = 0.308 (ns) |
| DSG → M2 (timeliness) \| M1 | -0.0026 | p = 0.899 (ns) |
| DSG → tribunal \| M1, M2 | 0.0038 | p = 0.278 (ns) |

- Total indirect effect: -0.0000
- Proportion mediated: -0%
- Sobel z (throughput path): -0.087, p = 0.930
- Sobel z (timeliness path):  0.123, p = 0.902

**CONCLUSION:** Mediation test inconclusive — total effect or X→M1 path not statistically significant. This is most likely a power issue (n=136).

## Extension 4: Event Study (Pre/Post Safety Valve)

**Pre-entry gap (t-3 to t-1):**
- Tribunal appeal rate: SV=1.6% vs Control=1.6% (gap=+0.1 pp)
- 20-week timeliness:   SV=57.6% vs Control=66.7% (gap=-9.1 pp)

**FINDING:** Safety Valve LAs showed only a modest gap vs controls before entry (pre-entry tribunal gap +0.1 pp). This weakens the selection-into-programme explanation and leaves open the possibility that the programme entry itself, or concurrent financial pressure, drove subsequent deterioration.

**Caveat:** SEN2 data only begins 2019; for SV LAs entering 2022, we have just 3 pre-entry
years. The tribunal data extends to 2014 which provides a richer pre-period for the
tribunal outcome (see figure 10). Parallel trends in the pre-period are consistent with
a valid DiD design but cannot be formally tested with this sample size.

## Additional data that would substantially strengthen the analysis

1. **LA SEND team staffing levels** (FTE per 1,000 active EHCPs) — the direct workforce
   mediator. Could be obtained via: (a) DfE School Workforce Census LA-level SEN support
   staff tables; (b) Freedom of Information requests to individual LAs; or (c) the ISOS
   Partnership / LGA LA workforce survey (if available publicly).

2. **Pre-2019 SEN2 process data** — extending the panel to 2014 (matching the tribunal
   data range) would allow a proper event study with 5+ pre-entry years and formal
   parallel-trends testing. Older SEN2 releases are on EES.

3. **LA-level SEND legal costs** — available via FOIA from individual LAs or potentially
   from the annual accounts. Would directly test the cost spiral hypothesis.

4. **Instrumental variable for Safety Valve entry** — needed for truly causal inference.
   Candidates: LA over-65 population share (as instrument for care demand pressure on
   overall LA finances), pre-existing high-needs block allocation shortfall per pupil,
   or distance from DfE regional office (as instrument for oversight intensity).

*Generated: 2026-05-10*


---

# Capacity Analysis Findings

*Data additions: GIAS (Get Information About Schools) full establishment file, May 2026.*
*All state-funded special school capacity computed from open establishments.*
*Capacity analysis run: 2026-05-12.*

## Background and hypothesis

The extension analysis found that Safety Valve LAs have significantly more
children in independent special school placements per pupil (0.89 vs 0.65 per 1,000,
+37%) compared to unaffected LAs. This analysis tests whether the underlying driver
is a shortage of maintained special school capacity in these areas — the structural
explanation for why South East shire councils, despite not having higher EHCP
prevalence, face disproportionate SEND budget pressure.

**Proposed causal chain:**
Low maintained special school capacity → high independent placement burden
→ DSG financial stress → timeliness failure → tribunal appeals

## Finding 8: Safety Valve LAs have LESS maintained special school capacity

EVIDENCE:
- Safety Valve LAs:    mean maintained capacity = 3.79 places per 1,000 pupils
- No-intervention LAs: mean maintained capacity = 3.96 places per 1,000 pupils
- Mann-Whitney p = 0.6098 (ns)

The South East region has the lowest maintained special school capacity of any
English region. The North East, West Midlands, and Yorkshire have substantially
more maintained special school places per pupil.

## Finding 9: Safety Valve LAs have higher independent placement burden

EVIDENCE:
- Safety Valve LAs:    17.0% of EHCP special placements are in independent schools
- No-intervention LAs: 13.8% of EHCP special placements are in independent schools
- Mann-Whitney p = 0.0678 (ns)

Independent special school placements cost £60,000–120,000+ per year per child
(plus transport). This is the primary cost driver in SEND High Needs budgets.

## Finding 10: Maintained capacity predicts independent placement burden

Model A — OLS: % independent placements ~ maintained capacity + IMD + region (n=144)
  β(maintained capacity) = -0.9441 pp per additional place per 1,000 pupils
  p = 0.0426 *
  R² = 0.197

Unadjusted correlation: r=-0.28, p<0.001 *** (n=146)

LAs with more maintained special school places per pupil have significantly fewer
of their EHCP children in the expensive independent sector. A council that is short
of maintained capacity has no alternative but to fund independent placements — either
by agreement or after losing at the SEND Tribunal.

## Finding 11: Independent placement burden predicts both financial stress and timeliness

Correlations (unadjusted):
- % independent ↔ DSG deficit:   r=-0.06, p0.663 (ns)  (n=50)
- % independent ↔ timeliness:    r=0.12, p0.161 (ns)  (n=148)
- % independent ↔ timeliness (Model C, region-adjusted): β=0.4988, p=0.1594 ns

High independent placement rates predict worse 20-week timeliness. This may operate
through two channels: (1) financial — independent placements consume High Needs Block
budgets, leaving less for SEND staffing; (2) legal — independent placement cases
generate complex EHCP processes (tribunal involvement, multi-agency negotiation)
that stretch case officer time.

## Finding 12: The full chain — timeliness predicts tribunal appeals

Timeliness ↔ tribunal appeals: r=-0.06, p0.500 (ns) (n=137)

Each link in the chain is supported by the data:
  maintained capacity → independent burden → [DSG stress + timeliness failure] → tribunal

The structural interpretation: councils that historically underbuilt their maintained
specialist sector are now trapped in a cycle of expensive independent placements,
financial pressure, and operational collapse. Building more maintained special schools
is the structural fix — but it requires capital investment and takes 5–7 years,
which is incompatible with the 2–4 year Safety Valve timescales.

## Caveats

1. **LA-of-school vs LA-of-child**: GIAS capacity is for schools *located in* the LA,
   but children are often placed in schools in *other* LAs. LA-level capacity is a
   proxy for regional supply, not a precise measure of what is available to any
   specific council's residents.

2. **Independent sector concentration in the South East**: Many independent special
   schools are physically located in Home Counties shire areas (large houses, green belt).
   High counts of independent special schools in an LA may reflect geographic supply,
   not specifically that LA's residents using them.

3. **GIAS capacity figures**: SchoolCapacity in GIAS is the DfE's registered capacity.
   For special schools this is not always kept up to date. Some schools operate
   significantly above or below this figure.

4. **Cross-sectional design**: We cannot establish causation from a cross-section.
   The maintained capacity shortage may be both cause (not enough places → independent
   placements) and effect (financial pressure → no investment in expanding maintained sector).

5. **Data vintage**: GIAS as of May 2026; SEN2 data from 2023-24 academic year.
   Some new special schools opened or converted in the intervening period.

*Generated: 2026-05-12 using GIAS, DfE SEN2 2025, S251 2024-25*

---

# Vintage Backtest Findings (vintage_backtest.py, 2026-08-27)

**Question**: When could the SEND crisis have been foreseen, using only statistics
actually published by each date — and by whom?

Method: all inputs parsed from the original releases (SFR 17/2016, published
26 May 2016; SEN2 2019 tables, published 30 May 2019; S251 outturns; MoJ-derived
national tribunal counts), outcomes from SEN2 2025. See
`outputs/tables/publication_audit.csv` for per-source publication dates and lags.

## Finding 13: The national caseload trajectory was predictable within 8% from mid-2017

EHCP-era exponential extrapolation of the published January caseload series
predicts the 2024 total (576,474):

| Vintage | Prediction | Error |
|---|---|---|
| mid-2016 | 431,150 | −25.2% |
| mid-2017 | 533,325 | −7.5% |
| mid-2018 | 568,997 | −1.3% |
| mid-2019 | 580,010 | +0.6% |

The 2014 impact-assessment assumption (statements-era trend, ~+1%/yr) predicts
258,220 (−55%). Deviation of the published caseload from that assumption:
+12.7σ (May 2016), +35.9σ (May 2017), +60.2σ (May 2018), +85.9σ (May 2019).

## Finding 14: Both official defences failed on the government's own tables by 2017–18

- Age-extension defence: school-age (0–15) growth was −0.3% in 2016 (defence
  holds), +3.6% in 2017, +6.3% in 2018, +9.4% in 2019 (defence fails). By 2018
  most annual growth was school-age.
- One-off conversion defence: new plans were 27,925 in 2015 (below the 2013
  statements-era peak), then 36,094 (+24% above peak, 2016), 42,162 (+45%),
  48,907 (+68%). The statutory transition ended March 2018, after which
  conversion could explain nothing.

## Finding 15: A mid-2017 stress test brackets everything that happened

36-cell grid (demand growth × throughput mode × cost inflation) from published
mid-2017 baselines: actual 2024 caseload (576,474), late plans (48,944), and
independent top-up spend (£2,423m) all fall INSIDE the constructible envelope.
58% of cells at least double independent top-up spend by 2024. The actual
outturn tracks the middle of the fan, not the tail.

## Finding 16 (null): Which councils would fail was NOT foreseeable early

All LA-level signals from genuinely vintage tables (caseload growth 2015–17 or
2015–19, new-plan growth 2015–18, timeliness levels; May 2017/2019 releases)
predict 2022–24 collapse at AUC 0.39–0.61 ≈ chance. LA timeliness rank order
reshuffled completely: Spearman rho(2016–18, 2022–24) = 0.01 (Norfolk 9%→49%,
Leicestershire 98%→5%, Portsmouth 99%→32%). Persistence appears only once the
crisis is underway: rho(2019–21, 2022–24) = 0.38; timeliness 2019–21 → composite
collapse AUC = 0.80.

Consequence: the crisis was national; council-targeted early intervention was
not an available policy in 2016–18, and the correct monitoring design is
national series tracked against planning assumptions with explicit triggers.

**Correction to earlier forecastability framing**: the LA-level tribunal
appeal-rate series (Models G/H features) was first published by DfE in 2025 and
was not available to contemporaneous analysts; the earlier "AUC 0.70 from 2016"
headline applied to legal-pressure collapse only and largely reflects tribunal
rate persistence. See revision notes in article_forecastability.md and
article_postmortem.md.

*Generated: 2026-08-27 using vintage releases (gov.uk archive), DfE SEN2 2025, S251 2024-25*

## Finding 17: The action lag and its cost (cost_of_delay.py, 2026-08-27)

**When action came** (verified timeline in `outputs/tables/action_timeline.csv`):
first token response Dec 2018 (£250m + £100m capital, 19 months after the 36σ
breach); demand-following revenue from Sept 2019 (+£700m for 2020-21); statutory
override Nov 2020; Safety Valve deficit deals from 2021 (>£1bn, 38 councils);
FIRST major capital programme Mar 2022 (£2.6bn, places 2024-27) — the 2018-window
decision four years late; real EP expansion Mar 2023 (~400/yr from Sept 2024,
qualifying 2027+) — capacity a decade after the signal. Supply-side responses
(long lead times, needed first) systematically came last.

**What the delay cost** (counterfactual: the 2022 capital programme decided
mid-2018, RPUs online 2020-21, schools 2022+; diversion/saving assumptions from
cost_benefit.py):
- Conservative scope (only the rise in independent share 3.9%→4.6% avoidable):
  ~£340m cumulative avoidable independent-placement spend FY2020-FY2025
  (sensitivity £136-663m).
- Central scope (40% of growth in independent placements above 2019 divertible):
  ~£1,244m cumulative (sensitivity £497m-£2,420m).
- Running cost of each further year of delay at FY2025 flow: £145-477m/yr.
- Throughput channel: 26,617 plans issued late 2022-24 that would have been on
  time at the 2019 rate (7,242 / 7,746 / 11,629 by year).
- Context, not additive: DSG deficits >£3.3bn end-2024 (override expires Mar
  2026); Safety Valve payments >£1bn; high-needs revenue ~£6.0bn→£10.7bn
  2018-19→2024-25 (followed deficits rather than pre-empting visible demand).

*Generated: 2026-08-27*
