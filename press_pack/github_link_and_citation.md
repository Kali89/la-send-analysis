# How to cite and link

---

## Repository

**github.com/Kali89/la-send-analysis**

The repository contains:
- Full Python source code for all analyses (MIT licence)
- All data outputs including 143-LA risk score table, 1,753-row panel timeseries, and AUC results across 124 model evaluations
- 43 figures (150 dpi PNG)
- Three substantive articles and this evidence pack
- Methodology notes and caveats

All outputs are derived from Crown Copyright data published under the Open Government Licence v3.0.

---

## How to cite

### For news articles / media

> Analysis by Matt Sharpe (Oxford Internet Institute / Automattic), using DfE SEN2 2025 statistics, S251 local authority expenditure returns, and SEND Tribunal data. Full methodology and code: github.com/Kali89/la-send-analysis

### For academic or policy documents

> Sharpe, M. (2026). *England's SEND crisis: LA-level analysis of gatekeeping, timeliness failure, and forecastability* [Data analysis]. Oxford Internet Institute. Available at: https://github.com/Kali89/la-send-analysis

---

## Author

**Matt Sharpe**
Staff data scientist, Automattic
Part-time DPhil candidate, Social Data Science, Oxford Internet Institute

Correspondence: matthew.sharpe@oii.ox.ac.uk

This analysis was conducted independently, using publicly available data, and does not represent the views of Automattic or the University of Oxford.

---

## Data sources (direct links)

| Dataset | Publisher | Notes |
|---|---|---|
| SEN2 2025 | DfE Explore Education Statistics | explore-education-statistics.service.gov.uk |
| S251 local authority expenditure 2024-25 | DfE Explore Education Statistics | explore-education-statistics.service.gov.uk |
| SEND Tribunals 2014–2024 | DfE (SEN2 2025 supporting file) | Included in SEN2 2025 download |
| GIAS all establishments | get-information-schools.service.gov.uk | Download → all establishments |
| IMD 2019 | MHCLG | English indices of deprivation 2019, Table 10 |
| LSOA 2021 centroids | ONS ArcGIS | Open Geography Portal |

---

## Key figures for reproduction

To reproduce the core findings from scratch:

```bash
pip install pandas numpy matplotlib seaborn scipy statsmodels scikit-learn openpyxl
python analysis.py          # Core SEN2 analysis → figures 01–10
python extension.py         # DSG, event study, mediation → appends FINDINGS.md
python capacity_analysis.py # GIAS capacity → figures 11–14
python timeliness_analysis.py # Capacity ceiling, spend per EHCP → figures 17–21
python forecastability_analysis.py # Risk scores, AUC heatmap → figures 35–43
```

Scripts 3–5 require manual data downloads (GIAS ~61 MB, S251 ~12 MB). See README for full instructions.
