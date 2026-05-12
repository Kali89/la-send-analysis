#!/usr/bin/env python3.12
"""
spend_model.py
Population-weighted school access distances + "should spend" regression model.

Section 1:  Download and cache LSOA 2021 population-weighted centroids
Section 2:  Compute per-LSOA distance to nearest maintained special school
            by primary SEN type, aggregate to LA level
Section 3:  Extract S251 line 1.2.3 (independent placement top-up) per LA/year
Section 4:  Load SEN need-type shares (% ASD, % SEMH per LA)
Section 5:  Merge predictors and build OLS regression for spend per EHCP
Section 6:  Figures and residuals analysis

Outputs:
  data/raw/lsoa_centroids_2021.csv        — cached LSOA PWC download
  outputs/tables/la_lsoa_distances.csv    — LA-level mean LSOA distances
  outputs/tables/la_spend_model.csv       — full merged dataset for model
  outputs/tables/spend_model_results.txt  — regression summary
  outputs/figures/26_lsoa_distance_map.png
  outputs/figures/27_spend_model_residuals.png
  outputs/figures/28_actual_vs_predicted.png
"""

import os, time, json, urllib.request
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.spatial import cKDTree
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings('ignore')

DATA_DIR  = 'data/raw'
OUT_FIG   = 'outputs/figures'
OUT_TAB   = 'outputs/tables'

KEY_SEN    = ['ASD', 'SEMH', 'SLD', 'MLD', 'SLCN']
EN_REGIONS = {
    'South East', 'North West', 'London', 'West Midlands',
    'Yorkshire and the Humber', 'South West', 'East of England',
    'East Midlands', 'North East',
}
STATUS_PAL = {
    'Safety Valve':           '#d73027',
    'Delivering Better Value':'#fc8d59',
    'No intervention':        '#4575b4',
}

# ── Section 1: Download LSOA population-weighted centroids ────────────────────

CENTROID_CACHE = f'{DATA_DIR}/lsoa_centroids_2021.csv'

def _paginate_arcgis(base_url, fields, total, page_size=2000, with_geometry=False):
    """Paginate an ArcGIS FeatureServer, return list of attribute dicts.

    Steps by actual records returned — handles servers with maxRecordCount < page_size.
    """
    rows = []
    offset = 0
    fields_str = ','.join(fields)
    while offset < total:
        geo_params = "&returnGeometry=true&outSR=27700" if with_geometry else "&returnGeometry=false"
        url = (f"{base_url}/query?where=1%3D1"
               f"&outFields={fields_str}&resultOffset={offset}"
               f"&resultRecordCount={page_size}{geo_params}&f=json")
        req = urllib.request.Request(url, headers={'User-Agent': 'Python'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        batch = data.get('features', [])
        if not batch:
            break
        for feat in batch:
            row = feat['attributes'].copy()
            if with_geometry and feat.get('geometry'):
                row['easting']  = feat['geometry']['x']
                row['northing'] = feat['geometry']['y']
            rows.append(row)
        offset += len(batch)  # advance by actual records, not requested page_size
        print(f"  downloaded {len(rows):,} / {total:,}", end='\r')
        time.sleep(0.05)
    print()
    return rows

def _get_count(base_url):
    r = urllib.request.urlopen(
        f"{base_url}/query?where=1%3D1&returnCountOnly=true&f=json", timeout=15)
    return json.loads(r.read()).get('count', 0)

lsoa = None
if os.path.exists(CENTROID_CACHE):
    lsoa_tmp = pd.read_csv(CENTROID_CACHE)
    # Validate cache has upper-tier county council codes (E10xxxxx)
    if lsoa_tmp['la_code'].str.startswith('E10', na=False).sum() > 0:
        print(f"Loading cached LSOA centroids from {CENTROID_CACHE}…")
        lsoa = lsoa_tmp
    else:
        print("  Cache has lower-tier codes only — re-downloading with upper-tier lookup…")
        os.remove(CENTROID_CACHE)

if lsoa is None:
    print("Downloading LSOA 2021 population-weighted centroids…")
    CENT_BASE = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest"
                 "/services/LSOA_PopCentroids_EW_2021_V4/FeatureServer/0")
    LKP_BASE  = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest"
                 "/services/LSOA21_UTLA22_EW_LU_v2/FeatureServer/0")

    n_cent = _get_count(CENT_BASE)
    n_lkp  = _get_count(LKP_BASE)
    print(f"  centroids: {n_cent:,}  |  UTLA lookup: {n_lkp:,}")

    print("  Fetching centroids (with geometry)…")
    cent_rows = _paginate_arcgis(CENT_BASE, ['LSOA21CD'], n_cent, with_geometry=True)
    cent_df = pd.DataFrame(cent_rows)

    print("  Fetching LSOA→UTLA lookup (attributes only)…")
    lkp_rows = _paginate_arcgis(LKP_BASE, ['LSOA21CD','UTLA22CD','UTLA22NM'], n_lkp, with_geometry=False)
    lkp_df = pd.DataFrame([{'LSOA21CD': r['LSOA21CD'],
                             'la_code':  r['UTLA22CD'],
                             'la_name':  r['UTLA22NM']}
                            for r in lkp_rows])

    lsoa = cent_df.merge(lkp_df, on='LSOA21CD', how='left')
    # Filter England only (codes start with E)
    lsoa = lsoa[lsoa['la_code'].str.startswith('E', na=False)].copy()
    lsoa.to_csv(CENTROID_CACHE, index=False)
    print(f"  Saved {len(lsoa):,} England LSOAs to {CENTROID_CACHE}")

print(f"  LSOA records: {len(lsoa):,}  |  LAs: {lsoa['la_code'].nunique()}")

# ── Section 2: Load special schools and compute per-LSOA distances ────────────
print("\nLoading special schools…")
gias = pd.read_csv(f'{DATA_DIR}/edubasealldata20260512.csv',
                   encoding='latin-1', low_memory=False)
gias.columns = [c.lower().strip() for c in gias.columns]
gias['easting']  = pd.to_numeric(gias['easting'],  errors='coerce')
gias['northing'] = pd.to_numeric(gias['northing'], errors='coerce')
gias['schoolcapacity'] = pd.to_numeric(gias['schoolcapacity'], errors='coerce')

STATE_TYPES = [
    'Community special school', 'Academy special converter',
    'Academy special sponsor led', 'Foundation special school',
    'Free schools special', 'Non-maintained special school',
]
INDEP_TYPES = ['Other independent special school']

open_eng = gias[
    gias['gor (name)'].isin(EN_REGIONS) &
    gias['establishmentstatus (name)'].isin(['Open', 'Open, but proposed to close']) &
    gias['easting'].notna() & gias['northing'].notna()
].copy()

special = open_eng[open_eng['typeofestablishment (name)'].isin(STATE_TYPES + INDEP_TYPES)].copy()
special['is_independent'] = special['typeofestablishment (name)'].isin(INDEP_TYPES)
special['sen1_raw'] = special['sen1 (name)'].fillna('')
special['sen_primary'] = (
    special['sen1_raw'].str.split(' - ').str[0].str.strip()
    .where(special['sen1_raw'].str.split(' - ').str[0].str.strip().isin(KEY_SEN), 'Other')
)

state_sp = special[~special['is_independent']].copy()
indep_sp = special[special['is_independent']].copy()
print(f"  State: {len(state_sp):,}  |  Independent: {len(indep_sp):,}")

# Per-SEN KD-trees for state schools
state_trees = {}
for sen in KEY_SEN:
    sub = state_sp[state_sp['sen_primary'] == sen]
    if len(sub) > 0:
        state_trees[sen] = (cKDTree(sub[['easting','northing']].values), sub)
    print(f"  State {sen} schools: {len(sub)}")

# For each LSOA, distance to nearest state school of each type
print("\nComputing LSOA distances (this may take 30–60 s)…")
lsoa_xy = lsoa[['easting','northing']].values

dist_cols = {}
for sen, (tree, _sub) in state_trees.items():
    dists, _ = tree.query(lsoa_xy)          # vectorised — fast
    dist_cols[f'dist_state_{sen}_km'] = dists / 1000

# Also: distance to nearest INDEP school by type
for sen in ['ASD', 'SEMH']:
    sub = indep_sp[indep_sp['sen_primary'] == sen]
    if len(sub) > 0:
        t = cKDTree(sub[['easting','northing']].values)
        dists, _ = t.query(lsoa_xy)
        dist_cols[f'dist_indep_{sen}_km'] = dists / 1000

for col, vals in dist_cols.items():
    lsoa[col] = vals

print("  Done.")

# ── Section 3: Aggregate to LA level ─────────────────────────────────────────
print("\nAggregating to LA level…")
dist_agg_cols = [c for c in lsoa.columns if c.startswith('dist_')]

# Mean (central tendency of access)
la_mean = (lsoa.groupby('la_code')[dist_agg_cols].mean().reset_index()
           .rename(columns={c: c + '_lsoa_mean' for c in dist_agg_cols}))

# SD (within-LA access heterogeneity — are some LSOAs much farther than others?)
la_sd = (lsoa.groupby('la_code')[dist_agg_cols].std().reset_index()
         .rename(columns={c: c + '_lsoa_sd' for c in dist_agg_cols}))

# Max (worst-case access / SEND desert indicator)
la_max = (lsoa.groupby('la_code')[dist_agg_cols].max().reset_index()
          .rename(columns={c: c + '_lsoa_max' for c in dist_agg_cols}))

# Geographic population dispersal: RMS distance of LSOAs from LA centroid
# High values = sprawling council; low values = compact / urban
def rms_from_centroid(g):
    e, n = g['easting'].values, g['northing'].values
    return np.sqrt(np.mean((e - e.mean())**2 + (n - n.mean())**2)) / 1000

pop_spread = (lsoa.groupby('la_code')
              .apply(rms_from_centroid)
              .reset_index(name='pop_spread_km'))

la_dist = (la_mean
           .merge(la_sd,      on='la_code')
           .merge(la_max,     on='la_code')
           .merge(pop_spread, on='la_code'))

la_dist.to_csv(f'{OUT_TAB}/la_lsoa_distances.csv', index=False)
print(f"  Saved {OUT_TAB}/la_lsoa_distances.csv  ({len(la_dist)} LAs, "
      f"{len(la_dist.columns)-1} distance features)")

# ── Section 4: Extract S251 line 1.2.3 ───────────────────────────────────────
print("\nLoading S251 expenditure data…")
s251 = pd.read_csv(f'{DATA_DIR}/s251_2025/data/s251_alleducation_la_regional_national.csv',
                   encoding='latin-1', low_memory=False)
s251.columns = [c.lower().strip() for c in s251.columns]
s251_la = s251[s251['geographic_level'] == 'Local authority'].copy()
s251_la['la_code'] = s251_la['new_la_code'].fillna(s251_la['old_la_code'].astype(str))
s251_la['gross_expenditure'] = pd.to_numeric(s251_la['gross_expenditure'], errors='coerce')

# Map S251 academic year to calendar year (matching SEN2 timeliness convention)
S251_TO_CAL = {
    201516:2016, 201617:2017, 201718:2018, 201819:2019, 201920:2020,
    202021:2021, 202122:2022, 202223:2023, 202324:2024, 202425:2025,
}
s251_la['cal_year'] = s251_la['time_period'].map(S251_TO_CAL)

def extract_line(pattern, label):
    rows = s251_la[s251_la['category_of_expenditure'].str.contains(pattern, na=False, regex=False)]
    return (rows.groupby(['la_code', 'cal_year'])['gross_expenditure']
            .sum().reset_index().rename(columns={'gross_expenditure': label}))

spend_lines = {
    '1.2.1':   'topup_maintained',
    '1.2.2':   'topup_academies',
    '1.2.3':   'topup_independent',
    '1.2.13':  'therapies',
    '2.1.1':   'ep_service',
    '2.1.2':   'sen_admin',
    '2.1.4':   'sen_transport',
}

spend = None
for pattern, label in spend_lines.items():
    tmp = extract_line(pattern, label)
    spend = tmp if spend is None else spend.merge(tmp, on=['la_code','cal_year'], how='outer')

# Total high-needs placement spend = 1.2.1 + 1.2.2 + 1.2.3
for col in ['topup_maintained','topup_academies','topup_independent']:
    spend[col] = spend[col].fillna(0)
spend['topup_total'] = spend['topup_maintained'] + spend['topup_academies'] + spend['topup_independent']

print(f"  S251 spend rows: {len(spend)}  |  years: {sorted(spend['cal_year'].dropna().unique())}")
# Sanity check: top independent spenders 2024
s24 = spend[spend['cal_year']==2024].nlargest(5,'topup_independent')
print("  Top independent spenders 2024:")
for _, row in s24.iterrows():
    meta_tmp = pd.read_csv(f'{OUT_TAB}/la_summary_2024_extended.csv')
    meta_tmp.columns = [c.lower().replace(' ','_') for c in meta_tmp.columns]
    name = meta_tmp[meta_tmp['la_code']==row['la_code']]['la_name'].values
    print(f"    {name[0] if len(name) else row['la_code']}: £{row['topup_independent']/1e6:.1f}m")
    break  # just first one to avoid re-loading meta in loop

# ── Section 5: Load SEN need-type shares ──────────────────────────────────────
print("\nLoading SEN need-type shares…")
needs = pd.read_csv(f'{DATA_DIR}/sen2_2025/data/sen_needs_all_plans.csv')
needs.columns = [c.lower().strip() for c in needs.columns]

# Already wide format with _pc columns; filter to LA level, 2024, all plans total
la_needs = needs[
    (needs['geographic_level'] == 'Local authority') &
    (needs['breakdown_topic'] == 'All EHC plans') &
    (needs['breakdown'] == 'All EHC plans')
].copy()
la_needs['la_code'] = la_needs['new_la_code'].fillna(la_needs['old_la_code'].astype(str))

# Rename percentage columns
need_pct = la_needs[['la_code', 'asd_pc', 'semh_pc', 'sld_pc', 'mld_pc', 'slcn_pc']].copy()
need_pct.columns = ['la_code', 'pct_asd', 'pct_semh', 'pct_sld', 'pct_mld', 'pct_slcn']
for c in ['pct_asd','pct_semh','pct_sld','pct_mld','pct_slcn']:
    need_pct[c] = pd.to_numeric(need_pct[c], errors='coerce')
print(f"  Need shares for {len(need_pct)} LAs")

# ── Section 6: Load meta and merge all predictors ─────────────────────────────
print("\nMerging data…")
meta = pd.read_csv(f'{OUT_TAB}/la_summary_2024_extended.csv')
meta.columns = [c.lower().replace(' ','_') for c in meta.columns]
meta['intervention_status'] = meta['intervention_status'].fillna('No intervention')

cap = pd.read_csv(f'{OUT_TAB}/la_capacity_2024.csv')
cap.columns = [c.lower().replace(' ','_') for c in cap.columns]

pupils_raw = pd.read_csv(f'{DATA_DIR}/sen_pupils_2025/data/sen_phase_type_.csv')
pupils_raw['total_pupils'] = pd.to_numeric(pupils_raw['total_pupils'], errors='coerce')
total_pupils = (
    pupils_raw[pupils_raw['geographic_level'] == 'Local authority']
    .groupby('new_la_code', as_index=False)['total_pupils'].sum()
    .rename(columns={'new_la_code': 'la_code'})
)

# Spend for 2024
spend24 = spend[spend['cal_year'] == 2024].copy()

model_df = (
    meta[['la_code','la_name','region','intervention_status',
          'n_ehcp_active','imd_average_score']]
    .merge(spend24[['la_code','topup_independent','topup_total',
                    'ep_service','sen_admin','sen_transport']], on='la_code', how='left')
    .merge(cap[['la_code','indep_placements_per1000','pct_special_independent']], on='la_code', how='left')
    .merge(la_dist, on='la_code', how='left')
    .merge(need_pct, on='la_code', how='left')
    .merge(total_pupils, on='la_code', how='left')
)

# Per-EHCP spend outcomes
model_df['indep_per_ehcp']  = model_df['topup_independent'] / model_df['n_ehcp_active'].replace(0, np.nan)
model_df['total_per_ehcp']  = model_df['topup_total']       / model_df['n_ehcp_active'].replace(0, np.nan)
model_df['indep_per_pupil'] = model_df['topup_independent'] / model_df['total_pupils'].replace(0, np.nan)

# Prevalence rate
model_df['ehcp_rate_pct'] = model_df['n_ehcp_active'] / model_df['total_pupils'].replace(0, np.nan) * 100

print(f"  Model dataset: {len(model_df)} LAs")
print(f"  Non-null indep_per_ehcp: {model_df['indep_per_ehcp'].notna().sum()}")
model_df.to_csv(f'{OUT_TAB}/la_spend_model.csv', index=False)

# ── Section 7: OLS regression ─────────────────────────────────────────────────
print("\nFitting OLS regression…")

# Use log outcome to handle skew; add 1 to avoid log(0) issues
model_df['log_indep_per_ehcp'] = np.log(model_df['indep_per_ehcp'].clip(lower=1))

# Select complete cases for key predictors
PREDICTORS = [
    'dist_state_ASD_km_lsoa_mean',   # mean access to ASD provision
    'dist_state_SEMH_km_lsoa_mean',  # mean access to SEMH provision
    'dist_state_ASD_km_lsoa_sd',     # within-LA heterogeneity of ASD access
    'dist_state_SEMH_km_lsoa_sd',    # within-LA heterogeneity of SEMH access
    'pop_spread_km',                  # geographic dispersal of population
    'pct_asd', 'pct_semh',
    'imd_average_score',
    'ehcp_rate_pct',
]
OUTCOME = 'log_indep_per_ehcp'

reg_df = model_df.dropna(subset=[OUTCOME] + PREDICTORS).copy()
print(f"  Complete cases for regression: {len(reg_df)}")

# Add region dummies
reg_df['region_clean'] = reg_df['region'].str.replace(' ', '_').str.replace('and_','').str.lower()
region_dummies = pd.get_dummies(reg_df['region_clean'], drop_first=True, prefix='r')

X = pd.concat([
    reg_df[PREDICTORS].reset_index(drop=True),
    region_dummies.reset_index(drop=True)
], axis=1).astype(float)
X = sm.add_constant(X)
y = reg_df[OUTCOME].reset_index(drop=True)

model = sm.OLS(y, X).fit(cov_type='HC3')

# Save results
results_path = f'{OUT_TAB}/spend_model_results.txt'
with open(results_path, 'w') as f:
    f.write("Dependent variable: log(independent placement top-up per EHCP)\n")
    f.write("S251 line 1.2.3, 2023/24\n\n")
    f.write(str(model.summary()))
print(f"  Saved {results_path}")
print(f"  R²={model.rsquared:.3f}  adj-R²={model.rsquared_adj:.3f}  n={int(model.nobs)}")
print()
print("  Key coefficients:")
key_vars = ['dist_state_ASD_km_lsoa_mean', 'dist_state_SEMH_km_lsoa_mean',
            'dist_state_ASD_km_lsoa_sd', 'dist_state_SEMH_km_lsoa_sd',
            'pop_spread_km', 'pct_asd', 'pct_semh',
            'imd_average_score', 'ehcp_rate_pct']
for v in key_vars:
    if v in model.params.index:
        c, p = model.params[v], model.pvalues[v]
        sig = '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else ''
        print(f"    {v:<45s}  β={c:+.4f}  p={p:.4f} {sig}")

# ── Residuals and predictions ──────────────────────────────────────────────────
reg_df = reg_df.copy()
reg_df['predicted_log']  = model.fittedvalues.values
reg_df['residual_log']   = model.resid.values
reg_df['predicted_indep_per_ehcp'] = np.exp(reg_df['predicted_log'])
reg_df['actual_indep_per_ehcp']    = np.exp(reg_df[OUTCOME])
reg_df['overspend_ratio'] = reg_df['actual_indep_per_ehcp'] / reg_df['predicted_indep_per_ehcp']

# ── Section 8: Figures ────────────────────────────────────────────────────────
print("\nBuilding figures…")

# ── Fig 26: LSOA-mean ASD distance vs intervention status ─────────────────────
col = 'dist_state_ASD_km_lsoa_mean'
sv_v   = model_df[model_df['intervention_status']=='Safety Valve'][col].dropna()
dbv_v  = model_df[model_df['intervention_status']=='Delivering Better Value'][col].dropna()
none_v = model_df[model_df['intervention_status']=='No intervention'][col].dropna()

fig, axes = plt.subplots(1, 3, figsize=(15, 6))
fig.suptitle('LSOA population-weighted distance to nearest maintained special school\n'
             '(mean across all LSOAs in LA)', fontsize=13, fontweight='bold')

sen_pairs = [
    ('ASD',  'dist_state_ASD_km_lsoa_mean'),
    ('SEMH', 'dist_state_SEMH_km_lsoa_mean'),
    ('SLCN', 'dist_state_SLCN_km_lsoa_mean'),
]
data_sets  = [sv_v, dbv_v, none_v]
palette    = ['#d73027', '#fc8d59', '#4575b4']
xlabels    = ['Safety\nValve', 'Delivering\nBetter Value', 'No\nintervention']

for ax, (sen, scol) in zip(axes, sen_pairs):
    vals = [model_df[model_df['intervention_status']==s][scol].dropna().values
            for s in ['Safety Valve','Delivering Better Value','No intervention']]
    bp = ax.boxplot(vals, patch_artist=True, notch=False,
                    medianprops=dict(color='black', linewidth=2))
    for patch, c in zip(bp['boxes'], palette):
        patch.set_facecolor(c); patch.set_alpha(0.75)
    ax.set_xticks([1,2,3]); ax.set_xticklabels(xlabels, fontsize=9)
    ax.set_title(f'Nearest maintained {sen} school', fontsize=11, fontweight='bold')
    ax.set_ylabel('km' if ax == axes[0] else '')
    ax.yaxis.grid(True, alpha=0.4)
    sv_v2  = vals[0]; none_v2 = vals[2]
    if len(sv_v2)>3 and len(none_v2)>3:
        _, p = stats.mannwhitneyu(sv_v2, none_v2, alternative='two-sided')
        ax.set_xlabel(f'SV vs None: p={p:.4f}', fontsize=9)

plt.tight_layout()
plt.savefig(f'{OUT_FIG}/26_lsoa_distance_by_status.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 26_lsoa_distance_by_status.png")

# ── Fig 27: Actual vs predicted spend, coloured by status ─────────────────────
fig, ax = plt.subplots(figsize=(10, 8))
for status, color in STATUS_PAL.items():
    sub = reg_df[reg_df['intervention_status'] == status]
    ax.scatter(sub['predicted_indep_per_ehcp'], sub['actual_indep_per_ehcp'],
               c=color, label=status, alpha=0.8, s=60, zorder=3)

lim_max = reg_df[['predicted_indep_per_ehcp','actual_indep_per_ehcp']].max().max() * 1.05
ax.plot([0, lim_max], [0, lim_max], 'k--', lw=1, alpha=0.5, label='Perfect prediction')
ax.set_xlabel('Predicted indep. top-up per EHCP (£)', fontsize=12)
ax.set_ylabel('Actual indep. top-up per EHCP (£)', fontsize=12)
ax.set_title('Actual vs predicted independent placement spend per EHCP\n'
             'S251 line 1.2.3, 2023/24', fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.yaxis.grid(True, alpha=0.3); ax.xaxis.grid(True, alpha=0.3)

# Annotate biggest outliers
outliers = reg_df.nlargest(5, 'overspend_ratio')
for _, row in outliers.iterrows():
    ax.annotate(row['la_name'],
                xy=(row['predicted_indep_per_ehcp'], row['actual_indep_per_ehcp']),
                xytext=(8, 4), textcoords='offset points', fontsize=7, color='#555')

plt.tight_layout()
plt.savefig(f'{OUT_FIG}/27_actual_vs_predicted_spend.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 27_actual_vs_predicted_spend.png")

# ── Fig 28: Residuals by LA, coloured by status ────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7))
for status, color in STATUS_PAL.items():
    sub = reg_df[reg_df['intervention_status'] == status].sort_values('residual_log')
    ax.scatter(range(len(sub)), sub['residual_log'],
               c=color, label=f"{status} (n={len(sub)})", alpha=0.75, s=50)

ax.axhline(0, color='black', lw=1, ls='--')
ax.set_xlabel('Local authorities (ranked by residual within each group)', fontsize=11)
ax.set_ylabel('Residual (log scale)\n+ve = spending more than predicted', fontsize=11)
ax.set_title('Residuals from "should spend" model\nS251 line 1.2.3 per EHCP, 2023/24',
             fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.yaxis.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT_FIG}/28_spend_residuals.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 28_spend_residuals.png")

# ── Summary: who's over/under spending? ───────────────────────────────────────
print("\n=== Model summary ===")
print(f"R² = {model.rsquared:.3f}  (explaining {model.rsquared*100:.0f}% of variance in log indep spend/EHCP)")
print()
print("Median overspend ratio by status (actual / predicted):")
for status in ['Safety Valve','Delivering Better Value','No intervention']:
    sub = reg_df[reg_df['intervention_status']==status]['overspend_ratio']
    print(f"  {status}: {sub.median():.2f}x  (n={len(sub)})")

print()
print("Biggest over-spenders (actual >> predicted):")
top_over = reg_df.nlargest(8,'overspend_ratio')[['la_name','intervention_status',
    'actual_indep_per_ehcp','predicted_indep_per_ehcp','overspend_ratio']]
for _, r in top_over.iterrows():
    print(f"  {r['la_name']:<25s} ({r['intervention_status']:<26s}): "
          f"actual £{r['actual_indep_per_ehcp']:,.0f}  predicted £{r['predicted_indep_per_ehcp']:,.0f}  "
          f"ratio {r['overspend_ratio']:.2f}x")

print()
print("Biggest under-spenders (actual << predicted):")
top_under = reg_df.nsmallest(5,'overspend_ratio')[['la_name','intervention_status',
    'actual_indep_per_ehcp','predicted_indep_per_ehcp','overspend_ratio']]
for _, r in top_under.iterrows():
    print(f"  {r['la_name']:<25s} ({r['intervention_status']:<26s}): "
          f"actual £{r['actual_indep_per_ehcp']:,.0f}  predicted £{r['predicted_indep_per_ehcp']:,.0f}  "
          f"ratio {r['overspend_ratio']:.2f}x")

print("\nDone.")
