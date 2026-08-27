#!/usr/bin/env python3
"""
cost_of_delay.py

"When was action actually taken — and what did the 2017-18 inaction cost?"

Builds on vintage_backtest.py, which establishes that the national crisis was
quantitatively predictable from mid-2017 (within 7.5%) and undeniable by
mid-2018 (within 1.3%), and that the low-regret response window was 2017-18.

Part 1 assembles the verified timeline of actual government action against the
signal timeline.

Part 2 quantifies the cost of the delay through two counterfactuals in which
the capacity decisions actually taken in 2022-2024 are taken in 2018 instead
(same programmes, same money, earlier start):

  A. CONSERVATIVE ("mix-shift only"): maintained capacity online from 2021
     holds the independent share of placements at its 2019 level; only the
     share excess is treated as avoidable. All volume growth is absorbed.
  B. CENTRAL ("diversion of growth"): maintained capacity absorbs a fraction
     (base 40% — the diversion rate used in cost_benefit.py, capped there at
     65%) of the GROWTH in independent placements above the 2019 count,
     ramping in over 2021-2023 as RPUs (2-yr lead) then schools (4-6 yr
     lead) come online.

Savings per diverted child-year: £75,000 base (independent minus maintained
cost, consistent with cost_benefit.py; S251 2023/24 median independent cost
£97,322). Sensitivity: £60k / £75k / £97k x diversion 20% / 40% / 60%.

A throughput channel counts plans issued late in 2022-24 that would have been
on time had 20-week performance held at its 2019 level (an EP cohort expanded
from September 2018 qualifies by 2021-22).

Outputs
-------
outputs/figures/51_cost_of_delay.png
outputs/tables/action_timeline.csv
outputs/tables/cost_of_delay.csv
outputs/tables/cost_of_delay_sensitivity.csv
"""

from __future__ import annotations
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

warnings.filterwarnings('ignore')

ROOT      = Path(__file__).parent
FIG_DIR   = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'
FIGURE_DPI = 150

BASE_SHARE_YEAR   = 2019       # last pre-ramp observation year in SEN2 data
DIVERSION_BASE    = 0.40       # cost_benefit.py base diversion rate
SAVING_PER_CHILD  = 75_000     # £/yr, net of maintained top-up (cost_benefit.py)
RAMP = {2021: 1/3, 2022: 2/3}  # capacity ramp under a 2018 capital decision
                               # (RPUs online 2020-21, schools 2022+); 2023+ = 1.0

C_ACTUAL = '#222222'
C_CF     = '#2ca02c'
C_WEDGE  = '#d62728'


def to_num(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.strip().str.replace(',', ''),
                         errors='coerce')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: DATA
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("Loading placement, spend, and timeliness data...")
print("=" * 70)

nat = pd.read_csv(TABLE_DIR / 'vintage_national_series.csv', index_col='year')

cas = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/caseload.csv', low_memory=False)
cas_nat = cas[cas['geographic_level'] == 'National'].copy()
if 'breakdown_topic' in cas_nat.columns:
    m = cas_nat['breakdown_topic'].eq('All EHC plans')
    if m.any():
        cas_nat = cas_nat[m]
cas_nat['jan'] = cas_nat['time_period'].astype(str).str[:4].astype(int) + 1
for c in ['ehcplans', 'special_independent']:
    cas_nat[c] = to_num(cas_nat[c]).values
place = cas_nat.groupby('jan')[['ehcplans', 'special_independent']].sum()
place['indep_share'] = place['special_independent'] / place['ehcplans']

indep_topup = nat['s251_indep_topup_gbp_m'].dropna()          # £m by FY-end
unit_cost = (indep_topup.reindex(place.index) * 1e6 / place['special_independent'])
print(place.assign(unit_cost=unit_cost).to_string(float_format='{:,.3f}'.format))

tl = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/timeliness_20_week.csv', low_memory=False)
tl_nat = tl[(tl['geographic_level'] == 'National') &
            (tl['breakdown_topic'] == 'All EHC plans issued')].copy()
tl_nat['year'] = tl_nat['time_period'].astype(int)
tl_nat['den']    = to_num(tl_nat['plans_issued_den']).values
tl_nat['within'] = to_num(tl_nat['plans_issued_within_20_weeks']).values
tl_nat = tl_nat.set_index('year')[['den', 'within']].sort_index()
tl_nat['rate'] = tl_nat['within'] / tl_nat['den']

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: THE ACTION TIMELINE (verified against contemporary sources)
# ─────────────────────────────────────────────────────────────────────────────
print("\nWriting action timeline...")

timeline = [
    # (date, kind, event, lag from May 2017 signal in years)
    ('2016-05', 'signal', 'First anomaly: caseload +6.7%, but attributable to 16-25 age extension (school-age -0.3%). Genuinely ambiguous.', None),
    ('2017-05', 'signal', 'THE PIVOT: caseload +12.1% (36 sigma above 2014 planning assumption); school-age growth positive; new plans +24% above any statements-era year. Low-regret window opens.', 0.0),
    ('2017-12', 'signal', 'First S251 outturn trend: independent top-ups ~£1bn, rising 8%/yr.', 0.6),
    ('2018-03', 'signal', 'Statutory transition ends: conversion can no longer explain growth.', 0.8),
    ('2018-05', 'signal', 'Caseload +11.3% (60 sigma); new plans +45% above statements-era peak. Window for capital decisions.', 1.0),
    ('2018-12', 'action', 'FIRST RESPONSE: £250m revenue top-up + £100m capital over two years (~4% of high-needs budget/yr); call for evidence.', 1.6),
    ('2019-05', 'signal', 'Caseload +10.7% (86 sigma); extrapolation now predicts 2024 within 1%. NAO report (Sept) and Education Committee (Oct) publish the diagnosis.', 2.0),
    ('2019-09', 'action', 'SEND Review launched. Spending round adds >£700m high-needs revenue for 2020-21 (demand-following). First modest EP training expansion announced: intake ~160 to ~200/yr from Sept 2020 (qualify 2023).', 2.3),
    ('2020-11', 'action', 'DSG statutory override: deficits moved off council balance sheets (accounting measure, no capacity).', 3.5),
    ('2021-03', 'action', 'Safety Valve programme begins: bespoke deficit-recovery deals (38 councils by 2024, >£1bn of DfE payments).', 3.8),
    ('2022-03', 'action', 'SEND green paper. FIRST MAJOR CAPITAL PROGRAMME: £2.6bn high-needs capital 2022-25 (announced SR21) - the 2018-window decision, four years late; places land 2024-27.', 4.8),
    ('2022-07', 'action', 'Delivering Better Value programme (~54 councils).', 5.2),
    ('2023-03', 'action', 'SEND & AP Improvement Plan: workforce plan, quality standards. £21m for 2024+2025 EP cohorts (~400/yr intake from Sept 2024; qualify 2027+).', 5.8),
    ('2024-12', 'action', 'Safety Valve closed to new entrants. Cumulative DSG deficits >£3.3bn; override extended to March 2026.', 7.6),
    ('2026-02', 'action', 'White paper: structural redesign of the 2014 framework.', 8.8),
]
timeline_df = pd.DataFrame(timeline, columns=['date', 'kind', 'event', 'years_after_2017_signal'])
timeline_df.to_csv(TABLE_DIR / 'action_timeline.csv', index=False)
print(timeline_df[['date', 'kind', 'event']].to_string(index=False, max_colwidth=80))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: COUNTERFACTUAL A/B — PLACEMENT CAPACITY CHANNEL
# ─────────────────────────────────────────────────────────────────────────────
print("\nComputing placement-channel counterfactuals...")

base_share = place.loc[BASE_SHARE_YEAR, 'indep_share']
base_count = place.loc[BASE_SHARE_YEAR, 'special_independent']
print(f"  Baseline ({BASE_SHARE_YEAR}): {base_count:,.0f} independent placements "
      f"({base_share:.2%} of caseload)")

rows = []
for yr in place.index:
    if yr <= BASE_SHARE_YEAR:
        continue
    ramp = RAMP.get(yr, 1.0 if yr >= 2023 else 0.0)
    P, C = place.loc[yr, 'special_independent'], place.loc[yr, 'ehcplans']
    share_excess  = max(0.0, P - base_share * C)      # conservative scope
    growth_excess = max(0.0, P - base_count)          # central scope
    for scope, excess in [('A_mix_shift_only', share_excess),
                          ('B_diversion_of_growth', growth_excess)]:
        diverted = DIVERSION_BASE * ramp * excess
        rows.append({
            'fy_end': yr, 'scope': scope, 'ramp': ramp,
            'indep_actual': P, 'excess_pool': excess,
            'diverted_children': diverted,
            'saving_gbp_m': diverted * SAVING_PER_CHILD / 1e6,
        })

cf = pd.DataFrame(rows)
cum = cf.groupby('scope')['saving_gbp_m'].sum()
print(f"  Cumulative avoidable spend FY2020-FY2025 (base case: d={DIVERSION_BASE:.0%}, "
      f"£{SAVING_PER_CHILD/1000:.0f}k/child):")
for scope, v in cum.items():
    print(f"    {scope}: £{v:,.0f}m")
flow_2025 = cf[cf.fy_end == 2025].set_index('scope')['saving_gbp_m']
print(f"  FY2025 flow alone: A £{flow_2025.get('A_mix_shift_only', np.nan):,.0f}m | "
      f"B £{flow_2025.get('B_diversion_of_growth', np.nan):,.0f}m")

# Sensitivity: diversion x saving (central scope, cumulative through FY2025)
sens_rows = []
for d in [0.20, 0.40, 0.60]:
    for sv in [60_000, 75_000, 97_322]:
        for scope in ['A_mix_shift_only', 'B_diversion_of_growth']:
            sub = cf[cf.scope == scope]
            total = (sub['excess_pool'] * sub['ramp'] * d * sv).sum() / 1e6
            sens_rows.append({'scope': scope, 'diversion': d,
                              'saving_per_child': sv, 'cumulative_gbp_m': total})
sens = pd.DataFrame(sens_rows)
sens.to_csv(TABLE_DIR / 'cost_of_delay_sensitivity.csv', index=False, float_format='%.0f')
b_range = sens[sens.scope == 'B_diversion_of_growth']['cumulative_gbp_m']
a_range = sens[sens.scope == 'A_mix_shift_only']['cumulative_gbp_m']
print(f"  Sensitivity range (A): £{a_range.min():,.0f}m - £{a_range.max():,.0f}m")
print(f"  Sensitivity range (B): £{b_range.min():,.0f}m - £{b_range.max():,.0f}m")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: THROUGHPUT CHANNEL — EXCESS LATE PLANS
# ─────────────────────────────────────────────────────────────────────────────
print("\nComputing throughput-channel counterfactual...")

tl_base = tl_nat.loc[2019, 'rate']    # 58.7% within 20 weeks (incl. exceptions)
late_rows = []
for yr in [2022, 2023, 2024]:
    den = tl_nat.loc[yr, 'den']
    actual_late = den - tl_nat.loc[yr, 'within']
    cf_late = den * (1 - tl_base)
    late_rows.append({'year': yr, 'plans_issued': den,
                      'late_actual': actual_late, 'late_cf_2019_rate': cf_late,
                      'excess_late': actual_late - cf_late})
late_df = pd.DataFrame(late_rows)
excess_late_total = late_df['excess_late'].sum()
print(late_df.to_string(index=False, float_format='{:,.0f}'.format))
print(f"  Excess late plans 2022-24 vs 2019-rate counterfactual: "
      f"{excess_late_total:,.0f}")

cf.to_csv(TABLE_DIR / 'cost_of_delay.csv', index=False, float_format='%.1f')
late_df.to_csv(TABLE_DIR / 'cost_of_delay.csv', mode='a', index=False,
               float_format='%.1f')

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: FIGURE 51
# ─────────────────────────────────────────────────────────────────────────────
print("\nProducing Figure 51...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5.8))

# Left: actual independent top-up spend vs counterfactual band
ax = axes[0]
yrs = [y for y in indep_topup.index if y >= 2016]
actual_spend = indep_topup.loc[yrs]
cf_b = cf[cf.scope == 'B_diversion_of_growth'].set_index('fy_end')['saving_gbp_m']
cf_a = cf[cf.scope == 'A_mix_shift_only'].set_index('fy_end')['saving_gbp_m']
cf_spend_b = actual_spend - cf_b.reindex(yrs).fillna(0)
cf_spend_a = actual_spend - cf_a.reindex(yrs).fillna(0)
ax.plot(yrs, actual_spend / 1000, color=C_ACTUAL, lw=2.5, marker='o', ms=5,
        label='Actual (S251 outturn)')
ax.plot(yrs, cf_spend_b / 1000, color=C_CF, lw=2.0, linestyle='--',
        label='Counterfactual: 2018 capital decision\n(central, 40% diversion of growth)')
ax.fill_between(yrs, cf_spend_b / 1000, actual_spend / 1000,
                color=C_WEDGE, alpha=0.18, label='Avoidable spend')
ax.plot(yrs, cf_spend_a / 1000, color=C_CF, lw=1.2, linestyle=':',
        label='Counterfactual: conservative\n(mix-shift only)')
ax.axvline(2018, color='gray', lw=1.2, linestyle=':')
ax.text(2018.08, 0.60, 'capital decision\n(counterfactual)', fontsize=7.5,
        color='dimgray', transform=ax.get_xaxis_transform())
ax.axvline(2022, color='gray', lw=1.2, linestyle=':')
ax.text(2022.08, 0.60, '£2.6bn capital\n(actual)', fontsize=7.5,
        color='dimgray', transform=ax.get_xaxis_transform())
ax.set_xlabel('Financial year ending')
ax.set_ylabel('Independent top-up spend (£bn)')
ax.set_title('Independent placement spend:\nactual vs 2018-decision counterfactual',
             fontsize=10, fontweight='bold')
ax.legend(fontsize=7.5, loc='upper left')
ax.grid(True, alpha=0.3)

# Right: cumulative avoidable spend under both scopes
ax2 = axes[1]
cum_b = cf_b.reindex(sorted(cf_b.index)).cumsum()
cum_a = cf_a.reindex(sorted(cf_a.index)).cumsum()
ax2.plot(cum_b.index, cum_b / 1000, color=C_WEDGE, lw=2.5, marker='o', ms=5,
         label='Central (B): 40% diversion of growth')
ax2.plot(cum_a.index, cum_a / 1000, color='#ff7f0e', lw=2.0, marker='s', ms=4,
         label='Conservative (A): mix-shift only')
for series, col in [(cum_b, C_WEDGE), (cum_a, '#ff7f0e')]:
    final_yr, final_v = series.index[-1], series.iloc[-1]
    ax2.annotate(f'£{final_v/1000:.1f}bn', xy=(final_yr, final_v / 1000),
                 xytext=(-40, 6), textcoords='offset points',
                 fontsize=9, fontweight='bold', color=col)
ax2.set_xlabel('Financial year ending')
ax2.set_ylabel('Cumulative avoidable spend (£bn)')
ax2.set_title('Cumulative cost of the delayed capacity decision\n'
              '(same programme, built from 2018 instead of 2022)',
              fontsize=10, fontweight='bold')
ax2.legend(fontsize=8, loc='upper left')
ax2.grid(True, alpha=0.3)

plt.suptitle('What the 2017-18 inaction cost: placement-capacity channel',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(FIG_DIR / '51_cost_of_delay.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 51")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("COST OF DELAY SUMMARY")
print("=" * 70)
print(f"Placement channel, cumulative FY2020-FY2025:")
print(f"  Conservative (mix-shift only) : £{cum['A_mix_shift_only']:,.0f}m "
      f"(range £{a_range.min():,.0f}m-£{a_range.max():,.0f}m)")
print(f"  Central (40% of growth)       : £{cum['B_diversion_of_growth']:,.0f}m "
      f"(range £{b_range.min():,.0f}m-£{b_range.max():,.0f}m)")
print(f"  Running cost of each further year of delay (FY2025 flow): "
      f"£{flow_2025.get('A_mix_shift_only', np.nan):,.0f}m-"
      f"£{flow_2025.get('B_diversion_of_growth', np.nan):,.0f}m/yr")
print(f"Throughput channel: {excess_late_total:,.0f} plans issued late in 2022-24 "
      f"that would have been on time at the 2019 rate")
print("Context (not additive): DSG deficits >£3.3bn by end-2024; Safety Valve "
      "payments >£1bn; high-needs revenue funding rose ~£6.0bn (2018-19) to "
      "£10.7bn (2024-25) — demand-following, after deficits formed.")
print("\nDone.")
