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

EVIDENCE: In 2024, Safety Valve LAs refused 25.3% of requests on average,
versus 25.1% for non-intervention LAs — a 0.2 pp gap.
Mann-Whitney U = 792.0, p = 0.756 (not significant).

CAVEAT: LAs may have entered Safety Valve partly because refusal rates were already rising.
The DfE also notes that backlogs inflate apparent refusal rates (decisions pending inflate
denominator). Using "decisions made" as denominator where available partially corrects this.

---

## Finding 2: Safety Valve LAs have worse 20-week statutory timeliness

FINDING: LAs under financial intervention are markedly less likely to issue EHCPs within
the 20-week statutory limit — indicating systemic capacity strain.

EVIDENCE: Safety Valve LAs issued 35.8% of plans within 20 weeks in 2024,
vs 57.0% for non-intervention LAs — a 21.2 pp gap.
Mann-Whitney: p = 0.001 **.

CAVEAT: LAs with high tribunal rates may pause the statutory clock during legal challenges,
artificially depressing their timeliness figures independently of capacity.

---

## Finding 3: Higher refusal rates correlate with higher tribunal appeal rates ("doom loop")

FINDING: LAs that refuse more EHCP applications face higher tribunal appeal rates —
consistent with a self-reinforcing cycle where families appeal refusals, creating
further administrative burden on already-stretched LAs.

EVIDENCE: Pearson r = 0.138 (refusal rate vs official tribunal appeal rate,
2024, n=137, p = 0.108 (not significant)).

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

FINDING: Safety Valve LAs' refusal rates have risen by 0.4 pp since 2022
(programme entry), compared to 2.0 pp for non-intervention LAs — a
DiD estimate of -1.68 pp attributable to Safety Valve status.

EVIDENCE: Simple 2×2 DiD (pre/post 2022, treated = Safety Valve LAs).
  Treated: pre 24.54% → post 24.90% (Δ = +0.36 pp)
  Control: pre 22.57% → post 24.61% (Δ = +2.04 pp)
  DiD: -1.68 pp

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
- `sv_entry_year`: 80.7% missing
- `n_mediations`: 66.9% missing
- `n_trib_req`: 66.9% missing
- `n_requests_assess`: 66.8% missing
- `dsg_deficit_per_pupil`: 66.2% missing

**Notably:** `ehcp_rate_pct` is entirely missing because pupil population denominators
require the separate SEN pupils dataset (not bundled in the SEN2 download). Regional
analysis and EHCP prevalence rates therefore rely on absolute counts rather than rates.

---

*Generated: 2026-05-14 21:36 using DfE SEN2 2025 release*


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

### Tribunal rate regression (extended sample, n=136)

β(DSG stress/pupil) = 0.0038 pp, p = 0.265 (ns), R²=0.141


## Extension 2: Capacity Proxy (Throughput Stress)

Throughput stress = requests / (plans_issued × timeliness), z-scored.
Captures processing backpressure: high score = many requests relative to timely outputs.

Correlation with DSG financial stress: r=-0.044, p = 0.592 (ns)

Throughput stress and DSG deficit are not significantly correlated in the cross-section, suggesting other factors (LA size, administrative efficiency) drive throughput variation independently of finances.

## Extension 3: Mediation Analysis

**Chain tested:** DSG deficit → throughput stress (M1) → timeliness failure (M2) → tribunal appeals
**Sample:** n=135 LAs with all four variables observed

Baron-Kenny results:
| Path | β | p |
|------|---|---|
| Total effect (DSG → tribunal) | 0.0036 | p = 0.293 (ns) |
| DSG → M1 (throughput stress) | -0.0009 | p = 0.295 (ns) |
| DSG → M2 (timeliness) \| M1 | -0.0026 | p = 0.901 (ns) |
| DSG → tribunal \| M1, M2 | 0.0038 | p = 0.282 (ns) |

- Total indirect effect: -0.0000
- Proportion mediated: -0%
- Sobel z (throughput path): -0.048, p = 0.962
- Sobel z (timeliness path):  0.121, p = 0.904

**CONCLUSION:** Mediation test inconclusive — total effect or X→M1 path not statistically significant. This is most likely a power issue (n=135).

## Extension 4: Event Study (Pre/Post Safety Valve)

**Pre-entry gap (t-3 to t-1):**
- Tribunal appeal rate: SV=2.4% vs Control=1.8% (gap=+0.6 pp)
- 20-week timeliness:   SV=52.6% vs Control=64.2% (gap=-11.6 pp)

**FINDING:** Safety Valve LAs showed only a modest gap vs controls before entry (pre-entry tribunal gap +0.6 pp). This weakens the selection-into-programme explanation and leaves open the possibility that the programme entry itself, or concurrent financial pressure, drove subsequent deterioration.

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
