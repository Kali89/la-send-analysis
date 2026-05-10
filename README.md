# England's SEND Crisis: LA-Level Analysis

**Is England's SEND funding crisis causing local councils to gatekeep EHCP applications?**

This repository contains the full analysis pipeline, outputs, and write-up for an investigation into whether financially stressed English local authorities (those under the DfE's Safety Valve programme) are refusing more EHCP applications, failing on statutory timeliness, and facing more SEND Tribunal appeals.

**Key finding:** Financially stressed councils are not refusing significantly more applications — but nearly two-thirds of children assessed in Safety Valve authorities wait longer than the legal 20-week limit for their plan. The crisis is a capacity collapse, not a gatekeeping story.

→ **[Read the full article](article.md)**

---

## Findings at a glance

| Outcome | Safety Valve LAs | No-intervention LAs | p-value |
|---|---|---|---|
| Refusal rate | 25.3% | 25.1% | 0.76 (ns) |
| 20-week compliance | **35.8%** | **57.0%** | 0.001 ** |
| Official tribunal appeal rate | **7.5%** | **5.4%** | 0.045 * |

The five worst LA performers on timeliness in 2024 (Devon 3.2%, Cambridgeshire 7.7%, West Sussex 11.4%, Medway 11.7%, Essex 16.2%) are all Safety Valve authorities.

---

## Repository structure

```
├── analysis.py                  # Main analysis pipeline (data load → figures → tables)
├── extension.py                 # Extension: DSG expansion, mediation, event study
├── article.md                   # Full write-up / blog post
├── outputs/
│   ├── FINDINGS.md              # Detailed statistical findings + caveats
│   ├── figures/                 # 13 PNG charts (150 dpi)
│   │   ├── 01_national_trends.png
│   │   ├── 02_la_refusal_rates_2024.png
│   │   ├── 03_la_timeliness_2024.png
│   │   ├── 03b_la_ehcp_rate_2024.png
│   │   ├── 03c_la_tribunal_rate_2024.png
│   │   ├── 04_regional_boxplots.png
│   │   ├── 05_intervention_vs_none_trends.png
│   │   ├── 06_refusal_vs_tribunal_scatter.png
│   │   ├── 07_regression_coefficients.png
│   │   ├── 07b_regression_coefficients_extended.png
│   │   ├── 08_event_study.png
│   │   ├── 09_mediation_path.png
│   │   └── 10_sv_la_trajectories.png
│   └── tables/
│       ├── la_summary_2024.csv          # 151-LA 2024 cross-section
│       ├── la_summary_2024_extended.csv # + full DSG coverage
│       ├── panel_timeseries.csv         # 1,753 LA-year rows (2014–2024)
│       ├── regression_results.txt       # OLS summaries (n=50)
│       └── regression_results_extended.txt  # OLS summaries (n≈150)
└── data/
    └── raw/                     # Not committed — see Download instructions below
```

---

## Data sources

All data are from official DfE sources and are downloaded programmatically by the analysis scripts. No manual downloads are required to reproduce the 2019–2024 core analysis.

| Dataset | Source | Notes |
|---|---|---|
| SEN2 2025 (requests, timeliness, caseload, plans) | [DfE Explore Education Statistics](https://explore-education-statistics.service.gov.uk/find-statistics/education-health-and-care-plans) | Downloaded via EES API |
| SEND Tribunal appeal rate 2014–2024 | DfE SEN2 2025 supporting file | First published 2025 |
| S251 LA & School Expenditure 2024–25 | [DfE Explore Education Statistics](https://explore-education-statistics.service.gov.uk/find-statistics/la-and-school-expenditure) | DSG 1.9.3 carry-forward; 153 LAs |
| SEN pupils 2024–25 | [DfE Explore Education Statistics](https://explore-education-statistics.service.gov.uk/find-statistics/special-educational-needs-in-england) | Total pupils by LA (denominator) |
| IMD 2019 | [MHCLG IoD2019 Table 10](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/833995/File_10_-_IoD2019_Local_Authority_District_Summaries__lower-tier__.xlsx) | Downloaded at runtime |

Safety Valve and Delivering Better Value programme membership from DfE programme announcements (2022–2025).

---

## Reproducing the analysis

```bash
# Install dependencies
pip install pandas numpy matplotlib seaborn scipy statsmodels requests openpyxl

# Run core analysis (downloads SEN2 2025 data automatically on first run)
python analysis.py

# Run extension (DSG expansion, mediation, event study)
python extension.py
```

The scripts download the required data to `data/raw/` on first run. The S251 and SEN pupils downloads are large (~350MB and ~4.7GB respectively); the SEN2 data is ~36MB.

---

## Methodology notes

- **Non-parametric tests:** Mann-Whitney U (two-group) and Kruskal-Wallis H (three-group) for all group comparisons, given non-normal distributions.
- **OLS regressions:** DV ∈ {refusal rate, timeliness, tribunal rate}; predictors: DSG financial stress per pupil, IMD 2019 average score, region fixed effects. Two samples: n=50 (hardcoded DSG estimates) and n≈150 (S251 full data).
- **Event study:** Safety Valve entry year as t=0; outcomes averaged by event-time for SV vs no-intervention LAs. Pre-period uses tribunal data back to 2014.
- **Mediation (Baron-Kenny):** Chain: DSG deficit → throughput stress (M1) → 20-week timeliness (M2) → tribunal appeal rate. Sobel test for each indirect path. All paths non-significant in the 134-LA sample.
- **Small LAs excluded:** City of London and Isles of Scilly excluded from all statistical tests due to tiny population.

---

## Caveats

1. **Refusal rate inflation by backlogs:** LAs with large backlogs show lower *apparent* refusal rates (decisions still pending). Gatekeeping via delay rather than formal refusal is not captured by refusal rates.
2. **Timeliness and tribunal clock-stopping:** LAs can pause the statutory 20-week clock during mediation/tribunal proceedings, which may depress reported timeliness independently of capacity.
3. **DSG balance ≠ operational capacity:** End-of-year DSG carry-forward is an accounting figure; it does not directly measure staffing levels or throughput capacity.
4. **Selection into Safety Valve:** SV LAs were already performing worse before programme entry (pre-entry timeliness gap: −10.2 pp). Causal inference from cross-sectional comparisons should be treated with caution.
5. **Parallel trends unverifiable:** The event study has only 3 pre-entry years of SEN2 process data (2019–2021) for most SV LAs, limiting formal DiD assumptions.

---

## Licence

Code: MIT. Data outputs in `outputs/` are derived from Crown Copyright data (Open Government Licence v3.0).
