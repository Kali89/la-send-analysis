#!/usr/bin/env python3
"""
timeliness_analysis.py

Three analyses:
1. Capacity ceiling — absolute timely throughput vs demand by LA over time
2. Operational spending per EHCP — EP service, SEN admin, transport (2015/16–2024/25)
3. Three-bucket delay distribution and individual LA trajectories

Produces figures 17–21.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

ROOT     = Path(__file__).parent
FIG_DIR  = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'

COLORS = {'Safety Valve': '#d62728', 'DBV': '#ff7f0e', 'None': '#1f77b4'}
STATUS_ORDER = ['Safety Valve', 'DBV', 'None']

def safe(s):
    return pd.to_numeric(
        str(s).strip().replace(',', '').replace('x', 'nan').replace('z', 'nan')
               .replace('-', 'nan').replace('..', 'nan').replace('c', 'nan'),
        errors='coerce'
    )

def safe_series(s):
    return pd.to_numeric(
        s.astype(str).str.strip().replace(
            {'x': np.nan, 'z': np.nan, '-': np.nan, '..': np.nan, 'c': np.nan}
        ), errors='coerce'
    )

# ─── map S251 academic year (e.g. 202324) → calendar year (2024) ────────────
S251_TO_CAL = {
    201516: 2016, 201617: 2017, 201718: 2018, 201819: 2019,
    201920: 2020, 202021: 2021, 202122: 2022, 202223: 2023,
    202324: 2024, 202425: 2025,
}

print("Loading data...")

# ═══════════════════════════════════════════════════════════════════════════
# PART 1: LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════

summary  = pd.read_csv(TABLE_DIR / 'la_summary_2024_extended.csv')
meta     = summary[['la_code', 'la_name', 'intervention_status', 'region']].drop_duplicates('la_code')

# ── Timeliness (calendar year, LA level) ────────────────────────────────────
tim_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/timeliness_20_week.csv', low_memory=False)
tim = tim_raw[(tim_raw['geographic_level'] == 'Local authority') &
              (tim_raw['breakdown'] == 'All EHC plans issued')].copy()
for col in ['plans_issued_den', 'plans_issued_within_20_weeks',
            'pc_plans_issued_within_20_weeks',
            'pc_plans_issued_gt20weeks_ltYear', 'pc_plans_issued_gt_1_year']:
    tim[col] = safe_series(tim[col])
tim = tim.rename(columns={'new_la_code': 'la_code'})
tim['n_timely'] = tim['plans_issued_den'] * tim['pc_plans_issued_within_20_weeks'] / 100
tim = tim.merge(meta.drop(columns=['la_name'], errors='ignore'),
                on='la_code', how='left')
tim['status'] = tim['intervention_status'].fillna('None')

# ── Requests (calendar year, LA level) ──────────────────────────────────────
req_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/requests.csv', low_memory=False)
req = req_raw[req_raw['geographic_level'] == 'Local authority'].copy()
for col in ['requests_made', 'requests_refused', 'requests_ceased_withdrawn']:
    if col in req.columns:
        req[col] = safe_series(req[col])
req = req.rename(columns={'new_la_code': 'la_code'})

# ── S251 spending (academic year, LA level) ──────────────────────────────────
print("Loading S251 spending data...")
s251 = pd.read_csv(
    ROOT / 'data/raw/s251_2025/data/s251_alleducation_la_regional_national.csv',
    low_memory=False, encoding='latin-1'
)
s251_la = s251[s251['geographic_level'] == 'Local authority'].copy()
s251_la['gross_exp'] = s251_la['gross_expenditure'].apply(safe)
s251_la = s251_la.rename(columns={'new_la_code': 'la_code'})
s251_la['cal_year'] = s251_la['time_period'].map(S251_TO_CAL)

SPEND_LINES = {
    'ep_service':    '2.1.1 Educational psychology service',
    'sen_admin':     '2.1.2 SEN administration, assessment and coordination and monitoring',
    'sen_transport': '2.1.4 Home to school transport (pre 16): SEN transport expenditure',
}

spend_wide = {}
for key, line in SPEND_LINES.items():
    df = (s251_la[s251_la['category_of_expenditure'] == line]
          [['la_code', 'la_name', 'cal_year', 'gross_exp']]
          .rename(columns={'gross_exp': key}))
    spend_wide[key] = df

spend = spend_wide['ep_service']
for key in ['sen_admin', 'sen_transport']:
    spend = spend.merge(spend_wide[key][['la_code', 'cal_year', key]],
                        on=['la_code', 'cal_year'], how='outer')
spend = spend.merge(meta[['la_code', 'intervention_status', 'region']],
                    on='la_code', how='left')
spend['status'] = spend['intervention_status'].fillna('None')

# ── EHCP caseload (academic year) ────────────────────────────────────────────
cas_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/caseload.csv', low_memory=False)
cas_all = []
for tp in [201819, 201920, 202021, 202122, 202223]:
    df = cas_raw[(cas_raw['time_period'] == tp) &
                 (cas_raw['geographic_level'] == 'Local authority')].copy()
    df['ehcplans'] = safe_series(df['ehcplans'])
    df['cal_year'] = S251_TO_CAL[tp]
    cas_all.append(df[['new_la_code', 'cal_year', 'ehcplans']])
for tp in [202324, 202425]:
    df = cas_raw[(cas_raw['time_period'] == tp) &
                 (cas_raw['geographic_level'] == 'Local authority') &
                 (cas_raw['breakdown_topic'] == 'All EHC plans')].copy()
    df['ehcplans'] = safe_series(df['ehcplans'])
    df['cal_year'] = S251_TO_CAL[tp]
    cas_all.append(df[['new_la_code', 'cal_year', 'ehcplans']])

caseload = (pd.concat(cas_all, ignore_index=True)
            .rename(columns={'new_la_code': 'la_code'})
            .drop_duplicates(['la_code', 'cal_year']))

# Merge spend with caseload
spend = spend.merge(caseload, on=['la_code', 'cal_year'], how='left')

# Per-EHCP spend
spend['ep_per_ehcp']        = spend['ep_service']    / spend['ehcplans']
spend['admin_per_ehcp']     = spend['sen_admin']      / spend['ehcplans']
spend['transport_per_ehcp'] = spend['sen_transport']  / spend['ehcplans']
spend['operational_per_ehcp'] = spend['ep_per_ehcp'] + spend['admin_per_ehcp']

print(f"  Spend panel: {len(spend)} rows, {spend['la_code'].nunique()} LAs, "
      f"years {sorted(spend['cal_year'].dropna().unique())}")

# ═══════════════════════════════════════════════════════════════════════════
# PART 2: CAPACITY CEILING ANALYSIS (Figure 17 + 18)
# ═══════════════════════════════════════════════════════════════════════════

print("\nBuilding capacity ceiling analysis...")

# ── Figure 17: Absolute timely throughput vs total demand ────────────────────
agg = (tim.groupby(['time_period', 'status'])
       .agg(total_plans=('plans_issued_den', 'sum'),
            timely_plans=('n_timely', 'sum'))
       .reset_index())
agg['late_plans'] = agg['total_plans'] - agg['timely_plans']
agg['pct_timely'] = agg['timely_plans'] / agg['total_plans'] * 100

fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)

for ax, status in zip(axes, STATUS_ORDER):
    d = agg[agg['status'] == status]
    color = COLORS[status]
    ax.fill_between(d['time_period'], d['total_plans'],
                    alpha=0.18, color=color, label='Total plans issued')
    ax.fill_between(d['time_period'], d['timely_plans'],
                    alpha=0.7, color=color, label='Issued within 20 weeks')
    ax.plot(d['time_period'], d['total_plans'],  color=color, lw=2)
    ax.plot(d['time_period'], d['timely_plans'], color=color, lw=2, linestyle='--')
    ax.set_title(status, fontsize=12, fontweight='bold', color=color)
    ax.set_xlabel('Year')
    ax.set_ylabel('Plans issued (aggregate)')
    ax.set_xticks(d['time_period'])
    ax.grid(True, alpha=0.3)
    # Annotate latest gap
    if len(d) > 0:
        latest = d.sort_values('time_period').iloc[-1]
        gap = latest['total_plans'] - latest['timely_plans']
        ax.annotate(f"{gap:,.0f} plans\nlate in {int(latest['time_period'])}",
                    xy=(latest['time_period'], latest['total_plans'] - gap/2),
                    fontsize=8, ha='right', color=color, alpha=0.8)

axes[0].legend(fontsize=8)
fig.suptitle(
    'Timely throughput vs total demand by intervention status (aggregate)\n'
    'Shaded gap = plans issued outside the 20-week legal limit',
    fontsize=12, fontweight='bold'
)
plt.tight_layout()
fig.savefig(FIG_DIR / '17_capacity_ceiling_aggregate.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 17")

# ── Figure 18: LA-level demand growth vs timely capacity growth ──────────────
tim_pivot = (tim[tim['time_period'].isin([2019, 2024])]
             .pivot_table(index='la_code', columns='time_period',
                         values=['plans_issued_den', 'n_timely'])
             .reset_index())
tim_pivot.columns = ['la_code', 'demand_2019', 'demand_2024', 'timely_2019', 'timely_2024']
tim_pivot = tim_pivot.merge(meta, on='la_code', how='left')
tim_pivot['status'] = tim_pivot['intervention_status'].fillna('None')
tim_pivot['demand_growth_pct'] = (tim_pivot['demand_2024'] / tim_pivot['demand_2019'] - 1) * 100
tim_pivot['timely_growth_pct'] = (tim_pivot['timely_2024'] / tim_pivot['timely_2019'] - 1) * 100
tim_pivot = tim_pivot.dropna(subset=['demand_growth_pct', 'timely_growth_pct'])
# Cap extreme outliers for display
tim_pivot['demand_growth_pct'] = tim_pivot['demand_growth_pct'].clip(-20, 200)
tim_pivot['timely_growth_pct'] = tim_pivot['timely_growth_pct'].clip(-100, 200)

fig, ax = plt.subplots(figsize=(10, 8))

for status in STATUS_ORDER:
    d = tim_pivot[tim_pivot['status'] == status]
    ax.scatter(d['demand_growth_pct'], d['timely_growth_pct'],
               color=COLORS[status], alpha=0.7,
               s=60 if status == 'Safety Valve' else 40,
               zorder=3 if status == 'Safety Valve' else 2,
               label=f'{status} (n={len(d)})')

# Diagonal: y=x means timely capacity grew as fast as demand
ax.plot([-20, 200], [-20, 200], 'k--', lw=1, alpha=0.4, label='Capacity kept pace')
ax.axhline(0, color='grey', lw=0.8, alpha=0.4)
ax.axvline(0, color='grey', lw=0.8, alpha=0.4)

# Annotate worst SV cases (high demand, flat/negative timely growth)
worst = tim_pivot[(tim_pivot['status']=='Safety Valve') &
                  (tim_pivot['timely_growth_pct'] < -20)].nlargest(5, 'demand_growth_pct')
for _, row in worst.iterrows():
    ax.annotate(row['la_name'], (row['demand_growth_pct'], row['timely_growth_pct']),
                fontsize=7, xytext=(4, -8), textcoords='offset points', color='#d62728')

ax.set_xlabel('Growth in total plans issued 2019→2024 (%)', fontsize=11)
ax.set_ylabel('Growth in plans issued within 20 weeks 2019→2024 (%)', fontsize=11)
ax.set_title(
    'Assessment demand vs timely capacity growth by LA, 2019–2024\n'
    'Councils above the diagonal kept pace; below the diagonal fell behind',
    fontsize=11, fontweight='bold'
)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(FIG_DIR / '18_demand_vs_capacity_growth.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 18")

# Print capacity ceiling summary
print("\n  Capacity ceiling — absolute timely plans (aggregate by status):")
pivot_summary = agg.pivot_table(index='time_period', columns='status',
                                values=['total_plans','timely_plans','pct_timely'])
print(pivot_summary.round(0).to_string())

# ═══════════════════════════════════════════════════════════════════════════
# PART 3: SPENDING PER EHCP (Figure 19)
# ═══════════════════════════════════════════════════════════════════════════

print("\nBuilding spending analysis...")

# National trend: spend per EHCP by component
nat_spend = (spend[spend['status'].isin(STATUS_ORDER)]
             .groupby(['cal_year', 'status'])
             .agg(
                 ep_total=('ep_service', 'sum'),
                 admin_total=('sen_admin', 'sum'),
                 transport_total=('sen_transport', 'sum'),
                 ehcp_total=('ehcplans', 'sum'),
             )
             .reset_index())
nat_spend = nat_spend[nat_spend['ehcp_total'] > 0]
nat_spend['ep_per_ehcp']        = nat_spend['ep_total']        / nat_spend['ehcp_total']
nat_spend['admin_per_ehcp']     = nat_spend['admin_total']     / nat_spend['ehcp_total']
nat_spend['transport_per_ehcp'] = nat_spend['transport_total'] / nat_spend['ehcp_total']

print("\n  Spend per EHCP by status (2024):")
yr2024 = nat_spend[nat_spend['cal_year'] == 2024]
for _, row in yr2024.iterrows():
    print(f"  {row['status']}: EP=£{row['ep_per_ehcp']:.0f}  "
          f"Admin=£{row['admin_per_ehcp']:.0f}  "
          f"Transport=£{row['transport_per_ehcp']:.0f}")

# ── Figure 19: Spend per EHCP trends ────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)
spend_cols = [
    ('ep_per_ehcp',        'EP service spend per active EHCP (£)',         'Educational Psychology'),
    ('admin_per_ehcp',     'SEN admin/assessment spend per active EHCP (£)', 'SEND Administration'),
    ('transport_per_ehcp', 'SEN transport spend per active EHCP (£)',        'SEN Transport'),
]

for ax, (col, ylabel, title) in zip(axes, spend_cols):
    for status in STATUS_ORDER:
        d = nat_spend[nat_spend['status'] == status].sort_values('cal_year')
        d = d[d[col].notna() & (d[col] > 0) & (d['cal_year'] >= 2016)]
        ax.plot(d['cal_year'], d[col], color=COLORS[status], lw=2,
                marker='o', markersize=4, label=status)
    ax.set_xlabel('Year')
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'£{x:,.0f}'))

axes[0].legend(fontsize=9)
fig.suptitle(
    'Operational spend per active EHCP by intervention status, 2016–2024\n'
    'Note: these cover EP services, administration, and transport only — '
    'not placement top-up costs (the largest expenditure)',
    fontsize=10, fontweight='bold'
)
plt.tight_layout()
fig.savefig(FIG_DIR / '19_spend_per_ehcp.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 19")

# ═══════════════════════════════════════════════════════════════════════════
# PART 4: THREE-BUCKET DELAY DISTRIBUTION (Figure 20)
# ═══════════════════════════════════════════════════════════════════════════

print("\nBuilding delay distribution analysis...")

tim24 = tim[tim['time_period'] == 2024].copy()
tim24 = tim24.dropna(subset=['pc_plans_issued_within_20_weeks',
                              'pc_plans_issued_gt20weeks_ltYear',
                              'pc_plans_issued_gt_1_year'])
tim24 = tim24[~tim24['la_code'].isin(
    summary[summary['is_small_la'] == True]['la_code'].tolist()
)]

# Sort by timely %
tim24_sorted = tim24.sort_values('pc_plans_issued_within_20_weeks')

fig, ax = plt.subplots(figsize=(14, 10))

y_pos = np.arange(len(tim24_sorted))
ax.barh(y_pos, tim24_sorted['pc_plans_issued_within_20_weeks'],
        color='#2ca02c', alpha=0.8, label='Within 20 weeks')
ax.barh(y_pos, tim24_sorted['pc_plans_issued_gt20weeks_ltYear'],
        left=tim24_sorted['pc_plans_issued_within_20_weeks'],
        color='#ff7f0e', alpha=0.8, label='20 weeks – 1 year')
ax.barh(y_pos, tim24_sorted['pc_plans_issued_gt_1_year'],
        left=(tim24_sorted['pc_plans_issued_within_20_weeks'] +
              tim24_sorted['pc_plans_issued_gt20weeks_ltYear']),
        color='#d62728', alpha=0.9, label='Over 1 year')

# Mark intervention status with right-edge tick colour
for i, (_, row) in enumerate(tim24_sorted.iterrows()):
    status = row['status'] if pd.notna(row.get('status')) else 'None'
    dot_color = COLORS.get(status, '#888888')
    ax.plot(102, i, marker='|', color=dot_color, markersize=8, markeredgewidth=2)

ax.set_yticks(y_pos)
ax.set_yticklabels(tim24_sorted['la_name'].fillna(tim24_sorted['la_code']), fontsize=6)
ax.set_xlabel('Percentage of plans issued (%)', fontsize=11)
ax.set_title('Timeliness breakdown by local authority, 2024\n'
             'Right-edge bars: ■ Safety Valve  ■ DBV  ■ No intervention',
             fontsize=11, fontweight='bold')
ax.axvline(100, color='grey', lw=0.5, alpha=0.4)
ax.set_xlim(0, 107)

legend_patches = [
    mpatches.Patch(color='#2ca02c', label='Within 20 weeks (legal limit)'),
    mpatches.Patch(color='#ff7f0e', label='20 weeks – 1 year'),
    mpatches.Patch(color='#d62728', label='Over 1 year'),
]
status_patches = [mpatches.Patch(color=COLORS[s], label=s) for s in STATUS_ORDER]
ax.legend(handles=legend_patches + status_patches, loc='lower right', fontsize=8, ncol=2)
ax.grid(True, axis='x', alpha=0.3)

plt.tight_layout()
fig.savefig(FIG_DIR / '20_timeliness_three_buckets_2024.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 20")

# Print extreme >1yr cases
print("\n  LAs with highest % plans taking >1 year (2024):")
print(tim24.nlargest(15, 'pc_plans_issued_gt_1_year')
      [['la_name', 'status', 'pc_plans_issued_within_20_weeks',
        'pc_plans_issued_gt20weeks_ltYear', 'pc_plans_issued_gt_1_year']]
      .to_string(index=False))

# ═══════════════════════════════════════════════════════════════════════════
# PART 5: SV LA INDIVIDUAL TRAJECTORIES (Figure 21)
# ═══════════════════════════════════════════════════════════════════════════

print("\nBuilding SV individual trajectory analysis...")

sv_las = meta[meta['intervention_status'] == 'Safety Valve']['la_code'].tolist()
sv_tim = tim[tim['la_code'].isin(sv_las)].copy()

# Classify councils as improving/deteriorating based on 2022→2024 change
change = (sv_tim[sv_tim['time_period'].isin([2022, 2024])]
          .pivot_table(index=['la_code', 'la_name'], columns='time_period',
                      values='pc_plans_issued_within_20_weeks')
          .reset_index())
change.columns = ['la_code', 'la_name', 'pct_2022', 'pct_2024']
change['change'] = change['pct_2024'] - change['pct_2022']
change = change.sort_values('pct_2024', ascending=False)

improving    = change[change['change'] > 5]['la_code'].tolist()
deteriorating = change[change['change'] < -5]['la_code'].tolist()

fig, axes = plt.subplots(1, 2, figsize=(16, 8))

for ax, (group, label, color) in zip(axes, [
    (improving,     'Improving (2022→2024 +5pp or more)',     '#2ca02c'),
    (deteriorating, 'Deteriorating (2022→2024 −5pp or more)', '#d62728'),
]):
    grp_data = sv_tim[sv_tim['la_code'].isin(group)]
    for la_code, la_grp in grp_data.groupby('la_code'):
        la_grp = la_grp.sort_values('time_period')
        name = la_grp['la_name'].iloc[0] if la_grp['la_name'].notna().any() else la_code
        ax.plot(la_grp['time_period'], la_grp['pc_plans_issued_within_20_weeks'],
                lw=1.5, alpha=0.75, marker='o', markersize=3)
        # Label endpoint
        latest = la_grp.dropna(subset=['pc_plans_issued_within_20_weeks']).iloc[-1]
        ax.annotate(name, (latest['time_period'], latest['pc_plans_issued_within_20_weeks']),
                    fontsize=6.5, xytext=(3, 0), textcoords='offset points', va='center')

    ax.axhline(20, color='grey', lw=1, linestyle=':', alpha=0.6, label='20% threshold')
    ax.set_ylim(-5, 110)
    ax.set_xlim(2018.5, 2025)
    ax.set_xticks(range(2019, 2025))
    ax.set_xlabel('Year')
    ax.set_ylabel('% EHCPs issued within 20 weeks')
    ax.set_title(f'Safety Valve LAs — {label}\n(n={len(group)})',
                 fontsize=10, fontweight='bold', color=color)
    ax.grid(True, alpha=0.3)

fig.suptitle('Within-Safety-Valve divergence: some councils recovering, others in freefall',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(FIG_DIR / '21_sv_timeliness_trajectories.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 21")

# ─── Summary stats ────────────────────────────────────────────────────────
print("\nImproving SV councils (2022→2024):")
print(change[change['change'] > 5][['la_name','pct_2022','pct_2024','change']].round(1).to_string(index=False))
print("\nDeteriorating SV councils (2022→2024):")
print(change[change['change'] < -5][['la_name','pct_2022','pct_2024','change']].round(1).to_string(index=False))

# ─── Correlation: spending vs timeliness ─────────────────────────────────
print("\nCorrelation: operational spend per EHCP vs timeliness (2024):")
spend24  = spend[spend['cal_year'] == 2024].copy()
tim24_sp = tim24.merge(spend24[['la_code','ep_per_ehcp','admin_per_ehcp',
                                  'transport_per_ehcp']], on='la_code', how='inner')
for col, label in [('ep_per_ehcp','EP per EHCP'),
                    ('admin_per_ehcp','Admin per EHCP'),
                    ('transport_per_ehcp','Transport per EHCP')]:
    sub = tim24_sp[['pc_plans_issued_within_20_weeks', col]].dropna()
    r, p = stats.pearsonr(sub['pc_plans_issued_within_20_weeks'], sub[col])
    sig = '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else 'ns'
    print(f"  {label}: r={r:.3f}, p={p:.4f} {sig}")

# ─── Save tables ─────────────────────────────────────────────────────────
change.to_csv(TABLE_DIR / 'sv_timeliness_change.csv', index=False, float_format='%.1f')

spend_out = (spend[spend['cal_year'] >= 2019]
             [['la_code', 'la_name', 'status', 'cal_year',
               'ep_service', 'sen_admin', 'sen_transport', 'ehcplans',
               'ep_per_ehcp', 'admin_per_ehcp', 'transport_per_ehcp']]
             .sort_values(['la_code', 'cal_year']))
spend_out.to_csv(TABLE_DIR / 'spend_per_ehcp.csv', index=False, float_format='%.2f')

print("\nDone. Figures 17–21 saved.")
