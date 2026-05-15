# Methodology summary
### One page for journalists and researchers

---

## Data

All data is Crown Copyright, published by the Department for Education under the Open Government Licence.

| Dataset | Years | Used for |
|---|---|---|
| DfE SEN2 2025 (requests, timeliness, caseload, plans) | 2019–2024 | All core analyses |
| SEND Tribunal appeal rates 2014–2024 | 2014–2024 | Group comparisons, prediction models |
| S251 local authority expenditure returns | 2015/16–2024/25 | DSG balance, spending regressions, risk scores |
| SEN2 historical need-type data | 2015/16–2019/20 | Prediction model features |
| GIAS all establishments (May 2026) | 2026 | Capacity analysis |
| IMD 2019 deprivation scores | 2019 | Regression controls |

Safety Valve and Delivering Better Value programme membership is taken from DfE programme announcements (2022–2025). Programme status is not used as a predictor or target in any model.

City of London and Isles of Scilly are excluded from all analyses due to population size.

---

## Group comparisons (Article 1)

Safety Valve LAs (n=29) are compared to no-intervention LAs (n=57) using non-parametric Mann-Whitney U tests, given non-normal distributions. All p-values reported are two-sided. The three headline outcomes are refusal rate, 20-week timeliness, and tribunal appeal rate.

OLS regressions control for DSG financial stress per pupil, IMD 2019 deprivation, and region fixed effects. The event study uses Safety Valve entry year as t=0 and compares pre- and post-entry trajectories to no-intervention councils over the same calendar period.

---

## Forecastability models (Article 2)

Eight model families (A–H) are trained using logistic regression on features constructed exclusively from data available at each training year (2016–2021). The collapse outcome (2022–2024) is defined from observable data — not programme membership:

- **Timeliness collapse**: mean 20-week compliance < 40% over 2022–2024
- **Legal-pressure collapse**: mean tribunal appeal rate > 75th percentile
- **Placement collapse**: independent placements > 75th percentile per 1,000 pupils
- **Composite**: flags on ≥ 2 of the above 3

Models are evaluated using leave-one-out cross-validated AUC, Precision@10, and Precision@20. Higher AUC indicates better discrimination between councils that did and did not collapse.

The current risk scores use Model E (need-type counts + timeliness trend) at training year 2021, which achieves the highest LOO-CV AUC for composite collapse (0.82). Scores reflect structural similarity to councils that entered collapse — not a prediction of programme entry or official status.

---

## Facility planning model (Articles 3–4)

For every local authority and primary need type (ASD, SEMH, MLD, SLD), a priority score is computed as: unmet demand (children with that need type exceeding the maintained sector's designated capacity share) × projected demand growth to 2030 × independent placement pressure (% of current special placements in the independent sector) × log-distance to the nearest maintained school of that type. This ranks 467 LA × need-type combinations by urgency.

**Facility type threshold**: if the nearest maintained provision of that type is within 20km (15km for SEMH), a resourced provision unit (RPU) programme is recommended; beyond that threshold, a new maintained special school. Location recommendations are derived from the distance-weighted centroid of the worst-served third of LSOAs within each LA, cross-referenced to the nearest named school as a place indicator.

---

## Cost-benefit model (Article 5)

The top 30 priority facilities are modelled over a 15-year horizon (2025–2040). Capital benchmarks follow the ESFA free school programme: £20 million per new 100-place maintained special school, £2 million per 15-place resourced provision unit. Revenue savings assume £75,000 per child per year diverted from independent to maintained provision (conservatively discounted from the S251 2023/24 median of £97,322). A base 40% diversion rate is adjusted upward proportionally for LAs with high existing independent placement rates and capped at 65%. Lead times and occupancy ramp-up are modelled explicitly (new schools: 4-year build, then 50%/100% occupancy in years 5/6; RPUs: 2-year lead, then 60%/100% in years 3/4). Cashflows are discounted at HMT Green Book rate (3.5%). The model has not been formally optimism-bias adjusted, but a full sensitivity table (4 saving assumptions × 3 capital overrun scenarios) is published in `cost_benefit_sensitivity.csv`.

---

## Key limitations

1. **Refusal rates understate gatekeeping**: councils with large backlogs show lower apparent refusal rates because many decisions are still pending. Gatekeeping via delay is not captured.
2. **Forecastability ≠ causation**: high AUC partly reflects autocorrelation in persistent structural conditions, not pure future prediction.
3. **Pre-entry selection**: Safety Valve LAs were already 11.6 percentage points worse on timeliness in the three years before programme entry. Cross-sectional comparisons cannot establish that the programme caused deterioration.
4. **Need-type data gap**: LA-level EHCP counts by primary need type are only available for 2015/16–2019/20 and 2024/25. The years 2020/21–2023/24 have no published LA-level breakdown.

---

## Reproducibility

All code, data outputs, and figures are publicly available. The full analysis can be reproduced by running five Python scripts in sequence using publicly downloadable DfE data.

**github.com/Kali89/la-send-analysis**
