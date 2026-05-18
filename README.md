# England's SEND Crisis: LA-Level Analysis

A data-driven analysis of England's Special Educational Needs and Disability (SEND) system. The analysis identifies what is driving the system-wide timeliness failure, tests whether the collapse was foreseeable from publicly available data, and makes the data-driven case for a forward capital programme of maintained specialist provision.

**Published outputs:**

1. **[System-wide timeliness failure: what the data show and why](article.md)** — 59 of 151 councils failed the 20-week legal standard in more than 60% of cases in 2024. The failure cuts across all council types and is driven by a structural mismatch between SEMH provision and need — not by which DfE programme a council belongs to.

2. **[The collapse was foreseeable — and the next one already is](article_forecastability.md)** — Using only data available in 2016, tribunal appeal rates and independent placement spend could already identify which councils would hit systemic failure (AUC 0.70). By 2021 the same signals achieved AUC 0.88. The warning was in the public data.

3. **[A data-driven post-mortem](article_postmortem.md)** — What the data showed at each decision point, when it should have prompted action, and what a data-literate government should have done differently.

4. **[Policy briefing note](briefing_note.md)** — One-page summary for ministers and officials.

5. **[Literature review](literature_review.md)** — Positioning this analysis against existing academic and policy evidence on SEND system performance.

**For journalists and policymakers:** a ready-to-use [evidence pack](press_pack/) is available, including a master overview, 500-word explainer, facility priority planning, invest-to-save cost-benefit analysis, policy asks, methodology summary, and anticipated challenges.

---

## Key findings at a glance

### System-wide timeliness failure (Article 1)

| Metric | Value |
|---|---|
| National 20-week compliance, 2024 | 51.8% |
| Councils below 40% compliance | 59 of 151 (39%) |
| Councils below 20% compliance | 24 of 151 |
| SEMH share of EHCP caseload, 2015/16 → 2024/25 | 12.7% → 20.7% |
| SEMH schools as share of new maintained openings, pre/post 2016 | 21.6% → 11.2% |
| Distance to nearest maintained SEMH school → independent spend | β=+0.016/km, p=0.003 |

The worst performers span all council types: Devon (Safety Valve, 3.2%), Portsmouth (no programme, 4.3%), Leicestershire (DBV, 4.3%), Cornwall (DBV, 7.4%), Slough (Safety Valve, 7.4%). Programme membership does not predict timeliness (SV vs no-programme Mann-Whitney p=0.904).

### Forecastability (Article 2 — eight model families A–H)

| Forecast year | Model | Target | LOO-CV AUC |
|---|---|---|---|
| 2016 | G: Signals (tribunal + spend) | Legal-pressure collapse | 0.70 |
| 2019 | B: Need-type counts only | Timeliness collapse | 0.69 |
| 2019 | B: Need-type counts only | Legal-pressure collapse | 0.77 |
| 2020 | G: Signals only | Legal-pressure collapse | 0.83 |
| 2021 | E: Counts + timeliness | Composite collapse | **0.82** |
| 2021 | G: Signals only | Legal-pressure collapse | **0.88** |

**Key finding:** Need-type growth (Model B) predicted timeliness collapse as well as or better than system-failure signals; for legal-pressure and placement collapse, tribunal rates and independent spend dominated. Proportional need-type shares (Model C) are near-useless for prediction (AUC ~0.50) — the informative signal is absolute volume.

**Councils with no current DfE programme showing elevated risk scores:**

| Council | Risk score | Mean timeliness 2022–24 |
|---|---|---|
| Essex | 0.83 | 9.3% |
| Newcastle upon Tyne | 0.75 | 9.4% |
| Bromley | 0.75 | 33.7% |
| Hertfordshire | 0.73 | 43.0% |
| Staffordshire | 0.69 | 33.5% |
| Derby | 0.67 | 20.6% |

Essex and Newcastle are not approaching crisis — they are already in it with fewer than one in ten plans issued on time. These are model outputs indicating structural similarity to councils already in collapse; they are not official designations.

### Facility planning and cost-benefit

**467 LA × need-type provision gaps** identified and ranked by urgency (designation mismatch × demand growth × independent placement pressure × access distance). Top 30 priority facilities — 20 new maintained special schools and 10 resourced provision units — require **£420 million** of capital investment and generate an estimated **£76 million per year** in avoided independent placement costs at full operation. 15-year Green Book-style discounted NPV: **£220 million**. Undiscounted break-even: **2034**.

---

## Programme membership

Safety Valve and Delivering Better Value programme lists are sourced from:
- **Safety Valve (38 councils, 4 waves, 2021–2024):** [gov.uk/government/publications/dedicated-schools-grant-very-high-deficit-intervention](https://www.gov.uk/government/publications/dedicated-schools-grant-very-high-deficit-intervention). Programme closed to new entrants December 2024; agreements no longer binding from April 2026.
- **Delivering Better Value (~54 councils, 3 tranches, 2022–2023):** [dbvinsend.com/participating-local-authorities](https://www.dbvinsend.com/participating-local-authorities)

---

## Repository structure

```
├── analysis.py                    # Core pipeline: SEN2 2025, tribunal data, regressions
├── extension.py                   # DSG S251 expansion, mediation, event study
├── capacity_analysis.py           # GIAS special school capacity analysis
├── spend_model.py                 # LSOA access distances + spend regression model
├── mismatch_analysis.py           # Need-type vs supply mismatch over time
├── timeliness_analysis.py         # Timeliness deep-dive: S251 spend vs compliance
├── prediction_analysis.py         # Early prediction of Safety Valve status
├── forecastability_analysis.py    # Forecastability study, risk scores, scenario projections
├── facility_planning.py           # LA × need-type facility priority scoring
├── facility_location.py           # LSOA-level within-LA location drill-down
├── cost_benefit.py                # 15-year invest-to-save cost-benefit model (top 30)
├── mapping_analysis.py            # Interactive maps (requires folium)
├── article.md                     # Article 1: System-wide timeliness failure
├── article_forecastability.md     # Article 2: Forecastability
├── article_postmortem.md          # Article 3: Data-driven post-mortem
├── briefing_note.md               # One-page policy briefing
├── literature_review.md           # Academic and policy context
├── press_pack/                    # Evidence pack for journalists and policymakers
│   ├── README.md                  # Navigation guide — start here
│   ├── overview_for_journalists.md
│   ├── 500_word_explainer.md
│   ├── facility_priorities.md
│   ├── cost_benefit_and_comparators.md
│   ├── policy_asks.md
│   ├── anticipated_challenges.md
│   ├── one_page_methodology.md
│   ├── github_link_and_citation.md
│   ├── figures_for_media/         # Recommended figures (6 PNGs)
│   └── tables_for_media/          # Recommended tables (4 CSVs)
├── outputs/
│   ├── FINDINGS.md                # Detailed statistical findings
│   ├── figures/                   # 49 PNG charts (150 dpi)
│   └── tables/
│       ├── la_summary_2024_extended.csv     # 151-LA 2024 cross-section
│       ├── panel_timeseries.csv             # 1,741 LA-year rows (2014–2024)
│       ├── la_collapse_labels.csv           # Collapse labels per LA (3 definitions)
│       ├── forecastability_summary.csv      # AUC × model family × year × collapse type (124 evaluations)
│       ├── forecastability_verdict.csv      # Forecastability verdict per collapse type × year
│       ├── la_risk_scores_2024.csv          # Current risk scores (143 LAs)
│       ├── la_scenario_forecasts.csv        # 5-scenario projections to 2030 per LA
│       ├── la_capacity_2024.csv             # Special school capacity panel (151 LAs)
│       ├── la_spend_model.csv               # LSOA distance + spend model outputs
│       ├── la_mismatch_2024.csv             # Need-type mismatch scores (151 LAs)
│       ├── facility_priority_list.csv       # 467 LA × need-type priorities ranked
│       ├── facility_priority_top20.csv      # Top 20 priorities (press-ready)
│       ├── facility_locations.csv           # Top 40 with LSOA-level location recommendation
│       ├── cost_benefit_summary.csv         # Per-facility NPV and break-even (top 30)
│       ├── cost_benefit_national.csv        # Annual cumulative cashflow 2025–2040
│       ├── cost_benefit_sensitivity.csv     # NPV sensitivity: 4 saving × 3 capex scenarios
│       └── comparator_profile.csv           # Model LA vs at-risk LA profiles
└── data/
    └── raw/                       # Not committed — see Download instructions below
```

---

## Data sources

| Dataset | Source | Required for |
|---|---|---|
| SEN2 2025 (requests, timeliness, caseload, plans) | DfE Explore Education Statistics | All analyses |
| SEND Tribunal appeal rate 2014–2024 | DfE SEN2 2025 supporting file | All analyses |
| S251 LA & School Expenditure 2015/16–2024/25 | DfE Explore Education Statistics | Extension, forecastability, spend model |
| SEN pupils 2024–25 | DfE Explore Education Statistics | Capacity analysis |
| SEN2 historical 2019–20 (need-type 2015/16–2019/20) | DfE archive | Mismatch, forecastability |
| GIAS all establishments (May 2026) | get-information-schools.service.gov.uk | Capacity, facility planning, location |
| LSOA 2021 centroids | ONS ArcGIS | Spend model, facility location |
| IMD 2019 | MHCLG IoD2019 Table 10 | All regression models |

Safety Valve programme membership: [gov.uk](https://www.gov.uk/government/publications/dedicated-schools-grant-very-high-deficit-intervention) (38 councils, 4 waves, 2021–2024). Delivering Better Value programme membership: [dbvinsend.com](https://www.dbvinsend.com/participating-local-authorities) (~54 councils, 3 tranches, 2022–2023).

---

## Reproducing the analysis

```bash
# Install dependencies
pip install pandas numpy matplotlib seaborn scipy statsmodels scikit-learn pyproj requests openpyxl

# Run in order — each script builds on outputs of earlier ones

# 1. Core analysis: SEN2 data → timeliness, refusals, tribunals, regressions
python analysis.py

# 2. Extension: DSG S251 expansion, mediation, event study
python extension.py

# 3. Capacity: GIAS special school capacity and structural chain
#    Requires: data/raw/edubasealldata20260512.csv (GIAS download page)
python capacity_analysis.py

# 4. Access distances and spend regression
#    Requires: data/raw/lsoa_centroids_2021.csv (ONS ArcGIS)
python spend_model.py

# 5. Need-type mismatch over time
#    Requires: data/raw/special-educational-needs-in-england_2019-20.zip
python mismatch_analysis.py

# 6. Timeliness deep-dive (S251 spend vs compliance)
python timeliness_analysis.py

# 7. Forecastability, risk scores, scenario projections
#    Requires all data/raw/ above; must run after steps 1–2
python forecastability_analysis.py

# 8. Facility priority scoring (LA × need-type)
python facility_planning.py

# 9. LSOA-level within-LA location drill-down
#    Requires: data/raw/lsoa_centroids_2021.csv and data/raw/edubasealldata20260512.csv
python facility_location.py

# 10. Invest-to-save cost-benefit model (top 30 facilities)
python cost_benefit.py

# 11. Early prediction analysis
python prediction_analysis.py
```

**Note:** Scripts 3–11 require manual data downloads. GIAS (~61MB) is from the DfE's Get Information About Schools download page. The S251 zip (~12MB) and SEN pupils (~4.7GB) are from DfE Explore Education Statistics. `mapping_analysis.py` requires `pip install folium` and runs independently.

---

## Forecastability methodology

The `forecastability_analysis.py` script predicts system collapse in 2022–2024 using only data available at each year from 2016 to 2021. Collapse is defined from observable outcomes, not programme status.

**Collapse definitions:**
- Timeliness collapse: mean 20-week compliance < 40% over 2022–2024
- Legal-pressure collapse: mean official appeal rate > 75th percentile
- Placement/cost collapse: independent placements > 75th percentile per 1,000 pupils
- Composite: flags on ≥ 2 of the 3 above

**Eight model families (A–H):**
- `A_total_demand`: total EHCP caseload level + log-linear growth rate
- `B_need_type_counts`: absolute EHCP counts + 3yr absolute growth in ASD, SEMH, SLCN, MLD — tests whether demand-type growth alone predicted collapse
- `C_need_type_shares`: need-type percentage composition only (composition vs volume)
- `D_counts_capacity`: need-type counts + independent top-up spend + EP service spend
- `E_counts_throughput`: need-type counts + 20-week compliance trend (2019+ only)
- `F_counts_cost`: need-type counts + independent top-up spend + DSG balance
- `G_signals_only`: tribunal appeal rate + trend + independent top-up % of DSG
- `H_full`: all available features combined

**Need-type data note:** LA-level EHCP counts by primary need type are published for 2015/16–2019/20 and 2024/25 only. The years 2020/21–2023/24 have no published LA-level breakdown. Models B–F and H use 2020 data as a proxy for the 2021 training year.

---

## Methodology notes

- **Non-parametric tests:** Mann-Whitney U (two-group) and Kruskal-Wallis H (three-group) for group comparisons, given non-normal distributions.
- **OLS regressions:** DV ∈ {refusal rate, timeliness, tribunal rate}; predictors: DSG financial stress per pupil, IMD 2019 average score, region fixed effects.
- **Event study:** Safety Valve entry year as t=0; outcomes averaged by event-time for SV vs no-intervention LAs. Pre-period uses tribunal data back to 2014.
- **Mediation (Baron-Kenny):** Chain: DSG deficit → throughput stress → 20-week timeliness → tribunal appeal rate. All paths non-significant in the 136-LA sample.
- **Facility priority score:** unmet demand × demand growth to 2030 × independent placement pressure × log-distance to nearest maintained school of that type.
- **Cost-benefit:** HMT Green Book-style 3.5% discount rate; ESFA capital benchmarks (£20m new special school / £2m RPU); £75,000/yr saving per diverted child (S251 2023/24 median: £97,322); 40% base diversion rate, capped at 65%.
- **Small LAs excluded:** City of London and Isles of Scilly excluded from all analyses.

---

## Caveats

1. **Programme membership ≠ performance cause:** SV and DBV LAs were selected into programmes on financial criteria, not timeliness. Cross-sectional comparisons between groups should not be read as programme effects.
2. **Refusal rates understate gatekeeping:** LAs with large backlogs show lower apparent refusal rates because many decisions are still pending. Gatekeeping via delay is not captured.
3. **Timeliness clock-stopping:** LAs can pause the statutory 20-week clock during mediation/tribunal proceedings.
4. **Forecastability ≠ causation:** High AUC from early tribunal rates partly reflects autocorrelation in persistent structural conditions.
5. **DSG balance ≠ operational capacity:** End-of-year DSG carry-forward is an accounting figure.
6. **Scenario projections are sensitivity illustrations**, not forecasts. Policy interventions and capital programmes are not modelled.
7. **Cost-benefit model is indicative:** No formal optimism-bias adjustment. Full sensitivity table (4 saving assumptions × 3 capital overrun scenarios) in `cost_benefit_sensitivity.csv`.
8. **Facility recommendations are planning-level,** not site-specific. Recommended locations indicate the part of an LA to target; detailed site selection requires local planning input.

---

## Licence

Code: MIT. Data outputs in `outputs/` are derived from Crown Copyright data (Open Government Licence v3.0).

*Author: Matt Sharpe, Oxford Internet Institute — matthew.sharpe@oii.ox.ac.uk*
