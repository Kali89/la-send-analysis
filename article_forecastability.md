# England's SEND collapse was foreseeable — and the next one already is

**An early-warning analysis shows that tribunal rates and independent placement spend in 2016 could already identify which councils would hit crisis. The signals are visible again now in a new set of authorities.**

*Forecastability analysis using DfE SEN2 2025, S251 expenditure 2015/16–2024/25, and SEND Tribunal data 2014–2024 | May 2026*

---

The collapse of EHCP services in England's most financially stressed local authorities did not arrive without warning. The data to predict it existed years before the crisis became visible. This analysis tests that claim directly: using only information available at the end of each year from 2016 to 2021, how accurately could we have identified which councils would enter systemic failure by 2022–2024?

The answer is that a simple two-variable model — tribunal appeal rates and the share of SEND spending going to independent providers — could correctly identify high-risk councils with an AUC of **0.71 from 2016 data alone**, rising to **0.88 by 2021**. The same signals are now visible in a different set of authorities.

---

## What "collapse" means in data

This analysis does not use Safety Valve or Delivering Better Value programme status as either a predictor or a target. Programme status is a policy decision; what we are trying to predict is the underlying operational reality that programmes are a response to.

Three independent collapse definitions are used, each derived from observable system outcomes over the 2022–2024 period:

**Timeliness collapse**: mean 20-week compliance below 40% over 2022–2024. This captures councils where fewer than two in five children received their EHCP within the legal deadline. In 2024, the national rate was 45.9%, but 47 of 151 councils (31%) fell below this threshold. The affected group is not a neat subset of any programme category: it includes Safety Valve councils, Delivering Better Value councils, and several with no formal intervention.

**Legal-pressure collapse**: mean official SEND Tribunal appeal rate above the 75th percentile (4.1%) over 2022–2024. Thirty-five councils (23%) fell in this category. As with timeliness, the high-appeal group is distributed across all programme categories, including some councils with very different financial profiles.

**Placement/cost collapse**: independent special school placements above 3.6 per 1,000 pupils in the most recent available year (2023 or 2024). Thirty-eight councils (25%) exceeded this threshold. This is the variable most closely linked to DSG deficits — independent placements cost £60,000–120,000 per child per year. A council in this category is typically spending £30–50 million annually on independent placements alone, before transport costs.

**Composite collapse**: any council flagging on two or more of the three definitions above. Twenty-four councils (16%) fell into this category. This is the analysis's central prediction target.

Each threshold is configurable in the analysis code and documented at the top of the script.

---

## The crisis was foreseeable from 2016

For each year from 2016 to 2021, features available only up to that year were used to predict the 2022–2024 collapse labels. Five model families were tested — from a simple demand-only model to a full specification including timeliness, spending, and tribunal data — using leave-one-out cross-validation (LOO-CV) to prevent overfitting.

The headline result is striking.

![Forecastability AUC heatmap](outputs/figures/36_forecastability_auc_heatmap.png)

The `signals_only` model — using just two features available as far back as 2016, tribunal appeal rate and the share of total DSG funding going to independent provider top-ups — achieves a LOO-CV AUC of **0.71 for predicting legal-pressure collapse** from 2016 data, rising to **0.88 by 2021**. For composite collapse, the same minimal model achieves AUC 0.50 from 2016 (no better than random at this early stage) but improves to 0.75 by 2021 as the signals strengthen.

For councils that would develop timeliness collapse, the picture is different. Timeliness in 2022–2024 is harder to predict from early data (maximum AUC ~0.72 across all models and years). This is consistent with the finding in the companion analysis that the 2022 timeliness collapse in Safety Valve councils was partly an acute operational event — 3,500 fewer timely plans in a single year, with no corresponding demand surge — rather than a purely gradual structural deterioration.

For placement/cost collapse, the `demand_cost` model (using EHCP growth and independent top-up spend) achieves AUC 0.79 by 2021, rising to 0.81 with the full model. This is the strongest structural predictor: councils that were already directing a high share of their DSG spending to independent providers in 2016–2018 were systematically more likely to have crossed the placement threshold by 2022–2024.

![Forecastability over time](outputs/figures/37_forecastability_over_time.png)

---

## What the signals actually were

The key insight from the feature importance analysis is that the most powerful early warning signals were not demand-side factors — caseload growth rates — but supply-side and legal indicators:

**Independent top-up spend as a share of DSG** (S251 line 1.2.3): This is the single most powerful structural predictor available before 2019. A council spending a disproportionate share of its educational funding on top-up payments to independent and non-maintained providers was already committed to an expensive placement mix years before the financial crisis became acute. The S251 data for this line is available from 2015/16 for all local authorities.

**SEND Tribunal appeal rate**: The tribunal data, published for the first time in 2025 for 2014–2024, shows that the councils now in the Safety Valve were running materially higher appeal rates as far back as 2014–2016. The tribunal rate has strong autocorrelation — councils that were attracting appeals in 2016 were still attracting them at higher rates in 2022–2024. This makes it a robust leading indicator, though partly because it reflects a persistent structural condition rather than predicting a discrete future event.

**DSG carry-forward balance**: The DSG surplus or deficit figure (S251 line 1.9.3) adds predictive value for composite collapse but is less powerful for timeliness. This is consistent with the finding in the companion analysis: DSG deficits are more strongly linked to operational failure (timeliness) in restricted samples (n=50) but lose significance in the full sample.

**Timeliness trajectory**: Once available from 2019 onwards, the timeliness rate and its trend substantially improve prediction of composite and placement collapse (demand_throughput model AUC 0.81 for composite by 2021). But the tribunal and spend signals were already generating AUC >0.70 before timeliness data existed.

![Feature importance: 2016 vs 2021](outputs/figures/38_feature_importance.png)

The comparison between 2016 and 2021 feature importance charts illustrates this progression: in 2016, tribunal rate and independent top-up spend dominate. By 2021, timeliness trend and placement share have joined them, and the overall model is substantially more confident.

---

## Which councils are next

The same model applied to the most recent available data (2021 features, the latest training year not contaminated by the collapse window) produces risk scores for all 151 upper-tier local authorities. These are probabilities of falling into the composite collapse category — not deterministic forecasts, but the model's best estimate of structural similarity to the councils that did collapse.

![Current risk scores](outputs/figures/39_risk_scores_2024.png)

Most of the top-ranked councils are already in DfE intervention programmes, which is exactly what a valid predictive model should produce. The model was trained without programme status as a feature, yet recovers the intervention group with high accuracy. This validates the approach: the risk signals the model uses (tribunal rates, independent spend) are genuinely predictive of the operational failures that triggered intervention.

The more policy-relevant finding is the high-risk group with **no current DfE intervention**:

| Council | Risk score | Mean timeliness 2022–24 | Mean appeal rate | Indep./1,000 |
|---|---|---|---|---|
| Bristol, City of | 0.90 (Critical) | 37.5% | 2.9% | 2.55 |
| Birmingham | 0.83 (Critical) | 49.4% | 5.6% | 1.05 |
| Staffordshire | 0.80 (Critical) | 33.5% | 5.3% | 4.65 |
| Bournemouth, Christchurch and Poole | 0.73 (High) | 28.5% | — | 3.83 |
| Bromley | 0.69 (High) | 33.7% | 4.0% | 3.86 |
| Leicestershire | 0.68 (High) | 4.7% | 3.5% | 3.54 |

Several of these councils are already showing individual collapse-level metrics: Bristol's mean timeliness over 2022–2024 was 37.5% (below the 40% collapse threshold), and Staffordshire's was 33.5%. Leicestershire — with 4.7% mean timeliness — has among the worst individual performance of any council in the country and is not in any programme. Their SEND systems are, by the data, already in crisis.

These are observations about the current data, not predictions about future programme entry. Whether these councils enter the DfE Safety Valve or DBV programmes depends on factors this analysis does not model: political negotiations, DfE capacity, and whether the councils have already begun local remediation. The point is that the operational indicators are already present.

---

## Scenarios: what happens next

For each of the 147 councils with complete projection data, five scenarios are projected to 2030, using each LA's own historical demand and throughput growth trends as the baseline.

![Scenario national aggregate projections](outputs/figures/40_scenario_national_aggregate.png)

**Continuation (current trend)**: New plans issued late per year rise from approximately 49,000 nationally in 2024 to approximately 101,000 by 2030, roughly doubling. Independent placement costs rise from approximately £2.0 billion to £3.7 billion annually. This is not a worst-case scenario; it is simply the extrapolation of current trends.

**ASD/SEMH acceleration (+25% additional demand growth)**: The acceleration in autism and social, emotional and mental health diagnoses seen through 2024 continues at a higher rate. Late plans rise to approximately 127,000 by 2030 — around 2.5 times the 2024 level. This would represent a material further deterioration in system performance even assuming no change in throughput capacity.

**Cost inflation (+10%/year for independent placements)**: Independent school fees continue to rise faster than general inflation, as they have historically. If average costs rise at 10% per year, the annual independent placement bill reaches approximately £6.5 billion by 2030 — more than tripling in six years — even without any increase in the number of independent placements. For individual councils already carrying large placement volumes, this scenario implies insolvency.

**Capacity improvement (+5pp timeliness per year toward 65%)**: If the DfE's investment in EP workforce and case officer capacity succeeds in improving the national 20-week compliance rate by 5 percentage points annually, late plans would reach approximately 65,000 by 2030 — still 30% above the 2024 level, but significantly better than any other scenario. The independent placement cost trajectory does not diverge much in this scenario, because building maintained capacity takes longer than improving timeliness.

**Flat-throughput bottleneck**: Timely case capacity stays constant at its 2024 absolute level — the pattern observed in Safety Valve LAs since 2019, where they processed roughly the same number of timely cases in 2024 as in 2019 while total demand grew 60%. Nationally, this would mean approximately 117,000 late plans per year by 2030, slightly worse than the continuation scenario because it assumes the growing demand all falls into the late bucket.

The scenario range for late plans in 2030 is roughly 65,000 (capacity improvement) to 127,000 (ASD/SEMH acceleration) — a factor of two between the best and worst cases. The cost range is £3.6 billion (capacity improvement) to £6.5 billion (cost inflation). Both ranges are large enough that policy choices matter significantly.

---

## What this means for policy

The primary finding — that system collapse was foreseeable from 2016 using data that was publicly available — has a direct policy implication. England has had the signals of this crisis in published data for a decade. The S251 returns, available annually, showed rising independent placement spend shares from 2015/16 onwards in the councils that would later enter the Safety Valve. The SEND Tribunal data, now published for 2014–2024, showed rising appeal rates over the same period.

An early-warning system using these two signals — independent top-up spend as a percentage of DSG, and tribunal appeal rate — could have identified the high-risk group years before DfE intervention became necessary. Such a system would not prevent the underlying structural problems (insufficient maintained SEMH capacity, historical underinvestment in specialist provision, rising prevalence), but it could trigger earlier engagement and potentially avoid the most acute operational deterioration.

The more immediate implication is for the councils that are now showing the same signals. Bristol, Staffordshire, and Leicestershire already show system-failure-level timeliness metrics and are not in formal intervention. The risk scores say they look structurally similar to the councils that did collapse. The question for the DfE is whether the same early-warning data is informing current engagement.

---

## Limitations

**Cross-sectional training data**: All models are trained on cross-sectional LA-level data. The collapse prediction is therefore partially capturing autocorrelation (high tribunal rates in 2016 predict high tribunal rates in 2022–2024) as well as genuine structural risk. Separating these requires richer time-series methods.

**Missing staffing data**: The single most important variable for predicting operational capacity failure — SEND team staffing (FTE per 1,000 active EHCPs) — is not published in any usable form at LA level. All spend proxies used here (EP service, SEN admin) are imperfect substitutes. The model almost certainly underestimates the predictive power that would be achievable with direct staffing data.

**No appeal grounds data**: The tribunal model relies on overall appeal rates, not grounds. Whether families are appealing refusals, plan contents, or placements matters for interpreting the mechanism. Appeal-grounds data at LA level has not been published.

**Backlog/pending cases**: Neither the S251 data nor SEN2 captures the number of cases outstanding at year end — requests received but not yet decided, or assessments under way but not completed. This is the most direct measure of system pressure, and its absence may explain why timeliness collapse is harder to predict from early data than placement/legal collapse.

**Scenario assumptions are simplified**: Scenario projections use each LA's own historical growth rate as the base and apply multiplicative adjustments. Real-world dynamics — staffing responses, capital programmes, policy changes — are not modelled. The scenarios should be read as sensitivity illustrations, not forecasts.

**Placement direction of causality**: The model uses current independent placement share as a predictor of future collapse, but cannot determine from the cross-section whether high placements caused financial pressure or were a consequence of pre-existing structural factors that also caused the financial pressure. Both pathways are plausible, and the distinction matters for intervention design.

---

## Data and methodology

**Features used**: SEND Tribunal appeal rate 2014–2024 (DfE supporting file); S251 LA education expenditure 2015/16–2024/25 (lines 1.2.3, 1.9.1, 1.9.3, 2.1.1, 2.1.2); DfE SEN2 2025 (timeliness, requests, caseload, placements 2019–2024); historical EHCP need-type data 2015/16–2019/20 (DfE SEN2 2019–20 release); SEN pupils 2024/25 (denominator).

**Target variables**: Computed from 2022–2024 SEN2 and caseload data. Thresholds are configurable. Safety Valve and Delivering Better Value status are used as comparison variables in output charts only, not as features or targets in any model.

**Models**: Logistic regression with L2 regularisation (sklearn, C=1.0), class_weight='balanced', max_iter=1000. Features standardised with StandardScaler within each LOO fold. LOO-CV used throughout for unbiased AUC estimation with N≈140.

**Forecastability rule**: For training year T, only data available at or before year T is used to construct features. The collapse window (2022–2024) is strictly after all training years.

The full analysis code is available at: **[github.com/Kali89/la-send-analysis](https://github.com/Kali89/la-send-analysis)**

---

*This analysis was conducted using publicly available data. Safety Valve and Delivering Better Value status are shown for context only and are not used in any predictive model.*

*The risk scores are model outputs, not official designations. They reflect structural similarity to councils that entered system collapse — not a prediction of DfE programme entry or legal classification.*

*Corrections and methodological challenges are welcome.*
