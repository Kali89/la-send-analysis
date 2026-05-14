#!/usr/bin/env python3
"""
prediction_analysis.py

Two analyses:
1. Retrospective: Could data available in 2016 have predicted which local
   authorities would end up in the Safety Valve programme (2022+)?
2. Forward-looking: Which currently-unaffected LAs are on a trajectory
   toward crisis by 2030?

Produces figures 14-16 and two output tables.
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
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')

ROOT = Path(__file__).parent
FIG_DIR  = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'

COLORS = {'Safety Valve': '#d62728', 'DBV': '#ff7f0e', 'None': '#1f77b4'}
ALPHA  = {'Safety Valve': 0.9, 'DBV': 0.6, 'None': 0.4}

def to_numeric_safe(s):
    return pd.to_numeric(
        s.astype(str).str.strip().replace(
            {'x': np.nan, 'z': np.nan, '-': np.nan, '..': np.nan, 'c': np.nan}
        ), errors='coerce'
    )

def roc_auc_manual(y_true, y_score):
    """AUC via Mann-Whitney U (exact equivalent)."""
    n_pos = int(y_true.sum())
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.nan
    ranks = stats.rankdata(y_score)
    rank_sum = float(ranks[np.array(y_true, dtype=bool)].sum())
    u = rank_sum - n_pos * (n_pos + 1) / 2
    return u / (n_pos * n_neg)

def roc_curve_manual(y_true, y_score):
    thresholds = np.sort(np.unique(y_score))[::-1]
    n_pos = y_true.sum()
    n_neg = len(y_true) - n_pos
    fprs, tprs = [0.0], [0.0]
    for t in thresholds:
        pred = (y_score >= t)
        tp = (pred & (y_true == 1)).sum()
        fp = (pred & (y_true == 0)).sum()
        tprs.append(tp / n_pos)
        fprs.append(fp / n_neg)
    fprs.append(1.0); tprs.append(1.0)
    return np.array(fprs), np.array(tprs)

# ═══════════════════════════════════════════════════════════════════════════
# PART 1: DATA ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

print("Loading data...")

panel   = pd.read_csv(TABLE_DIR / 'panel_timeseries.csv')
summary = pd.read_csv(TABLE_DIR / 'la_summary_2024_extended.csv')
capacity = pd.read_csv(TABLE_DIR / 'la_capacity_2024.csv')

# ── 1a. Tribunal features from 2014-2016 ────────────────────────────────────
trib = (panel[panel['year'].between(2014, 2016) & panel['la_code_static'].notna()]
        .drop_duplicates(['la_code_static','year'])
        .pivot(index='la_code_static', columns='year',
               values='la_official_appeal_rate_pct')
        .rename(columns={2014: 'trib_2014', 2015: 'trib_2015', 2016: 'trib_2016'})
        .reset_index()
        .rename(columns={'la_code_static': 'la_code'}))

def _slope(row):
    y = np.array([row.trib_2014, row.trib_2015, row.trib_2016], dtype=float)
    mask = ~np.isnan(y)
    if mask.sum() < 2:
        return np.nan
    return float(np.polyfit(np.arange(3)[mask], y[mask], 1)[0])

trib['trib_slope_1416'] = trib.apply(_slope, axis=1)

# ── 1b. 2018/19 caseload (earliest available — pre-Safety Valve) ─────────────
print("Loading caseload data...")
cas_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/caseload.csv', low_memory=False)

def _load_caseload_year(df_raw, time_period):
    df = df_raw[(df_raw['time_period'] == time_period) &
                (df_raw['geographic_level'] == 'Local authority')].copy()
    # For 2023/24+ data is broken down by age; filter to grand total
    if 'breakdown_topic' in df.columns:
        has_all = df['breakdown_topic'].eq('All EHC plans').any()
        if has_all:
            df = df[df['breakdown_topic'] == 'All EHC plans']
        else:
            # sum over breakdowns (age groups)
            num_cols = ['ehcplans', 'special_independent', 'special_total',
                        'special_la_maintained', 'special_academy_free']
            available = [c for c in num_cols if c in df.columns]
            for c in available:
                df[c] = to_numeric_safe(df[c])
            df = (df.groupby('new_la_code', as_index=False)[available].sum())
            df['la_name'] = (cas_raw[(cas_raw['time_period'] == time_period) &
                                     (cas_raw['geographic_level'] == 'Local authority')]
                             .drop_duplicates('new_la_code')
                             .set_index('new_la_code')['la_name'])
            return df.rename(columns={'new_la_code': 'la_code'})
    for c in ['ehcplans', 'special_independent', 'special_total']:
        if c in df.columns:
            df[c] = to_numeric_safe(df[c])
    return df.rename(columns={'new_la_code': 'la_code'})

cas1819 = _load_caseload_year(cas_raw, 201819)
cas1819['pct_independent_1819'] = (
    to_numeric_safe(cas1819['special_independent']) /
    to_numeric_safe(cas1819['special_total']) * 100
).where(to_numeric_safe(cas1819['special_total']) > 0)
cas1819['ehcplans_1819'] = to_numeric_safe(cas1819['ehcplans'])

# ── 1c. Multi-year caseload for growth rates ─────────────────────────────────
cas_years = {}
for tp, yr in [(201819,2019),(201920,2020),(202021,2021),(202122,2022),(202223,2023)]:
    df = _load_caseload_year(cas_raw, tp)
    df['ehcplans'] = to_numeric_safe(df['ehcplans'])
    cas_years[yr] = df[['la_code','ehcplans']].rename(columns={'ehcplans': f'ehcp_{yr}'})

# 2023/24 and 2024/25 with breakdown_topic filter
for tp, yr in [(202324,2024),(202425,2025)]:
    df = cas_raw[(cas_raw['time_period']==tp) &
                 (cas_raw['geographic_level']=='Local authority') &
                 (cas_raw['breakdown_topic']=='All EHC plans')].copy()
    if len(df) == 0:
        df = cas_raw[(cas_raw['time_period']==tp) &
                     (cas_raw['geographic_level']=='Local authority')].copy()
        df['ehcplans'] = to_numeric_safe(df['ehcplans'])
        df = df.groupby('new_la_code', as_index=False)['ehcplans'].sum()
        df = df.rename(columns={'new_la_code':'la_code'})
    else:
        df['ehcplans'] = to_numeric_safe(df['ehcplans'])
        df = df.rename(columns={'new_la_code':'la_code'})
    cas_years[yr] = df[['la_code','ehcplans']].rename(columns={'ehcplans': f'ehcp_{yr}'})

cas_multi = cas1819[['la_code','la_name','ehcplans_1819']].copy()
for yr, df in cas_years.items():
    cas_multi = cas_multi.merge(df, on='la_code', how='left')

# Log-linear EHCP growth rate (2019–2023, skip 2020/21 COVID year)
def _growth_rate(row):
    years = [2019, 2022, 2023]
    cols  = ['ehcplans_1819', 'ehcp_2022', 'ehcp_2023']
    vals  = [row[c] for c in cols]
    xs, ys = [], []
    for x, v in zip(years, vals):
        if pd.notna(v) and v > 0:
            xs.append(x)
            ys.append(np.log(v))
    if len(xs) < 2:
        return np.nan
    slope, _ = np.polyfit(xs, ys, 1)
    return float(slope)  # log-scale slope ≈ annual growth rate

cas_multi['ehcp_annual_growth'] = cas_multi.apply(_growth_rate, axis=1)

# ── 1d. LA meta: intervention status, IMD, region ────────────────────────────
meta = (summary[['la_code','la_name','intervention_status','imd_average_score','region']]
        .drop_duplicates('la_code'))

# ── 1e. Capacity (maintained special school places per 1,000 pupils) ─────────
cap_cols = ['la_code','maintained_special_capacity_per1000',
            'indep_placements_per1000','pct_special_independent',
            'special_indep_placements','special_total','state_special_capacity']
cap_sub = capacity[[c for c in cap_cols if c in capacity.columns]].copy()

# Back-calculate total_pupils from capacity per-1000 ratios
cap_sub['total_pupils'] = np.where(
    cap_sub['maintained_special_capacity_per1000'] > 0,
    cap_sub['state_special_capacity'] / (cap_sub['maintained_special_capacity_per1000'] / 1000),
    np.nan
)

# ── 1f. Assemble features dataframe ─────────────────────────────────────────
features = (trib
    .merge(cas1819[['la_code','pct_independent_1819','ehcplans_1819']], on='la_code', how='left')
    .merge(meta, on='la_code', how='left')
    .merge(cap_sub, on='la_code', how='left')
)

features['is_sv']  = (features['intervention_status'] == 'Safety Valve').astype(int)
features['is_dbv'] = (features['intervention_status'] == 'DBV').astype(int)
features['is_south_east'] = features['region'].isin(
    ['South East', 'East of England']).astype(int)

# Drop small LAs
small_la_codes = panel[panel['is_small_la']==True]['la_code_static'].unique()
features = features[~features['la_code'].isin(small_la_codes)].copy()

print(f"Feature set: {len(features)} LAs, {features['is_sv'].sum()} Safety Valve, "
      f"{features['is_dbv'].sum()} DBV")
print(f"  trib_2016 non-null: {features['trib_2016'].notna().sum()}")
print(f"  pct_independent_1819 non-null: {features['pct_independent_1819'].notna().sum()}")
print(f"  maintained_capacity_per1000 non-null: {features['maintained_special_capacity_per1000'].notna().sum()}")

# ═══════════════════════════════════════════════════════════════════════════
# PART 2: RETROSPECTIVE MODEL
# ═══════════════════════════════════════════════════════════════════════════
print("\nFitting retrospective prediction model...")

PREDICTORS = ['trib_2016', 'pct_independent_1819', 'imd_average_score']
MODEL_LABELS = {
    'trib_2016': 'Tribunal rate 2016\n(true 2016 data)',
    'pct_independent_1819': '% in independent special schools 2018/19\n(earliest available)',
    'imd_average_score': 'Deprivation score (IMD 2019)',
}

model_data = features[['la_code','la_name','is_sv','is_dbv','intervention_status',
                        'region','is_south_east'] + PREDICTORS].dropna().copy()

print(f"  Model sample: {len(model_data)} LAs, {model_data['is_sv'].sum()} SV, "
      f"{model_data['is_dbv'].sum()} DBV")

# Standardise predictors
for p in PREDICTORS:
    model_data[f'{p}_z'] = (model_data[p] - model_data[p].mean()) / model_data[p].std()

X_cols = [f'{p}_z' for p in PREDICTORS]
X = sm.add_constant(model_data[X_cols])
y = model_data['is_sv'].values

# In-sample fit
logit_model = sm.Logit(y, X).fit(disp=False)
model_data['pred_prob'] = logit_model.predict(X)

in_sample_auc = roc_auc_manual(y, model_data['pred_prob'].values)
print(f"  In-sample AUC: {in_sample_auc:.3f}")
print(logit_model.summary2().tables[1])

# Leave-one-out cross-validation
loo_probs = np.empty(len(model_data))
for i in range(len(model_data)):
    mask = np.ones(len(model_data), dtype=bool)
    mask[i] = False
    X_tr = X.values[mask]
    y_tr = y[mask]
    X_te = X.values[i:i+1]
    try:
        m = sm.Logit(y_tr, X_tr).fit(disp=False, maxiter=200)
        loo_probs[i] = m.predict(X_te)[0]
    except Exception:
        loo_probs[i] = np.nan

model_data['loo_prob'] = loo_probs
valid_loo = ~np.isnan(loo_probs)
loo_auc = roc_auc_manual(y[valid_loo], loo_probs[valid_loo])
print(f"  LOO-CV AUC:   {loo_auc:.3f}")

# ── Figure 14: ROC curves ────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Left: ROC curve
fpr_is, tpr_is = roc_curve_manual(y, model_data['pred_prob'].values)
fpr_loo, tpr_loo = roc_curve_manual(y[valid_loo], loo_probs[valid_loo])

ax = axes[0]
ax.plot(fpr_is,  tpr_is,  color='steelblue', lw=2,
        label=f'In-sample (AUC = {in_sample_auc:.2f})')
ax.plot(fpr_loo, tpr_loo, color='darkorange', lw=2, linestyle='--',
        label=f'LOO cross-validation (AUC = {loo_auc:.2f})')
ax.plot([0,1],[0,1], 'k--', lw=1, alpha=0.4, label='Random (AUC = 0.50)')
ax.fill_between(fpr_loo, tpr_loo, alpha=0.08, color='darkorange')
ax.set_xlabel('False Positive Rate', fontsize=11)
ax.set_ylabel('True Positive Rate', fontsize=11)
ax.set_title('Predicting Safety Valve status\nfrom 2016-era data', fontsize=12, fontweight='bold')
ax.legend(fontsize=9)
ax.set_xlim(0,1); ax.set_ylim(0,1)
ax.grid(True, alpha=0.3)

# Right: coefficient plot
coef_df = pd.DataFrame({
    'label': [MODEL_LABELS[p] for p in PREDICTORS],
    'coef':  logit_model.params[1:].values,
    'se':    logit_model.bse[1:].values,
})
colors_c = ['#d62728' if c > 0 else '#1f77b4' for c in coef_df['coef']]
ax2 = axes[1]
ax2.barh(coef_df['label'], coef_df['coef'], xerr=1.96*coef_df['se'],
         color=colors_c, alpha=0.75, capsize=4)
ax2.axvline(0, color='black', lw=1)
ax2.set_xlabel('Log-odds coefficient (standardised)', fontsize=11)
ax2.set_title('Model coefficients\n(standardised predictors)', fontsize=12, fontweight='bold')
ax2.grid(True, axis='x', alpha=0.3)

plt.tight_layout()
fig.savefig(FIG_DIR / '14b_retrospective_roc.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 14b")

# ── Figure 15: 2016 early warning list ──────────────────────────────────────
ranked = model_data.sort_values('loo_prob', ascending=False).reset_index(drop=True)
ranked['rank'] = ranked.index + 1
# Show top 50 for context
top = ranked.head(50).copy()

# Shading: how many of top N are SV?
top_30_precision = top.head(30)['is_sv'].mean()
print(f"\n  Precision@30 (LOO): {top_30_precision:.1%} of top-30 are Safety Valve")
print(f"  Safety Valve recall in top 30: "
      f"{top.head(30)['is_sv'].sum()}/{model_data['is_sv'].sum()}")

fig, ax = plt.subplots(figsize=(10, 14))

y_pos = np.arange(len(top))
bar_colors = [COLORS.get(s, '#888888') for s in top['intervention_status'].fillna('None')]

bars = ax.barh(y_pos, top['loo_prob'], color=bar_colors, alpha=0.8, height=0.7)

# Labels
for i, row in top.iterrows():
    label = row['la_name'] if pd.notna(row['la_name']) else row['la_code']
    ax.text(row['loo_prob'] + 0.005, top.index.get_loc(i) if False else list(top.index).index(i),
            label, va='center', fontsize=7.5)

# Threshold line at rank 30 (the number of actual SV LAs approximately)
ax.axhline(29.5, color='black', lw=1.5, linestyle=':', alpha=0.6, label='Top 30 threshold')

# Legend
patches = [mpatches.Patch(color=COLORS['Safety Valve'], label='Safety Valve (actual)'),
           mpatches.Patch(color=COLORS['DBV'],          label='Delivering Better Value (actual)'),
           mpatches.Patch(color=COLORS['None'],         label='No intervention (actual)')]
ax.legend(handles=patches, loc='lower right', fontsize=9)

ax.set_yticks(y_pos)
ax.set_yticklabels([f"#{r}" for r in top['rank']], fontsize=8)
ax.invert_yaxis()
ax.set_xlabel('Predicted probability of Safety Valve status (LOO-CV)', fontsize=11)
ax.set_title(
    f'Early warning: which LAs would a 2016 model have flagged?\n'
    f'Features: tribunal rate (2016), % independent placements (2018/19), deprivation\n'
    f'Top-30 precision: {top_30_precision:.0%} | LOO-CV AUC: {loo_auc:.2f}',
    fontsize=11, fontweight='bold'
)
ax.set_xlim(0, min(1.0, top['loo_prob'].max() * 1.35))
ax.grid(True, axis='x', alpha=0.3)

plt.tight_layout()
fig.savefig(FIG_DIR / '15_early_warning_list.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 15")

# ═══════════════════════════════════════════════════════════════════════════
# PART 3: FORWARD-LOOKING STRESS TEST (2024 → 2030)
# ═══════════════════════════════════════════════════════════════════════════
print("\nBuilding forward-looking stress model...")

COST_PER_PLACE = 80_000  # £80k/year midpoint estimate

# Assemble projection base
proj = (cas_multi[['la_code','la_name','ehcplans_1819','ehcp_annual_growth',
                    'ehcp_2023','ehcp_2024']]
        .merge(cap_sub[['la_code','special_indep_placements','special_total',
                         'pct_special_independent','total_pupils']], on='la_code', how='left')
        .merge(meta[['la_code','intervention_status','region']], on='la_code', how='left')
        .dropna(subset=['ehcp_annual_growth','special_indep_placements',
                        'pct_special_independent','total_pupils'])
)
proj = proj[~proj['la_code'].isin(small_la_codes)].copy()

print(f"  Projection sample: {len(proj)} LAs")

# Current (2024) independent placement count and cost
proj['indep_placements_2024'] = proj['special_indep_placements'].clip(lower=0)
proj['annual_cost_2024_m'] = proj['indep_placements_2024'] * COST_PER_PLACE / 1e6

# Cap unrealistic growth rates at 10%/year (some LAs have COVID artefacts)
proj['growth_capped'] = proj['ehcp_annual_growth'].clip(lower=-0.05, upper=0.10)

# Project EHCP count to 2030 (6 years)
HORIZON = 6
proj['ehcp_2030'] = proj['ehcp_2024'].fillna(proj['ehcp_2023']) * np.exp(proj['growth_capped'] * HORIZON)

# Rate: independent special placements per total EHCP (not % within special sector)
# Using ehcp_2024 as base; fall back to ehcp_2023 where needed
proj['ehcp_base'] = proj['ehcp_2024'].fillna(proj['ehcp_2023'])
proj['indep_per_ehcp'] = (proj['special_indep_placements'] /
                          proj['ehcp_base'].replace(0, np.nan))

# Assume this rate stays constant (upper-bound scenario — SV agreements aim to reduce it)
proj['indep_placements_2030'] = proj['ehcp_2030'] * proj['indep_per_ehcp']
proj['annual_cost_2030_m'] = proj['indep_placements_2030'] * COST_PER_PLACE / 1e6
proj['cost_increase_m'] = proj['annual_cost_2030_m'] - proj['annual_cost_2024_m']
proj['cost_increase_per_pupil'] = (proj['cost_increase_m'] * 1e6) / proj['total_pupils']

# ── Figure 16: Forward-looking scatter ───────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(15, 7))

for ax, x_col, x_label, title_suffix in [
    (axes[0], 'annual_cost_2024_m', 'Current annual cost (£m, 2024)',
     'Current burden vs projected growth'),
    (axes[1], 'cost_increase_per_pupil', 'Projected cost increase per pupil (£, 2024→2030)',
     'Cost increase per pupil by 2030'),
]:
    for status, grp in proj.groupby('intervention_status', dropna=False):
        status_label = status if pd.notna(status) else 'None'
        if status_label not in COLORS:
            continue
        ax.scatter(grp[x_col], grp['annual_cost_2030_m'],
                   color=COLORS[status_label], alpha=0.65,
                   s=60 if status_label == 'Safety Valve' else 35,
                   zorder=3 if status_label == 'Safety Valve' else 2,
                   label=status_label)

    # Annotate top emerging non-SV LAs by projected cost
    emerging = (proj[proj['intervention_status'].isin(['None', np.nan]) |
                     proj['intervention_status'].isna()]
                .nlargest(8, 'annual_cost_2030_m'))
    for _, row in emerging.iterrows():
        ax.annotate(row['la_name'], (row[x_col], row['annual_cost_2030_m']),
                    fontsize=7, xytext=(4, 2), textcoords='offset points', color='#1f77b4', alpha=0.8)

    ax.set_xlabel(x_label, fontsize=10)
    ax.set_ylabel('Projected annual independent placement cost 2030 (£m)', fontsize=10)
    ax.set_title(title_suffix, fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

fig.suptitle(
    'Forward-looking stress test: projected independent placement costs 2030\n'
    f'Assumption: current % in independent schools constant; growth rate capped at 10%/yr\n'
    f'Cost per independent placement: £{COST_PER_PLACE:,}/yr',
    fontsize=11, fontweight='bold', y=1.02
)
plt.tight_layout()
fig.savefig(FIG_DIR / '16_forward_looking_2030.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 16")

# ── Summary table: emerging at-risk LAs ─────────────────────────────────────
at_risk = (proj[['la_code','la_name','region','intervention_status',
                  'ehcp_annual_growth','annual_cost_2024_m','annual_cost_2030_m',
                  'cost_increase_m','cost_increase_per_pupil']]
           .sort_values('annual_cost_2030_m', ascending=False)
           .head(40))

at_risk.to_csv(TABLE_DIR / 'forward_looking_2030.csv', index=False, float_format='%.2f')

# ── Save prediction features ─────────────────────────────────────────────────
save_cols = ['la_code','la_name','region','intervention_status',
             'trib_2016','trib_slope_1416','pct_independent_1819',
             'imd_average_score','maintained_special_capacity_per1000','is_sv']
features[save_cols].to_csv(TABLE_DIR / 'prediction_features_2016.csv', index=False, float_format='%.3f')

# ── Print top emerging LAs ───────────────────────────────────────────────────
print("\nTop 15 highest projected cost 2030 (by intervention status):")
print(proj[['la_name','intervention_status','annual_cost_2024_m',
            'annual_cost_2030_m','cost_increase_m','ehcp_annual_growth']]
      .sort_values('annual_cost_2030_m', ascending=False)
      .head(15)
      .to_string(index=False, float_format=lambda x: f'{x:.1f}'))

print("\nTop 10 currently-unaffected LAs by projected 2030 cost:")
none_las = proj[proj['intervention_status'].isna() | (proj['intervention_status']=='None')]
print(none_las[['la_name','annual_cost_2024_m','annual_cost_2030_m',
                 'cost_increase_m','ehcp_annual_growth']]
      .sort_values('annual_cost_2030_m', ascending=False)
      .head(10)
      .to_string(index=False, float_format=lambda x: f'{x:.1f}'))

print("\nDone. Figures 14-16 saved to outputs/figures/")
