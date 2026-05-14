# A data-driven post-mortem of England's SEND crisis

**Using ten years of published data — tribunal records, local authority spending returns, EHCP caseload statistics, and placement figures — this analysis asks four questions: what should we have known about the coming crisis? When should we have known it? What should have been done in response? And what do we do now?**

*Analysis using DfE SEN2 2025, S251 expenditure 2015/16–2024/25, SEND Tribunal data 2014–2024, and EHCP need-type data 2015/16–2019/20 | May 2026*

---

A post-mortem is not an exercise in blame. It is a structured attempt to learn: to reconstruct what was knowable, what was done, and what the gap between those two things cost. This analysis applies that discipline to England's SEND system — a statutory framework in which local authorities are legally required to assess children with special educational needs and issue Education, Health and Care Plans within twenty weeks. By 2024, fewer than half of those plans were being issued on time nationally, more than a third of councils were failing to meet the statutory deadline in four out of every five cases, and the cost of placing children in independent specialist settings was running at approximately two billion pounds a year and rising.

The data to understand how this happened, and to have partially prevented it, was publicly available throughout. It was not assembled into an early-warning picture that produced action at the right time.

---

## Part One: What happened

The SEND system came under sustained pressure from multiple directions simultaneously. Understanding what failed requires separating three distinct crisis types, because they had different causes, different warning signals, and different solutions.

**Timeliness collapse** is the most visible failure. In 2024, the national 20-week compliance rate was 45.9%. Among the councils in the government's Safety Valve programme — those with the most acute financial pressure — it was 35.8%. Forty-seven councils, nearly a third of all upper-tier local authorities in England, had mean compliance rates below 40% across 2022–2024. These are councils where, on average, more than six in ten children waited longer than the legal deadline for their plan.

**Legal-pressure collapse** is a different pattern. Thirty-five councils had mean SEND Tribunal appeal rates above the 75th percentile nationally over 2022–2024. High appeal rates are expensive in officer time, legal costs, and — critically — tribunal outcomes, which often force higher-cost placements than the council had originally proposed. Some of the councils with the highest appeal rates were not the same as those with the worst timeliness. These are partly distinct failure modes.

**Placement and cost collapse** is the fiscal dimension. Thirty-eight councils had independent special school placement rates above 3.6 per thousand pupils — the top quartile nationally. A council at that level is typically spending £30–50 million per year on independent placements alone, before transport. Independent placement fees have risen faster than general inflation for a decade. A council whose caseload grows while its placement mix shifts toward independent providers faces an almost mechanical DSG deficit, regardless of how well it manages its assessment process.

Twenty-four councils — 16% of all upper-tier local authorities — showed failure on at least two of these three dimensions simultaneously.

None of this was inevitable. And critically, none of it was unforeseeable.

---

## Part Two: What should we have known

The question is not whether someone in government *felt* concerned about SEND pressures. It is whether the *data* available in the published record supported a specific, actionable understanding of the risk — and, if so, which data and from when.

This analysis tests that directly. Using only information available at each year from 2016 to 2021, eight model families were trained to predict which councils would enter systemic failure by 2022–2024. The models use no benefit of hindsight: features are constructed strictly from data that existed at each training date.

The headline finding is that early warning signals existed, but they were different for different types of failure.

**For timeliness failure, the warning was in the demand data.**

Absolute caseload growth — particularly in ASD (autistic spectrum disorder) and SEMH (social, emotional and mental health) diagnoses — predicted which councils would subsequently fail to meet statutory deadlines. A model using only need-type caseload counts and growth rates, with no tribunal history and no financial data, achieves a prediction accuracy (LOO-CV AUC) of 0.69 for timeliness collapse from 2019 data. The equivalent model using only system-stress signals — tribunal rates and independent placement spend — performs near-randomly on timeliness (AUC 0.50). The demand complexity signal and the financial-stress signal are predicting different things.

This finding is *consistent with* a throughput mechanism: councils absorbing rapid growth in ASD and SEMH caseloads — need types that tend to require specialist input, multi-agency coordination, and more complex plan-writing — faced rising per-case workload that total caseload volumes alone do not capture. But it is worth being precise: the model is predictive, not causal. It shows that need-type growth was *associated* with subsequent timeliness failure; it does not directly measure the staffing, EP hours, or assessment complexity that might explain why.

One important caveat: a model using only total EHCP demand — ignoring need type entirely — performs similarly to the need-type model for timeliness (AUC 0.65–0.70 across training years). The cleaner result is that need-type *shares* — the proportional composition of a council's caseload — are near-useless for prediction (AUC ~0.50). Absolute volume matters; proportional mix does not, independently of volume. This suggests that monitoring systems focused on the percentage of EHCPs that are ASD or SEMH, rather than the absolute growth in those numbers, were looking at the wrong measure.

**For legal-pressure and placement failure, the warning was in the financial and legal data.**

A model using tribunal appeal rate and independent top-up spend as a percentage of DSG — both published annually since 2015/16 — achieves AUC 0.71 for legal-pressure collapse from 2016 data alone, rising to 0.88 by 2021. For placement and cost collapse, the same signals achieve AUC 0.72–0.80 from 2019 onward (0.56–0.72 in 2016–2018 as the signal builds), with the full model reaching 0.86 from 2019.

The tribunal rate has strong autocorrelation: councils that were attracting high appeal rates in 2014–2016 continued to do so in 2022–2024. This is not purely a prediction of future events — it partly reflects a persistent structural condition in how some councils operate, how local advice ecosystems work, and how parental awareness and expectations vary. But it is precisely that persistence that makes it a useful early signal: a council running above-average tribunal rates in 2016 was structurally more likely to be in the high-appeal group six years later.

**The two-signal picture.**

A useful way to summarise the forecastability findings is this: by 2019, there were two distinct and largely independent early-warning signals in the published data. Rising absolute ASD and SEMH caseloads were warning of timeliness failure. Rising independent placement spend and tribunal rates were warning of financial and legal-pressure failure. The councils that subsequently collapsed on composite measures were disproportionately those that were already showing both.

A monitoring framework that combined these signals would not have predicted the crisis with certainty. But it would have identified a high-risk group with substantially better-than-random accuracy, years before the crisis became acute.

---

## Part Three: When should we have known it

The forecastability results show how prediction accuracy evolved as more data accumulated. For legal-pressure collapse, the tribunal and spend signals were already generating AUC above 0.70 from 2016. For timeliness and composite collapse, the signals strengthened materially once three years of caseload data were available — from around 2019 — when absolute growth features became computable over a meaningful window.

But the "when should we have known it" question has a practical dimension that the AUC figures alone do not capture. The interventions that matter most have the longest lead times.

Training an educational psychologist takes three to four years after a psychology degree. Building a new maintained special school takes four to six years from planning to first pupils. Establishing resourced provision within an existing mainstream school takes one to two years. This means that a government that waits for certainty before acting on these interventions is, in practice, choosing not to act on them at all within the relevant time horizon.

The first full year of EHCP data — 2015/16, published mid-2016 — already showed that the original government impact assessment's assumption of roughly one-to-one conversion from Statements to EHCPs was wrong. EHCP numbers were above Statement numbers and rising. That is sufficient evidence to commission analysis. It is not yet sufficient to commit capital.

Once two consecutive years of above-expected growth were visible — by around 2016/17, with ASD and SEMH visibly driving the trend and rising independent top-up spend appearing in the S251 returns — the case for acting on low-cost, long-lead interventions was established. Two confirmed years of trend in a statutory demand-led system, with a known multi-year delivery lag on the relevant responses, is a reasonable threshold. The data existed. The trend was confirmed. The pipeline for the longest-lead interventions should have started filling.

---

## Part Four: What should have been done

The strongest version of this critique is not "government should have predicted the autism diagnosis rate in 2030." Nobody could reasonably be expected to do that. The critique is narrower and more specific: some interventions are *low-regret* — they remain worthwhile under a wide range of plausible futures, cost relatively little if demand turns out lower than feared, and become very costly to delay if demand continues to grow.

| Intervention | Cost | Lead time | Low-regret? |
|---|---|---|---|
| Expand EP training places | Low | 3–4 years | Yes — useful under almost any demand scenario |
| Publish EHCP quality standards | Low | 6–12 months | Yes — reduces burden and tribunal risk regardless |
| Commission specialist capacity audit | Low | 6–12 months | Yes — prerequisite for any capital decision |
| Resourced provision in mainstream schools | Medium | 1–2 years | Yes — flexible, reversible, local |
| New maintained special schools | High | 4–6 years | Moderate — requires demand confidence, longer commitment |

A government that had run a genuine demand stress test in 2016 or 2017 — asking what happens to timeliness, placements, tribunal volumes, and DSG balances if ASD and SEMH caseloads rise by 10%, 25%, or 50%, while assessment capacity, maintained specialist places, and placement costs move in different ways — would have seen that the low-regret interventions were justified under almost every plausible scenario. They did not require certainty. They required the kind of planning discipline that statutory demand-led systems with long capital lead times should routinely apply.

The government did not need to predict the rise in autism or SEMH demand. It needed to test whether the system could survive it.

By around 2016/17, three low-regret interventions should have been underway: expanded EP training places (cheap, four-year lead time, visible bottleneck); national EHCP quality standards (months to develop, reduces plan-writing burden and tribunal risk regardless of demand trajectory); and a maintained specialist capacity audit to map where provision would need to grow. Once a third year of confirmed trend made the structural shift unambiguous and DSG stress began appearing in the published S251 returns, the case for a capital programme for resourced provision within mainstream schools — the fastest and most flexible way to create local maintained alternatives to independent placements — was clear.

It would not be fair to require new special school construction before the trend was confirmed, or to require precise prevalence forecasts. What is fair to require is that a government running a statutory entitlement system with known long-lead interventions begins the low-regret ones once a trend is confirmed, and plans the higher-regret ones once the trend is unambiguous.

By the time the 2023 SEND and AP Improvement Plan focused seriously on workforce and specialist-capacity expansion — the broadly correct response — many councils were already deep into operational and financial crisis. The plan contained most of what was needed. It would have been considerably more effective had it begun several years earlier.

One counter-argument deserves acknowledgement. The government's February 2026 white paper frames the problem primarily as a structural design failure: the 2014 Act created perverse funding mechanisms, inadequate demand-management triggers, and a system of statutory entitlements that could not be sustained without legislative change. That analysis is not wrong. Structural reform was also needed, and the white paper's redesign — the four-tier system, national price bands for independent school fees, and EHCP restrictions from 2030 — represents a belated reckoning with those design flaws. But the structural argument does not exculpate the failure to act on low-regret interventions. EP training expansion and a capacity audit are not alternatives to legislative reform — they are complementary responses operating on different timescales. A government beginning the legislative process in 2018 could have run both tracks simultaneously. That it did not is a separate failure from the structural one.

---

## Part Five: What do we do now

The post-mortem has a forward-looking purpose. The same signals that predicted the 2022–2024 crisis are visible now in a different set of councils.

**The monitoring dashboard that should exist — and largely does not.**

A useful early-warning system would not track only total EHCP numbers or high-needs block expenditure. It would monitor five signal categories simultaneously, because they warn of different failure modes:

1. **Absolute need-type growth** — the number of new ASD, SEMH, and SLCN EHCPs issued per year per LA, not just as a share of the total. Rising absolute numbers in these categories, relative to assessment throughput, predict timeliness failure. Existing published tracking — by the IFS, IfG, and in DfE's own statistics — tends to report ASD and SEMH as percentages of the total EHCP caseload. The forecastability analysis shows that shares are near-useless for prediction; the signal is in absolute volume.

2. **Timely assessment throughput** — plans issued within 20 weeks as a proportion of new requests, tracked as a trend rather than a single-year snapshot. A council whose throughput rate is falling while demand is rising is compressing its buffer.

3. **Independent-provider exposure** — independent top-up spend as a percentage of total DSG (S251 line 1.2.3 / line 1.9.1). A rising share predicts both cost collapse and reduced negotiating room as the maintained alternative diminishes.

4. **Tribunal pressure** — appeal rate and trend. High autocorrelation means this signal is partly structural, but a rising trend adds information about the direction of travel.

5. **DSG carry-forward** — the end-of-year surplus or deficit as a percentage of total DSG. A council moving into deficit is losing the financial buffer that allows it to absorb demand shocks.

These five signals, tracked together for each of the 151 upper-tier local authorities and updated annually from published data, would give a materially better picture of system risk than any single indicator. The data for all five is available in the published record. The combination is not being monitored in any systematic public framework.

**Which councils currently show the risk signature.**

A predictive model trained on 2021 features — combining need-type caseload growth with timeliness trend, using no Safety Valve or DBV programme status as an input — identifies the following councils with no current DfE intervention as showing structural similarity to councils that entered systemic failure:

| Council | Risk score | Mean timeliness 2022–24 | Mean appeal rate | Indep./1,000 pupils |
|---|---|---|---|---|
| Bristol, City of | 0.90 | 37.5% | 2.9% | 2.55 |
| Birmingham | 0.82 | 49.4% | 5.6% | 1.05 |
| Bromley | 0.77 | 33.7% | 4.0% | 3.86 |
| Lewisham | 0.72 | 53.5% | 2.6% | 5.28 |
| Staffordshire | 0.69 | 33.5% | 5.3% | 4.65 |
| Central Bedfordshire | 0.64 | 26.5% | 2.5% | 1.0 |

Several of these councils are not in the *risk* of collapse — they are already in it on individual indicators. Bristol's mean timeliness over 2022–2024 was 37.5%, below the 40% threshold used throughout this analysis. Bromley's was 33.7%. Staffordshire's was 33.5%. Central Bedfordshire's was 26.5%, among the worst in the country. These are not predictions of future failure. They are observations about a present that is already in crisis, in councils without a formal DfE intervention framework around them.

These risk scores are model outputs, not official designations. They reflect structural similarity to councils that entered collapse — not a prediction of programme entry.

**What happens next under different scenarios.**

For each of 147 councils with complete data, five scenarios are projected to 2030 using each LA's own historical demand and throughput growth as a baseline.

Under continuation of current trends, late plans rise from approximately 49,000 nationally in 2024 to approximately 101,000 by 2030, and independent placement costs rise from approximately £2.0 billion to £3.7 billion. If ASD and SEMH demand accelerates by 25% above trend — a plausible scenario, not an extreme one — late plans reach approximately 127,000. If independent placement fees continue rising at 10% per year, placement costs reach approximately £6.5 billion by 2030 even without any increase in the number of children placed. If assessment capacity improves by five percentage points per year — requiring significant and sustained investment in EP and case officer capacity — late plans reach approximately 65,000, still a third above today's level.

The range between the best and worst scenarios by 2030 is roughly a factor of two on late plans and a factor of nearly two on costs. Policy choices in the next two to three years will determine which part of that range materialises. The interventions with the longest lead times — EP workforce expansion, resourced provision capital, maintained special school places — need to be in the pipeline now to affect outcomes by 2028–2030.

---

## What the post-mortem tells us

Three things emerge from assembling this evidence.

**The data to have seen this coming was available.** Tribunal rates, independent placement spend, and absolute need-type growth were all in the published record. The signals were not hidden. They were not assembled into a monitoring picture that produced action at the right time.

**The forecasting failure was not a failure to predict autism prevalence.** It was a failure to stress-test a statutory demand-led system against the scenarios where demand and costs moved in directions that were all plausible given the data available by 2016. Banks stress test against recessions they cannot forecast. SEND should have been tested against demand and cost shocks it could not precisely predict.

**The window for low-regret action was 2016–2018.** Not because the crisis was certain by then, but because the interventions with the longest lead times — EP training, specialist capacity planning, resourced provision — needed to be in motion by then to have matured at the right moment. Most of what eventually appeared in the 2023 SEND Improvement Plan was the right response. It would have been considerably more effective several years earlier.

The councils now showing the same risk signatures that predicted earlier failures are identifiable from the published data today. The question is whether the monitoring, planning, and intervention framework that was absent in 2016 is being built now — and whether it will be connected to action in time to make a difference.

---

## Data and methodology notes

All analysis uses publicly available data. Safety Valve and Delivering Better Value programme status are used as comparison variables only — they do not enter any predictive model as features or targets. The forecastability models use logistic regression with L2 regularisation, evaluated by leave-one-out cross-validation (LOO-CV AUC) to avoid overfitting with N≈140 local authorities. Eight model families were tested, ranging from a total-demand baseline to a full specification combining need-type counts, tribunal history, S251 spend, and timeliness trends. Collapse is defined from observable 2022–2024 outcomes, with configurable thresholds. Full methodology, code, and output data are available at [github.com/Kali89/la-send-analysis](https://github.com/Kali89/la-send-analysis).

---

*This analysis was conducted using publicly available data. Risk scores are model outputs reflecting structural similarity to councils that entered system collapse — not official designations or predictions of programme entry.*

*Corrections and methodological challenges are welcome.*
