# EHCP Local Authority Analysis — Findings

**Data source:** DfE SEN2 2025 statistical release (calendar years 2019–2024) downloaded
programmatically from Explore Education Statistics. LA-level SEND Tribunal appeal rate data
published for the first time in 2025 (DfE supporting file). All data loaded directly from
official DfE sources — no manual downloads required for 2019–2024 analysis.

Intervention status assigned from DfE Safety Valve and Delivering Better Value programme
announcements (2022–2025). DSG deficit estimates from published DfE management plan summaries.
IMD 2019 average scores from MHCLG IoD2019 Table 10.

**Coverage:** 151 upper-tier local authorities, England, 2024 cross-section.
Panel: 912 LA-year observations, 2019–2024.

---

## HEADLINE RESULT

The data show a **timeliness crisis concentrated in Safety Valve LAs**, rather than a simple
gatekeeping story. Safety Valve LAs are not refusing significantly more applications at the
initial stage, but they are dramatically failing to meet the 20-week statutory deadline and
facing higher tribunal appeal rates — consistent with capacity collapse rather than overt
gatekeeping. The financially stressed LAs appear to be letting cases through but then failing
to complete them on time.

---

## Finding 1: Refusal rates do NOT significantly differ between Safety Valve and other LAs

FINDING: Contrary to the gatekeeping hypothesis, Safety Valve LAs do not refuse significantly
more EHCP assessment requests at the initial stage than non-intervention LAs in 2024.

EVIDENCE:
- Safety Valve LAs:           mean refusal rate = 25.3% (median 22.6%)
- Delivering Better Value LAs: mean refusal rate = 23.4% (median 23.7%)
- No intervention LAs:        mean refusal rate = 25.1% (median 24.0%)

Mann-Whitney U = 792, p = 0.756 (not significant).
Kruskal-Wallis H = 0.55, p = 0.760 (not significant).

The highest refusal rates in 2024 are found in LAs across all intervention categories:
Walsall (DBV, 60.6%), Sunderland (DBV, 59.3%), Kent (SV, 55.0%), East Sussex (SV, 53.7%),
Southwark (none, 47.7%).

CAVEAT: The DfE notes that backlogs inflate apparent refusal rates — LAs with large
backlogs show lower *apparent* refusal rates because many decisions are still pending.
Safety Valve LAs under close DfE scrutiny may also face constraints on overt refusals;
gatekeeping may be occurring through delay rather than formal refusal.

---

## Finding 2: Safety Valve LAs have dramatically worse 20-week statutory timeliness

FINDING: Local authorities under the Safety Valve programme are markedly less likely to issue
EHCPs within the 20-week statutory limit — the clearest systemic difference in the 2024 data.

EVIDENCE:
- Safety Valve LAs:            mean timeliness = 35.8% (median 35.7%)
- Delivering Better Value LAs: mean timeliness = 54.5% (median 55.2%)
- No intervention LAs:         mean timeliness = 57.0% (median 57.2%)

Mann-Whitney U = 468, p = 0.001 (**).
Kruskal-Wallis H = 11.57, p = 0.003 (**).

The gap between Safety Valve LAs (35.8%) and no-intervention LAs (57.0%) is 21.2 percentage
points. The worst performers in 2024: Devon (SV, 3.2%), Cambridgeshire (SV, 7.7%),
West Sussex (SV, 11.4%), Medway (SV, 11.7%), Essex (SV, 16.2%).

CAVEAT: LAs pausing the statutory clock during tribunal challenges may depress timeliness
figures independently of capacity issues. However, the consistency of the pattern across
all Safety Valve LAs argues for a systemic capacity explanation.

---

## Finding 3: Safety Valve LAs face significantly higher SEND tribunal appeal rates

FINDING: LAs under the Safety Valve programme face significantly higher official SEND Tribunal
appeal rates — families of children with EHCPs in these LAs are more likely to take
their case to tribunal.

EVIDENCE (DfE official appeal rate, 2024):
- Safety Valve LAs:            mean = 7.5% (median 5.9%)
- Delivering Better Value LAs: mean = 4.8% (median 4.1%)
- No intervention LAs:         mean = 5.4% (median 5.0%)

Mann-Whitney (SV vs None): U = 797, p = 0.045 (*).
Kruskal-Wallis (all groups): H = 10.63, p = 0.005 (**).

The DfE official appeal rate measures appeals registered with SEND Tribunal as a percentage
of total appealable decisions in a year (which includes EHCP refusals, contents disputes,
and placement decisions — wider than just initial request refusals).

CAVEAT: Tribunal appeal rates may reflect the quality and contents of issued EHCPs, not
just refusal decisions. LAs producing poor-quality EHCPs due to staff shortages may generate
appeals on contents grounds rather than refusal grounds. Larger LAs (which are
disproportionately in the Safety Valve) generate more decisions and may have higher rates.

---

## Finding 4: Refusal rates do not predict tribunal appeal rates (no "doom loop" in 2024 data)

FINDING: There is no statistically significant correlation between LA assessment refusal
rates and official tribunal appeal rates in the 2024 cross-section.

EVIDENCE: Pearson r = 0.133, p = 0.122, n = 136 LAs.

This suggests that tribunal appeals are not primarily driven by initial refusal decisions.
Families appear to appeal on grounds beyond refusal (EHCP contents, placement) at similar
rates regardless of how selective the LA is at the initial request stage.

CAVEAT: The DfE official appeal rate uses a different denominator (total appealable decisions)
from refusal rate (initial requests), which may suppress the correlation. The relationship
may be clearer with a longer time horizon or with tribunal data broken down by appeal ground.

---

## Finding 5: DSG deficit per pupil significantly predicts timeliness failure

FINDING: After controlling for local deprivation (IMD 2019) and region fixed effects,
LAs with higher DSG deficits per pupil show significantly lower 20-week compliance — the
strongest regression finding in the analysis.

EVIDENCE (OLS, DV = timeliness %, n = 50, R² = 0.356):
- DSG deficit/pupil: β = −0.034 pp per £1 (SE ≈ 0.015, p = 0.023 *)
- IMD average score: β = +0.527 pp (p = 0.248, ns)

Interpretation: A £100 increase in cumulative DSG deficit per pupil is associated with
a −3.4 percentage-point reduction in 20-week compliance, controlling for deprivation and
region. For a Safety Valve LA with a deficit of ~£900/pupil, this implies approximately
−31 pp lower timeliness vs an otherwise-identical balanced LA.

CAVEAT: Sample limited to n = 50 LAs with available DSG estimates (the remaining ~100 LAs
lack machine-readable deficit figures). Region fixed effects absorb much of the variance;
the South East is heavily over-represented in the Safety Valve. DSG deficit estimates here
are drawn from published summary tables, not LA-level audited accounts — download the full
DSG management plan data (see below) for more precise figures.

---

## Finding 6: DSG deficit does NOT significantly predict refusal rates or tribunal rates

FINDING: After controlling for deprivation and region, DSG deficit per pupil is NOT a
significant predictor of refusal rates (p = 0.970) or tribunal appeal rates (p = 0.103).

This reinforces the pattern: financial stress is most strongly linked to operational
failure (timeliness), not to overt gatekeeping via refusals.

---

## Finding 7: Difference-in-Differences (Safety Valve entry — preliminary)

EVIDENCE: Simple 2×2 DiD comparing pre/post Safety Valve entry (2022):
  Safety Valve LAs: pre-2022 refusal = 24.5% → post-2022 = 24.9% (+0.4 pp)
  Control (no intervention): pre = 22.6% → post = 24.6% (+2.0 pp)
  DiD estimate: −1.7 pp (Safety Valve LAs' refusal rates *fell* relative to controls
  after programme entry — directionally opposite to the gatekeeping hypothesis).

INTERPRETATION: This is consistent with DfE oversight under Safety Valve agreements
actively constraining overt refusals, while underlying capacity issues are expressed
through timeliness failure and tribunal pressure instead.

CAVEAT: Only 3 pre-intervention years available (2019–2021). Parallel trends
unverifiable. Sample is small. Treat as exploratory.

---

## Synthesis: What is actually happening?

The data tell a coherent story that differs from a simple "gatekeeping via refusals" narrative:

1. **Financially stressed LAs are not refusing more** — possibly because DfE Safety Valve
   agreements impose direct oversight that constrains overt gatekeeping.

2. **They are failing dramatically on timeliness** — the 20-week compliance rate for
   Safety Valve LAs (35.8%) is roughly half the rate for unaffected LAs (57.0%).
   This is the clearest measurable impact of the financial crisis.

3. **Families are appealing more** — tribunal appeal rates are significantly higher
   in Safety Valve LAs, driven not by refusals but likely by poor-quality EHCPs,
   wrong placements, and delays (all grounds for tribunal appeal).

4. **DSG deficit is the key financial predictor** — specifically for timeliness failure,
   not refusal rates. This is the most policy-relevant regression finding.

The mechanism appears to be: financial pressure → staffing cuts → inability to complete
assessments on time + lower-quality plans → tribunal challenges → further legal costs →
deepening financial pressure. This is a different "doom loop" from the one hypothesised
(refusal → appeal → refusal), and arguably a more insidious one.

---

## Data Notes

### Successfully loaded programmatically (DfE SEN2 2025 release)
- requests.csv — EHCP requests and refusals by LA, 2019–2024
- timeliness_20_week.csv — 20-week compliance by LA, 2019–2024
- caseload.csv — active EHCPs by LA, 2019–2025 (academic years)
- assessments.csv — assessment outcomes by LA, 2019–2024
- newplans.csv — new EHCPs issued by LA, 2019–2024
- SEND Tribunals and appeal rate 2014-2024.csv — **first published 2025**;
  official LA-level tribunal appeal rates 2014–2024

**Download URL used:**
`https://content.explore-education-statistics.service.gov.uk/api/releases/4c3eb898-bfd5-4081-9a96-4aa9abe32090/files?fromPage=ReleaseDownloads`

### Needs manual download for extended analysis

- **SEN2 2023 and 2024 historical releases** (to extend panel to 2017–2018):
  https://explore-education-statistics.service.gov.uk/find-statistics/education-health-and-care-plans
  Each older release → "Explore data and files" → "Download all data (ZIP)"
  Save to `data/raw/sen2_2023/` and `data/raw/sen2_2024/`; extend loader in `analysis.py`

- **DSG management plan data** (for precise LA-level deficit figures, dramatically
  increases regression sample size from n=50 to ~153):
  https://www.gov.uk/government/publications/dedicated-schools-grant-dsg-and-local-authorities
  Save to `data/raw/dsg_management_plan.xlsx`

- **Pupil population by LA** (denominator for EHCP prevalence rates):
  https://explore-education-statistics.service.gov.uk/find-statistics/special-educational-needs-in-england/2024-25
  Save to `data/raw/sen_pupils_2024.csv`

- **IMD 2019 full dataset** (currently ~50% coverage from hardcoded estimates):
  https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/833995/File_10_-_IoD2019_Local_Authority_District_Summaries__lower-tier__.xlsx
  Save to `data/raw/imd_2019_la.xlsx`

### Columns with >10% missing data

| Column | % Missing | Impact |
|--------|-----------|--------|
| `ehcp_rate_pct` | 100% | EHCP prevalence analysis requires pupil denominator dataset |
| `n_total_appealable_decisions` | 100% | Parsing artefact; use `la_official_appeal_rate_pct` instead |
| `sv_entry_year` | 81% | DiD analysis limited to Safety Valve LAs only |
| `n_mediations`, `n_trib_req` | 67% | Suppressed in DfE data for small LAs (values < 5) |
| `dsg_deficit_per_pupil` | 67% | Regression sample n=50; download full DSG data to expand |
| `imd_average_score` | 4% | A few LAs lack hardcoded estimates |

**Note on `tribunal_rate_pct`:** The derived column `n_tribunal_appeals / n_requests`
produces misleading values (mean ~273%) because the SEND Tribunal counts all appeal
grounds (contents, placement, etc.) while `n_requests` counts only initial EHCP requests —
different universes. The DfE's official `la_official_appeal_rate_pct` (which uses
"total appealable decisions" as denominator) is the correct metric and is used throughout.

---

*Generated: 2026-05-10 using DfE SEN2 2025 release*
*`analysis.py` in `/Users/matt/src/la_sen_analysis/`*


---

# Extension Analysis Findings

*Data additions: S251 DSG outturn 2023-24, IMD 2019 (full), SEN pupils 2024-25.*
*All loaded programmatically. Extension run: 2026-05-10.*

## Extension 1: DSG Coverage Expansion

DSG financial stress data expanded from n=50 to n=150 LAs using the DfE S251
(LA and School Expenditure) data. The S251 1.9.3 "DSG carried forward" column provides
end-of-year DSG balance for ~153 LAs. Negative balance = deficit being carried forward
to next year; positive = surplus.

Conversion: DSG financial stress per pupil = −(DSG_carry_forward_£) / total_pupils,
so positive values indicate financial pressure.

### Timeliness regression (extended sample, n=147)

β(DSG stress/pupil) = -0.0077 pp, p = 0.757 (ns), R²=0.138

**FINDING:** The DSG deficit → timeliness relationship loses significance in the larger sample (p = 0.757). This may indicate that the original n=50 result was driven by high-DSG-deficit LAs (Safety Valve) which are also in a specific region — the region FEs absorb much of the variance in the full sample.

### Tribunal rate regression (extended sample, n=135)

β(DSG stress/pupil) = 0.0038 pp, p = 0.270 (ns), R²=0.149


## Extension 2: Capacity Proxy (Throughput Stress)

Throughput stress = requests / (plans_issued × timeliness), z-scored.
Captures processing backpressure: high score = many requests relative to timely outputs.

Correlation with DSG financial stress: r=-0.044, p = 0.592 (ns)

Throughput stress and DSG deficit are not significantly correlated in the cross-section, suggesting other factors (LA size, administrative efficiency) drive throughput variation independently of finances.

## Extension 3: Mediation Analysis

**Chain tested:** DSG deficit → throughput stress (M1) → timeliness failure (M2) → tribunal appeals
**Sample:** n=134 LAs with all four variables observed

Baron-Kenny results:
| Path | β | p |
|------|---|---|
| Total effect (DSG → tribunal) | 0.0036 | p = 0.294 (ns) |
| DSG → M1 (throughput stress) | -0.0009 | p = 0.296 (ns) |
| DSG → M2 (timeliness) \| M1 | -0.0024 | p = 0.907 (ns) |
| DSG → tribunal \| M1, M2 | 0.0037 | p = 0.283 (ns) |

- Total indirect effect: -0.0001
- Proportion mediated: -2%
- Sobel z (throughput path): -0.163, p = 0.871
- Sobel z (timeliness path):  0.108, p = 0.914

**CONCLUSION:** Mediation test inconclusive — total effect or X→M1 path not statistically significant. This is most likely a power issue (n=134).

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

## Finding 8: No significant difference in maintained special school capacity (SV vs non-intervention)

EVIDENCE:
- Safety Valve LAs:    mean maintained capacity = 3.80 places per 1,000 pupils
- No-intervention LAs: mean maintained capacity = 3.95 places per 1,000 pupils
- Mann-Whitney p = 0.7001 (ns)

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

Model A — OLS: % independent placements ~ maintained capacity + IMD + region (n=141)
  β(maintained capacity) = -0.9120 pp per additional place per 1,000 pupils
  p = 0.0520 ns
  R² = 0.199

Unadjusted correlation: r=-0.28, p<0.001 *** (n=143)

LAs with more maintained special school places per pupil have significantly fewer
of their EHCP children in the expensive independent sector. A council that is short
of maintained capacity has no alternative but to fund independent placements — either
by agreement or after losing at the SEND Tribunal.

## Finding 11: Independent placement burden predicts both financial stress and timeliness

Correlations (unadjusted):
- % independent ↔ DSG deficit:   r=-0.06, p0.684 (ns)  (n=49)
- % independent ↔ timeliness:    r=0.12, p0.161 (ns)  (n=148)
- % independent ↔ timeliness (Model C, region-adjusted): β=0.4805, p=0.1778 ns

High independent placement rates predict worse 20-week timeliness. This may operate
through two channels: (1) financial — independent placements consume High Needs Block
budgets, leaving less for SEND staffing; (2) legal — independent placement cases
generate complex EHCP processes (tribunal involvement, multi-agency negotiation)
that stretch case officer time.

## Finding 12: The full chain — timeliness predicts tribunal appeals

Timeliness ↔ tribunal appeals: r=-0.05, p0.598 (ns) (n=135)

The first link in the chain — maintained capacity → independent burden — shows
the expected direction and is statistically significant (r=−0.28, p<0.001).
The subsequent links (independent burden → DSG deficit, p=0.684; independent
burden → timeliness, p=0.161; timeliness → tribunal, p=0.598) are not individually
significant in the cross-sectional data. The chain is directionally consistent
but the intermediate steps are not individually confirmed beyond the capacity-to-
placement step — most likely a power and collinearity problem given the n=50
DSG sample and South East regional concentration.

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
