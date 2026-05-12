#!/usr/bin/env python3.12
"""
mismatch_analysis.py
Provision-need mismatch analysis: how the profile of maintained special school
provision compares to the EHCP need profile, nationally and by LA, 2015/16-2024/25.

Sections:
  1. Historical EHCP demand by need type (2015/16–2019/20) — from 2019-20 SEN2 zip
  2. Current EHCP demand by need type (2024/25) — from SEN2 2025
  3. GIAS supply profile — maintained special school capacity by designated SEN type
  4. GIAS new-supply cohort — what type of schools opened in each era
  5. Compute mismatch indices per LA
  6. Figures 29–33
  7. Regression: does mismatch predict independent spend per EHCP?

Outputs:
  outputs/tables/demand_national_trend.csv
  outputs/tables/la_mismatch_2024.csv
  outputs/figures/29_national_demand_shift.png
  outputs/figures/30_mismatch_by_status.png
  outputs/figures/31_mismatch_vs_spend.png
  outputs/figures/32_new_supply_cohort.png
  outputs/figures/33_la_fingerprints.png
"""

import os, zipfile, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
import statsmodels.api as sm

warnings.filterwarnings('ignore')

DATA_DIR = 'data/raw'
OUT_FIG  = 'outputs/figures'
OUT_TAB  = 'outputs/tables'

EN_REGIONS = {
    'South East', 'North West', 'London', 'West Midlands',
    'Yorkshire and the Humber', 'South West', 'East of England',
    'East Midlands', 'North East',
}
STATE_TYPES = [
    'Community special school', 'Academy special converter',
    'Academy special sponsor led', 'Foundation special school',
    'Free schools special', 'Non-maintained special school',
]
KEY_SEN = ['ASD', 'SEMH', 'SLD', 'MLD', 'SLCN']
STATUS_PAL = {
    'Safety Valve':            '#d73027',
    'Delivering Better Value': '#fc8d59',
    'No intervention':         '#4575b4',
}

NEED_MAP = {
    'Autistic Spectrum Disorder':             'ASD',
    'Social, Emotional and Mental Health':    'SEMH',
    'Moderate Learning Difficulty':           'MLD',
    'Severe Learning Difficulty':             'SLD',
    'Profound & Multiple Learning Difficulty':'PMLD',
    'Speech, Language and Communications needs': 'SLCN',
    'Physical Disability':                    'PD',
    'Specific Learning Difficulty':           'SpLD',
    'Hearing Impairment':                     'HI',
    'Visual Impairment':                      'VI',
    'Multi- Sensory Impairment':              'MSI',
    'Other Difficulty/Disability':            'Other',
}

# Academic-year labels for display
YEAR_LABELS = {
    201516: '2015/16', 201617: '2016/17', 201718: '2017/18',
    201819: '2018/19', 201920: '2019/20', 202425: '2024/25',
}

# ── Section 1: Historical EHCP need-type data (2015/16–2019/20) ──────────────
print("Loading historical need-type data (2015/16–2019/20)…")

hist_zip = f'{DATA_DIR}/special-educational-needs-in-england_2019-20.zip'
with zipfile.ZipFile(hist_zip) as z:
    with z.open('data/sen_age_gender.csv') as f:
        chunks = pd.read_csv(
            f,
            usecols=['time_period', 'geographic_level', 'pupil_sen_status',
                     'phase_type_grouping', 'primary_need',
                     'new_la_code', 'number_of_pupils'],
            chunksize=200_000,
        )
        rows = []
        for chunk in chunks:
            chunk.columns = [c.lower() for c in chunk.columns]
            sub = chunk[
                (chunk['geographic_level'] == 'Local authority') &
                (chunk['pupil_sen_status'] == 'Statement or EHC') &
                (chunk['phase_type_grouping'] == 'Total') &
                (chunk['primary_need'].isin(NEED_MAP))
            ].copy()
            sub['n'] = pd.to_numeric(sub['number_of_pupils'], errors='coerce')
            rows.append(sub[['time_period', 'new_la_code', 'primary_need', 'n']])
        hist = pd.concat(rows, ignore_index=True)

hist['need'] = hist['primary_need'].map(NEED_MAP)
hist['la_code'] = hist['new_la_code']

# LA-year totals (across all need types) and per-need counts
totals_hist = (hist.groupby(['la_code', 'time_period'])['n']
               .sum().reset_index(name='total'))
hist = hist.merge(totals_hist, on=['la_code', 'time_period'])
hist['pct'] = hist['n'] / hist['total'] * 100

# National averages by year
nat_hist = (hist.groupby(['time_period', 'need'])
            .apply(lambda g: g['n'].sum() / g['total'].max() * 100
                   if g['total'].max() > 0 else np.nan)
            .reset_index(name='pct_national'))

# Wide LA-year table
demand_hist = (
    hist.pivot_table(index=['la_code', 'time_period'], columns='need', values='pct')
    .reset_index()
)
demand_hist.columns.name = None
demand_hist.columns = (['la_code', 'time_period'] +
                       [f'pct_{c}' for c in demand_hist.columns[2:]])

print(f"  Loaded: {hist['time_period'].nunique()} years, "
      f"{demand_hist['la_code'].nunique()} LAs")

# ── Section 2: Current EHCP need-type data (2024/25) ─────────────────────────
print("Loading current need-type data (2024/25)…")
needs_now = pd.read_csv(f'{DATA_DIR}/sen2_2025/data/sen_needs_all_plans.csv')
needs_now.columns = [c.lower().strip() for c in needs_now.columns]
needs_now = needs_now[
    (needs_now['geographic_level'] == 'Local authority') &
    (needs_now['breakdown_topic']   == 'All EHC plans') &
    (needs_now['breakdown']         == 'All EHC plans')
].copy()
needs_now['la_code'] = needs_now['new_la_code'].fillna(needs_now['old_la_code'].astype(str))
needs_now['total_ehcp_now'] = pd.to_numeric(needs_now['ehc_plans'], errors='coerce')
for col in ['asd_pc', 'semh_pc', 'mld_pc', 'sld_pc', 'slcn_pc']:
    needs_now[col] = pd.to_numeric(needs_now[col], errors='coerce')

demand_now = needs_now[['la_code', 'asd_pc', 'semh_pc', 'mld_pc', 'sld_pc',
                         'slcn_pc', 'total_ehcp_now']].copy()
demand_now.columns = ['la_code', 'pct_ASD_now', 'pct_SEMH_now', 'pct_MLD_now',
                      'pct_SLD_now', 'pct_SLCN_now', 'total_ehcp_now']
print(f"  Loaded: {len(demand_now)} LAs")

# ── National trend: combine historical + current ──────────────────────────────
# Historical national totals by year and need type
nat_demand = (
    hist.groupby(['time_period', 'need'])['n'].sum()
    .reset_index()
)
year_totals = hist.groupby('time_period')['n'].sum().reset_index(name='year_total')
nat_demand = nat_demand.merge(year_totals, on='time_period')
nat_demand['pct_national'] = nat_demand['n'] / nat_demand['year_total'] * 100

# Current national totals
nat_now_counts = {}
for need, col in [('ASD','asd_pc'),('SEMH','semh_pc'),('MLD','mld_pc'),
                  ('SLD','sld_pc'),('SLCN','slcn_pc')]:
    # Weighted average (approximate — use mean of LA %s as national proxy)
    nat_now_counts[need] = needs_now[col].mean()

nat_now_rows = [{'time_period': 202425, 'need': k, 'pct_national': v}
                for k, v in nat_now_counts.items()]
nat_trend = pd.concat([
    nat_demand[nat_demand['need'].isin(KEY_SEN)][['time_period','need','pct_national']],
    pd.DataFrame(nat_now_rows)
], ignore_index=True)

nat_trend.to_csv(f'{OUT_TAB}/demand_national_trend.csv', index=False)
print(f"  Saved national trend: {OUT_TAB}/demand_national_trend.csv")

# ── Section 3: GIAS supply profile ───────────────────────────────────────────
print("\nBuilding GIAS maintained supply profile…")
gias = pd.read_csv(f'{DATA_DIR}/edubasealldata20260512.csv',
                   encoding='latin-1', low_memory=False)
gias.columns = [c.lower().strip() for c in gias.columns]
gias['schoolcapacity'] = pd.to_numeric(gias['schoolcapacity'], errors='coerce')
gias['easting']  = pd.to_numeric(gias['easting'],  errors='coerce')
gias['northing'] = pd.to_numeric(gias['northing'], errors='coerce')

open_eng = gias[
    gias['gor (name)'].isin(EN_REGIONS) &
    gias['establishmentstatus (name)'].isin(['Open', 'Open, but proposed to close'])
].copy()
state_sp = open_eng[open_eng['typeofestablishment (name)'].isin(STATE_TYPES)].copy()
state_sp['sen1_raw'] = state_sp['sen1 (name)'].fillna('')
state_sp['sen_primary'] = (
    state_sp['sen1_raw'].str.split(' - ').str[0].str.strip()
    .where(state_sp['sen1_raw'].str.split(' - ').str[0].str.strip().isin(KEY_SEN), 'Other')
)
state_sp['cap'] = state_sp['schoolcapacity'].fillna(
    state_sp['schoolcapacity'].median()  # impute missing with national median
)

# LA code: use lacode (3-digit) mapped via SEN2 meta, or use la_code from meta
# We need ONS LA code — use the la_code field if available
state_sp['lacode_raw'] = state_sp['la (code)'].astype(str).str.zfill(3)

# Use SEN2 meta for LA code mapping (3-digit → ONS E-code)
meta = pd.read_csv(f'{OUT_TAB}/la_summary_2024_extended.csv')
meta.columns = [c.lower().replace(' ', '_') for c in meta.columns]
# meta has la_code (ONS) and la_name
pupils_raw = pd.read_csv(f'{DATA_DIR}/sen_pupils_2025/data/sen_phase_type_.csv')
pupils_raw.columns = [c.lower() for c in pupils_raw.columns]
la_code_map = (
    pupils_raw[pupils_raw['geographic_level'] == 'Local authority']
    [['new_la_code', 'old_la_code']]
    .drop_duplicates()
)
la_code_map['old_str'] = (
    pd.to_numeric(la_code_map['old_la_code'], errors='coerce')
    .dropna().astype(int).astype(str).str.zfill(3)
)
code_lkp = la_code_map.dropna(subset=['old_str']).set_index('old_str')['new_la_code'].to_dict()

state_sp['la_code'] = state_sp['lacode_raw'].map(code_lkp)

# Aggregate capacity by LA and SEN type
supply_cap = (
    state_sp.groupby(['la_code', 'sen_primary'])['cap']
    .sum().reset_index(name='capacity')
)
supply_total = (
    supply_cap.groupby('la_code')['capacity']
    .sum().reset_index(name='total_cap')
)
supply_cap = supply_cap.merge(supply_total, on='la_code')
supply_cap['supply_pct'] = supply_cap['capacity'] / supply_cap['total_cap'] * 100

supply_wide = supply_cap.pivot_table(
    index='la_code', columns='sen_primary', values='supply_pct', fill_value=0
).reset_index()
supply_wide.columns.name = None
supply_wide.columns = (['la_code'] +
                       [f'supply_pct_{c}' for c in supply_wide.columns[1:]])

print(f"  Supply profile for {len(supply_wide)} LAs")
print(f"  National supply mix:")
nat_supply = supply_cap.groupby('sen_primary')['capacity'].sum()
nat_supply_pct = nat_supply / nat_supply.sum() * 100
for t in KEY_SEN + ['Other']:
    print(f"    {t}: {nat_supply_pct.get(t, 0):.1f}%")

# ── Section 4: New-supply cohort analysis ────────────────────────────────────
print("\nBuilding new-supply cohort by year…")
state_sp['opendate'] = pd.to_datetime(state_sp['opendate'], errors='coerce')
state_sp['open_year'] = state_sp['opendate'].dt.year

cohort = (
    state_sp[state_sp['opendate'].notna() & (state_sp['open_year'] >= 2005)]
    .groupby(['open_year', 'sen_primary'])
    .size().reset_index(name='n_schools')
)
cohort_total = cohort.groupby('open_year')['n_schools'].sum().reset_index(name='total')
cohort = cohort.merge(cohort_total, on='open_year')
cohort['pct'] = cohort['n_schools'] / cohort['total'] * 100

# ── Section 5: Merge and compute mismatch ────────────────────────────────────
print("\nComputing mismatch indices…")

# Get 2015/16 demand for pre/post comparison
demand_1516 = demand_hist[demand_hist['time_period'] == 201516].copy()
demand_1516 = demand_1516.rename(columns={
    'pct_ASD': 'pct_ASD_1516', 'pct_SEMH': 'pct_SEMH_1516',
    'pct_MLD': 'pct_MLD_1516', 'pct_SLD': 'pct_SLD_1516',
})

mismatch = (
    meta[['la_code', 'la_name', 'region', 'intervention_status']]
    .merge(demand_now, on='la_code', how='left')
    .merge(supply_wide, on='la_code', how='left')
    .merge(demand_1516[['la_code', 'pct_ASD_1516', 'pct_SEMH_1516',
                         'pct_MLD_1516', 'pct_SLD_1516']], on='la_code', how='left')
)
mismatch['intervention_status'] = mismatch['intervention_status'].fillna('No intervention')

# ASD gap: demand - supply (positive = more ASD need than maintained provision)
mismatch['asd_gap']  = mismatch['pct_ASD_now']  - mismatch.get('supply_pct_ASD',  pd.Series(dtype=float))
mismatch['semh_gap'] = mismatch['pct_SEMH_now'] - mismatch.get('supply_pct_SEMH', pd.Series(dtype=float))
mismatch['mld_gap']  = mismatch['pct_MLD_now']  - mismatch.get('supply_pct_MLD',  pd.Series(dtype=float))

# Overall mismatch index: sum of positive gaps for ASD and SEMH
mismatch['mismatch_index'] = (
    mismatch['asd_gap'].clip(lower=0) + mismatch['semh_gap'].clip(lower=0)
)

# Demand shift 2015/16 → 2024/25
mismatch['asd_demand_shift']  = mismatch['pct_ASD_now']  - mismatch['pct_ASD_1516']
mismatch['semh_demand_shift'] = mismatch['pct_SEMH_now'] - mismatch['pct_SEMH_1516']

# Merge in spend data for regression
spend_df = pd.read_csv(f'{OUT_TAB}/la_spend_model.csv')
spend_df.columns = [c.lower() for c in spend_df.columns]
spend_df['log_indep_per_ehcp'] = np.log(spend_df['indep_per_ehcp'].clip(lower=1))
mismatch = mismatch.merge(
    spend_df[['la_code', 'indep_per_ehcp', 'log_indep_per_ehcp']],
    on='la_code', how='left'
)

mismatch.to_csv(f'{OUT_TAB}/la_mismatch_2024.csv', index=False)
print(f"  Saved: {OUT_TAB}/la_mismatch_2024.csv  ({len(mismatch)} LAs)")
print()

# Print summary by status
print("Mismatch by intervention status (2024/25):")
print(f"  {'Status':<28}  {'ASD gap':>8}  {'SEMH gap':>9}  {'MLD gap':>8}  {'Mismatch idx':>13}")
for status in ['Safety Valve', 'Delivering Better Value', 'No intervention']:
    sub = mismatch[mismatch['intervention_status'] == status]
    print(f"  {status:<28}  "
          f"{sub['asd_gap'].median():>+7.1f}pp  "
          f"{sub['semh_gap'].median():>+8.1f}pp  "
          f"{sub['mld_gap'].median():>+7.1f}pp  "
          f"{sub['mismatch_index'].median():>12.1f}")

print()
print("Demand shift 2015/16 → 2024/25 by status:")
print(f"  {'Status':<28}  {'ASD shift':>10}  {'SEMH shift':>11}")
for status in ['Safety Valve', 'Delivering Better Value', 'No intervention']:
    sub = mismatch[mismatch['intervention_status'] == status]
    print(f"  {status:<28}  "
          f"{sub['asd_demand_shift'].median():>+9.1f}pp  "
          f"{sub['semh_demand_shift'].median():>+10.1f}pp")

# ── Section 6: Figures ────────────────────────────────────────────────────────
print("\nBuilding figures…")

# Palette for need types
NEED_COLOURS = {
    'ASD':  '#e41a1c',
    'SEMH': '#ff7f00',
    'MLD':  '#4daf4a',
    'SLD':  '#984ea3',
    'SLCN': '#377eb8',
    'PMLD': '#a65628',
    'Other':'#999999',
}

# ── Fig 29: National demand shift 2015/16–2024/25 ─────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6))

focus_needs = ['ASD', 'SEMH', 'MLD', 'SLD', 'SLCN']
years_ordered = [201516, 201617, 201718, 201819, 201920, 202425]
x_labels = [YEAR_LABELS[y] for y in years_ordered]
x_pos = list(range(len(years_ordered)))

for need in focus_needs:
    ys = []
    for yr in years_ordered:
        row = nat_trend[(nat_trend['time_period'] == yr) & (nat_trend['need'] == need)]
        ys.append(row['pct_national'].values[0] if len(row) else np.nan)
    ax.plot(x_pos, ys, marker='o', linewidth=2.5, markersize=6,
            color=NEED_COLOURS[need], label=need)
    # Annotate first and last point
    if not np.isnan(ys[0]):
        ax.annotate(f'{ys[0]:.1f}%', xy=(x_pos[0], ys[0]),
                    xytext=(-22, 4), textcoords='offset points',
                    fontsize=8, color=NEED_COLOURS[need])
    if not np.isnan(ys[-1]):
        ax.annotate(f'{ys[-1]:.1f}%', xy=(x_pos[-1], ys[-1]),
                    xytext=(5, -4), textcoords='offset points',
                    fontsize=8, color=NEED_COLOURS[need])

# Add a gap indicator between 2019/20 and 2024/25
ax.axvline(4.5, color='grey', lw=1, ls=':', alpha=0.6)
ax.text(4.52, ax.get_ylim()[1] * 0.97 if ax.get_ylim()[1] > 0 else 35,
        'data gap\n2020–2024', fontsize=7, color='grey', va='top')

ax.set_xticks(x_pos)
ax.set_xticklabels(x_labels, fontsize=10)
ax.set_ylabel('% of all EHCP children', fontsize=11)
ax.set_title('National EHCP need-type profile, 2015/16–2024/25\n'
             'Demand has shifted toward ASD and SEMH', fontsize=13, fontweight='bold')
ax.legend(fontsize=10, loc='center right')
ax.yaxis.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT_FIG}/29_national_demand_shift.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 29_national_demand_shift.png")

# ── Fig 30: Mismatch by intervention status ────────────────────────────────────
statuses = ['Safety Valve', 'Delivering Better Value', 'No intervention']
gap_vars = [('asd_gap', 'ASD gap', '#e41a1c'), ('semh_gap', 'SEMH gap', '#ff7f00'),
            ('mld_gap', 'MLD gap', '#4daf4a')]

fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
fig.suptitle('Provision–need mismatch by intervention status, 2024/25\n'
             'Positive = more EHCP children with this need than maintained provision capacity',
             fontsize=12, fontweight='bold')

for ax, (var, label, col) in zip(axes, gap_vars):
    vals = [mismatch[mismatch['intervention_status'] == s][var].dropna().values
            for s in statuses]
    bp = ax.boxplot(vals, patch_artist=True, notch=False,
                    medianprops=dict(color='black', linewidth=2))
    for patch in bp['boxes']:
        patch.set_facecolor(col); patch.set_alpha(0.65)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(['Safety\nValve', 'Delivering\nBetter Value',
                        'No\nintervention'], fontsize=9)
    ax.axhline(0, color='black', lw=0.8, ls='--', alpha=0.5)
    ax.set_title(label, fontsize=11, fontweight='bold')
    ax.yaxis.grid(True, alpha=0.3)
    if ax == axes[0]:
        ax.set_ylabel('Demand % − Supply %  (percentage points)', fontsize=10)
    # Mann-Whitney: SV vs None
    sv_v = vals[0]; none_v = vals[2]
    if len(sv_v) > 3 and len(none_v) > 3:
        _, p = stats.mannwhitneyu(sv_v, none_v, alternative='two-sided')
        stars = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
        ax.set_xlabel(f'SV vs None: p={p:.3f} {stars}', fontsize=9)

plt.tight_layout()
plt.savefig(f'{OUT_FIG}/30_mismatch_by_status.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 30_mismatch_by_status.png")

# ── Fig 31: Mismatch index vs independent spend per EHCP ─────────────────────
fig, ax = plt.subplots(figsize=(10, 7))
plot_df = mismatch.dropna(subset=['mismatch_index', 'indep_per_ehcp'])

for status, color in STATUS_PAL.items():
    sub = plot_df[plot_df['intervention_status'] == status]
    ax.scatter(sub['mismatch_index'], sub['indep_per_ehcp'],
               c=color, label=f'{status} (n={len(sub)})', alpha=0.75, s=55, zorder=3)

# Regression line
from numpy.polynomial import polynomial as P
xv = plot_df['mismatch_index'].values
yv = plot_df['indep_per_ehcp'].values
mask = np.isfinite(xv) & np.isfinite(yv)
if mask.sum() > 5:
    slope, intercept, r, p_val, _ = stats.linregress(xv[mask], yv[mask])
    x_line = np.linspace(xv[mask].min(), xv[mask].max(), 100)
    ax.plot(x_line, intercept + slope * x_line, 'k--', lw=1.5, alpha=0.6,
            label=f'OLS: r={r:.2f}, p={p_val:.3f}')

# Annotate biggest outliers
for _, row in plot_df.nlargest(5, 'indep_per_ehcp').iterrows():
    ax.annotate(row['la_name'],
                xy=(row['mismatch_index'], row['indep_per_ehcp']),
                xytext=(5, 3), textcoords='offset points', fontsize=7, color='#555')

ax.set_xlabel('Provision–need mismatch index (ASD gap + SEMH gap, pp)', fontsize=11)
ax.set_ylabel('Independent placement top-up per EHCP (£, S251 1.2.3, 2023/24)', fontsize=11)
ax.set_title('Mismatch between EHCP need profile and maintained provision\n'
             'vs independent placement spend per EHCP', fontsize=12, fontweight='bold')
ax.legend(fontsize=9)
ax.yaxis.grid(True, alpha=0.3); ax.xaxis.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT_FIG}/31_mismatch_vs_spend.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 31_mismatch_vs_spend.png")

# ── Fig 32: New-supply cohort by year ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 6))
cohort_pivot = cohort[cohort['sen_primary'].isin(KEY_SEN + ['Other'])].pivot_table(
    index='open_year', columns='sen_primary', values='n_schools', fill_value=0
)
# Smooth with 3-year rolling mean
cohort_smooth = cohort_pivot.rolling(3, center=True).mean()

bottom = np.zeros(len(cohort_smooth))
colors = [NEED_COLOURS.get(c, '#aaa') for c in cohort_smooth.columns]
for col, color in zip(cohort_smooth.columns, colors):
    ax.bar(cohort_smooth.index, cohort_smooth[col], bottom=bottom,
           label=col, color=color, alpha=0.8, width=0.8)
    bottom += cohort_smooth[col].fillna(0).values

ax.axvline(2016.5, color='black', lw=1.5, ls='--', alpha=0.7,
           label='2016 (SV programme begins)')
ax.set_xlabel('Year school opened', fontsize=11)
ax.set_ylabel('Number of new maintained special schools (3-yr rolling avg)', fontsize=11)
ax.set_title('What type of new maintained special schools were built each year?\n'
             'SEMH share of new openings has fallen sharply since 2016',
             fontsize=12, fontweight='bold')
ax.legend(fontsize=9, loc='upper left')
ax.yaxis.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT_FIG}/32_new_supply_cohort.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 32_new_supply_cohort.png")

# ── Fig 33: LA fingerprints — need vs supply for selected LAs ────────────────
# Select: 4 SV LAs with highest mismatch + 2 low-mismatch comparators
sv_ranked = (mismatch[mismatch['intervention_status'] == 'Safety Valve']
             .dropna(subset=['mismatch_index'])
             .nlargest(4, 'mismatch_index'))
comparators = (mismatch[mismatch['intervention_status'] == 'No intervention']
               .dropna(subset=['mismatch_index'])
               .nsmallest(2, 'mismatch_index'))
selected = pd.concat([sv_ranked, comparators])

need_cols = ['ASD', 'SEMH', 'MLD', 'SLD', 'SLCN']
need_demand_cols = ['pct_ASD_now', 'pct_SEMH_now', 'pct_MLD_now', 'pct_SLD_now', 'pct_SLCN_now']
need_supply_cols = ['supply_pct_ASD', 'supply_pct_SEMH', 'supply_pct_MLD',
                    'supply_pct_SLD', 'supply_pct_SLCN']

n_las = len(selected)
if n_las == 0:
    print("  skipped: 33_la_fingerprints.png (no LAs with complete mismatch data)")
    print("\nDone.")
    import sys; sys.exit(0)
fig, axes = plt.subplots(2, n_las, figsize=(3.5 * n_las, 7))
fig.suptitle('EHCP need profile vs maintained supply profile — selected LAs\n'
             'Top row: demand (% of EHCP children); Bottom row: supply (% of maintained capacity)',
             fontsize=11, fontweight='bold')

for col_idx, (_, row) in enumerate(selected.iterrows()):
    name = row['la_name']
    status = row['intervention_status']
    color = STATUS_PAL.get(status, '#999')
    title_color = color

    demand_vals = [row.get(d, 0) or 0 for d in need_demand_cols]
    supply_vals = [row.get(s, 0) or 0 for s in need_supply_cols]

    x = np.arange(len(need_cols))

    # Demand bar
    ax_top = axes[0, col_idx]
    bars = ax_top.bar(x, demand_vals, color=[NEED_COLOURS[n] for n in need_cols], alpha=0.8)
    ax_top.set_title(f'{name}\n({status[:4]}…)', fontsize=8, color=title_color, fontweight='bold')
    ax_top.set_xticks(x); ax_top.set_xticklabels(need_cols, fontsize=8)
    ax_top.set_ylim(0, 55)
    if col_idx == 0:
        ax_top.set_ylabel('% of EHCP children', fontsize=9)
    ax_top.yaxis.grid(True, alpha=0.3)

    # Supply bar
    ax_bot = axes[1, col_idx]
    ax_bot.bar(x, supply_vals, color=[NEED_COLOURS[n] for n in need_cols], alpha=0.5,
               edgecolor='black', linewidth=0.5)
    ax_bot.set_xticks(x); ax_bot.set_xticklabels(need_cols, fontsize=8)
    ax_bot.set_ylim(0, 55)
    if col_idx == 0:
        ax_bot.set_ylabel('% of maintained capacity', fontsize=9)
    ax_bot.yaxis.grid(True, alpha=0.3)

    # Mark mismatch
    mi = row.get('mismatch_index', 0)
    ax_bot.set_xlabel(f'Mismatch: {mi:.0f}pp', fontsize=8)

plt.tight_layout()
plt.savefig(f'{OUT_FIG}/33_la_fingerprints.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 33_la_fingerprints.png")

# ── Section 7: Regression ─────────────────────────────────────────────────────
print("\nRegression: mismatch → log(indep per EHCP)…")

reg_vars = ['mismatch_index', 'asd_gap', 'semh_gap',
            'pct_ASD_now', 'pct_SEMH_now', 'total_ehcp_now']
reg_df = mismatch.dropna(subset=['log_indep_per_ehcp', 'mismatch_index']).copy()
reg_df['region_clean'] = reg_df['region'].str.replace(' ', '_').str.replace('and_','').str.lower()
rdummies = pd.get_dummies(reg_df['region_clean'], drop_first=True, prefix='r')

X = pd.concat([
    reg_df[['mismatch_index', 'asd_gap', 'semh_gap',
            'pct_ASD_now', 'pct_SEMH_now']].reset_index(drop=True),
    rdummies.reset_index(drop=True)
], axis=1).astype(float)
X = sm.add_constant(X)
y = reg_df['log_indep_per_ehcp'].reset_index(drop=True)

model = sm.OLS(y, X).fit(cov_type='HC3')
with open(f'{OUT_TAB}/mismatch_regression.txt', 'w') as f:
    f.write("Dependent variable: log(S251 1.2.3 per EHCP)\n\n")
    f.write(str(model.summary()))

print(f"  R²={model.rsquared:.3f}  adj-R²={model.rsquared_adj:.3f}  n={int(model.nobs)}")
for v in ['mismatch_index', 'asd_gap', 'semh_gap', 'pct_ASD_now', 'pct_SEMH_now']:
    if v in model.params.index:
        c, p = model.params[v], model.pvalues[v]
        sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        print(f"  {v:<30s}  β={c:+.4f}  p={p:.4f} {sig}")

print("\nDone.")
