# The investment case for SEN capacity: what it costs, what it saves, and what good looks like

---

## The investment case

Thirty priority facilities — twenty new maintained special schools and ten resourced provision units added to existing schools — require a combined capital outlay of £420 million. Based on a conservative saving of £75,000 per year for each child diverted from an independent placement to a maintained school, those thirty facilities generate cumulative avoided costs that cross the £420 million threshold in 2034: nine years after the capital is committed. By 2040, on the same conservative assumptions, the portfolio has saved £887 million in avoided independent placement costs against a £420 million investment — a net return of £467 million over fifteen years, or roughly £1.10 saved for every £1 spent, before discounting.

Applying a Green Book-style discount rate of 3.5%, the fifteen-year net present value of the portfolio is £220 million. For the highest-efficiency facilities — those serving LAs with the greatest distance to maintained provision and the highest independent placement pressure — the discounted NPV exceeds £13 million per school.

The £75,000 annual saving figure is deliberately conservative. The S251 outturn data for 2023/24 shows a median independent special school placement cost of £97,322 per child per year. The £75,000 figure discounts this to account for placements at the lower end of the cost range and for cases where cross-boundary maintained placements would have been found anyway. Each new maintained special school (100 places, ESFA free school programme benchmark: £20 million) is modelled as diverting approximately 40% of its places from the independent sector — adjusted upward for LAs where independent placement rates are already high, and capped at 65% to avoid implausible assumptions. Resourced provision units (15 places, ESFA benchmark: £2 million) operate on the same principles, becoming self-financing against avoided placement costs within six years.

### Top 10 facilities by 15-year NPV

| Rank | LA | Need type | Facility type | Capital (£m) | Annual saving at capacity (£m) | 15yr NPV (£m) | Break-even |
|---|---|---|---|---|---|---|---|
| 5 | Cornwall | ASD | New special school | £20m | £4.0m | £13.3m | 2035 |
| 12 | Cornwall | SEMH | New special school | £20m | £4.0m | £13.3m | 2035 |
| 6 | Norfolk | MLD | New special school | £20m | £3.8m | £11.8m | 2036 |
| 26 | Shropshire | SEMH | New special school | £20m | £3.7m | £10.5m | 2036 |
| 17 | Wiltshire | SEMH | New special school | £20m | £3.6m | £9.9m | 2036 |
| 8 | Suffolk | ASD | New special school | £20m | £3.6m | £9.7m | 2036 |
| 28 | Suffolk | SEMH | New special school | £20m | £3.6m | £9.7m | 2036 |
| 22 | Kent | SEMH | New special school | £20m | £3.6m | £9.6m | 2036 |
| 25 | Derbyshire | SEMH | New special school | £20m | £3.6m | £9.5m | 2036 |
| 20 | West Sussex | SEMH | New special school | £20m | £3.6m | £9.5m | 2036 |

The RPUs in the top 10 priority rankings — Hampshire, Essex, Norfolk, and Lancashire — break even earlier (2031–2032) because of their lower capital cost, though their absolute NPV is smaller. The economic case for the RPU programme is the faster payback; the economic case for new schools is the larger absolute return in LAs where geography makes a full new school necessary.

---

## What good looks like

The data does not require international comparators to establish what a well-functioning SEND system looks like within England. Five local authorities — Lincolnshire, Liverpool, Southampton, Oldham, and Gateshead — currently meet all four criteria for system health: timeliness above 70% (average 91.7%), maintained special school capacity above 5.0 places per 1,000 pupils (average 6.1), independent placement rate below 15% (average 5.2%), and at least four state special schools. None is in the Safety Valve programme.

Lincolnshire issues 99% of EHCPs on time, maintains 5.2 maintained special school places per 1,000 pupils, and places just 6.5% of its special school children in the independent sector. Liverpool's rate is 97.9% on time, with 5.8 places per 1,000 and 6.8% independent. Southampton achieves 93.5% timeliness with an independent placement rate of just 3.8%.

These are not unusually wealthy councils. Oldham has an average IMD deprivation score of 33.2 — more deprived than all five of the lowest-timeliness authorities in this analysis. Liverpool's score is 42.4, the highest deprivation of any model LA. Liverpool serves a more deprived population than Devon (IMD 18.0) and yet achieves timeliness nearly thirty times higher. This evidence weakens the argument that poor SEND performance is explained solely by deprivation or hard-to-serve populations — though it does not prove causation, since other factors including commissioning culture and long-standing investment decisions will also matter.

The gap between the model LAs and the five worst-performing councils in this dataset is stark. Devon, Portsmouth, Leicestershire, Kingston upon Hull, and Plymouth issue EHCPs on time for fewer than 6% of children, against 91.7% for model LAs. The at-risk group maintains an average of 4.8 maintained special school places per 1,000 pupils against 6.1 for model LAs. Their average independent placement rate is 12.6% — more than twice the model LA rate of 5.2%.

This pattern is consistent with supply constraints — rather than demand or population characteristics alone — as a significant driver of poor performance. Devon has only 3.9 maintained special school places per 1,000 pupils, a 28.8% independent placement rate, and timeliness of 3.2%. The high independent placement rate and low maintained capacity appear structurally linked, though the causal direction is not uniquely identified by this data.

---

## Sensitivity and caveats

The £220 million NPV figure is sensitive to three assumptions. First, the saving per diverted child. If the true net saving is £60,000 rather than £75,000 — reflecting a greater share of lower-cost placements — the portfolio NPV falls to £92 million but remains positive. At £40,000 (a very conservative floor, less than half the S251 median), the 15-year NPV turns negative (−£78 million) — the case at this saving level depends on a longer horizon or higher diversion rates than modelled. At £90,000 (still below the £97,322 median), the NPV reaches £349 million.

Second, capital cost overruns. A 25% overrun on all facilities increases total capital to £525 million. At the base saving assumption of £75,000, the portfolio NPV falls to £116 million — still positive. At £60,000 saving and 25% overrun, the NPV turns marginally negative (−£13 million); the invest-to-save case at that combination is borderline. A 40% overrun at the base £75,000 saving gives an NPV of £53 million — positive but substantially reduced.

Third, diversion rate. Not all children currently in independent placements could appropriately move to maintained settings. The model's 40% base diversion rate — adjusted upward for LAs with high independent placement exposure, capped at 65% — is deliberately conservative. It is not assumed that all independent placements are substitutable.

The model includes lead times and occupancy ramp-up for all facilities. It does not model HMT optimism bias, distributional impacts, or non-monetised benefits (reduced tribunal stress, improved education outcomes). All sensitivity outputs are available in `cost_benefit_sensitivity.csv` in the repository.

---

## Policy implication

The modelling shows two things with reasonable confidence. First, the location of where England's maintained SEN capacity needs to be built: a ranked list of thirty facility investments, totalling £420 million, that would address the most acute structural deficits in access, need-type alignment, and demand growth. Second, that this investment pays back. On conservative assumptions about diversion rates and savings, the portfolio reaches break-even in nine years and generates £467 million in net benefit by 2040.

The model LA evidence adds a third point: the system can work. Five English councils — operating in varied geographies, facing varied deprivation levels — achieve timeliness above 80%, maintain-sector capacity above 5 places per 1,000, and independent placement rates below 7%. They prove that it is possible to run a high-functioning SEND system within existing funding structures. The question is no longer whether the investment makes economic sense, or whether it is possible to build sufficient maintained capacity. The question is who decides to commit the capital, who funds the programme, and when the decision is made. Given four-to-six year lead times on new special schools, a decision deferred to 2027 means no new places before 2033 — and three further years of independent placement costs at £97,000 per child per year.

---

*Data sources: S251 2023/24 outturn (DfE), ESFA free school capital programme benchmarks (DfE, 2023), SEN2 2024/25 (DfE), GIAS school register (May 2026), ONS LSOA 2021 population-weighted centroids. Discount rate: HMT Green Book 3.5%. Capital benchmarks: ESFA free school programme (new special school £20m / 100 places; resourced provision unit £2m / 15 places). Saving per diverted placement: £75,000/yr (S251 median £97,322/yr, conservatively discounted). All model outputs reproducible from `cost_benefit.py` in the repository.*

*Full analysis, data and code: github.com/Kali89/la-send-analysis*
