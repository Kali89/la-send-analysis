#!/usr/bin/env python3
"""
forecastability_analysis.py

"Was England's SEND collapse foreseeable — and which councils are next?"

Tests whether data available at each year from 2016 to 2021 could predict
2022-2024 system collapse.  Collapse is defined from observable outcomes only;
Safety Valve / DBV status is NOT used as a predictor or target.

Now includes eight model families (A–H) to directly test whether absolute
growth in ASD, SEMH, SLCN, and MLD need-type counts could have predicted
collapse — separately from system-failure signals (tribunal rates, independent
placement spend).

Outputs
-------
outputs/figures/34–43       PNG charts
outputs/tables/la_collapse_labels.csv
outputs/tables/forecastability_summary.csv
outputs/tables/la_risk_scores_2024.csv
outputs/tables/la_scenario_forecasts.csv
outputs/tables/forecastability_verdict.csv
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
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
COLLAPSE_TIMELINESS_THRESH     = 40.0   # mean 20-week compliance (%) below this
COLLAPSE_APPEAL_PERCENTILE     = 0.75   # top quartile of appeal rates
COLLAPSE_PLACEMENT_PERCENTILE  = 0.75   # top quartile of indep. placements / 1000 pupils
COMPOSITE_MIN_FLAGS            = 2      # need ≥ this many collapse flags

FORECAST_YEARS   = [2016, 2017, 2018, 2019, 2020, 2021]
COLLAPSE_WINDOW  = [2022, 2023, 2024]

SCENARIO_HORIZON   = 6
COST_PER_PLACEMENT = 80_000
COST_INFLATION_PA  = 0.10

FIGURE_DPI  = 150
RANDOM_SEED = 42

ROOT      = Path(__file__).parent
FIG_DIR   = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'

# Primary need types tracked (matching both historic and SEN2 2025 data)
NT_TYPES_MAIN = ['asd', 'semh', 'slcn', 'mld']   # core four for models
NT_TYPES_ALL  = ['asd', 'semh', 'slcn', 'mld', 'sld', 'pmld', 'spld', 'oth']

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
s251_la['feat_year'] = (s251_la['time_period'].astype(str).str[:4].astype(int) + 1)

SPEND_LINES = {
    '1.2.1': 'topup_maintained',
    '1.2.3': 'topup_independent',
    '1.9.1': 'dsg_total',
    '1.9.3': 'dsg_carry',
    '2.1.1': 'ep_service',
    '2.1.2': 'sen_admin',
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
hist_raw.columns = [c.replace('﻿', '').replace('ï»¿', '') for c in hist_raw.columns]

hist_la = hist_raw[
    (hist_raw['geographic_level'] == 'Local authority') &
    (hist_raw['pupil_sen_status'].str.contains('Statement|EHC', na=False)) &
    (hist_raw['phase_type_grouping'] == 'Total')
].copy()

hist_la['la_code'] = hist_la['new_la_code'].astype(str).str.strip()
hist_la['ehcp_n'] = to_num(hist_la['number_of_pupils']).values
hist_la['feat_year'] = (hist_la['time_period'].astype(str).str[:4].astype(int) + 1)

ehcp_hist = (hist_la[hist_la['primary_need'] == 'Total']
             .groupby(['la_code', 'feat_year'])['ehcp_n']
             .sum().reset_index()
             .rename(columns={'ehcp_n': 'ehcp_count'}))

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
all_ehcp_mask = cas_la.get('breakdown_topic', pd.Series('', index=cas_la.index)) == 'All EHC plans'
if all_ehcp_mask.any():
    cas_la = cas_la[all_ehcp_mask].copy()

for col in ['ehcplans', 'special_independent', 'special_total',
            'special_la_maintained', 'special_academy_free']:
    if col in cas_la.columns:
        cas_la[col] = to_num(cas_la[col]).values

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

# ── 3e. Total pupils (2024/25) ─────────────────────────────────────────────────
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
ehcp_cas2 = ehcp_cas[['la_code', 'feat_year', 'ehcp_count_cas']].rename(
    columns={'ehcp_count_cas': 'ehcp_count'}
)
ehcp_all = pd.concat([
    ehcp_hist[['la_code', 'feat_year', 'ehcp_count']],
    ehcp_cas2[['la_code', 'feat_year', 'ehcp_count']],
], ignore_index=True).drop_duplicates(['la_code', 'feat_year'], keep='last')
ehcp_all = ehcp_all.merge(
    ehcp_cas[['la_code', 'feat_year', 'n_special_indep',
              'n_special_total', 'pct_special_independent']],
    on=['la_code', 'feat_year'], how='left'
)

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

# ── 3g. LA-level need-type panel ─────────────────────────────────────────────
print("  Building LA-level need-type panel...")

# Mapping from historical zip primary_need labels → short codes
NEED_MAP_HIST = {
    'Autistic Spectrum Disorder':              'asd',
    'Social, Emotional and Mental Health':     'semh',
    'Speech, Language and Communications needs': 'slcn',
    'Moderate Learning Difficulty':            'mld',
    'Severe Learning Difficulty':              'sld',
    'Profound & Multiple Learning Difficulty': 'pmld',
    'Specific Learning Difficulty':            'spld',
    'Other Difficulty/Disability':             'oth',
}

# Historical zip: LA × year × need-type (feat_years 2016–2020, real data)
hist_nt = hist_la[
    hist_la['primary_need'].isin(NEED_MAP_HIST) &
    hist_la['la_code'].isin(ALL_LAS)
].copy()
hist_nt['need_short'] = hist_nt['primary_need'].map(NEED_MAP_HIST)
hist_nt_wide = (hist_nt.groupby(['la_code', 'feat_year', 'need_short'])['ehcp_n']
                .sum().unstack('need_short').reset_index())
hist_nt_wide.columns = (
    ['la_code', 'feat_year'] +
    [f'ehcp_{c}_count' for c in hist_nt_wide.columns[2:]]
)
hist_nt_wide['nt_data_real'] = True

# SEN2 2025 needs file: LA × need-type (feat_year 2025, real data)
needs25_raw = pd.read_csv(
    ROOT / 'data/raw/sen2_2025/data/sen_needs_all_plans.csv', low_memory=False
)
needs25_la = needs25_raw[
    (needs25_raw['geographic_level'] == 'Local authority') &
    (needs25_raw.get('breakdown_topic', pd.Series('', index=needs25_raw.index)) == 'All EHC plans')
].copy()
needs25_la['la_code'] = needs25_la['new_la_code'].astype(str).str.strip()
needs25_la['feat_year'] = needs25_la['time_period'].astype(str).str[:4].astype(int) + 1

nt_col_map = {
    'number_asd': 'ehcp_asd_count', 'number_semh': 'ehcp_semh_count',
    'number_slcn': 'ehcp_slcn_count', 'number_mld': 'ehcp_mld_count',
    'number_sld': 'ehcp_sld_count', 'number_pmld': 'ehcp_pmld_count',
    'number_spld': 'ehcp_spld_count', 'number_oth': 'ehcp_oth_count',
}
needs25_wide = needs25_la[['la_code', 'feat_year'] + list(nt_col_map)].copy()
needs25_wide = needs25_wide.rename(columns=nt_col_map)
for c in needs25_wide.columns[2:]:
    needs25_wide[c] = to_num(needs25_wide[c]).values
needs25_wide['nt_data_real'] = True
needs25_wide = needs25_wide[needs25_wide['la_code'].isin(ALL_LAS)].copy()

# Combine
nt_count_cols = [f'ehcp_{nt}_count' for nt in NT_TYPES_ALL]
# Ensure all columns present in both frames
for c in nt_count_cols:
    for df in [hist_nt_wide, needs25_wide]:
        if c not in df.columns:
            df[c] = np.nan

nt_la = pd.concat([
    hist_nt_wide[['la_code', 'feat_year'] + nt_count_cols + ['nt_data_real']],
    needs25_wide[['la_code', 'feat_year'] + nt_count_cols + ['nt_data_real']],
], ignore_index=True).drop_duplicates(['la_code', 'feat_year'])

# Total across tracked need types (for share calculation)
nt_la['ehcp_total_nt'] = nt_la[nt_count_cols].sum(axis=1, min_count=1)

# Share columns
for nt in NT_TYPES_ALL:
    col = f'ehcp_{nt}_count'
    share_col = f'ehcp_{nt}_share'
    nt_la[share_col] = np.where(
        nt_la['ehcp_total_nt'] > 0,
        nt_la[col] / nt_la['ehcp_total_nt'] * 100,
        np.nan
    )

print(f"  Need-type panel: {len(nt_la)} rows, "
      f"real data years: {sorted(nt_la[nt_la['nt_data_real']]['feat_year'].unique())}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: NATIONAL TREND CHARTS (Figures 34, 42, 43)
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding national trend charts...")

# National totals
cas_nat = cas_raw[(cas_raw['geographic_level'] == 'National')].copy()
if 'breakdown_topic' in cas_nat.columns:
    mask_all = cas_nat['breakdown_topic'].eq('All EHC plans')
    if mask_all.any():
        cas_nat = cas_nat[mask_all]
cas_nat['ehcp_total'] = to_num(cas_nat['ehcplans']).values
cas_nat['feat_year'] = cas_nat['time_period'].astype(str).str[:4].astype(int) + 1
cas_nat_yr = cas_nat.groupby('feat_year')['ehcp_total'].sum().reset_index()

hist_nat_total = (nat_hist[nat_hist['primary_need'] == 'Total']
                  .groupby('feat_year')['ehcp_n'].sum().reset_index()
                  .rename(columns={'ehcp_n': 'ehcp_total'}))
nat_total = (pd.concat([hist_nat_total, cas_nat_yr])
             .drop_duplicates('feat_year', keep='last')
             .sort_values('feat_year'))

# National need-type % from mismatch analysis output
nt_pct = pd.read_csv(TABLE_DIR / 'demand_national_trend.csv')
nt_pct['feat_year'] = nt_pct['time_period'].astype(str).str[:4].astype(int) + 1
nt_wide = nt_pct.pivot(index='feat_year', columns='need', values='pct_national').reset_index()
nt_wide = nt_wide.merge(nat_total, on='feat_year', how='inner')

need_types_show = ['ASD', 'SEMH', 'SLCN', 'MLD', 'SLD']
for nt in need_types_show:
    if nt in nt_wide.columns:
        nt_wide[f'n_{nt}'] = nt_wide[nt] / 100 * nt_wide['ehcp_total']
nt_wide['n_Other'] = nt_wide['ehcp_total'] - sum(
    nt_wide.get(f'n_{nt}', pd.Series(0, index=nt_wide.index))
    for nt in need_types_show
    if f'n_{nt}' in nt_wide.columns
)

total_by_year = (pd.concat([
    hist_nat_total.rename(columns={'ehcp_total': 'n'}),
    cas_nat_yr.rename(columns={'ehcp_total': 'n'})
]).drop_duplicates('feat_year', keep='last').sort_values('feat_year'))

# Figure 34: Total EHCPs + stacked by need type
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

ax = axes[0]
yrs = total_by_year['feat_year'].values
ns  = to_num(total_by_year['n']).values
ax.fill_between(yrs, ns / 1000, alpha=0.15, color='#1f77b4')
ax.plot(yrs, ns / 1000, color='#1f77b4', lw=2.5, marker='o', ms=5)
ax.set_title('Total active EHCPs in England\n(absolute count, thousands)', fontweight='bold')
ax.set_ylabel('EHCPs (thousands)')
ax.set_xlabel('Academic year (end)')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}k'))
ax.grid(True, alpha=0.3)
ax.set_xlim(2016, 2026)
for yr in [2016, 2025]:
    row = total_by_year[total_by_year['feat_year'] == yr]
    if not row.empty:
        v = float(to_num(row['n'].values)[0]) / 1000
        ax.annotate(f'{v:.0f}k', xy=(yr, v), xytext=(0, 8),
                    textcoords='offset points', ha='center', fontsize=9, fontweight='bold')

ax2 = axes[1]
nt_plot = nt_wide[nt_wide['ehcp_total'].notna()].sort_values('feat_year').copy()
if not nt_plot.empty:
    stack_cols   = [f'n_{nt}' for nt in ['Other', 'SLD', 'MLD', 'SLCN', 'SEMH', 'ASD']
                    if f'n_{nt}' in nt_plot.columns]
    stack_labels = [c.replace('n_', '') for c in stack_cols]
    stack_colors = [NT_COLORS.get(l, '#888888') for l in stack_labels]
    stack_data   = [to_num(nt_plot[c]).values / 1000 for c in stack_cols]
    ax2.stackplot(nt_plot['feat_year'].values, stack_data,
                  labels=stack_labels, colors=stack_colors, alpha=0.8)
    ax2.set_title('EHCP caseload by primary need type\n(absolute count, thousands)', fontweight='bold')
    ax2.set_ylabel('EHCPs (thousands)')
    ax2.set_xlabel('Academic year (end)')
    ax2.legend(loc='upper left', fontsize=8, framealpha=0.8)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_xlim(nt_plot['feat_year'].min(), nt_plot['feat_year'].max() + 0.5)
    ax2.annotate('* 2020/21–2023/24 LA-level need-type\nbreakdown not available',
                 xy=(0.98, 0.05), xycoords='axes fraction', ha='right', fontsize=7,
                 style='italic', color='gray')

plt.suptitle('England EHCP demand: absolute counts, 2015/16–2024/25',
             fontsize=13, fontweight='bold', y=1.01)
plt.tight_layout()
fig.savefig(FIG_DIR / '34_national_demand_absolute.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 34")

# Figure 42: Need-type indexed growth (2016 = 100)
nt_index_data = nt_wide[nt_wide['ehcp_total'].notna()].sort_values('feat_year').copy()
base_row = nt_index_data[nt_index_data['feat_year'] == 2016]

fig, ax = plt.subplots(figsize=(11, 6))
nt_show = [('ASD', '#1f77b4'), ('SEMH', '#d62728'), ('SLCN', '#ff7f0e'),
           ('MLD', '#2ca02c'), ('SLD', '#9467bd')]
for nt_label, color in nt_show:
    col = f'n_{nt_label}'
    if col not in nt_index_data.columns:
        continue
    base_val = float(base_row[col].values[0]) if not base_row.empty and pd.notna(base_row[col].values[0]) else np.nan
    if pd.isna(base_val) or base_val == 0:
        continue
    indexed = nt_index_data[col].values / base_val * 100
    ax.plot(nt_index_data['feat_year'].values, indexed,
            label=nt_label, color=color, lw=2.5, marker='o', ms=5)

# Gap marker
ax.axvspan(2020.4, 2024.6, alpha=0.07, color='gray')
ax.text(2022.5, ax.get_ylim()[0] if ax.get_ylim()[0] > 0 else 95,
        'LA-level\nbreakdown\nnot available', ha='center', fontsize=7,
        color='gray', style='italic', va='bottom')
ax.axhline(100, color='black', lw=1, linestyle=':', alpha=0.5)
ax.set_title('National EHCP caseload by primary need type\n(indexed, 2016 = 100)',
             fontweight='bold', fontsize=12)
ax.set_xlabel('Academic year (end)')
ax.set_ylabel('Index (2016 = 100)')
ax.legend(fontsize=10, framealpha=0.9)
ax.grid(True, alpha=0.3)
ax.set_xlim(2016, 2026)
plt.tight_layout()
fig.savefig(FIG_DIR / '42_national_needtype_indexed.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 42")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: COLLAPSE LABEL COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────
print("\nComputing collapse labels...")

window = rich[rich['year'].isin(COLLAPSE_WINDOW)].copy()

la_timeliness = (window.groupby('la_code')['timeliness_pct']
                 .agg(mean_timeliness='mean', n_timeliness='count').reset_index())
la_appeals    = (window.groupby('la_code')['la_official_appeal_rate_pct']
                 .agg(mean_appeal='mean', n_appeal='count').reset_index())

latest_placement = (rich[rich['year'].isin([2023, 2024]) & rich['indep_per_1000'].notna()]
                    .sort_values('year')
                    .groupby('la_code').last()[['indep_per_1000', 'pct_special_independent']]
                    .reset_index())

appeal_thresh    = la_appeals['mean_appeal'].quantile(COLLAPSE_APPEAL_PERCENTILE)
placement_thresh = latest_placement['indep_per_1000'].quantile(COLLAPSE_PLACEMENT_PERCENTILE)
print(f"  Timeliness collapse threshold : < {COLLAPSE_TIMELINESS_THRESH}%")
print(f"  Appeal collapse threshold     : > {appeal_thresh:.2f}% ({COLLAPSE_APPEAL_PERCENTILE:.0%}ile)")
print(f"  Placement collapse threshold  : > {placement_thresh:.3f}/1000 ({COLLAPSE_PLACEMENT_PERCENTILE:.0%}ile)")

collapse = meta[['la_code', 'la_name', 'region', 'intervention_status']].copy()
collapse = collapse.merge(la_timeliness, on='la_code', how='left')
collapse = collapse.merge(la_appeals,    on='la_code', how='left')
collapse = collapse.merge(latest_placement, on='la_code', how='left')

collapse['y_timeliness'] = (collapse['mean_timeliness'] < COLLAPSE_TIMELINESS_THRESH).astype(float)
collapse['y_appeal']     = (collapse['mean_appeal']     > appeal_thresh).astype(float)
collapse['y_placement']  = (collapse['indep_per_1000']  > placement_thresh).astype(float)

for col in ['y_timeliness', 'y_appeal', 'y_placement']:
    collapse[col] = np.where(collapse[col].isna(), np.nan, collapse[col])

_all_na = collapse[['y_timeliness', 'y_appeal', 'y_placement']].isna().all(axis=1)
collapse['n_flags'] = (collapse[['y_timeliness', 'y_appeal', 'y_placement']]
                       .apply(lambda r: r.sum(skipna=True), axis=1))
collapse['y_composite'] = (collapse['n_flags'] >= COMPOSITE_MIN_FLAGS).astype(float)
collapse.loc[_all_na, 'y_composite'] = np.nan  # LAs missing all three metrics → not classified

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
    for status in status_order:
        s_data = sub[sub['intervention_status'].fillna('None') == status]
        color  = STATUS_COLORS.get(status, '#888888')
        collapsed_s   = s_data[s_data[y_col] == 1]
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
# SECTION 6: LA SCATTER — NEED-TYPE GROWTH vs COLLAPSE (Figure 43)
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding LA need-type growth scatter (Figure 43)...")

# Compute 2016→2020 absolute growth in ASD and SEMH for each LA
nt_2016 = nt_la[nt_la['feat_year'] == 2016][['la_code', 'ehcp_asd_count', 'ehcp_semh_count']].copy()
nt_2020 = nt_la[nt_la['feat_year'] == 2020][['la_code', 'ehcp_asd_count', 'ehcp_semh_count']].copy()
nt_growth_scatter = nt_2016.merge(nt_2020, on='la_code', suffixes=('_2016', '_2020'))
nt_growth_scatter['asd_abs_growth'] = nt_growth_scatter['ehcp_asd_count_2020'] - nt_growth_scatter['ehcp_asd_count_2016']
nt_growth_scatter['semh_abs_growth'] = nt_growth_scatter['ehcp_semh_count_2020'] - nt_growth_scatter['ehcp_semh_count_2016']
nt_growth_scatter = nt_growth_scatter.merge(
    collapse[['la_code', 'y_composite', 'y_timeliness', 'intervention_status']],
    on='la_code', how='left'
)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax, y_col, title_suffix in [
    (axes[0], 'y_composite', 'composite collapse 2022–24'),
    (axes[1], 'y_timeliness', 'timeliness collapse 2022–24'),
]:
    sub = nt_growth_scatter.dropna(subset=['asd_abs_growth', 'semh_abs_growth', y_col]).copy()
    collapse_mask = sub[y_col] == 1
    ax.scatter(sub.loc[~collapse_mask, 'asd_abs_growth'],
               sub.loc[~collapse_mask, 'semh_abs_growth'],
               c='#aec7e8', alpha=0.65, s=40, zorder=2, label='Did not collapse')
    ax.scatter(sub.loc[collapse_mask, 'asd_abs_growth'],
               sub.loc[collapse_mask, 'semh_abs_growth'],
               c='#d62728', alpha=0.8, s=60, marker='D', zorder=3, label='Collapsed')

    # Label top outliers
    top_outliers = (sub[collapse_mask]
                    .assign(tot=lambda d: d['asd_abs_growth'] + d['semh_abs_growth'])
                    .nlargest(5, 'tot'))
    for _, row in top_outliers.iterrows():
        la_name = collapse.loc[collapse['la_code'] == row['la_code'], 'la_name'].values
        label = la_name[0].split(',')[0] if len(la_name) > 0 else ''
        ax.annotate(label, xy=(row['asd_abs_growth'], row['semh_abs_growth']),
                    fontsize=7, alpha=0.8, xytext=(3, 3), textcoords='offset points')

    ax.set_xlabel('Absolute increase in ASD EHCPs, 2016→2020', fontsize=10)
    ax.set_ylabel('Absolute increase in SEMH EHCPs, 2016→2020', fontsize=10)
    ax.set_title(f'ASD vs SEMH growth (2016–2020)\nby {title_suffix}', fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

plt.suptitle(
    'Do LAs with higher ASD and SEMH growth 2016–2020 show worse 2022–24 outcomes?\n'
    '(Programme status not used in models)',
    fontsize=11, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '43_la_needtype_growth_vs_collapse.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 43")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: FEATURE CONSTRUCTION BY YEAR (NO LEAKAGE)
# ─────────────────────────────────────────────────────────────────────────────
print("\nConstructing feature sets by forecast year...")

# Data availability map (by feature year T):
#   Tribunal:         T from 2014 (panel)
#   S251 spend:       T = feat_year (academic yr T-1/T), from 2016
#   EHCP caseload:    hist zip up to 2020; SEN2 from 2019
#   Need-type counts: REAL from 2016–2020 (hist zip); 2025 (SEN2) — NOT 2021–2024
#                     For training year 2021: use 2020 real data as proxy
#   Timeliness:       SEN2 from 2019
#   Placement share:  SEN2 from 2019
#   Refusal rate:     SEN2 from 2019

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

    trib_col_T = f'trib_{T}'
    feats['trib_level'] = feats.get(trib_col_T, pd.Series(np.nan, index=feats.index))
    slope_cols = [c for c in feats.columns if c.startswith('trib_') and
                  c != 'trib_level' and c.split('_')[1].isdigit() and
                  int(c.split('_')[1]) <= T]

    def _slope(row):
        yr  = np.array([int(c.split('_')[1]) for c in slope_cols], dtype=float)
        val = np.array([row[c] for c in slope_cols], dtype=float)
        return linear_slope(val, yr)
    feats['trib_slope'] = feats.apply(_slope, axis=1) if slope_cols else np.nan

    # --- EHCP total caseload features ---
    ehcp_T = ehcp_all[(ehcp_all['feat_year'] <= T) &
                      (ehcp_all['la_code'].isin(ALL_LAS))].copy()
    if not ehcp_T.empty:
        ehcp_latest = (ehcp_T.sort_values('feat_year')
                       .groupby('la_code').last()[['ehcp_count']].reset_index())
        feats = feats.merge(ehcp_latest.rename(columns={'ehcp_count': 'ehcp_level'}),
                            on='la_code', how='left')

        def _ehcp_growth(sub):
            sub2 = sub[sub['feat_year'] <= T].sort_values('feat_year')
            return log_linear_slope(sub2['ehcp_count'].values, sub2['feat_year'].values)
        ehcp_growth = (ehcp_T.groupby('la_code')
                       .apply(_ehcp_growth).reset_index()
                       .rename(columns={0: 'ehcp_growth'}))
        feats = feats.merge(ehcp_growth, on='la_code', how='left')
    else:
        feats['ehcp_level'] = np.nan
        feats['ehcp_growth'] = np.nan

    # --- S251 spend features (from 2016) ---
    spend_T = spend[spend['feat_year'] <= T].sort_values('feat_year')
    spend_latest = spend_T.groupby('la_code').last().reset_index()
    for col in ['topup_independent_pct', 'dsg_balance_pct', 'ep_service_pct', 'sen_admin_pct']:
        if col in spend_latest.columns:
            feats = feats.merge(spend_latest[['la_code', col]], on='la_code', how='left')

    if T >= 2017:
        spend_Tm2 = spend[spend['feat_year'] == T - 2].set_index('la_code')
        spend_T1  = spend[spend['feat_year'] == T    ].set_index('la_code')
        idx = spend_Tm2.index.intersection(spend_T1.index)
        indep_growth_s = pd.Series(
            (spend_T1.loc[idx, 'topup_independent_pct'].values -
             spend_Tm2.loc[idx, 'topup_independent_pct'].values),
            index=idx, name='indep_spend_growth'
        )
        feats = feats.merge(indep_growth_s.reset_index().rename(
            columns={'index': 'la_code'}), on='la_code', how='left')
    else:
        feats['indep_spend_growth'] = np.nan

    # --- Placement share (SEN2, from 2019) ---
    if T >= 2019:
        pla_T = (ehcp_cas[ehcp_cas['feat_year'] <= T]
                 .sort_values('feat_year')
                 .groupby('la_code').last()[['pct_special_independent']].reset_index()
                 .rename(columns={'pct_special_independent': 'pct_indep_placement'}))
        feats = feats.merge(pla_T, on='la_code', how='left')
    else:
        feats['pct_indep_placement'] = np.nan

    # --- Timeliness (SEN2, from 2019) ---
    if T >= 2019:
        time_T = (rich[rich['year'] <= T]
                  .sort_values('year')
                  .groupby('la_code').last()[['timeliness_pct', 'refusal_rate_pct']].reset_index())
        feats = feats.merge(time_T, on='la_code', how='left')

        def _tl_slope(sub):
            sub2 = sub[sub['year'] <= T].sort_values('year')
            return linear_slope(sub2['timeliness_pct'].values, sub2['year'].values)
        tl_growth = (rich[rich['year'] <= T].groupby('la_code')
                     .apply(_tl_slope).reset_index()
                     .rename(columns={0: 'timeliness_trend'}))
        feats = feats.merge(tl_growth, on='la_code', how='left')
    else:
        feats['timeliness_pct']   = np.nan
        feats['refusal_rate_pct'] = np.nan
        feats['timeliness_trend'] = np.nan

    # --- Need-type features (REAL data 2016–2020; use 2020 as proxy for T=2021) ---
    # Restrict to real data only — no estimated gap-year extrapolation in models
    nt_T = nt_la[
        (nt_la['feat_year'] <= T) &
        (nt_la['nt_data_real'] == True) &
        (nt_la['la_code'].isin(ALL_LAS))
    ].copy()

    if not nt_T.empty:
        nt_latest = nt_T.sort_values('feat_year').groupby('la_code').last()
        nt_latest_year = nt_T.sort_values('feat_year').groupby('la_code')['feat_year'].last()

        for nt in NT_TYPES_MAIN:
            cnt_col   = f'ehcp_{nt}_count'
            share_col = f'ehcp_{nt}_share'
            feats[cnt_col]   = feats['la_code'].map(nt_latest[cnt_col])
            feats[share_col] = feats['la_code'].map(nt_latest[share_col])

        # 3-year absolute growth: count at latest ≤ T  minus  count at latest ≤ (T-3)
        for nt in NT_TYPES_MAIN:
            cnt_col = f'ehcp_{nt}_count'
            gkey = f'ehcp_{nt}_abs_growth_3yr'
            growth_map = {}
            for la in nt_T['la_code'].unique():
                la_sub = nt_T[nt_T['la_code'] == la].sort_values('feat_year')
                y_end   = la_sub.tail(1)
                y_start = la_sub[la_sub['feat_year'] <= (la_sub['feat_year'].max() - 3)].tail(1)
                if len(y_end) > 0 and len(y_start) > 0:
                    growth_map[la] = (float(y_end[cnt_col].values[0]) -
                                      float(y_start[cnt_col].values[0]))
            feats[gkey] = feats['la_code'].map(growth_map)

        # Flag whether need-type data is using real values at T or 2020 proxy
        feats['nt_data_proxy'] = (nt_latest_year.values < T).any() if not nt_latest_year.empty else False
    else:
        for nt in NT_TYPES_MAIN:
            for suffix in ['_count', '_share', '_abs_growth_3yr']:
                feats[f'ehcp_{nt}{suffix}'] = np.nan

    feats['feat_year'] = T
    return feats


features_by_year = {}
for T in FORECAST_YEARS:
    features_by_year[T] = build_features_for_year(T)
    f = features_by_year[T]
    nt_non_null = f['ehcp_asd_count'].notna().sum()
    print(f"  Features at {T}: {len(f)} LAs | "
          f"trib={f['trib_level'].notna().sum()} | "
          f"indep_spend={f['topup_independent_pct'].notna().sum()} | "
          f"timeliness={f['timeliness_pct'].notna().sum()} | "
          f"ASD count={nt_non_null}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: MODEL FAMILIES A–H + LOO-CV EVALUATION
# ─────────────────────────────────────────────────────────────────────────────
print("\nFitting model families A–H with LOO-CV...")

NT_COUNT_FEATS  = [f'ehcp_{nt}_count'          for nt in NT_TYPES_MAIN]
NT_GROWTH_FEATS = [f'ehcp_{nt}_abs_growth_3yr'  for nt in NT_TYPES_MAIN]
NT_SHARE_FEATS  = [f'ehcp_{nt}_share'            for nt in NT_TYPES_MAIN]

FAMILIES = {
    # A: total EHCP demand only (baseline: does caseload volume/growth predict collapse?)
    'A_total_demand': [
        'ehcp_growth', 'ehcp_level',
    ],
    # B: need-type absolute counts + 3yr absolute growth only (core new test)
    'B_need_type_counts': (
        NT_COUNT_FEATS + NT_GROWTH_FEATS
    ),
    # C: need-type SHARES only (tests whether shares, not absolute counts, matter)
    'C_need_type_shares': NT_SHARE_FEATS,
    # D: need-type counts + capacity proxy (independent spend %)
    'D_counts_capacity': (
        NT_COUNT_FEATS + NT_GROWTH_FEATS[:2] +
        ['topup_independent_pct', 'ep_service_pct']
    ),
    # E: need-type counts + throughput (available 2019+)
    'E_counts_throughput': (
        NT_COUNT_FEATS + NT_GROWTH_FEATS[:2] +
        ['timeliness_pct', 'timeliness_trend']
    ),
    # F: need-type counts + cost/financial features
    'F_counts_cost': (
        NT_COUNT_FEATS + NT_GROWTH_FEATS[:2] +
        ['topup_independent_pct', 'dsg_balance_pct']
    ),
    # G: system-failure signals only (current best performer — tribunal + spend)
    'G_signals_only': [
        'trib_level', 'trib_slope', 'topup_independent_pct',
    ],
    # H: full model (need-type + system signals + timeliness)
    'H_full': (
        NT_COUNT_FEATS + NT_GROWTH_FEATS +
        ['trib_level', 'trib_slope',
         'topup_independent_pct', 'dsg_balance_pct',
         'timeliness_pct', 'pct_indep_placement']
    ),
}

COLLAPSE_TARGETS = ['y_timeliness', 'y_appeal', 'y_placement', 'y_composite']

results = []

for T in FORECAST_YEARS:
    feats = features_by_year[T].copy()
    feats = feats.merge(
        collapse[['la_code', 'y_timeliness', 'y_appeal', 'y_placement',
                  'y_composite', 'n_flags']],
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
                'feat_year':       T,
                'model_family':    family_name,
                'collapse_type':   y_col,
                'n_la':            len(sub),
                'n_positive':      n_pos,
                'auc_loo':         auc_val,
                'precision_at_10': p10,
                'precision_at_20': p20,
            })

results_df = pd.DataFrame(results)
print(f"  Completed {len(results_df)} model evaluations")
results_df.to_csv(TABLE_DIR / 'forecastability_summary.csv', index=False, float_format='%.3f')
print("  Saved forecastability_summary.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9: FORECASTABILITY VERDICT
# ─────────────────────────────────────────────────────────────────────────────
print("\nComputing forecastability verdict by collapse type...")

verdict_rows = []
for y_col in COLLAPSE_TARGETS:
    sub = results_df[results_df['collapse_type'] == y_col].copy()
    if sub.empty:
        continue

    for T in FORECAST_YEARS:
        yr_sub = sub[sub['feat_year'] == T]
        if yr_sub.empty:
            continue

        auc_A = yr_sub[yr_sub['model_family'] == 'A_total_demand']['auc_loo'].max() if not yr_sub[yr_sub['model_family'] == 'A_total_demand'].empty else np.nan
        auc_B = yr_sub[yr_sub['model_family'] == 'B_need_type_counts']['auc_loo'].max() if not yr_sub[yr_sub['model_family'] == 'B_need_type_counts'].empty else np.nan
        auc_G = yr_sub[yr_sub['model_family'] == 'G_signals_only']['auc_loo'].max() if not yr_sub[yr_sub['model_family'] == 'G_signals_only'].empty else np.nan
        auc_H = yr_sub[yr_sub['model_family'] == 'H_full']['auc_loo'].max() if not yr_sub[yr_sub['model_family'] == 'H_full'].empty else np.nan
        auc_best = yr_sub['auc_loo'].max()
        best_model = yr_sub.loc[yr_sub['auc_loo'].idxmax(), 'model_family'] if not yr_sub.empty else 'N/A'

        # Classify verdict
        if pd.notna(auc_B) and auc_B >= 0.65 and (pd.isna(auc_G) or auc_B >= auc_G - 0.03):
            verdict = 'A: Need-type growth was predictive'
        elif pd.notna(auc_G) and pd.notna(auc_B) and auc_G > auc_B + 0.05:
            verdict = 'C: System-failure signals dominated'
        elif pd.notna(auc_H) and auc_H >= 0.70:
            verdict = 'B: Need-type + context jointly predictive'
        elif pd.notna(auc_best) and auc_best >= 0.60:
            verdict = 'B: Weakly predictive (best model modest)'
        else:
            verdict = 'D: Not forecastable at this training year'

        verdict_rows.append({
            'collapse_type': y_col,
            'feat_year': T,
            'auc_A_total_demand': auc_A,
            'auc_B_need_counts': auc_B,
            'auc_G_signals': auc_G,
            'auc_H_full': auc_H,
            'auc_best': auc_best,
            'best_model': best_model,
            'verdict': verdict,
        })

verdict_df = pd.DataFrame(verdict_rows)
verdict_df.to_csv(TABLE_DIR / 'forecastability_verdict.csv', index=False, float_format='%.3f')
print("  Saved forecastability_verdict.csv")
print("\nForecastability verdict summary:")
pivot_verdict = verdict_df.pivot(index='collapse_type', columns='feat_year', values='verdict')
print(pivot_verdict.to_string())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10: FORECASTABILITY CHARTS (Figures 36–38)
# ─────────────────────────────────────────────────────────────────────────────
print("\nProducing forecastability charts...")

collapse_labels_map = {
    'y_timeliness': 'Timeliness\ncollapse',
    'y_appeal':     'Legal-pressure\ncollapse',
    'y_placement':  'Placement/cost\ncollapse',
    'y_composite':  'Composite\ncollapse',
}
family_display = {
    'A_total_demand':    'A: Total EHCP demand',
    'B_need_type_counts':'B: Need-type counts\n(ASD/SEMH/SLCN/MLD)',
    'C_need_type_shares':'C: Need-type shares\n(% of total)',
    'D_counts_capacity': 'D: Counts + capacity',
    'E_counts_throughput':'E: Counts + timeliness\n(2019+ only)',
    'F_counts_cost':     'F: Counts + cost',
    'G_signals_only':    'G: System signals\n(tribunal + spend)',
    'H_full':            'H: Full model',
}

# Figure 36: AUC heatmap — all 8 model families × training year, per collapse type
fig, axes = plt.subplots(2, 2, figsize=(18, 14))
axes = axes.flatten()

for ax, y_col in zip(axes, COLLAPSE_TARGETS):
    sub = results_df[results_df['collapse_type'] == y_col].copy()
    if sub.empty:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        continue
    piv = sub.pivot(index='model_family', columns='feat_year', values='auc_loo')
    row_order = [f for f in FAMILIES if f in piv.index]
    piv = piv.loc[row_order]
    piv.index = [family_display.get(i, i) for i in piv.index]

    sns.heatmap(piv, ax=ax, annot=True, fmt='.2f', cmap='RdYlGn',
                vmin=0.45, vmax=0.95, cbar_kws={'label': 'LOO-CV AUC'},
                linewidths=0.5, linecolor='white', annot_kws={'size': 8})
    ax.set_title(f'{collapse_labels_map[y_col]}\n(AUC; random = 0.50)',
                 fontweight='bold', fontsize=10)
    ax.set_xlabel('Training data cut-off year', fontsize=9)
    ax.set_ylabel('')
    ax.tick_params(axis='y', labelsize=8)

plt.suptitle(
    'Forecastability: how well could earlier data predict 2022–24 system collapse?\n'
    'Eight model families A–H: A/B test whether need-type growth predicted collapse\n'
    'independently of system-failure signals (G)',
    fontsize=11, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '36_forecastability_auc_heatmap.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 36")

# Figure 37: Precision@20 heatmap and AUC over time
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Left: Best-model AUC over training years
ax = axes[0]
for y_col, ytitle in collapse_labels_map.items():
    sub = results_df[results_df['collapse_type'] == y_col]
    if sub.empty:
        continue
    best = sub.groupby('feat_year')['auc_loo'].max().reset_index()
    ax.plot(best['feat_year'], best['auc_loo'], marker='o', lw=2,
            label=ytitle.replace('\n', ' '))
ax.axhline(0.5, color='gray', lw=1, linestyle='--', alpha=0.5, label='Random (0.50)')
ax.set_xlabel('Training data cut-off year', fontsize=10)
ax.set_ylabel('Best-model LOO-CV AUC', fontsize=10)
ax.set_title('Best-model AUC vs training year\n(maximum across all 8 families)', fontweight='bold')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)
ax.set_xticks(FORECAST_YEARS)
ax.set_ylim(0.4, 1.0)

# Right: Precision@20 for key families over training years
ax2 = axes[1]
key_families = ['B_need_type_counts', 'G_signals_only', 'H_full']
colors_p20 = ['#ff7f0e', '#d62728', '#2ca02c']
for fam, col in zip(key_families, colors_p20):
    for y_col, ytitle in [('y_composite', 'Composite'), ('y_appeal', 'Appeal')]:
        sub = results_df[(results_df['model_family'] == fam) &
                         (results_df['collapse_type'] == y_col)]
        if sub.empty:
            continue
        ls = '-' if y_col == 'y_composite' else '--'
        ax2.plot(sub['feat_year'], sub['precision_at_20'], marker='s', lw=1.8,
                 color=col, linestyle=ls, alpha=0.8,
                 label=f"{family_display[fam].split(':')[0]}: {ytitle}")
baseline = results_df['n_positive'].mean() / results_df['n_la'].mean()
ax2.axhline(baseline, color='gray', lw=1, linestyle=':', alpha=0.5,
            label=f'Random baseline (~{baseline:.2f})')
ax2.set_xlabel('Training data cut-off year', fontsize=10)
ax2.set_ylabel('Precision@20', fontsize=10)
ax2.set_title('Precision@20: top-20 highest-risk LAs\n(key model families, composite & appeal targets)',
              fontweight='bold')
ax2.legend(fontsize=7)
ax2.grid(True, alpha=0.3)
ax2.set_xticks(FORECAST_YEARS)

plt.suptitle(
    'Forecastability improves over time — system-failure signals (G) dominated from 2016\n'
    'Need-type growth (B) added predictive value from 2019 when 3-year growth data available',
    fontsize=10, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '37_forecastability_over_time.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 37")

# Figure 38: Feature importance — 'H_full' at 2020 and 2021 (composite collapse)
fig, axes = plt.subplots(1, 2, figsize=(14, 8))

feat_labels = {
    'ehcp_growth':              'Total EHCP growth rate',
    'ehcp_level':               'Total EHCP level',
    'ehcp_asd_count':           'ASD: absolute count',
    'ehcp_semh_count':          'SEMH: absolute count',
    'ehcp_slcn_count':          'SLCN: absolute count',
    'ehcp_mld_count':           'MLD: absolute count',
    'ehcp_asd_abs_growth_3yr':  'ASD: 3yr absolute growth',
    'ehcp_semh_abs_growth_3yr': 'SEMH: 3yr absolute growth',
    'ehcp_slcn_abs_growth_3yr': 'SLCN: 3yr absolute growth',
    'ehcp_mld_abs_growth_3yr':  'MLD: 3yr absolute growth',
    'trib_level':               'Tribunal appeal rate',
    'trib_slope':               'Tribunal rate trend',
    'topup_independent_pct':    'Independent top-up\n(% of DSG)',
    'dsg_balance_pct':          'DSG carry-forward\n(% of DSG)',
    'timeliness_pct':           '20-week compliance',
    'pct_indep_placement':      '% in independent\nspecial schools',
    'ep_service_pct':           'EP service spend\n(% of DSG)',
}

target_col = 'y_composite'
for ax, T in zip(axes, [2020, 2021]):
    feats = features_by_year[T].copy()
    feats = feats.merge(collapse[['la_code', target_col]], on='la_code', how='inner')
    feats = feats[~feats['la_code'].isin(small_codes)].copy()

    fam_preds = [c for c in FAMILIES['H_full'] if c in feats.columns]
    sub = feats[fam_preds + [target_col]].dropna().copy()

    if len(sub) < 10:
        ax.text(0.5, 0.5, f'Insufficient data at {T}', ha='center', va='center',
                transform=ax.transAxes)
        continue

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(sub[fam_preds])
    y_arr    = sub[target_col].values.astype(int)

    lr = LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced',
                            random_state=RANDOM_SEED)
    lr.fit(X_scaled, y_arr)
    coefs = lr.coef_[0]

    coef_df = pd.DataFrame({'feature': fam_preds, 'coef': coefs})
    coef_df['label'] = coef_df['feature'].map(lambda x: feat_labels.get(x, x))
    coef_df = coef_df.sort_values('coef')

    # Colour by feature category
    def feat_color(f):
        if 'asd' in f or 'semh' in f or 'slcn' in f or 'mld' in f:
            return '#ff7f0e'   # orange = need-type
        if 'trib' in f or 'topup' in f or 'dsg' in f or 'pct_indep' in f:
            return '#d62728'   # red = system-failure signals
        if 'timeliness' in f:
            return '#2ca02c'   # green = throughput
        return '#1f77b4'       # blue = demand / other

    bar_colors = [feat_color(f) for f in coef_df['feature']]
    ax.barh(coef_df['label'], coef_df['coef'], color=bar_colors, alpha=0.80)
    ax.axvline(0, color='black', lw=1)
    ax.set_title(f'Model H (Full) feature importances\nTraining year {T} | Target: composite collapse\n'
                 f'n={len(sub)}, n_pos={y_arr.sum()}',
                 fontweight='bold', fontsize=9)
    ax.set_xlabel('Standardised log-odds coefficient', fontsize=9)
    ax.grid(True, axis='x', alpha=0.3)
    ax.tick_params(labelsize=8)

# Legend for colour categories
legend_patches = [
    mpatches.Patch(color='#ff7f0e', label='Need-type features (B model)'),
    mpatches.Patch(color='#d62728', label='System-failure signals (G model)'),
    mpatches.Patch(color='#2ca02c', label='Throughput / timeliness'),
    mpatches.Patch(color='#1f77b4', label='Total demand / other'),
]
fig.legend(handles=legend_patches, loc='lower center', ncol=4, fontsize=8,
           bbox_to_anchor=(0.5, -0.04))

plt.suptitle(
    'Which features drove composite collapse prediction?\n'
    '(Full model H, standardised coefficients; positive = higher risk)',
    fontsize=11, fontweight='bold', y=1.01
)
plt.tight_layout()
fig.savefig(FIG_DIR / '38_feature_importance.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 38")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11: CURRENT RISK SCORES (Figure 39)
# ─────────────────────────────────────────────────────────────────────────────
print("\nComputing current (2024) risk scores...")

# Use the best-performing model on composite collapse from 2021 features
sub_composite = results_df[results_df['collapse_type'] == 'y_composite']
if not sub_composite.empty:
    best_result = sub_composite.sort_values('auc_loo', ascending=False).iloc[0]
else:
    best_result = pd.Series({'feat_year': 2021, 'model_family': 'G_signals_only', 'auc_loo': np.nan})

best_T      = int(best_result['feat_year'])
best_family = best_result['model_family']
print(f"  Best model: family='{best_family}', year={best_T}, "
      f"AUC={best_result['auc_loo']:.3f}")

feats_2021 = features_by_year[2021].copy()
feats_2021 = feats_2021.merge(
    collapse[['la_code', 'y_timeliness', 'y_appeal', 'y_placement',
              'y_composite', 'n_flags', 'mean_timeliness', 'mean_appeal', 'indep_per_1000']],
    on='la_code', how='left'
)
feats_2021 = feats_2021[~feats_2021['la_code'].isin(small_codes)].copy()

fam_preds = [c for c in FAMILIES[best_family] if c in feats_2021.columns]
sub_2021  = feats_2021[fam_preds + ['la_code', 'la_name', 'region',
                                     'intervention_status', 'y_composite']].copy()
sub_clean = sub_2021.dropna(subset=fam_preds).copy()
X_all     = sub_clean[fam_preds].values.astype(float)
y_all     = sub_clean['y_composite'].fillna(0).values.astype(int)

scaler_f     = StandardScaler()
X_scaled_all = scaler_f.fit_transform(X_all)
lr_final     = LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced',
                                   random_state=RANDOM_SEED)
lr_final.fit(X_scaled_all, y_all)
sub_clean = sub_clean.copy()
sub_clean['risk_score'] = lr_final.predict_proba(X_scaled_all)[:, 1]

sub_clean['risk_decile'] = pd.qcut(sub_clean['risk_score'], q=10, labels=False,
                                    duplicates='drop') + 1
sub_clean['risk_tier'] = pd.cut(
    sub_clean['risk_score'],
    bins=[0, 0.25, 0.50, 0.75, 1.01],
    labels=['Low (< 25%)', 'Moderate (25–50%)', 'High (50–75%)', 'Critical (> 75%)'],
    right=False
)

sub_clean = sub_clean.merge(
    feats_2021[['la_code', 'mean_timeliness', 'mean_appeal', 'indep_per_1000',
                'topup_independent_pct', 'trib_level', 'ehcp_growth']],
    on='la_code', how='left'
)

risk_cols = ['la_code', 'la_name', 'region', 'intervention_status',
             'risk_score', 'risk_decile', 'risk_tier',
             'y_timeliness', 'y_appeal', 'y_placement', 'y_composite',
             'mean_timeliness', 'mean_appeal', 'indep_per_1000',
             'topup_independent_pct', 'trib_level', 'ehcp_growth']
out_risk = sub_clean[[c for c in risk_cols if c in sub_clean.columns]]
out_risk.to_csv(TABLE_DIR / 'la_risk_scores_2024.csv', index=False, float_format='%.3f')
print(f"  Risk scores saved for {len(out_risk)} LAs")

# Figure 39: Risk scores — top 40 LAs
top40 = sub_clean.sort_values('risk_score', ascending=False).head(40).copy()
top40['rank'] = range(1, len(top40) + 1)

def collapse_label_fn(row):
    flags = []
    if row.get('y_timeliness', 0) == 1: flags.append('T')
    if row.get('y_appeal',     0) == 1: flags.append('A')
    if row.get('y_placement',  0) == 1: flags.append('P')
    return ','.join(flags) if flags else 'None'

top40['collapse_flags'] = top40.apply(collapse_label_fn, axis=1)

fig, ax = plt.subplots(figsize=(11, 14))
bar_colors = [STATUS_COLORS.get(s if pd.notna(s) else 'None', '#888888')
              for s in top40['intervention_status']]
y_pos = np.arange(len(top40))
ax.barh(y_pos, top40['risk_score'], color=bar_colors, alpha=0.8, height=0.7)

for i, (_, row) in enumerate(top40.iterrows()):
    name  = row['la_name'] if pd.notna(row['la_name']) else row['la_code']
    flags = row['collapse_flags']
    label = f"{name}  [{flags}]" if flags != 'None' else name
    ax.text(row['risk_score'] + 0.005, i, label, va='center', fontsize=7.5)

ax.axvline(0.5, color='black', lw=1.5, linestyle=':', alpha=0.7, label='50% risk threshold')
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
# SECTION 12: SCENARIO PROJECTIONS (Figures 40–41)
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding scenario projections...")

base_2024 = (rich[rich['year'] == 2024]
             .merge(pupils, on='la_code', how='left')
             .merge(sub_clean[['la_code', 'risk_score', 'risk_tier',
                                'intervention_status']], on='la_code', how='left')
             .copy())
base_2024 = base_2024[~base_2024['la_code'].isin(small_codes)].copy()

def _growth_vec(grp, col, ymin=2019, ymax=2024):
    sub = grp[(grp['year'] >= ymin) & (grp['year'] <= ymax) & grp[col].notna()]
    return log_linear_slope(sub[col].values, sub['year'].values)

print("  Computing LA-level growth rates...")
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

base_2024['plans_growth_hist']  = base_2024['plans_growth_hist'].clip(-0.05, 0.12)
base_2024['timely_growth_hist'] = base_2024['timely_growth_hist'].clip(-0.15, 0.10)
base_2024['indep_growth_hist']  = base_2024['indep_growth_hist'].clip(-0.05, 0.12)

base_2024['demand_base'] = base_2024['n_plans_issued'].fillna(0)
base_2024['timely_base'] = base_2024['n_within_20w'].fillna(0)
base_2024['indep_base']  = base_2024['n_special_indep'].fillna(0)
base_2024['pct_indep_base'] = base_2024['pct_special_independent'].fillna(10) / 100

SCENARIOS = {
    'continuation':        {'demand_mult': 1.0,  'cost_mult': 1.0,
                            'throughput_mode': 'trend', 'placement_mult': 1.0},
    'asd_semh_accel':      {'demand_mult': 1.25, 'cost_mult': 1.0,
                            'throughput_mode': 'trend', 'placement_mult': 1.1},
    'cost_inflation':      {'demand_mult': 1.0,  'cost_mult': 1 + COST_INFLATION_PA,
                            'throughput_mode': 'trend', 'placement_mult': 1.0},
    'capacity_improvement':{'demand_mult': 1.0,  'cost_mult': 1.0,
                            'throughput_mode': 'improve', 'placement_mult': 0.95},
    'flat_throughput':     {'demand_mult': 1.0,  'cost_mult': 1.0,
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

    if pd.isna(demand0) or demand0 <= 0:
        continue

    for scen_name, scen_params in SCENARIOS.items():
        for t in range(SCENARIO_HORIZON + 1):
            year_t = 2024 + t
            dm   = scen_params['demand_mult']
            cm   = scen_params['cost_mult']
            pm   = scen_params['placement_mult']
            mode = scen_params['throughput_mode']

            demand_t = demand0 * np.exp(g_demand * dm * t)

            if mode == 'trend':
                timely_t = timely0 * np.exp(g_timely * t)
                timely_t = min(timely_t, demand_t)
            elif mode == 'flat':
                timely_t = timely0
            elif mode == 'improve':
                timely_rate = min(0.65, (timely0 / max(demand0, 1)) + 0.05 * t)
                timely_t = demand_t * timely_rate
            else:
                timely_t = timely0

            timely_t = max(0, timely_t)
            late_t   = max(0, demand_t - timely_t)
            indep_t  = indep0 * np.exp(g_indep * pm * t) if pd.notna(indep0) else np.nan
            cost_t   = (indep_t * COST_PER_PLACEMENT * (cm ** t) / 1e6
                        if pd.notna(indep_t) else np.nan)

            proj_rows.append({
                'la_code': la_code, 'la_name': la_name,
                'intervention_status': status, 'risk_score': risk,
                'scenario': scen_name, 'year': year_t,
                'demand_projected': demand_t,
                'timely_projected': timely_t,
                'late_projected':   late_t,
                'indep_placements_projected': indep_t,
                'cost_projected_m': cost_t,
            })

proj_df = pd.DataFrame(proj_rows)
proj_df.to_csv(TABLE_DIR / 'la_scenario_forecasts.csv', index=False, float_format='%.1f')
print(f"  Saved scenario forecasts: {len(proj_df)} rows")

nat_scen = (proj_df.groupby(['scenario', 'year'])
            .agg(late_total=('late_projected', 'sum'),
                 cost_total=('cost_projected_m', 'sum'),
                 demand_total=('demand_projected', 'sum'),
                 timely_total=('timely_projected', 'sum'))
            .reset_index())
nat_scen['timeliness_rate'] = (nat_scen['timely_total'] /
                                nat_scen['demand_total'].replace(0, np.nan) * 100)

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
    (axes[0], 'late_total',      'Late plans per year (absolute count)',
     'New plans issued outside 20-week limit\n(national aggregate)'),
    (axes[1], 'timeliness_rate', '20-week compliance (%)',
     'National 20-week compliance rate\n(% of new plans issued within 20 weeks)'),
    (axes[2], 'cost_total',      'Annual independent placement cost (£bn)',
     'Independent special school\nplacement costs (£bn/yr)'),
]:
    for scen, grp in nat_scen.groupby('scenario'):
        vals = grp.sort_values('year')[y_col]
        if y_col == 'cost_total':
            vals = vals / 1000
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

# Figure 41: High-risk non-SV LA scenario trajectories
high_risk_non_sv = (sub_clean[
    (~sub_clean['intervention_status'].isin(['Safety Valve'])) &
    sub_clean['risk_score'].notna()
].sort_values('risk_score', ascending=False)
.head(10)[['la_code', 'la_name']].values.tolist())

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
        if i % 5 == 0:
            ax.set_ylabel('Late plans/yr', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=7)

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
# SECTION 13: OUTPUT TABLES
# ─────────────────────────────────────────────────────────────────────────────
collapse.to_csv(TABLE_DIR / 'la_collapse_labels.csv', index=False, float_format='%.3f')
print("\nSaved la_collapse_labels.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14: SUMMARY PRINT
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("FORECASTABILITY SUMMARY — EIGHT MODEL FAMILIES A–H")
print("=" * 70)

print("\nBest LOO-CV AUC by collapse type, training year, and key model:")
pivot_key = (results_df[results_df['model_family'].isin(['A_total_demand', 'B_need_type_counts',
                                                          'G_signals_only', 'H_full'])]
             .pivot_table(index=['collapse_type', 'model_family'],
                          columns='feat_year', values='auc_loo', aggfunc='max'))
print(pivot_key.to_string(float_format='{:.2f}'.format))

print("\nForecastability verdict by collapse type and training year:")
if not verdict_df.empty:
    pv = verdict_df.pivot(index='collapse_type', columns='feat_year', values='verdict')
    for row_idx in pv.index:
        print(f"\n  {row_idx}:")
        for col in pv.columns:
            print(f"    {col}: {pv.loc[row_idx, col]}")

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
scen_2024_cont = nat_scen[(nat_scen['year'] == 2024) & (nat_scen['scenario'] == 'continuation')]
for scen in SCENARIOS:
    r2030 = scen_2030[scen_2030['scenario'] == scen]
    if not r2030.empty and not scen_2024_cont.empty:
        cost30 = float(r2030['cost_total'].values[0])
        cost24 = float(scen_2024_cont['cost_total'].values[0])
        late30 = float(r2030['late_total'].values[0])
        late24 = float(scen_2024_cont['late_total'].values[0])
        print(f"  {SCEN_LABELS[scen]:<48}: "
              f"late plans {late24:,.0f}→{late30:,.0f}, "
              f"cost £{cost24:.0f}m→£{cost30:.0f}m")

print("\nDone. Figures 34–43 and tables saved.")
print("Key question answered: Did need-type growth (Model B) predict collapse?")
if not verdict_df.empty:
    for y_col in COLLAPSE_TARGETS:
        yr2020 = verdict_df[(verdict_df['collapse_type'] == y_col) &
                             (verdict_df['feat_year'] == 2020)]
        if not yr2020.empty:
            auc_B = yr2020['auc_B_need_counts'].values[0]
            auc_G = yr2020['auc_G_signals'].values[0]
            verdict = yr2020['verdict'].values[0]
            print(f"  {y_col}: B(need-type)={auc_B:.2f}, G(signals)={auc_G:.2f} → {verdict}")
