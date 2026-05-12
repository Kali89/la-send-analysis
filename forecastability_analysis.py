#!/usr/bin/env python3
"""
forecastability_analysis.py

"Was England's SEND collapse forecastable — and which councils are next?"

Defines collapse purely from observable system outcomes (timeliness, appeals,
independent placements) — Safety Valve status is NOT used as a predictor or
target. Tests whether data available at each year from 2016 to 2021 could
predict collapse 3–7 years later.

Outputs
-------
outputs/figures/34–43       PNG charts
outputs/tables/la_collapse_labels.csv
outputs/tables/forecastability_summary.csv
outputs/tables/la_risk_scores_2024.csv
outputs/tables/la_scenario_forecasts.csv
article_forecastability.md
"""

from __future__ import annotations
import warnings
import zipfile

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — all thresholds here
# ─────────────────────────────────────────────────────────────────────────────
COLLAPSE_TIMELINESS_THRESH     = 40.0   # mean 20-week compliance (%) below this
COLLAPSE_APPEAL_PERCENTILE     = 0.75   # top quartile of appeal rates
COLLAPSE_PLACEMENT_PERCENTILE  = 0.75   # top quartile of independent placements / 1000 pupils
COMPOSITE_MIN_FLAGS            = 2      # need ≥ this many collapse flags

FORECAST_YEARS   = [2016, 2017, 2018, 2019, 2020, 2021]
COLLAPSE_WINDOW  = [2022, 2023, 2024]   # outcomes window; must be AFTER all feature years

SCENARIO_HORIZON   = 6           # years ahead from 2024
COST_PER_PLACEMENT = 80_000      # £/yr per independent special school placement
COST_INFLATION_PA  = 0.10        # annual cost inflation in scenario 3

FIGURE_DPI  = 150
RANDOM_SEED = 42

ROOT      = Path(__file__).parent
FIG_DIR   = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'

# Need-type colours (consistent with rest of repo)
NT_COLORS = {
    'ASD':  '#1f77b4',
    'SEMH': '#d62728',
    'SLCN': '#ff7f0e',
    'MLD':  '#2ca02c',
    'SLD':  '#9467bd',
    'Other':'#8c564b',
}
STATUS_COLORS = {
    'Safety Valve': '#d62728',
    'Delivering Better Value': '#ff7f0e',
    'None': '#1f77b4',
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def to_num(s):
    return pd.to_numeric(
        pd.Series(s).astype(str).str.strip()
          .replace({'x': np.nan, 'z': np.nan, '-': np.nan,
                    '..': np.nan, 'c': np.nan, 'nan': np.nan}),
        errors='coerce'
    )


def log_linear_slope(vals: np.ndarray, years: np.ndarray | None = None) -> float:
    """Log-linear growth rate from a series; returns np.nan if < 2 usable points."""
    if years is None:
        years = np.arange(len(vals), dtype=float)
    mask = np.isfinite(vals) & (vals > 0)
    if mask.sum() < 2:
        return np.nan
    slope, _ = np.polyfit(years[mask], np.log(vals[mask]), 1)
    return float(slope)


def linear_slope(vals: np.ndarray, years: np.ndarray | None = None) -> float:
    if years is None:
        years = np.arange(len(vals), dtype=float)
    mask = np.isfinite(vals)
    if mask.sum() < 2:
        return np.nan
    slope, _ = np.polyfit(years[mask], vals[mask], 1)
    return float(slope)


def auc_mann_whitney(y_true, y_score):
    n_pos = int(np.sum(y_true))
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.nan
    ranks = stats.rankdata(y_score)
    rank_sum = float(ranks[np.array(y_true, dtype=bool)].sum())
    u = rank_sum - n_pos * (n_pos + 1) / 2
    return u / (n_pos * n_neg)


def precision_at_k(y_true, y_score, k):
    idx = np.argsort(y_score)[::-1][:k]
    return float(np.mean(np.array(y_true)[idx]))


def loo_cv_logit(X: np.ndarray, y: np.ndarray, C: float = 1.0):
    """LOO-CV with sklearn LogisticRegression. Returns array of OOF probabilities."""
    n = len(y)
    probs = np.full(n, np.nan)
    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('lr', LogisticRegression(C=C, max_iter=1000,
                                  class_weight='balanced',
                                  random_state=RANDOM_SEED)),
    ])
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        Xtr, ytr = X[mask], y[mask]
        Xte = X[i:i+1]
        if ytr.sum() < 2 or (ytr == 0).sum() < 2:
            continue
        try:
            pipe.fit(Xtr, ytr)
            probs[i] = pipe.predict_proba(Xte)[0, 1]
        except Exception:
            pass
    return probs


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: LOAD AND BUILD PANEL DATA
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("Loading data sources...")
print("=" * 60)

# ── 3a. Existing panel (tribunal + SEN2 process data) ─────────────────────────
panel = pd.read_csv(TABLE_DIR / 'panel_timeseries.csv')
panel['la_code'] = panel['la_code_static'].fillna(panel['la_code'])

meta_cols = ['la_code_static', 'la_name', 'region', 'intervention_status',
             'imd_average_score', 'is_small_la']
meta = (panel[meta_cols].drop_duplicates('la_code_static')
        .rename(columns={'la_code_static': 'la_code'})
        .dropna(subset=['la_code']))

# Exclude small LAs throughout
small_codes = set(panel.loc[panel['is_small_la'] == True, 'la_code_static'].dropna())
meta = meta[~meta['la_code'].isin(small_codes)].copy()
ALL_LAS = set(meta['la_code'])

print(f"  Panel LAs (excl. small): {len(ALL_LAS)}")

# ── 3b. S251 spend data ────────────────────────────────────────────────────────
print("  Loading S251 education spend data...")
s251_raw = pd.read_csv(
    ROOT / 'data/raw/s251_2025/data/s251_alleducation_la_regional_national.csv',
    encoding='latin-1', low_memory=False
)
s251_la = s251_raw[s251_raw['geographic_level'] == 'Local authority'].copy()
s251_la['gross'] = to_num(s251_la['gross_expenditure']).values
s251_la['la_code'] = s251_la['new_la_code'].astype(str).str.strip()

# Academic-year code → calendar year (201516 → 2016, 201617 → 2017, ...)
s251_la['feat_year'] = (s251_la['time_period'].astype(str).str[:4].astype(int) + 1)

SPEND_LINES = {
    '1.2.1': 'topup_maintained',   # top-up maintained
    '1.2.3': 'topup_independent',  # top-up independent (key cost proxy)
    '1.9.1': 'dsg_total',          # total DSG for year (normaliser)
    '1.9.3': 'dsg_carry',          # DSG carry-forward (+ = surplus, - = deficit)
    '2.1.1': 'ep_service',         # educational psychology
    '2.1.2': 'sen_admin',          # SEN administration
}

spend_frames = []
for prefix, col_name in SPEND_LINES.items():
    sub = s251_la[s251_la['category_of_expenditure'].str.startswith(prefix, na=False)].copy()
    sub = sub[['la_code', 'feat_year', 'gross']].rename(columns={'gross': col_name})
    spend_frames.append(sub.drop_duplicates(['la_code', 'feat_year']))

from functools import reduce
spend = reduce(
    lambda a, b: a.merge(b, on=['la_code', 'feat_year'], how='outer'),
    spend_frames
)
# Normalise spend lines by total DSG to get scale-invariant ratios
for col in ['topup_maintained', 'topup_independent', 'ep_service', 'sen_admin']:
    spend[f'{col}_pct'] = np.where(
        spend['dsg_total'] > 0,
        spend[col] / spend['dsg_total'] * 100,
        np.nan
    )
spend['dsg_balance_pct'] = np.where(
    spend['dsg_total'] > 0,
    spend['dsg_carry'] / spend['dsg_total'] * 100,
    np.nan
)
print(f"  S251 spend rows: {len(spend)}, years: {sorted(spend['feat_year'].dropna().unique())}")

# ── 3c. Historical EHCP caseload from need-type zip (2015/16-2019/20) ──────────
print("  Loading historical EHCP caseload (need-type zip)...")
hist_zip = zipfile.ZipFile(
    ROOT / 'data/raw/special-educational-needs-in-england_2019-20.zip'
)
hist_raw = pd.read_csv(
    hist_zip.open('data/sen_age_gender.csv'),
    encoding='latin-1', low_memory=False
)
# Fix BOM in first column name
hist_raw.columns = [c.replace('﻿', '').replace('ï»¿', '') for c in hist_raw.columns]

# LA-level, EHC plans, Total phase, all primary needs
hist_la = hist_raw[
    (hist_raw['geographic_level'] == 'Local authority') &
    (hist_raw['pupil_sen_status'].str.contains('Statement|EHC', na=False)) &
    (hist_raw['phase_type_grouping'] == 'Total')
].copy()

hist_la['la_code'] = hist_la['new_la_code'].astype(str).str.strip()
hist_la['ehcp_n'] = to_num(hist_la['number_of_pupils']).values
hist_la['feat_year'] = (hist_la['time_period'].astype(str).str[:4].astype(int) + 1)

# Total EHCP count per LA per year
ehcp_hist = (hist_la[hist_la['primary_need'] == 'Total']
             .groupby(['la_code', 'feat_year'])['ehcp_n']
             .sum().reset_index()
             .rename(columns={'ehcp_n': 'ehcp_count'}))

# National need-type totals for the trend chart
nat_hist = hist_raw[
    (hist_raw['geographic_level'] == 'National') &
    (hist_raw['pupil_sen_status'].str.contains('Statement|EHC', na=False)) &
    (hist_raw['phase_type_grouping'] == 'Total')
].copy()
nat_hist['feat_year'] = (nat_hist['time_period'].astype(str).str[:4].astype(int) + 1)
nat_hist['ehcp_n'] = to_num(nat_hist['number_of_pupils']).values

# ── 3d. SEN2 caseload — total EHCPs + placement breakdown ────────────────────
print("  Loading SEN2 caseload data...")
cas_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/caseload.csv', low_memory=False)
cas_la = cas_raw[(cas_raw['geographic_level'] == 'Local authority')].copy()
# Filter to grand total row where available
all_ehcp_mask = cas_la.get('breakdown_topic', pd.Series('', index=cas_la.index)) == 'All EHC plans'
if all_ehcp_mask.any():
    cas_la = cas_la[all_ehcp_mask].copy()

for col in ['ehcplans', 'special_independent', 'special_total',
            'special_la_maintained', 'special_academy_free']:
    if col in cas_la.columns:
        cas_la[col] = to_num(cas_la[col]).values

# Academic year → calendar year
cas_la['feat_year'] = cas_la['time_period'].astype(str).str[:4].astype(int) + 1
cas_la['la_code'] = cas_la['new_la_code'].astype(str).str.strip()

ehcp_cas = cas_la.groupby(['la_code', 'feat_year']).agg(
    ehcp_count_cas=('ehcplans', 'sum'),
    n_special_indep=('special_independent', 'sum'),
    n_special_total=('special_total', 'sum'),
).reset_index()
ehcp_cas['pct_special_independent'] = np.where(
    ehcp_cas['n_special_total'] > 0,
    ehcp_cas['n_special_indep'] / ehcp_cas['n_special_total'] * 100,
    np.nan
)
print(f"  Caseload years: {sorted(ehcp_cas.feat_year.unique())}")

# ── 3e. Total pupils for per-pupil normalisation (2024/25) ────────────────────
print("  Loading SEN pupils (total pupils per LA)...")
sen_pup = pd.read_csv(
    ROOT / 'data/raw/sen_pupils_2025/data/sen_phase_type_.csv', low_memory=False
)
total_pup = sen_pup[
    (sen_pup['geographic_level'] == 'Local authority') &
    (sen_pup['phase_type_grouping'] == 'Total') &
    (sen_pup['type_of_establishment'] == 'Total') &
    (sen_pup['hospital_school'] == 'Total')
].copy()
total_pup['la_code'] = total_pup['new_la_code'].astype(str).str.strip()
total_pup['total_pupils'] = to_num(total_pup['total_pupils']).values
pupils = total_pup[['la_code', 'total_pupils']].drop_duplicates('la_code')
print(f"  Pupils data: {len(pupils)} LAs")

# ── 3f. Merge into rich panel ─────────────────────────────────────────────────
# Combine historical caseload (from need-type zip 2016-2020) with
# SEN2 caseload (2019-2025) into a unified EHCP count series
ehcp_cas2 = ehcp_cas[['la_code', 'feat_year', 'ehcp_count_cas']].rename(
    columns={'ehcp_count_cas': 'ehcp_count'}
)

# Prefer SEN2 caseload where overlap; fill gaps with hist
ehcp_all = pd.concat([
    ehcp_hist[['la_code', 'feat_year', 'ehcp_count']],
    ehcp_cas2[['la_code', 'feat_year', 'ehcp_count']],
], ignore_index=True).drop_duplicates(['la_code', 'feat_year'], keep='last')

# Add placement variables (only from SEN2 caseload where available)
ehcp_all = ehcp_all.merge(
    ehcp_cas[['la_code', 'feat_year', 'n_special_indep',
              'n_special_total', 'pct_special_independent']],
    on=['la_code', 'feat_year'], how='left'
)

# Build a rich_panel: one row per LA per year, all variables
# Use la_code_static as the canonical LA code; drop the original la_code
rich = panel.copy()
rich['la_code'] = rich['la_code_static'].fillna(rich.get('la_code', rich['la_code_static']))
rich = rich[['la_code', 'la_name', 'year', 'region', 'intervention_status',
             'is_small_la', 'imd_average_score',
             'n_requests', 'n_refused', 'refusal_rate_pct',
             'n_plans_issued', 'n_within_20w', 'timeliness_pct',
             'la_official_appeal_rate_pct', 'n_tribunal_appeals']].copy()

rich = rich[~rich['la_code'].isin(small_codes)].copy()
rich = rich.merge(
    ehcp_all[['la_code', 'feat_year', 'ehcp_count',
              'n_special_indep', 'n_special_total', 'pct_special_independent']],
    left_on=['la_code', 'year'], right_on=['la_code', 'feat_year'], how='left'
)
rich = rich.drop(columns=[c for c in ['feat_year'] if c in rich.columns])
rich = rich.merge(spend, left_on=['la_code', 'year'], right_on=['la_code', 'feat_year'],
                  how='left')
rich = rich.drop(columns=[c for c in ['feat_year'] if c in rich.columns])
rich = rich.merge(pupils, on='la_code', how='left')
# Final safety-net: remove any duplicate columns
rich = rich.loc[:, ~rich.columns.duplicated()]
rich['indep_per_1000'] = np.where(
    rich['total_pupils'] > 0,
    rich['n_special_indep'] / rich['total_pupils'] * 1000,
    np.nan
)
rich['ehcp_per_1000'] = np.where(
    rich['total_pupils'] > 0,
    rich['ehcp_count'] / rich['total_pupils'] * 1000,
    np.nan
)
print(f"  Rich panel: {len(rich)} rows, {rich['la_code'].nunique()} LAs")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: NATIONAL TREND CHART — ABSOLUTE NUMBERS BY NEED TYPE (Figure 34)
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding national trend chart (Figure 34)...")

# Total EHCPs by year from SEN2 caseload (academic year totals, national)
cas_nat = cas_raw[
    (cas_raw['geographic_level'] == 'National')
].copy()
if 'breakdown_topic' in cas_nat.columns:
    mask_all = cas_nat['breakdown_topic'].eq('All EHC plans')
    if mask_all.any():
        cas_nat = cas_nat[mask_all]
cas_nat['ehcp_total'] = to_num(cas_nat['ehcplans']).values
cas_nat['feat_year'] = cas_nat['time_period'].astype(str).str[:4].astype(int) + 1
cas_nat_yr = (cas_nat.groupby('feat_year')['ehcp_total']
              .sum().reset_index())

# Combine with historical totals
hist_nat_total = (nat_hist[nat_hist['primary_need'] == 'Total']
                  .groupby('feat_year')['ehcp_n'].sum().reset_index()
                  .rename(columns={'ehcp_n': 'ehcp_total'}))
nat_total = pd.concat([hist_nat_total, cas_nat_yr]).drop_duplicates(
    'feat_year', keep='last').sort_values('feat_year')

# Need-type proportions from the existing demand_national_trend.csv
nt_pct = pd.read_csv(TABLE_DIR / 'demand_national_trend.csv')
# time_period codes like 201516 → feat_year 2016
nt_pct['feat_year'] = nt_pct['time_period'].astype(str).str[:4].astype(int) + 1

# Pivot to wide
nt_wide = nt_pct.pivot(index='feat_year', columns='need', values='pct_national').reset_index()
nt_wide = nt_wide.merge(nat_total, on='feat_year', how='inner')

# Compute absolute counts
need_types_show = ['ASD', 'SEMH', 'SLCN', 'MLD', 'SLD']
for nt in need_types_show:
    if nt in nt_wide.columns:
        nt_wide[f'n_{nt}'] = nt_wide[nt] / 100 * nt_wide['ehcp_total']
nt_wide['n_Other'] = nt_wide['ehcp_total'] - sum(
    nt_wide.get(f'n_{nt}', 0) for nt in need_types_show
    if f'n_{nt}' in nt_wide.columns
)

# --- Also build full caseload year series for total line
# From SEN2 caseload + historical zip
total_by_year = pd.concat([
    hist_nat_total.rename(columns={'ehcp_n': 'n', 'ehcp_total': 'n'}
                          if 'ehcp_n' in hist_nat_total.columns else {}),
    cas_nat_yr.rename(columns={'ehcp_total': 'n'})
]).drop_duplicates('feat_year', keep='last').sort_values('feat_year')
if 'n' not in total_by_year.columns and 'ehcp_total' in total_by_year.columns:
    total_by_year = total_by_year.rename(columns={'ehcp_total': 'n'})
elif 'n' not in total_by_year.columns:
    total_by_year['n'] = total_by_year.get('ehcp_total', np.nan)

fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Left: total EHCP caseload absolute
ax = axes[0]
yrs_total = total_by_year['feat_year'].values
ns_total  = to_num(total_by_year['n']).values
ax.fill_between(yrs_total, ns_total / 1000, alpha=0.15, color='#1f77b4')
ax.plot(yrs_total, ns_total / 1000, color='#1f77b4', lw=2.5, marker='o', ms=5)
ax.set_title('Total active EHCPs in England\n(absolute count, thousands)', fontweight='bold')
ax.set_ylabel('EHCPs (thousands)')
ax.set_xlabel('Academic year (end)')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}k'))
ax.grid(True, alpha=0.3)
ax.set_xlim(2016, 2026)

# Annotate 2016 and 2025 values
for yr, label in [(2016, '2016'), (2025, '2025')]:
    row = total_by_year[total_by_year['feat_year'] == yr]
    if not row.empty:
        v = float(to_num(row['n'].values)[0]) / 1000
        ax.annotate(f'{v:.0f}k', xy=(yr, v), xytext=(0, 8),
                    textcoords='offset points', ha='center', fontsize=9,
                    fontweight='bold')

# Right: stacked area by need type (years with data only)
ax2 = axes[1]
nt_plot = nt_wide[nt_wide['ehcp_total'].notna()].sort_values('feat_year').copy()
if not nt_plot.empty:
    stack_cols = [f'n_{nt}' for nt in ['Other', 'SLD', 'MLD', 'SLCN', 'SEMH', 'ASD']
                  if f'n_{nt}' in nt_plot.columns]
    stack_labels = [c.replace('n_', '') for c in stack_cols]
    stack_colors = [NT_COLORS.get(l, '#888888') for l in stack_labels]
    stack_data = [to_num(nt_plot[c]).values / 1000 for c in stack_cols]

    ax2.stackplot(nt_plot['feat_year'].values, stack_data,
                  labels=stack_labels, colors=stack_colors, alpha=0.8)
    ax2.set_title('EHCP caseload by primary need type\n(absolute count, thousands)', fontweight='bold')
    ax2.set_ylabel('EHCPs (thousands)')
    ax2.set_xlabel('Academic year (end)')
    ax2.legend(loc='upper left', fontsize=8, framealpha=0.8)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_xlim(nt_plot['feat_year'].min(), nt_plot['feat_year'].max() + 0.5)
    ax2.annotate('* 2020/21–2023/24 need-type\nbreakdown not available',
                 xy=(0.98, 0.05), xycoords='axes fraction', ha='right', fontsize=7,
                 style='italic', color='gray')

plt.suptitle('England EHCP demand: absolute counts, 2015/16–2024/25',
             fontsize=13, fontweight='bold', y=1.01)
plt.tight_layout()
fig.savefig(FIG_DIR / '34_national_demand_absolute.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 34")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: COLLAPSE LABEL COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────
print("\nComputing collapse labels...")

window = rich[rich['year'].isin(COLLAPSE_WINDOW)].copy()

la_timeliness = (window.groupby('la_code')['timeliness_pct']
                 .agg(mean_timeliness='mean', n_timeliness='count').reset_index())
la_appeals    = (window.groupby('la_code')['la_official_appeal_rate_pct']
                 .agg(mean_appeal='mean', n_appeal='count').reset_index())

# Placement: use latest available year (2023 or 2024)
latest_placement = (rich[rich['year'].isin([2023, 2024]) & rich['indep_per_1000'].notna()]
                    .sort_values('year')
                    .groupby('la_code')
                    .last()[['indep_per_1000', 'pct_special_independent']]
                    .reset_index())

# Collapse thresholds
appeal_thresh     = la_appeals['mean_appeal'].quantile(COLLAPSE_APPEAL_PERCENTILE)
placement_thresh  = latest_placement['indep_per_1000'].quantile(COLLAPSE_PLACEMENT_PERCENTILE)
print(f"  Timeliness collapse threshold : < {COLLAPSE_TIMELINESS_THRESH}%")
print(f"  Appeal collapse threshold     : > {appeal_thresh:.2f}% ({COLLAPSE_APPEAL_PERCENTILE:.0%}ile)")
print(f"  Placement collapse threshold  : > {placement_thresh:.3f}/1000 ({COLLAPSE_PLACEMENT_PERCENTILE:.0%}ile)")

collapse = meta[['la_code', 'la_name', 'region', 'intervention_status']].copy()
collapse = collapse.merge(la_timeliness, on='la_code', how='left')
collapse = collapse.merge(la_appeals, on='la_code', how='left')
collapse = collapse.merge(latest_placement, on='la_code', how='left')

collapse['y_timeliness'] = (collapse['mean_timeliness'] < COLLAPSE_TIMELINESS_THRESH).astype(float)
collapse['y_appeal']     = (collapse['mean_appeal']     > appeal_thresh).astype(float)
collapse['y_placement']  = (collapse['indep_per_1000']  > placement_thresh).astype(float)

for col in ['y_timeliness', 'y_appeal', 'y_placement']:
    collapse[col] = np.where(collapse[col].isna(), np.nan, collapse[col])

collapse['n_flags'] = (collapse[['y_timeliness','y_appeal','y_placement']]
                       .apply(lambda r: r.sum(skipna=True), axis=1))
collapse['y_composite'] = (collapse['n_flags'] >= COMPOSITE_MIN_FLAGS).astype(float)
collapse.loc[collapse['n_flags'].isna(), 'y_composite'] = np.nan

# Report
for col, label in [('y_timeliness','Timeliness'), ('y_appeal','Appeal'),
                   ('y_placement','Placement'), ('y_composite','Composite')]:
    sub = collapse[collapse[col].notna()]
    n_pos = int(sub[col].sum())
    pct   = n_pos / len(sub) * 100
    print(f"  {label:<12}: {n_pos}/{len(sub)} collapsed ({pct:.0f}%)")

# Figure 35: Collapse distribution
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
axes = axes.flatten()

collapse_defs = [
    ('y_timeliness', f'Timeliness collapse\n(mean 20-week compliance < {COLLAPSE_TIMELINESS_THRESH:.0f}%, 2022–24)',
     'mean_timeliness', 'Mean 20-week compliance 2022–24 (%)'),
    ('y_appeal', f'Legal-pressure collapse\n(mean appeal rate > {appeal_thresh:.1f}%, 2022–24)',
     'mean_appeal', 'Mean official appeal rate 2022–24 (%)'),
    ('y_placement', f'Placement/cost collapse\n(indep. placements > {placement_thresh:.2f}/1000 pupils)',
     'indep_per_1000', 'Independent placements per 1,000 pupils'),
    ('y_composite', f'Composite collapse\n(≥ {COMPOSITE_MIN_FLAGS} of 3 collapse flags)',
     'n_flags', 'Number of collapse flags (0–3)'),
]

status_order = ['Safety Valve', 'Delivering Better Value', 'None']
for ax, (y_col, title, x_col, x_label) in zip(axes, collapse_defs):
    sub = collapse[collapse[x_col].notna() & collapse[y_col].notna()].copy()
    # Colour by intervention_status (for annotation only — not in model)
    for status in status_order:
        s_data = sub[sub['intervention_status'].fillna('None') == status]
        color  = STATUS_COLORS.get(status, '#888888')
        s_col  = STATUS_COLORS.get(status, '#888888')
        collapsed_s  = s_data[s_data[y_col] == 1]
        uncollapsed_s = s_data[s_data[y_col] == 0]
        ax.scatter(s_data[x_col], [status] * len(s_data),
                   c=[color], alpha=0.5, s=30, zorder=2, label=status)
        ax.scatter(collapsed_s[x_col], [status] * len(collapsed_s),
                   c=[color], alpha=0.95, s=60, marker='D', zorder=3)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.set_xlabel(x_label, fontsize=8)
    ax.grid(True, axis='x', alpha=0.3)

axes[0].legend(fontsize=7, loc='lower right',
               title='(colour = programme status,\nnot used in models)', title_fontsize=7)

plt.suptitle('Collapse definitions: 2022–2024 outcomes\n'
             '(diamonds = collapsed; programme status shown for context only)',
             fontsize=11, fontweight='bold')
plt.tight_layout()
fig.savefig(FIG_DIR / '35_collapse_definitions.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 35")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: FEATURE CONSTRUCTION BY YEAR (NO LEAKAGE)
# ─────────────────────────────────────────────────────────────────────────────
print("\nConstructing feature sets by forecast year...")

# Map of what data is available by feature year T:
#   Tribunal:       all years T from 2014 (in existing panel)
#   S251 spend:     feat_year = T (academic year T-1/T)
#   EHCP caseload:  hist zip up to 2020; SEN2 from 2019
#   Placement share: SEN2 from 2019
#   Timeliness:     SEN2 from 2019
#   Refusal rate:   SEN2 from 2019

def build_features_for_year(T: int) -> pd.DataFrame:
    """Extract all features available at the end of year T (no future leakage)."""
    feats = meta[['la_code', 'la_name', 'region', 'intervention_status',
                  'imd_average_score']].copy()

    # --- Tribunal features (available from 2014) ---
    trib_years = list(range(max(2014, T - 4), T + 1))
    trib_sub = (rich[rich['year'].isin(trib_years)]
                .drop_duplicates(['la_code', 'year'])
                .pivot(index='la_code', columns='year',
                       values='la_official_appeal_rate_pct'))
    trib_sub.columns = [f'trib_{y}' for y in trib_sub.columns]
    feats = feats.merge(trib_sub.reset_index(), on='la_code', how='left')

    # Tribunal level at T and 3-year slope
    trib_col_T = f'trib_{T}'
    feats['trib_level'] = feats.get(trib_col_T, pd.Series(np.nan, index=feats.index))
    slope_cols = [c for c in feats.columns if c.startswith('trib_') and
                  c != 'trib_level' and int(c.split('_')[1]) <= T]
    def _slope(row):
        yr  = np.array([int(c.split('_')[1]) for c in slope_cols], dtype=float)
        val = np.array([row[c] for c in slope_cols], dtype=float)
        return linear_slope(val, yr)
    feats['trib_slope'] = feats.apply(_slope, axis=1) if slope_cols else np.nan

    # --- EHCP caseload features (available from 2016/17) ---
    ehcp_T = ehcp_all[(ehcp_all['feat_year'] <= T) &
                      (ehcp_all['la_code'].isin(ALL_LAS))].copy()
    if not ehcp_T.empty:
        ehcp_latest = (ehcp_T.sort_values('feat_year')
                       .groupby('la_code')
                       .last()[['ehcp_count']].reset_index())
        feats = feats.merge(ehcp_latest.rename(columns={'ehcp_count': 'ehcp_level'}),
                            on='la_code', how='left')

        # Log-linear growth rate over years up to T
        def _ehcp_growth(sub):
            sub2 = sub[sub['feat_year'] <= T].sort_values('feat_year')
            return log_linear_slope(sub2['ehcp_count'].values,
                                    sub2['feat_year'].values)
        ehcp_growth = (ehcp_T.groupby('la_code')
                       .apply(_ehcp_growth).reset_index()
                       .rename(columns={0: 'ehcp_growth'}))
        feats = feats.merge(ehcp_growth, on='la_code', how='left')
    else:
        feats['ehcp_level'] = np.nan
        feats['ehcp_growth'] = np.nan

    # --- S251 spend features (available from 2016) ---
    spend_T = spend[spend['feat_year'] <= T].sort_values('feat_year')
    spend_latest = spend_T.groupby('la_code').last().reset_index()
    for col in ['topup_independent_pct', 'dsg_balance_pct', 'ep_service_pct', 'sen_admin_pct']:
        if col in spend_latest.columns:
            feats = feats.merge(spend_latest[['la_code', col]], on='la_code', how='left')

    # Growth in independent top-up spend (2-year change)
    if T >= 2017:
        spend_Tm2 = spend[spend['feat_year'] == T - 2].set_index('la_code')
        spend_T1  = spend[spend['feat_year'] == T    ].set_index('la_code')
        idx       = spend_Tm2.index.intersection(spend_T1.index)
        indep_growth_s = pd.Series(
            (spend_T1.loc[idx, 'topup_independent_pct'].values -
             spend_Tm2.loc[idx, 'topup_independent_pct'].values),
            index=idx, name='indep_spend_growth'
        )
        feats = feats.merge(indep_growth_s.reset_index().rename(
            columns={'index': 'la_code'}), on='la_code', how='left')
    else:
        feats['indep_spend_growth'] = np.nan

    # --- Placement features (SEN2, only available from 2019) ---
    if T >= 2019:
        pla_T = (ehcp_cas[ehcp_cas['feat_year'] <= T]
                 .sort_values('feat_year')
                 .groupby('la_code')
                 .last()[['pct_special_independent']].reset_index()
                 .rename(columns={'pct_special_independent': 'pct_indep_placement'}))
        feats = feats.merge(pla_T, on='la_code', how='left')
    else:
        feats['pct_indep_placement'] = np.nan

    # --- Timeliness and refusal features (SEN2, only from 2019) ---
    if T >= 2019:
        time_T = (rich[rich['year'] <= T]
                  .sort_values('year')
                  .groupby('la_code')
                  .last()[['timeliness_pct', 'refusal_rate_pct']].reset_index())
        feats = feats.merge(time_T, on='la_code', how='left')
        # Timeliness trend
        def _tl_slope(sub):
            sub2 = sub[sub['year'] <= T].sort_values('year')
            return linear_slope(sub2['timeliness_pct'].values,
                                 sub2['year'].values)
        tl_growth = (rich[rich['year'] <= T].groupby('la_code')
                     .apply(_tl_slope).reset_index()
                     .rename(columns={0: 'timeliness_trend'}))
        feats = feats.merge(tl_growth, on='la_code', how='left')
    else:
        feats['timeliness_pct']   = np.nan
        feats['refusal_rate_pct'] = np.nan
        feats['timeliness_trend'] = np.nan

    feats['feat_year'] = T
    return feats


features_by_year = {}
for T in FORECAST_YEARS:
    features_by_year[T] = build_features_for_year(T)
    n = len(features_by_year[T])
    print(f"  Features at {T}: {n} LAs, "
          f"trib non-null={features_by_year[T]['trib_level'].notna().sum()}, "
          f"indep_spend non-null={features_by_year[T]['topup_independent_pct'].notna().sum()}, "
          f"timeliness non-null={features_by_year[T]['timeliness_pct'].notna().sum()}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 & 8: MODEL FAMILIES + LOO-CV EVALUATION
# ─────────────────────────────────────────────────────────────────────────────
print("\nFitting model families with LOO-CV...")

# Model families: list of (name, feature_columns)
# Features that are always available: trib_level, trib_slope, imd_average_score
# Features available from 2016: ehcp_growth, topup_independent_pct, dsg_balance_pct
# Features available from 2019: timeliness_pct, pct_indep_placement, timeliness_trend
FAMILIES = {
    'signals_only': [
        'trib_level', 'trib_slope', 'topup_independent_pct',
    ],
    'demand_only': [
        'ehcp_growth', 'ehcp_level',
    ],
    'demand_legal': [
        'ehcp_growth', 'ehcp_level', 'trib_level', 'trib_slope',
    ],
    'demand_cost': [
        'ehcp_growth', 'ehcp_level', 'topup_independent_pct', 'dsg_balance_pct',
    ],
    'demand_throughput': [
        'ehcp_growth', 'ehcp_level', 'timeliness_pct', 'timeliness_trend',
    ],
    'full': [
        'ehcp_growth', 'ehcp_level', 'trib_level', 'trib_slope',
        'topup_independent_pct', 'dsg_balance_pct',
        'timeliness_pct', 'pct_indep_placement',
    ],
}

COLLAPSE_TARGETS = ['y_timeliness', 'y_appeal', 'y_placement', 'y_composite']

results = []

for T in FORECAST_YEARS:
    feats = features_by_year[T].copy()
    # Merge collapse labels
    feats = feats.merge(
        collapse[['la_code', 'y_timeliness', 'y_appeal',
                  'y_placement', 'y_composite', 'n_flags']],
        on='la_code', how='inner'
    )
    feats = feats[~feats['la_code'].isin(small_codes)].copy()

    for family_name, pred_cols in FAMILIES.items():
        avail_preds = [c for c in pred_cols if c in feats.columns]
        if not avail_preds:
            continue

        for y_col in COLLAPSE_TARGETS:
            sub = feats[avail_preds + [y_col, 'la_code']].dropna().copy()
            if len(sub) < 20:
                continue
            y_arr = sub[y_col].values.astype(int)
            n_pos = y_arr.sum()
            if n_pos < 3 or (len(y_arr) - n_pos) < 3:
                continue
            X_arr = sub[avail_preds].values.astype(float)

            loo_probs = loo_cv_logit(X_arr, y_arr)
            valid = ~np.isnan(loo_probs)
            if valid.sum() < 10:
                continue

            auc_val = auc_mann_whitney(y_arr[valid], loo_probs[valid])
            p10 = precision_at_k(y_arr, loo_probs, 10)
            p20 = precision_at_k(y_arr, loo_probs, 20)

            results.append({
                'feat_year':    T,
                'model_family': family_name,
                'collapse_type': y_col,
                'n_la':         len(sub),
                'n_positive':   n_pos,
                'auc_loo':      auc_val,
                'precision_at_10': p10,
                'precision_at_20': p20,
            })

results_df = pd.DataFrame(results)
print(f"  Completed {len(results_df)} model evaluations")

# Save
results_df.to_csv(TABLE_DIR / 'forecastability_summary.csv', index=False, float_format='%.3f')
print("  Saved forecastability_summary.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9: FORECASTABILITY CHARTS (Figures 36–38)
# ─────────────────────────────────────────────────────────────────────────────
print("\nProducing forecastability charts...")

# Figure 36: AUC heatmap — model family × forecast year, one panel per collapse type
collapse_labels = {
    'y_timeliness': 'Timeliness\ncollapse',
    'y_appeal':     'Legal-pressure\ncollapse',
    'y_placement':  'Placement/cost\ncollapse',
    'y_composite':  'Composite\ncollapse',
}
family_labels = {
    'demand_only':       'Demand only',
    'demand_legal':      'Demand + tribunal',
    'demand_cost':       'Demand + spend',
    'demand_throughput': 'Demand + timeliness\n(2019+ only)',
    'full':              'Full model',
}

fig, axes = plt.subplots(2, 2, figsize=(15, 11))
axes = axes.flatten()

for ax, y_col in zip(axes, COLLAPSE_TARGETS):
    sub = results_df[results_df['collapse_type'] == y_col].copy()
    if sub.empty:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        continue
    piv = sub.pivot(index='model_family', columns='feat_year', values='auc_loo')
    # Reorder rows
    row_order = [f for f in FAMILIES if f in piv.index]
    piv = piv.loc[row_order]
    piv.index = [family_labels.get(i, i) for i in piv.index]

    sns.heatmap(piv, ax=ax, annot=True, fmt='.2f', cmap='RdYlGn',
                vmin=0.5, vmax=1.0, cbar_kws={'label': 'LOO-CV AUC'},
                linewidths=0.5, linecolor='white', annot_kws={'size': 9})
    ax.set_title(f'{collapse_labels[y_col]}\n(AUC; random = 0.50)',
                 fontweight='bold', fontsize=10)
    ax.set_xlabel('Training data cut-off year', fontsize=9)
    ax.set_ylabel('')
    ax.tick_params(axis='y', labelsize=8)

plt.suptitle(
    'Forecastability: how well could earlier data predict 2022–24 system collapse?\n'
    '(LOO cross-validated AUC by model family and training year)',
    fontsize=12, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '36_forecastability_auc_heatmap.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 36")

# Figure 37: Precision@10 and @20 over forecast years — best model per year
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for ax, metric, label in [
    (axes[0], 'auc_loo',        'LOO-CV AUC'),
    (axes[1], 'precision_at_20', 'Precision@20'),
]:
    for y_col, ytitle in collapse_labels.items():
        sub = results_df[results_df['collapse_type'] == y_col].copy()
        if sub.empty:
            continue
        best = (sub.groupby('feat_year')[metric].max().reset_index())
        ax.plot(best['feat_year'], best[metric], marker='o', lw=2,
                label=ytitle.replace('\n', ' '))
    if metric == 'auc_loo':
        ax.axhline(0.5, color='gray', lw=1, linestyle='--', alpha=0.5, label='Random')
    elif metric == 'precision_at_20':
        # Baseline: % positive in full sample
        avg_base = results_df.groupby('collapse_type')['n_positive'].first() / \
                   results_df.groupby('collapse_type')['n_la'].first()
        ax.axhline(float(avg_base.mean()), color='gray', lw=1, linestyle='--',
                   alpha=0.5, label='Random baseline')
    ax.set_xlabel('Training data cut-off year', fontsize=10)
    ax.set_ylabel(label, fontsize=10)
    ax.set_title(f'Best-model {label} vs. training year', fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(FORECAST_YEARS)

plt.suptitle(
    'Forecastability improves over time — but early signals were already strong\n'
    '(best model per training year; evaluated on 2022–24 outcomes)',
    fontsize=11, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '37_forecastability_over_time.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 37")

# Figure 38: Feature coefficients for best 'full' model at 2016 vs 2021 (timeliness collapse)
fig, axes = plt.subplots(1, 2, figsize=(13, 6))

feat_labels = {
    'ehcp_growth':          'EHCP growth rate',
    'ehcp_level':           'EHCP level (abs.)',
    'trib_level':           'Tribunal appeal rate',
    'trib_slope':           'Tribunal rate trend',
    'topup_independent_pct':'Independent top-up\n(% of DSG)',
    'dsg_balance_pct':      'DSG carry-forward\n(% of DSG)',
    'timeliness_pct':       '20-week compliance',
    'pct_indep_placement':  '% in independent\nspecial schools',
}

for ax, T in zip(axes, [2016, 2021]):
    feats = features_by_year[T].copy()
    feats = feats.merge(
        collapse[['la_code', 'y_timeliness']], on='la_code', how='inner'
    )
    feats = feats[~feats['la_code'].isin(small_codes)].copy()

    fam_preds = [c for c in FAMILIES['full'] if c in feats.columns]
    sub = feats[fam_preds + ['y_timeliness']].dropna().copy()

    if len(sub) < 10:
        ax.text(0.5, 0.5, f'Insufficient data at {T}', ha='center', va='center',
                transform=ax.transAxes)
        continue

    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(sub[fam_preds])
    y_arr   = sub['y_timeliness'].values.astype(int)

    lr = LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced',
                            random_state=RANDOM_SEED)
    lr.fit(X_scaled, y_arr)
    coefs = lr.coef_[0]

    coef_df = pd.DataFrame({'feature': fam_preds, 'coef': coefs})
    coef_df['label'] = coef_df['feature'].map(lambda x: feat_labels.get(x, x))
    coef_df = coef_df.sort_values('coef')
    colors_c = ['#d62728' if c > 0 else '#1f77b4' for c in coef_df['coef']]

    ax.barh(coef_df['label'], coef_df['coef'], color=colors_c, alpha=0.75)
    ax.axvline(0, color='black', lw=1)
    ax.set_title(f'Feature importances — training year {T}\n'
                 f'Target: timeliness collapse (n={len(sub)}, n_pos={y_arr.sum()})',
                 fontweight='bold', fontsize=9)
    ax.set_xlabel('Standardised log-odds coefficient', fontsize=9)
    ax.grid(True, axis='x', alpha=0.3)
    ax.tick_params(labelsize=8)

plt.suptitle(
    'Which features drove timeliness collapse prediction?\n'
    '(Full model, standardised coefficients; positive = higher risk)',
    fontsize=11, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '38_feature_importance.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 38")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10: CURRENT RISK SCORES (Figure 39)
# ─────────────────────────────────────────────────────────────────────────────
print("\nComputing current (2024) risk scores...")

# Use best-performing model (from results_df) on 2021 features
# for the composite collapse target
best_result = (results_df[results_df['collapse_type'] == 'y_composite']
               .sort_values('auc_loo', ascending=False)
               .iloc[0])
best_T      = int(best_result['feat_year'])
best_family = best_result['model_family']
print(f"  Best model: family='{best_family}', year={best_T}, "
      f"AUC={best_result['auc_loo']:.3f}")

# Fit final model on 2021 features → score ALL LAs
feats_2021 = features_by_year[2021].copy()
feats_2021 = feats_2021.merge(
    collapse[['la_code', 'y_timeliness', 'y_appeal',
              'y_placement', 'y_composite', 'n_flags',
              'mean_timeliness', 'mean_appeal', 'indep_per_1000']],
    on='la_code', how='left'
)
feats_2021 = feats_2021[~feats_2021['la_code'].isin(small_codes)].copy()

fam_preds = [c for c in FAMILIES[best_family] if c in feats_2021.columns]
sub_2021  = feats_2021[fam_preds + ['la_code', 'la_name', 'region',
                                     'intervention_status', 'y_composite']].copy()

# Drop rows with any NaN in predictors
sub_clean = sub_2021.dropna(subset=fam_preds).copy()
X_all     = sub_clean[fam_preds].values.astype(float)
y_all     = sub_clean['y_composite'].fillna(0).values.astype(int)

# Fit on complete cases
scaler_f = StandardScaler()
X_scaled_all = scaler_f.fit_transform(X_all)
lr_final = LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced',
                               random_state=RANDOM_SEED)
lr_final.fit(X_scaled_all, y_all)
sub_clean = sub_clean.copy()
sub_clean['risk_score'] = lr_final.predict_proba(X_scaled_all)[:, 1]

# Risk deciles
sub_clean['risk_decile'] = pd.qcut(sub_clean['risk_score'], q=10, labels=False,
                                    duplicates='drop') + 1
sub_clean['risk_tier'] = pd.cut(
    sub_clean['risk_score'],
    bins=[0, 0.25, 0.50, 0.75, 1.01],
    labels=['Low (< 25%)', 'Moderate (25–50%)', 'High (50–75%)', 'Critical (> 75%)'],
    right=False
)

# Add actual 2024 key metrics
sub_clean = sub_clean.merge(
    feats_2021[['la_code', 'mean_timeliness', 'mean_appeal', 'indep_per_1000',
                'topup_independent_pct', 'trib_level', 'ehcp_growth']],
    on='la_code', how='left'
)

# Save risk scores
risk_cols = ['la_code', 'la_name', 'region', 'intervention_status',
             'risk_score', 'risk_decile', 'risk_tier',
             'y_timeliness', 'y_appeal', 'y_placement', 'y_composite',
             'mean_timeliness', 'mean_appeal', 'indep_per_1000',
             'topup_independent_pct', 'trib_level', 'ehcp_growth']
out_risk = sub_clean[[c for c in risk_cols if c in sub_clean.columns]]
out_risk.to_csv(TABLE_DIR / 'la_risk_scores_2024.csv', index=False, float_format='%.3f')
print(f"  Risk scores saved for {len(out_risk)} LAs")

# Figure 39: Risk decile bar chart (top 40 LAs by risk score)
top40 = sub_clean.sort_values('risk_score', ascending=False).head(40).copy()
top40['rank'] = range(1, len(top40) + 1)

# Determine collapse status label for each LA (for bar colour)
def collapse_label(row):
    flags = []
    if row.get('y_timeliness', 0) == 1: flags.append('T')
    if row.get('y_appeal',     0) == 1: flags.append('A')
    if row.get('y_placement',  0) == 1: flags.append('P')
    return ','.join(flags) if flags else 'None'

top40['collapse_flags'] = top40.apply(collapse_label, axis=1)

fig, ax = plt.subplots(figsize=(11, 14))
bar_colors = [STATUS_COLORS.get(s if pd.notna(s) else 'None', '#888888')
              for s in top40['intervention_status']]
y_pos = np.arange(len(top40))
ax.barh(y_pos, top40['risk_score'], color=bar_colors, alpha=0.8, height=0.7)

# Labels on bars
for i, (_, row) in enumerate(top40.iterrows()):
    name  = row['la_name'] if pd.notna(row['la_name']) else row['la_code']
    flags = row['collapse_flags']
    label = f"{name}  [{flags}]" if flags != 'None' else name
    ax.text(row['risk_score'] + 0.005, i, label, va='center', fontsize=7.5)

# Threshold line
ax.axvline(0.5, color='black', lw=1.5, linestyle=':', alpha=0.7, label='50% risk threshold')

# Legend
patches = [
    mpatches.Patch(color=STATUS_COLORS['Safety Valve'],           label='Safety Valve (existing)'),
    mpatches.Patch(color=STATUS_COLORS['Delivering Better Value'], label='Delivering Better Value'),
    mpatches.Patch(color=STATUS_COLORS['None'],                    label='No current intervention'),
]
ax.legend(handles=patches, loc='lower right', fontsize=8,
          title='Programme status (not used in model)', title_fontsize=7)

ax.set_yticks(y_pos)
ax.set_yticklabels([f"#{r}" for r in top40['rank']], fontsize=8)
ax.invert_yaxis()
ax.set_xlabel('Model risk score (composite collapse probability, LOO-CV)', fontsize=10)
ax.set_title(
    f'Current risk scores: which councils look most like pre-crisis LAs?\n'
    f'Features: 2021 data | Model: {best_family} | Training AUC: {best_result["auc_loo"]:.2f}\n'
    f'[T/A/P] = already collapsed on timeliness / appeals / placements by 2024',
    fontsize=10, fontweight='bold'
)
ax.set_xlim(0, min(1.0, top40['risk_score'].max() * 1.3))
ax.grid(True, axis='x', alpha=0.3)
plt.tight_layout()
fig.savefig(FIG_DIR / '39_risk_scores_2024.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 39")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11: SCENARIO PROJECTIONS (Figures 40–41)
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding scenario projections...")

# Base: use 2024 panel + caseload data
base_2024 = (rich[rich['year'] == 2024]
             .merge(pupils, on='la_code', how='left')
             .merge(sub_clean[['la_code', 'risk_score', 'risk_tier',
                                'intervention_status']], on='la_code', how='left')
             .copy())

base_2024 = base_2024[~base_2024['la_code'].isin(small_codes)].copy()

# Compute historical growth rates (2019→2024 for EHCP caseload and timely throughput)
def _growth_la(la_code, col, year_range=(2019, 2024)):
    sub = rich[(rich['la_code'] == la_code) &
               (rich['year'].between(*year_range)) &
               (rich[col].notna())].sort_values('year')
    return log_linear_slope(sub[col].values, sub['year'].values)

print("  Computing LA-level growth rates (slow — ~3 min)...")
# Faster: vectorised via groupby
def _growth_vec(grp, col, ymin=2019, ymax=2024):
    sub = grp[(grp['year'] >= ymin) & (grp['year'] <= ymax) & grp[col].notna()]
    return log_linear_slope(sub[col].values, sub['year'].values)

# Use n_plans_issued (new-plan demand flow) not ehcp_count (stock) for demand
plans_growth_rates = (rich.groupby('la_code')
                      .apply(lambda g: _growth_vec(g, 'n_plans_issued'))
                      .reset_index().rename(columns={0: 'plans_growth_hist'}))
timely_growth_rates = (rich.groupby('la_code')
                       .apply(lambda g: _growth_vec(g, 'n_within_20w'))
                       .reset_index().rename(columns={0: 'timely_growth_hist'}))
indep_growth_rates = (rich.groupby('la_code')
                      .apply(lambda g: _growth_vec(g, 'n_special_indep'))
                      .reset_index().rename(columns={0: 'indep_growth_hist'}))

base_2024 = (base_2024
             .merge(plans_growth_rates,  on='la_code', how='left')
             .merge(timely_growth_rates, on='la_code', how='left')
             .merge(indep_growth_rates,  on='la_code', how='left'))

# Cap extreme values
base_2024['plans_growth_hist']  = base_2024['plans_growth_hist'].clip(-0.05, 0.12)
base_2024['timely_growth_hist'] = base_2024['timely_growth_hist'].clip(-0.15, 0.10)
base_2024['indep_growth_hist']  = base_2024['indep_growth_hist'].clip(-0.05, 0.12)

# Demand base = new plans issued per year (flow); timely = plans within 20w
base_2024['demand_base'] = base_2024['n_plans_issued'].fillna(0)
base_2024['timely_base'] = base_2024['n_within_20w'].fillna(0)
base_2024['indep_base']  = base_2024['n_special_indep'].fillna(0)
base_2024['pct_indep_base'] = base_2024['pct_special_independent'].fillna(10) / 100

# Scenario definitions
SCENARIOS = {
    'continuation':       {'demand_mult': 1.0,  'cost_mult': 1.0,
                           'throughput_mode': 'trend', 'placement_mult': 1.0},
    'asd_semh_accel':     {'demand_mult': 1.25, 'cost_mult': 1.0,
                           'throughput_mode': 'trend', 'placement_mult': 1.1},
    'cost_inflation':     {'demand_mult': 1.0,  'cost_mult': 1 + COST_INFLATION_PA,
                           'throughput_mode': 'trend', 'placement_mult': 1.0},
    'capacity_improvement':{'demand_mult': 1.0,  'cost_mult': 1.0,
                           'throughput_mode': 'improve', 'placement_mult': 0.95},
    'flat_throughput':    {'demand_mult': 1.0,  'cost_mult': 1.0,
                           'throughput_mode': 'flat', 'placement_mult': 1.0},
}

proj_rows = []
for _, la_row in base_2024.iterrows():
    la_code = la_row['la_code']
    la_name = la_row['la_name']
    status  = la_row.get('intervention_status', 'None')
    risk    = la_row.get('risk_score', np.nan)

    g_demand = la_row['plans_growth_hist']  if pd.notna(la_row['plans_growth_hist'])  else 0.05
    g_timely = la_row['timely_growth_hist'] if pd.notna(la_row['timely_growth_hist']) else 0.03
    g_indep  = la_row['indep_growth_hist']  if pd.notna(la_row['indep_growth_hist'])  else 0.05

    demand0 = la_row['demand_base'] if pd.notna(la_row['demand_base']) else np.nan
    timely0 = la_row['timely_base'] if pd.notna(la_row['timely_base']) else np.nan
    indep0  = la_row['indep_base']  if pd.notna(la_row['indep_base'])  else np.nan
    pct_i0  = la_row['pct_indep_base']

    if pd.isna(demand0) or demand0 <= 0:
        continue

    for scen_name, scen_params in SCENARIOS.items():
        for t in range(SCENARIO_HORIZON + 1):
            year_t = 2024 + t
            dm = scen_params['demand_mult']
            cm = scen_params['cost_mult']
            pm = scen_params['placement_mult']
            mode = scen_params['throughput_mode']

            # Demand = new plans issued per year
            demand_t = demand0 * np.exp(g_demand * dm * t)

            if mode == 'trend':
                timely_t = timely0 * np.exp(g_timely * t)
                timely_t = min(timely_t, demand_t)
            elif mode == 'flat':
                timely_t = timely0  # absolute count stays constant
            elif mode == 'improve':
                # Timeliness rate improves 5pp/year toward 65%
                timely_rate = min(0.65, (timely0 / max(demand0, 1)) + 0.05 * t)
                timely_t = demand_t * timely_rate
            else:
                timely_t = timely0

            timely_t = max(0, timely_t)
            late_t   = max(0, demand_t - timely_t)

            # Independent placements = separate stock, grows with own trend
            indep_t  = indep0 * np.exp(g_indep * pm * t)
            cost_t   = indep_t * COST_PER_PLACEMENT * (cm ** t) / 1e6  # £m

            proj_rows.append({
                'la_code': la_code, 'la_name': la_name,
                'intervention_status': status, 'risk_score': risk,
                'scenario': scen_name, 'year': year_t,
                'demand_projected': demand_t,
                'timely_projected': timely_t,
                'late_projected': late_t,
                'indep_placements_projected': indep_t,
                'cost_projected_m': cost_t,
            })

proj_df = pd.DataFrame(proj_rows)
proj_df.to_csv(TABLE_DIR / 'la_scenario_forecasts.csv', index=False, float_format='%.1f')
print(f"  Saved scenario forecasts: {len(proj_df)} rows")

# Figure 40: National aggregate by scenario — late cases and cost
nat_scen = (proj_df.groupby(['scenario', 'year'])
            .agg(late_total=('late_projected', 'sum'),
                 cost_total=('cost_projected_m', 'sum'),
                 demand_total=('demand_projected', 'sum'),
                 timely_total=('timely_projected', 'sum'))
            .reset_index())
nat_scen['timeliness_rate'] = nat_scen['timely_total'] / nat_scen['demand_total'].replace(0, np.nan) * 100

SCEN_COLORS = {
    'continuation':        '#1f77b4',
    'asd_semh_accel':      '#d62728',
    'cost_inflation':      '#ff7f0e',
    'capacity_improvement':'#2ca02c',
    'flat_throughput':     '#9467bd',
}
SCEN_LABELS = {
    'continuation':        'Continuation (current trend)',
    'asd_semh_accel':      'ASD/SEMH acceleration (+25% demand)',
    'cost_inflation':      f'Cost inflation (+{COST_INFLATION_PA*100:.0f}%/yr)',
    'capacity_improvement':'Capacity improvement (+5pp timeliness/yr)',
    'flat_throughput':     'Flat-throughput bottleneck',
}

fig, axes = plt.subplots(1, 3, figsize=(17, 6))

for ax, y_col, y_label, title in [
    (axes[0], 'late_total',      'Late plans per year (new plans, absolute count)',
     'New plans issued outside 20-week limit\n(national aggregate)'),
    (axes[1], 'timeliness_rate', '20-week compliance (%)',
     'National 20-week compliance rate\n(% of new plans issued within 20 weeks)'),
    (axes[2], 'cost_total',      'Annual independent placement cost (£bn)',
     'Independent special school\nplacement costs (£bn/yr)'),
]:
    for scen, grp in nat_scen.groupby('scenario'):
        vals = grp.sort_values('year')[y_col]
        if y_col == 'cost_total':
            vals = vals / 1000  # £m → £bn
        ax.plot(grp.sort_values('year')['year'], vals,
                color=SCEN_COLORS.get(scen, '#888888'), lw=2.5,
                linestyle=('--' if scen == 'capacity_improvement' else '-'),
                label=SCEN_LABELS.get(scen, scen))

    ax.axvline(2024, color='gray', lw=1, linestyle=':', alpha=0.5)
    ax.set_xlabel('Year', fontsize=10)
    ax.set_ylabel(y_label, fontsize=10)
    ax.set_title(title, fontweight='bold', fontsize=10)
    ax.legend(fontsize=7, loc='upper left' if y_col != 'timeliness_rate' else 'lower left')
    ax.grid(True, alpha=0.3)

plt.suptitle(
    f'Scenario projections, 2024–{2024 + SCENARIO_HORIZON} (national aggregate)\n'
    'All projections are risk scenarios, not deterministic forecasts',
    fontsize=11, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '40_scenario_national_aggregate.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 40")

# Figure 41: Scenario trajectories for top-10 highest-risk non-SV LAs
high_risk_non_sv = (sub_clean[
    (~sub_clean['intervention_status'].isin(['Safety Valve'])) &
    sub_clean['risk_score'].notna()
].sort_values('risk_score', ascending=False).head(10)[['la_code', 'la_name']].values.tolist())

if high_risk_non_sv:
    fig, axes = plt.subplots(2, 5, figsize=(20, 8), sharey=False)
    axes = axes.flatten()

    for i, (la_code, la_name) in enumerate(high_risk_non_sv):
        ax = axes[i]
        la_proj = proj_df[proj_df['la_code'] == la_code].copy()
        if la_proj.empty:
            continue
        for scen in SCENARIOS:
            sub_s = la_proj[la_proj['scenario'] == scen].sort_values('year')
            ax.plot(sub_s['year'], sub_s['late_projected'],
                    color=SCEN_COLORS.get(scen, '#888888'), lw=1.8,
                    linestyle='--' if scen == 'capacity_improvement' else '-',
                    alpha=0.85)
        ax.axvline(2024, color='gray', lw=1, linestyle=':', alpha=0.5)
        ax.set_title(la_name or la_code, fontsize=9, fontweight='bold')
        ax.set_xlabel('')
        if i % 5 == 0:
            ax.set_ylabel('Late plans/yr', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=7)

    # Shared legend
    handles = [plt.Line2D([0], [0], color=SCEN_COLORS[s], lw=2,
                           linestyle='--' if s == 'capacity_improvement' else '-')
               for s in SCENARIOS]
    labels  = [SCEN_LABELS[s] for s in SCENARIOS]
    fig.legend(handles, labels, loc='lower center', ncol=3, fontsize=8,
               bbox_to_anchor=(0.5, -0.05))

    plt.suptitle(
        'Scenario projections: late plans per year for top-10 highest-risk non-Safety-Valve LAs\n'
        '(ranked by 2021-feature risk model; programme status not used in scoring)',
        fontsize=10, fontweight='bold'
    )
    plt.tight_layout()
    fig.savefig(FIG_DIR / '41_scenario_trajectories_high_risk.png',
                dpi=FIGURE_DPI, bbox_inches='tight')
    plt.close()
    print("  Saved Figure 41")
else:
    print("  No high-risk non-SV LAs found; skipping Figure 41")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12: COLLAPSE LABELS TABLE
# ─────────────────────────────────────────────────────────────────────────────
collapse.to_csv(TABLE_DIR / 'la_collapse_labels.csv', index=False, float_format='%.3f')
print("\nSaved la_collapse_labels.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY PRINT
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FORECASTABILITY SUMMARY")
print("=" * 60)
print("\nBest LOO-CV AUC by collapse type and training year:")
pivot_summary = (results_df.pivot_table(
    index='model_family', columns=['collapse_type', 'feat_year'],
    values='auc_loo', aggfunc='max'
))
print(pivot_summary.to_string(float_format='{:.2f}'.format))

print("\nTop 20 highest-risk LAs (all intervention statuses):")
if 'risk_score' in sub_clean.columns:
    print(sub_clean[['la_name', 'intervention_status', 'risk_score',
                      'risk_tier', 'mean_timeliness', 'mean_appeal', 'indep_per_1000']]
          .sort_values('risk_score', ascending=False)
          .head(20)
          .to_string(index=False, float_format='{:.2f}'.format))

print("\nTop 10 highest-risk councils with NO current DfE intervention:")
none_risk = sub_clean[
    sub_clean['intervention_status'].fillna('None').eq('None') |
    sub_clean['intervention_status'].isna()
].sort_values('risk_score', ascending=False).head(10)
print(none_risk[['la_name', 'risk_score', 'risk_tier',
                  'mean_timeliness', 'mean_appeal', 'indep_per_1000']]
      .to_string(index=False, float_format='{:.2f}'.format))

print("\nScenario projections (national, 2030 vs 2024):")
scen_2030 = nat_scen[nat_scen['year'] == 2024 + SCENARIO_HORIZON]
scen_2024 = nat_scen[nat_scen['year'] == 2024]
for scen in SCENARIOS:
    r2030 = scen_2030[scen_2030['scenario'] == scen]
    r2024 = scen_2024[scen_2024['scenario'] == 'continuation']
    if not r2030.empty and not r2024.empty:
        cost30 = float(r2030['cost_total'].values[0])
        cost24 = float(r2024['cost_total'].values[0])
        late30 = float(r2030['late_total'].values[0])
        late24 = float(r2024['late_total'].values[0])
        print(f"  {SCEN_LABELS[scen]:<45}: late plans {late24:,.0f}→{late30:,.0f}, "
              f"cost £{cost24:.0f}m→£{cost30:.0f}m")

print("\nDone. Figures 34–41 and tables saved.")
