# England's SEND system: what the data shows, what it predicted, and what to do now

**Briefing note | Matt Sharpe, Oxford Internet Institute / Automattic | May 2026**

---

### What this analysis does

Using ten years of publicly available Crown data — DfE SEN2 statistics, S251 local authority expenditure returns, and SEND Tribunal records — this analysis identifies what is driving England's SEND timeliness crisis, tests whether the collapse was foreseeable from public data, and makes the data-driven case for a forward capital programme.

---

### Three findings

**1. The timeliness failure is system-wide and structurally driven.**

In 2024, 51.8% of EHCPs were issued within the legal 20-week limit nationally. 59 of 151 councils — nearly 40% — issued fewer than 40% of plans on time. The worst performers span every council type: Devon (Safety Valve, 3.2%), Portsmouth (no programme, 4.3%), Leicestershire (DBV, 4.3%), Plymouth (no programme, 6.0%), Cornwall (DBV, 7.4%), Slough (Safety Valve, 7.4%).

The primary driver is a structural mismatch: Social, Emotional and Mental Health (SEMH) need has grown from 12.7% to 20.7% of all EHCP children since 2015/16. Over the same period, new maintained SEMH school openings have halved as a share of all new special school openings. Councils whose populations live further from maintained SEMH provision spend significantly more on independent placements (p=0.003, n=146). Independent placements — median £97,322 per child per year — drive DSG deficits, which cut staffing, which slows assessment throughput, which compounds the crisis.

**2. The national crisis was foreseeable from mid-2017 — but which councils would fail was not.**

A publication-vintage backtest — using only statistics actually published by each date, taken from the original releases — shows that a one-line extrapolation of the DfE's own caseload series predicted the 2024 total within 8% from mid-2017, and within 1.3% from mid-2018. The 2014 reform's planning assumption (roughly one-for-one conversion of statements) was 36 standard deviations below the published data by May 2017, and the department's own age tables refuted the "it's just the new 16–25 age range" explanation from 2018. A 36-cell stress test constructible in mid-2017 brackets everything that later happened: actual 2024 caseload, late plans, and independent placement spend all fall inside it, and 58% of its cells double placement spending by 2024.

The counterpart finding is a null: no signal genuinely published in 2016–18 identified *which* councils would fail (all perform at chance; council timeliness rank order reshuffled completely, ρ=0.01). The crisis was national, so the necessary response — educational psychologist training, specialist capacity, funding reform — was national, and needed to start in 2017–18 to land in time. Published tracking that reports ASD and SEMH as a *percentage* of total EHCPs also watches the wrong measure: the informative signal is absolute volume growth against planning assumptions.

**3. Several councils with no formal DfE programme are already failing.**

A model trained on 2021 features — with no knowledge of programme membership — identifies the following councils with no current DfE intervention as structurally similar to councils that entered systemic failure. Given finding 2, this is a support-targeting tool (these councils are *already* deteriorating on observable metrics), not a prediction of future failures:

| Council | Risk score | Mean timeliness 2022–24 | Appeal rate | Indep./1,000 pupils |
|---|---|---|---|---|
| Essex | 0.83 | 9.3% | 5.2% | 1.6 |
| Newcastle upon Tyne | 0.75 | 9.4% | 0.9% | 0.9 |
| Bromley | 0.75 | 33.7% | 4.0% | 3.9 |
| Hertfordshire | 0.73 | 43.0% | 11.7% | 1.0 |
| Staffordshire | 0.69 | 33.5% | 5.3% | 4.7 |
| Derby | 0.67 | 20.6% | 5.7% | 2.9 |

Essex and Newcastle are not approaching crisis — they are already in it, with fewer than one in ten plans issued on time. Bromley, Staffordshire, and Derby are below the 40% threshold that defined collapse in this analysis. None has a formal DfE engagement framework.

*Risk scores are model outputs reflecting structural similarity to councils that entered collapse — not official designations.*

---

### The invest-to-save case

This analysis identifies 467 LA × need-type provision gaps across England, ranked by urgency. The top 30 priorities — 20 new maintained special schools and 10 resourced provision units — require approximately **£420 million** of capital investment and generate an estimated **£76 million per year** in avoided independent placement costs at full operation. The 15-year Green Book-style discounted net present value is **£220 million**. Undiscounted break-even: **2034**.

The urgency is created by lead times. New maintained special schools take four to six years from planning to first pupils. A capital decision deferred to 2027 delivers no new places before 2033, locking in three further years of independent placement costs accumulating at current rates.

---

### The policy question

The government's February 2026 white paper addresses the structural design failures of the 2014 Act. This is the right long-run response. But the 2014 reform failed in part because its planning assumptions carried no published monitoring triggers — the data breached them by 36σ without institutional consequence. Neither the old system nor the new one publishes its demand assumptions alongside a tracker of national caseload, new-plan flow, throughput, independent-provider exposure, and DSG balance, with explicit tripwires.

The data to build that framework is already published, and this analysis demonstrates it (the five series, with thresholds, in `outputs/tables/`). The question is whether DfE will attach it to the white paper's own assumptions — and whether the councils above are receiving proactive engagement proportionate to the deterioration the data already shows.

---

### Full analysis and code

All code, data, and methodology are publicly available and fully reproducible:
**github.com/Kali89/la-send-analysis**

Two substantive articles are published in the repository: an analysis of the system-wide timeliness failure and its structural causes, and a structured post-mortem examining what the public data should have prompted and when.

---

*Matt Sharpe is a part-time DPhil candidate in Social Data Science at the Oxford Internet Institute. This analysis was conducted independently using publicly available data.*

*Correspondence: matthew.sharpe@oii.ox.ac.uk*
