# Overview for journalists
### England's SEND system: diagnosis, evidence, and what should happen

---

## The one-sentence finding

England's SEND system is in systemic failure: fewer than half of all new Education, Health and Care Plans were issued within the legal 20-week limit in 2024, the failure cuts across all council types, and the structural cause — a shortage of the right kind of maintained provision — has been visible in the published data for a decade.

---

## The scale of the failure

In 2024, the national 20-week compliance rate for EHCPs was 51.8%. Fifty-nine of 151 upper-tier local authorities — nearly 40% — issued fewer than 40% of new plans on time. Approximately 49,000 children received their plan outside the legal time limit.

This is not a problem confined to councils that have received formal DfE intervention. Devon, in the government's Safety Valve programme, issued only 3.2% of plans on time. Portsmouth, with no formal DfE programme, issued 4.3%. Cornwall, in the Delivering Better Value programme, issued 7.4%. The failure is distributed across all council types.

---

## The structural cause

The problem is not that councils are assessing the wrong children or spending recklessly. It is that the right type of maintained provision does not exist in the right places.

SEMH (social, emotional and mental health) need has grown from 12.7% to 20.7% of the national EHCP caseload between 2015/16 and 2024/25. Over the same period, new maintained SEMH school openings halved as a share of all new special school openings since 2016. The maintained sector did not keep pace with the fastest-growing need type.

The consequence is measurable. Councils whose populations live further from maintained SEMH provision spend significantly more on independent specialist placements (p=0.003). Independent placements are the primary driver of DSG deficits: the median cost of an independent special school placement is £97,322 per child per year, roughly four times the cost of a maintained place. As deficits accumulate, councils cut support services, plans worsen, families go to tribunal, and legal costs compound the problem. This is a structural cycle, not a series of individual commissioning failures.

---

## The forecastability finding

Using only data published before the current crisis, predictive models trained on 2016 information could identify which councils would enter systemic failure — with leave-one-out cross-validated accuracy of AUC 0.70. By 2021, the same models achieved AUC 0.88.

The warning signals were tribunal appeal rates and independent placement spend as a share of the high-needs block. Both are published annually and have been since 2015/16. A council running above-average tribunal rates in 2016 was structurally more likely to be in serious difficulty by 2022–2024. These signals were in the public data. They were not assembled into any early-warning framework that produced action.

A public monitoring dashboard tracking five signals — need-type growth, timeliness trend, independent placement share, tribunal pressure, and DSG carry-forward — would give substantially better early warning than currently exists. The data for all five signals is already in the published record.

---

## The invest-to-save case

This analysis identifies 467 LA x need-type provision gaps across England, ranked by urgency. The top 30 priorities — 20 new maintained special schools and 10 resourced provision units — address the most acute structural deficits in Hampshire, Essex, Norfolk, Cornwall, Suffolk, Lancashire, Bradford, Hertfordshire, and elsewhere.

The capital cost is approximately £420 million (ESFA free school benchmarks: £20 million per new special school, £2 million per resourced provision unit). Against a conservative saving of £75,000 per year for each child redirected from independent to maintained provision, avoided costs cross the £420 million threshold by 2034. The 15-year Green Book-style discounted net present value is £220 million.

Lead times determine urgency. New maintained special schools take four to six years from planning to first pupils. A capital decision deferred to 2027 delivers no new places before 2033 — and locks in three further years of independent placement costs at current rates.

---

## The councils failing now with no DfE programme

Six councils currently show elevated risk scores and no formal DfE intervention:

| Council | Risk score | Mean timeliness 2022–24 | Mean appeal rate | Indep./1,000 pupils |
|---|---|---|---|---|
| Essex | 0.83 | 9.3% | 5.2% | 1.6 |
| Newcastle upon Tyne | 0.75 | 9.4% | 0.9% | 0.9 |
| Bromley | 0.75 | 33.7% | 4.0% | 3.9 |
| Hertfordshire | 0.73 | 43.0% | 11.7% | 1.0 |
| Staffordshire | 0.69 | 33.5% | 5.3% | 4.7 |
| Derby | 0.67 | 20.6% | 5.7% | 2.9 |

Essex and Newcastle are not "at risk of future failure" — they are already failing, with fewer than one in ten plans issued on time. Bromley, Staffordshire, and Derby are below the 40% threshold. Hertfordshire at 43% is borderline. None has a formal DfE programme around it. The question is whether DfE is engaging these councils proactively or waiting for their deficits to become unmanageable.

Risk scores are model outputs reflecting structural similarity to councils that entered systemic collapse — not official designations.

---

## What good looks like

High performance is achievable within existing structures. Lincolnshire issued 99% of EHCPs on time, Gateshead 82.3%, and Oldham 85.8%. None is a wealthy council with easy demographics. Their performance demonstrates that maintained supply, throughput capacity, and system design matter considerably — more than deprivation alone can explain.

---

## Caveats

- The cost-benefit model is indicative. It uses a Green Book-style discount rate (3.5%) and conservative diversion assumptions, but has not been subject to formal HMT optimism-bias adjustment. A 25% capital cost overrun would extend break-even by approximately two years without changing the sign of the 15-year NPV.
- Not all children in independent special schools could be served in maintained settings. The model assumes a 40% diversion rate (adjusted upward for LAs with high existing independent placement rates, capped at 65%), reflecting that some independent placements meet genuinely specialist needs unavailable in the maintained sector.
- The comparator councils (Lincolnshire, Gateshead, Oldham) illustrate that better outcomes are achievable under challenging conditions. They do not prove causation between supply levels and timeliness; other factors — commissioning culture, workforce stability, long-standing investment decisions — will also matter.
- All figures are derived from publicly available Crown copyright data (S251, SEN2, GIAS). The analysis applies statistical methods beyond what DfE currently publishes; it does not claim DfE's data is wrong.

---

## Contact and access

**Author**: Matt Sharpe, Oxford Internet Institute / Automattic
**Email**: matthew.sharpe@oii.ox.ac.uk
**Full analysis, data and code**: github.com/Kali89/la-send-analysis

*All underlying data is Crown Copyright (DfE). Methodology, code, and outputs are fully open and reproducible.*
