# England's SEND Crisis: LA-Level Analysis

Two analyses are published here:

1. **[The queue problem, not gatekeeping](article.md)** — Safety Valve councils are not refusing more applications; they are failing on timeliness, producing poor-quality plans, and driving higher tribunal rates through capacity collapse.

2. **[The collapse was foreseeable — and the next one already is](article_forecastability.md)** — Using only data available in 2016, tribunal appeal rates and independent placement spend could already identify which councils would hit systemic failure. The same signals are now visible in a new set of authorities.

**For journalists and policymakers:** a ready-to-use [evidence pack](press_pack/) is available, including a 500-word explainer, methodology summary, policy asks, anticipated challenges, and recommended figures.

---

## Key findings at a glance

### Article 1: Queue problem, not gatekeeping

| Outcome | Safety Valve LAs | No-intervention LAs | p-value |
|---|---|---|---|
| Refusal rate | 25.3% | 25.1% | 0.76 (ns) |
| 20-week compliance | **35.8%** | **57.0%** | 0.001 ** |
| Official tribunal appeal rate | **7.5%** | **5.4%** | 0.045 * |

### Article 2: Forecastability (eight model families A–H)

| Forecast year | Model | Target | LOO-CV AUC |
|---|---|---|---|
| 2016 | G: Signals (tribunal + spend) | Legal-pressure collapse | 0.71 |
| 2019 | B: Need-type counts only | Timeliness collapse | 0.69 |
| 2019 | B: Need-type counts only | Legal-pressure collapse | 0.77 |
| 2020 | G: Signals only | Legal-pressure collapse | 0.83 |
| 2021 | E: Counts + timeliness | Composite collapse | **0.82** |
| 2021 | G: Signals only | Legal-pressure collapse | **0.88** |

**Key finding:** Need-type growth (Model B) predicted timeliness collapse as well as or better than system-failure signals (AUC 0.66 vs 0.50 at the 2020 training year); but for legal-pressure and placement collapse, tribunal rates and independent spend dominated.

**High-risk councils with no current DfE intervention:** Bristol (risk score 0.90), Birmingham (0.82), Bromley (0.77), Lewisham (0.72), Staffordshire (0.69), Central Bedfordshire (0.64). These are model outputs indicating structural similarity to councils already in collapse; they are not official classifications.

---

## Repository structure

```
├── analysis.py                      # Core pipeline (SEN2 2025, tribunal, regressions)
├── extension.py                     # DSG expansion, mediation, event study
├── capacity_analysis.py             # GIAS special school capacity analysis
├── spend_model.py                   # LSOA access distance + spend regression
├── mismatch_analysis.py             # Need-type vs. supply mismatch over time
├── prediction_analysis.py           # Early prediction of Safety Valve status
├── forecastability_analysis.py      # Forecastability study (this new analysis)
├── article.md                       # Article 1: Queue problem
├── article_forecastability.md       # Article 2: Forecastability
├── outputs/
│   ├── FINDINGS.md                  # Detailed statistical findings
│   ├── figures/                     # 43 PNG charts (150 dpi)
│   └── tables/
│       ├── la_summary_2024_extended.csv     # 151-LA 2024 cross-section
│       ├── panel_timeseries.csv             # 1,753 LA-year rows (2014–2024)
│       ├── la_collapse_labels.csv           # Collapse labels per LA (3 definitions)
│       ├── forecastability_summary.csv      # AUC × model family × year × collapse type (124 evaluations)
│       ├── forecastability_verdict.csv      # Forecastability verdict per collapse type × year
│       ├── la_risk_scores_2024.csv          # Current risk deciles (143 LAs)
│       └── la_scenario_forecasts.csv        # 5-scenario projections to 2030
└── data/
    └── raw/                         # Not committed — see Download instructions
```

---

## Data sources

| Dataset | Source | Required for |
|---|---|---|
| SEN2 2025 (requests, timeliness, caseload, plans) | DfE Explore Education Statistics | All analyses |
| SEND Tribunal appeal rate 2014–2024 | DfE SEN2 2025 supporting file | All analyses |
| S251 LA & School Expenditure 2015/16–2024/25 | DfE Explore Education Statistics | Extension, forecastability |
| SEN pupils 2024–25 | DfE Explore Education Statistics | Forecastability, spend model |
| SEN2 historical 2019–20 (need-type 2015/16–2019/20) | DfE archive | Mismatch, forecastability |
| GIAS all establishments (May 2026) | get-information-schools.service.gov.uk | Capacity, spend model |
| LSOA 2021 centroids | ONS ArcGIS | Spend model |
| IMD 2019 | MHCLG IoD2019 Table 10 | All regression models |

Safety Valve and Delivering Better Value programme membership from DfE announcements (2022–2025).

---

## Reproducing the analysis

```bash
# Install dependencies
pip install pandas numpy matplotlib seaborn scipy statsmodels scikit-learn requests openpyxl

# 1. Core analysis: SEN2 data → timeliness, refusals, tribunals, regressions
python analysis.py

# 2. Extension: DSG S251 expansion, mediation, event study
python extension.py

# 3. Capacity: GIAS special school capacity and structural chain analysis
#    Requires: data/raw/edubasealldata20260512.csv (download from GIAS)
python capacity_analysis.py

# 4. Access distances: LSOA centroids → nearest special school by SEN type
#    Requires: data/raw/lsoa_centroids_2021.csv (ONS ArcGIS, auto-fetched or manual)
python spend_model.py

# 5. Provision-need mismatch over time
#    Requires: data/raw/special-educational-needs-in-england_2019-20.zip
python mismatch_analysis.py

# 6. Forecastability study: early warning signals, risk scores, scenario projections
#    Requires: all data/raw/ above (must run after analysis.py and extension.py)
python forecastability_analysis.py
```

**Note:** Scripts 3–6 require manual data downloads. GIAS (~61MB) is from the DfE's Get Information About Schools download page. The S251 zip (~12MB) and SEN pupils (~4.7GB) are from DfE Explore Education Statistics.

Scripts must be run in order (each builds on outputs of earlier ones). The core analysis (steps 1–2) can be run independently; steps 3–6 require the panel outputs from step 1.

---

## Forecastability methodology

The `forecastability_analysis.py` script predicts system collapse in 2022–2024 using only data available at each year from 2016 to 2021. Collapse is defined from observable outcomes, not programme status.

**Collapse definitions (configurable at top of script):**
- Timeliness collapse: mean 20-week compliance < 40% over 2022–2024
- Legal-pressure collapse: mean official appeal rate > 75th percentile
- Placement/cost collapse: independent placements > 75th percentile per 1,000 pupils
- Composite: flags on ≥ 2 of the 3 above

**Eight model families (A–H):**
- `A_total_demand`: total EHCP caseload level + log-linear growth rate only
- `B_need_type_counts`: absolute EHCP counts + 3yr absolute growth in ASD, SEMH, SLCN, MLD (no tribunal/spend/timeliness) — directly tests whether demand-type growth predicted collapse
- `C_need_type_shares`: need-type percentage composition only (tests composition vs. volume)
- `D_counts_capacity`: need-type counts + independent top-up spend + EP service spend
- `E_counts_throughput`: need-type counts + 20-week compliance trend (2019+ only)
- `F_counts_cost`: need-type counts + independent top-up spend + DSG balance
- `G_signals_only`: tribunal appeal rate + trend + independent top-up % of DSG (original strongest model)
- `H_full`: all available features combined

**Need-type data note:** LA-level EHCP counts by primary need type are only available for 2015/16–2019/20 (DfE historical release) and 2024/25 (SEN2 2025). The years 2020/21–2023/24 have no published LA-level need-type breakdown. Models B–F and H use 2020 data as a proxy for training year 2021, and can only produce 3-year growth features from 2019 onward.

**Key finding:** The answer to *did need-type growth predict collapse?* depends on which type of failure:
- **Timeliness collapse**: Model B (need-type counts only) outperforms Model G (signals), AUC 0.66 vs 0.50 at 2020. Need-type growth was the dominant predictor.
- **Legal-pressure and placement collapse**: Model G dominates (AUC 0.83–0.88), with B adding modest incremental value. System-failure signals dominated.

**Evaluation:** LOO cross-validated AUC, Precision@10, Precision@20. Safety Valve / DBV status never enters any model as feature or target.

---

## Methodology notes

- **Non-parametric tests:** Mann-Whitney U (two-group) and Kruskal-Wallis H (three-group) for all group comparisons, given non-normal distributions.
- **OLS regressions:** DV ∈ {refusal rate, timeliness, tribunal rate}; predictors: DSG financial stress per pupil, IMD 2019 average score, region fixed effects. Two samples: n=50 (hardcoded DSG estimates) and n=147 (S251 full data).
- **Event study:** Safety Valve entry year as t=0; outcomes averaged by event-time for SV vs no-intervention LAs. Pre-period uses tribunal data back to 2014.
- **Mediation (Baron-Kenny):** Chain: DSG deficit → throughput stress (M1) → 20-week timeliness (M2) → tribunal appeal rate. Sobel test for each indirect path. All paths non-significant in the 134-LA sample.
- **Small LAs excluded:** City of London and Isles of Scilly excluded from all statistical tests due to tiny population.

---

## Caveats

1. **Refusal rate inflation by backlogs:** LAs with large backlogs show lower *apparent* refusal rates (decisions still pending). Gatekeeping via delay rather than formal refusal is not captured by refusal rates.
2. **Timeliness and tribunal clock-stopping:** LAs can pause the statutory 20-week clock during mediation/tribunal proceedings, which may depress reported timeliness independently of capacity.
3. **Forecastability ≠ causal mechanism:** High AUC from early tribunal rates reflects partly autocorrelation (persistent structural conditions), not pure prediction of future events.
4. **DSG balance ≠ operational capacity:** End-of-year DSG carry-forward is an accounting figure; it does not directly measure staffing levels or throughput capacity.
5. **Scenario projections are sensitivity illustrations, not forecasts:** Real-world dynamics (policy interventions, capital programmes) are not modelled.
6. **Selection into Safety Valve:** SV LAs were already performing worse before programme entry (pre-entry timeliness gap: −11.6 pp, three years before entry). Causal inference from cross-sectional comparisons should be treated with caution.
7. **Parallel trends unverifiable:** The event study has only 3 pre-entry years of SEN2 process data (2019–2021) for most SV LAs, limiting formal DiD assumptions.

---

## Licence

Code: MIT. Data outputs in `outputs/` are derived from Crown Copyright data (Open Government Licence v3.0).
