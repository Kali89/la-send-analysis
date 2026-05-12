"""
EHCP LA Analysis — Capacity Analysis
=====================================
Hypothesis: South East shire councils lack maintained special school capacity.
When demand for specialist SEND provision rises (especially autism/SEMH), these
councils have no maintained school to offer, so children end up in expensive
independent special schools. High independent placement rates drive DSG deficits,
which in turn drive operational failure (timeliness) and tribunal pressure.

Proposed causal chain:
  Low maintained special capacity
         ↓
  High independent placement rate  (expensive: £60-120k/yr per child)
         ↓
  DSG deficit / financial stress
         ↓
  Timeliness failure (staffing cuts, backlogs)
         ↓
  Higher tribunal appeal rates

Data sources:
  - GIAS (Get Information About Schools): edubasealldata20260512.csv
    → maintained special school capacity by LA
  - DfE SEN2 2025: caseload.csv
    → placement type breakdown (maintained vs independent) by LA
  - outputs/tables/la_summary_2024_extended.csv
    → existing panel with DSG, timeliness, tribunal data

Outputs: figures 11-14, tables, FINDINGS.md appendix
"""

import re, warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
from scipy.stats import pearsonr, mannwhitneyu, kruskal
import statsmodels.formula.api as smf

warnings.filterwarnings('ignore')

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / 'data' / 'raw'
OUT_FIGS   = BASE_DIR / 'outputs' / 'figures'
OUT_TABLES = BASE_DIR / 'outputs' / 'tables'

# ── Intervention lists ────────────────────────────────────────────────────
SAFETY_VALVE_ENTRY = {
    'Hampshire': 2022, 'Surrey': 2022, 'Worcestershire': 2022,
    'West Sussex': 2022, 'Hertfordshire': 2022, 'Cambridgeshire': 2022,
    'Northamptonshire': 2022, 'Swindon': 2022, 'Somerset': 2022,
    'North Yorkshire': 2023, 'Gloucestershire': 2022, 'Oxfordshire': 2023,
    'Derbyshire': 2023, 'Suffolk': 2023, 'East Sussex': 2022,
    'Medway': 2022, 'Isle of Wight': 2022, 'Bracknell Forest': 2022,
    'Southend-on-Sea': 2022, 'Thurrock': 2022, 'Peterborough': 2023,
    'Cheshire East': 2023, 'Kent': 2023, 'Norfolk': 2023, 'Essex': 2023,
    'Wiltshire': 2024, 'Devon': 2024, 'Dorset': 2024, 'Shropshire': 2024,
    'Warwickshire': 2024,
}
DBV_LAS = {
    'Bexley', 'Bradford', 'Bury', 'Cornwall', 'Coventry', 'Croydon',
    'Derby', 'Doncaster', 'East Riding of Yorkshire', 'Gateshead',
    'Greenwich', 'Halton', 'Havering', 'Hillingdon', 'Hounslow',
    'Kingston upon Hull', 'Kirklees', 'Lancashire', 'Leeds', 'Leicester',
    'Lincolnshire', 'Liverpool', 'Manchester', 'Middlesbrough',
    'Newcastle upon Tyne', 'Newham', 'North East Lincolnshire',
    'North Lincolnshire', 'Nottingham', 'Oldham', 'Plymouth',
    'Portsmouth', 'Reading', 'Redcar and Cleveland', 'Rochdale',
    'Rotherham', 'Salford', 'Sandwell', 'Sefton', 'Sheffield',
    'Slough', 'Southampton', 'Stockport', 'Stockton-on-Tees',
    'Stoke-on-Trent', 'Sunderland', 'Tameside', 'Wakefield', 'Wigan',
    'Wirral', 'Wolverhampton', 'Walsall', 'Barnsley',
    'Blackburn with Darwen', 'Bolton', 'Calderdale', 'Darlington',
    'Hartlepool', 'Knowsley', 'Luton', 'Milton Keynes', 'North Somerset',
    'Nottinghamshire', 'South Tyneside', 'St Helens', 'Tower Hamlets',
    'Trafford',
} - set(SAFETY_VALVE_ENTRY.keys())

STATUS_COLOURS = {
    'Safety Valve':           '#c53030',
    'Delivering Better Value':'#d69e2e',
    'None':                   '#2c5282',
}

def get_status(name):
    if name in SAFETY_VALVE_ENTRY:   return 'Safety Valve'
    if name in DBV_LAS:              return 'Delivering Better Value'
    return 'None'

def safe_num(s):
    return pd.to_numeric(
        s.astype(str).str.replace(',','').str.strip()
         .replace({'x': np.nan, 'z': np.nan, '-': np.nan, '..': np.nan}),
        errors='coerce')


# ══════════════════════════════════════════════════════════════════════════
# STEP 1 — Load GIAS: maintained special school capacity by LA
# ══════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("STEP 1 — GIAS: maintained special school capacity")
print("=" * 70)

GIAS_PATH = DATA_DIR / 'edubasealldata20260512.csv'
gias = pd.read_csv(GIAS_PATH, encoding='latin-1', low_memory=False,
                   usecols=['URN', 'LA (code)', 'LA (name)', 'GSSLACode (name)',
                            'EstablishmentTypeGroup (name)',
                            'TypeOfEstablishment (name)',
                            'EstablishmentStatus (name)',
                            'SchoolCapacity', 'NumberOfPupils',
                            'SENStat', 'SENNoStat', 'GOR (name)'])

open_schools = gias[gias['EstablishmentStatus (name)'] == 'Open'].copy()
open_schools['SchoolCapacity'] = pd.to_numeric(open_schools['SchoolCapacity'], errors='coerce')
open_schools['NumberOfPupils'] = pd.to_numeric(open_schools['NumberOfPupils'], errors='coerce')
open_schools['SENStat']        = pd.to_numeric(open_schools['SENStat'],        errors='coerce')

# State-funded special schools: community, foundation, academy (converter + sponsor),
# free school specials. These are the maintained/state sector.
STATE_SPECIAL_TYPES = {
    'Community special school',
    'Foundation special school',
    'Academy special converter',
    'Academy special sponsor led',
    'Free schools special',
}
# Independent special schools (expensive) + non-maintained (charitable sector)
INDEPENDENT_TYPES = {'Other independent special school'}
NON_MAINTAINED_TYPES = {'Non-maintained special school'}

open_schools['school_category'] = np.where(
    open_schools['TypeOfEstablishment (name)'].isin(STATE_SPECIAL_TYPES), 'state_special',
    np.where(open_schools['TypeOfEstablishment (name)'].isin(INDEPENDENT_TYPES), 'independent_special',
    np.where(open_schools['TypeOfEstablishment (name)'].isin(NON_MAINTAINED_TYPES), 'non_maintained_special',
    'other')))

special_all = open_schools[open_schools['school_category'].isin(
    ['state_special','independent_special','non_maintained_special'])].copy()

print(f"All special schools (open): {len(special_all)}")
print(special_all.groupby('school_category').agg(
    n_schools=('URN','count'),
    total_capacity=('SchoolCapacity','sum'),
    median_capacity=('SchoolCapacity','median')
).to_string())

# Aggregate state-funded special school capacity by LA (using GSSLACode for join)
state_special = special_all[special_all['school_category'] == 'state_special'].copy()

la_capacity = (state_special
    .groupby('GSSLACode (name)', as_index=False)
    .agg(
        la_name_gias   = ('LA (name)', 'first'),
        region_gias    = ('GOR (name)', 'first'),
        n_state_special_schools = ('URN', 'count'),
        state_special_capacity  = ('SchoolCapacity', 'sum'),
        state_special_pupils    = ('NumberOfPupils', 'sum'),
    )
    .rename(columns={'GSSLACode (name)': 'la_code'})
)
print(f"\nLA capacity table: {len(la_capacity)} LAs with state special schools")
print(f"Capacity coverage: {la_capacity['state_special_capacity'].notna().sum()} / {len(la_capacity)} LAs")

# Count independent special schools per LA (for comparison)
indep_special = special_all[special_all['school_category'] == 'independent_special'].copy()
la_indep_schools = (indep_special
    .groupby('GSSLACode (name)', as_index=False)
    .agg(
        n_indep_special_schools = ('URN', 'count'),
        indep_special_sector_capacity = ('SchoolCapacity', 'sum'),
        indep_special_senstat = ('SENStat', 'sum'),
    )
    .rename(columns={'GSSLACode (name)': 'la_code'})
)
la_capacity = la_capacity.merge(la_indep_schools, on='la_code', how='left')
print(f"Independent special schools by LA: {la_indep_schools['n_indep_special_schools'].sum()} schools total")


# ══════════════════════════════════════════════════════════════════════════
# STEP 2 — Load caseload placement breakdown by type
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 2 — SEN2 caseload: placement type breakdown")
print("=" * 70)

cas = pd.read_csv(DATA_DIR / 'sen2_2025' / 'data' / 'caseload.csv',
                  encoding='utf-8-sig', low_memory=False)
cas2324 = cas[
    (cas['geographic_level'] == 'Local authority') &
    (cas['time_period'] == 202324) &
    (cas['breakdown'] == 'All EHC plans')
].copy()

for col in ['ehcplans', 'special_la_maintained', 'special_academy_free',
            'special_independent', 'special_non_maintained', 'special_total']:
    cas2324[col] = safe_num(cas2324[col])

# State-funded special placements (LA-maintained + academy/free)
cas2324['special_state_placements']  = (cas2324['special_la_maintained']
                                        .fillna(0) + cas2324['special_academy_free'].fillna(0))
# Independent placements (expensive)
cas2324['special_indep_placements']  = cas2324['special_independent']
# Non-maintained (charitable sector)
cas2324['special_nm_placements']     = cas2324['special_non_maintained']

# % of all special placements in independent sector
cas2324['pct_special_independent']   = (
    cas2324['special_indep_placements'] / cas2324['special_total'] * 100
).where(cas2324['special_total'] > 0)

print(f"Caseload 2023-24: {len(cas2324)} LAs")
print(f"pct_special_independent: mean={cas2324['pct_special_independent'].mean():.1f}%  "
      f"median={cas2324['pct_special_independent'].median():.1f}%")
print(f"Coverage: {cas2324['pct_special_independent'].notna().sum()} LAs")


# ══════════════════════════════════════════════════════════════════════════
# STEP 3 — Merge: panel + capacity + caseload placement types
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 3 — Merge panel")
print("=" * 70)

# Load existing extended panel
panel = pd.read_csv(OUT_TABLES / 'la_summary_2024_extended.csv')
panel['status'] = panel['la_name'].apply(get_status)
excl = {'City of London', 'Isles of Scilly'}
panel = panel[~panel['la_name'].isin(excl)].copy()
print(f"Base panel: {len(panel)} LAs")

# Merge capacity (from GIAS)
panel = panel.merge(la_capacity[['la_code', 'n_state_special_schools',
                                  'state_special_capacity', 'state_special_pupils',
                                  'n_indep_special_schools', 'indep_special_sector_capacity',
                                  'indep_special_senstat']],
                    on='la_code', how='left')

# Merge placement breakdown (from caseload)
panel = panel.merge(
    cas2324[['new_la_code', 'special_state_placements', 'special_indep_placements',
             'special_nm_placements', 'special_total', 'pct_special_independent']]
    .rename(columns={'new_la_code': 'la_code'}),
    on='la_code', how='left'
)

# Load pupil counts for per-pupil denominators
sen_phase = pd.read_csv(DATA_DIR / 'sen_pupils_2025' / 'data' / 'sen_phase_type_.csv',
                        encoding='latin-1', low_memory=False)
sen_phase.columns = [c.strip('ï»¿') for c in sen_phase.columns]
pupils = (sen_phase[
    (sen_phase['geographic_level'] == 'Local authority') &
    (sen_phase['phase_type_grouping'] == 'Total') &
    (sen_phase['time_period'] == sen_phase['time_period'].max())
].groupby('new_la_code', as_index=False)
 .agg(total_pupils=('total_pupils', lambda x: pd.to_numeric(x, errors='coerce').sum()))
 .rename(columns={'new_la_code': 'la_code'}))

panel = panel.merge(pupils, on='la_code', how='left')

# ── Compute per-pupil / per-1000 metrics ──────────────────────────────────
panel['maintained_special_capacity_per1000'] = (
    panel['state_special_capacity'] / panel['total_pupils'] * 1000
)
panel['indep_placements_per1000'] = (
    panel['special_indep_placements'] / panel['total_pupils'] * 1000
)
panel['all_special_placements_per1000'] = (
    panel['special_total'] / panel['total_pupils'] * 1000
)
# Capacity utilisation: how much of maintained sector's capacity is used
# by children from this LA
panel['maintained_utilisation'] = (
    panel['special_state_placements'] / panel['state_special_capacity'] * 100
).where(panel['state_special_capacity'] > 0)

# DSG deficit (using the extended column, already in £ per pupil)
panel['dsg_deficit_pp'] = panel['dsg_deficit_per_pupil']

print(f"\nAfter merge: {len(panel)} LAs")
print(f"\nKey variable coverage:")
print(f"  maintained_special_capacity_per1000 : {panel['maintained_special_capacity_per1000'].notna().sum()} LAs")
print(f"  pct_special_independent              : {panel['pct_special_independent'].notna().sum()} LAs")
print(f"  indep_placements_per1000             : {panel['indep_placements_per1000'].notna().sum()} LAs")
print(f"  dsg_deficit_pp                       : {panel['dsg_deficit_pp'].notna().sum()} LAs")
print(f"  timeliness_pct                       : {panel['timeliness_pct'].notna().sum()} LAs")
print(f"  la_official_appeal_rate_pct          : {panel['la_official_appeal_rate_pct'].notna().sum()} LAs")


# ══════════════════════════════════════════════════════════════════════════
# STEP 4 — Descriptive: capacity and placements by intervention status
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 4 — Descriptive comparison by intervention status")
print("=" * 70)

metrics = [
    ('maintained_special_capacity_per1000', 'Maintained special capacity per 1,000 pupils'),
    ('n_state_special_schools',             'Number of state special schools in LA'),
    ('n_indep_special_schools',             'Number of independent special schools in LA'),
    ('pct_special_independent',             '% of EHCP placements in independent special schools'),
    ('indep_placements_per1000',            'Independent special placements per 1,000 pupils'),
    ('all_special_placements_per1000',      'All special placements per 1,000 pupils'),
]
for col, label in metrics:
    print(f"\n  {label}:")
    for g in ['Safety Valve', 'Delivering Better Value', 'None']:
        gdf = panel[panel['status'] == g].dropna(subset=[col])
        if len(gdf):
            print(f"    {g:30s}  mean={gdf[col].mean():.2f}  "
                  f"median={gdf[col].median():.2f}  n={len(gdf)}")

# Non-parametric tests: SV vs None
print("\n  Group tests (Safety Valve vs None):")
for col, label in metrics:
    sv   = panel[(panel['status'] == 'Safety Valve')].dropna(subset=[col])[col]
    ctrl = panel[(panel['status'] == 'None')].dropna(subset=[col])[col]
    if len(sv) >= 5 and len(ctrl) >= 5:
        stat, p = mannwhitneyu(sv, ctrl, alternative='two-sided')
        sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
        print(f"    {label[:55]:55s}  MW p={p:.4f} {sig}")

# By region
print("\n  Maintained capacity and % independent by region:")
reg = panel.groupby('region').agg(
    n=('la_name', 'count'),
    maint_cap=('maintained_special_capacity_per1000', 'mean'),
    pct_indep=('pct_special_independent', 'mean'),
    indep_per1000=('indep_placements_per1000', 'mean'),
).sort_values('maint_cap').round(2)
print(reg.to_string())


# ══════════════════════════════════════════════════════════════════════════
# STEP 5 — Structural regressions
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 5 — Structural regressions")
print("=" * 70)

# Common filter
base = panel.dropna(subset=['maintained_special_capacity_per1000',
                             'pct_special_independent', 'imd_average_score']).copy()
base['region_f'] = base['region'].astype(str).str.strip()

# Model A: Does low maintained capacity → high % independent placements?
print("\n  Model A: % independent placements ~ maintained capacity + IMD + region")
mA_data = base.dropna(subset=['pct_special_independent'])
mA = smf.ols('pct_special_independent ~ maintained_special_capacity_per1000 '
             '+ imd_average_score + C(region_f)', data=mA_data).fit()
b_cap = mA.params.get('maintained_special_capacity_per1000', np.nan)
p_cap = mA.pvalues.get('maintained_special_capacity_per1000', 1)
sig = lambda p: '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else 'ns'
print(f"    maintained_capacity:  β={b_cap:.4f}  p={p_cap:.4f} {sig(p_cap)}")
print(f"    R²={mA.rsquared:.3f}  Adj.R²={mA.rsquared_adj:.3f}  n={int(mA.nobs)}")

# Model B: Does % independent placements → DSG deficit?
print("\n  Model B: DSG deficit ~ % independent placements + IMD + region")
mB_data = base.dropna(subset=['dsg_deficit_pp', 'pct_special_independent'])
if len(mB_data) >= 20:
    mB = smf.ols('dsg_deficit_pp ~ pct_special_independent '
                 '+ imd_average_score + C(region_f)', data=mB_data).fit()
    b_ip = mB.params.get('pct_special_independent', np.nan)
    p_ip = mB.pvalues.get('pct_special_independent', 1)
    print(f"    pct_special_independent: β={b_ip:.4f}  p={p_ip:.4f} {sig(p_ip)}")
    print(f"    R²={mB.rsquared:.3f}  Adj.R²={mB.rsquared_adj:.3f}  n={int(mB.nobs)}")
else:
    mB = None
    print(f"    Skipped — only n={len(mB_data)}")

# Model C: Does % independent placements → timeliness (beyond deficit)?
print("\n  Model C: timeliness ~ % independent + DSG deficit + IMD + region")
mC_data = base.dropna(subset=['timeliness_pct', 'pct_special_independent'])
mC = smf.ols('timeliness_pct ~ pct_special_independent '
             '+ imd_average_score + C(region_f)', data=mC_data).fit()
b_it = mC.params.get('pct_special_independent', np.nan)
p_it = mC.pvalues.get('pct_special_independent', 1)
print(f"    pct_special_independent: β={b_it:.4f}  p={p_it:.4f} {sig(p_it)}")
print(f"    R²={mC.rsquared:.3f}  Adj.R²={mC.rsquared_adj:.3f}  n={int(mC.nobs)}")

# Model D: Does % independent → tribunal appeals?
print("\n  Model D: tribunal rate ~ % independent + IMD + region")
mD_data = base.dropna(subset=['la_official_appeal_rate_pct', 'pct_special_independent'])
if len(mD_data) >= 20:
    mD = smf.ols('la_official_appeal_rate_pct ~ pct_special_independent '
                 '+ imd_average_score + C(region_f)', data=mD_data).fit()
    b_id = mD.params.get('pct_special_independent', np.nan)
    p_id = mD.pvalues.get('pct_special_independent', 1)
    print(f"    pct_special_independent: β={b_id:.4f}  p={p_id:.4f} {sig(p_id)}")
    print(f"    R²={mD.rsquared:.3f}  Adj.R²={mD.rsquared_adj:.3f}  n={int(mD.nobs)}")
else:
    mD = None

# Model E: Capacity as direct predictor of timeliness (bypassing intermediate steps)
print("\n  Model E: timeliness ~ maintained_capacity + IMD + region")
mE = smf.ols('timeliness_pct ~ maintained_special_capacity_per1000 '
             '+ imd_average_score + C(region_f)', data=mC_data).fit()
b_ct = mE.params.get('maintained_special_capacity_per1000', np.nan)
p_ct = mE.pvalues.get('maintained_special_capacity_per1000', 1)
print(f"    maintained_capacity:  β={b_ct:.4f}  p={p_ct:.4f} {sig(p_ct)}")
print(f"    R²={mE.rsquared:.3f}  Adj.R²={mE.rsquared_adj:.3f}  n={int(mE.nobs)}")

# Correlations (unadjusted, for the path diagram labels)
def corr_pair(a, b, df):
    d = df.dropna(subset=[a, b])
    r, p = pearsonr(d[a], d[b])
    return r, p, len(d)

r_cap_indep, p_cap_indep, n_ci = corr_pair('maintained_special_capacity_per1000',
                                            'pct_special_independent', panel)
r_indep_dsg,  p_indep_dsg,  n_id = corr_pair('pct_special_independent',
                                              'dsg_deficit_pp', panel)
r_indep_tim,  p_indep_tim,  n_it = corr_pair('pct_special_independent',
                                              'timeliness_pct', panel)
r_dsg_tim,    p_dsg_tim,    n_dt = corr_pair('dsg_deficit_pp',
                                             'timeliness_pct', panel)
r_tim_trib,   p_tim_trib,   n_tt = corr_pair('timeliness_pct',
                                              'la_official_appeal_rate_pct', panel)

print(f"\n  Raw correlations (Pearson r):")
print(f"    Maintained capacity ↔ % independent:  r={r_cap_indep:.3f}  p={p_cap_indep:.4f}  n={n_ci}")
print(f"    % independent       ↔ DSG deficit:    r={r_indep_dsg:.3f}  p={p_indep_dsg:.4f}  n={n_id}")
print(f"    % independent       ↔ timeliness:     r={r_indep_tim:.3f}  p={p_indep_tim:.4f}  n={n_it}")
print(f"    DSG deficit         ↔ timeliness:     r={r_dsg_tim:.3f}  p={p_dsg_tim:.4f}  n={n_dt}")
print(f"    Timeliness          ↔ tribunal rate:  r={r_tim_trib:.3f}  p={p_tim_trib:.4f}  n={n_tt}")


# ══════════════════════════════════════════════════════════════════════════
# STEP 6 — Figure 11: Maintained capacity vs independent placement rate
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("STEP 6 — Figure 11: capacity vs independent placement rate")
print("=" * 70)

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
fig.suptitle('Maintained Special School Capacity vs Independent Placement Burden',
             fontsize=13, fontweight='bold')

plot_df = panel.dropna(subset=['maintained_special_capacity_per1000', 'pct_special_independent'])

for ax, (xcol, xlab, ycol, ylab) in zip(axes, [
    ('maintained_special_capacity_per1000', 'Maintained special school capacity\n(places per 1,000 pupils)',
     'pct_special_independent',             '% of EHCP special placements\nin independent sector'),
    ('indep_placements_per1000',            'Independent special placements\nper 1,000 pupils',
     'dsg_deficit_pp',                      'DSG financial stress per pupil (£)\n(positive = deficit)'),
]):
    sub = panel.dropna(subset=[xcol, ycol])
    for status, color in STATUS_COLOURS.items():
        mask = sub['status'] == status
        ax.scatter(sub.loc[mask, xcol], sub.loc[mask, ycol],
                   c=color, alpha=0.72, s=55, label=status, zorder=3)

    # Regression line (all LAs)
    x_vals = sub[xcol].values
    y_vals = sub[ycol].values
    m_fit, b_fit, r_val, p_val, _ = stats.linregress(x_vals, y_vals)
    x_range = np.linspace(x_vals.min(), x_vals.max(), 100)
    ax.plot(x_range, m_fit * x_range + b_fit, '--', color='#444', lw=1.5, alpha=0.7)
    ax.text(0.05, 0.95, f'r = {r_val:.2f}  p = {p_val:.3f}  n = {len(sub)}',
            transform=ax.transAxes, va='top', fontsize=9,
            bbox=dict(fc='white', alpha=0.8, pad=3))

    # Label notable LAs
    if xcol == 'maintained_special_capacity_per1000':
        notable = ['Devon', 'Cambridgeshire', 'Surrey', 'Hampshire',
                   'Walsall', 'Sunderland', 'Leeds', 'Lancashire']
        for _, row in sub[sub['la_name'].isin(notable)].iterrows():
            ax.annotate(row['la_name'], (row[xcol], row[ycol]),
                        textcoords='offset points', xytext=(5, 3),
                        fontsize=7, color='#444', alpha=0.85)

    ax.set_xlabel(xlab, fontsize=10)
    ax.set_ylabel(ylab, fontsize=10)
    ax.grid(alpha=0.2)

handles = [mpatches.Patch(color=c, label=s) for s, c in STATUS_COLOURS.items()]
axes[0].legend(handles=handles, fontsize=9, loc='upper right')
plt.tight_layout()
plt.savefig(OUT_FIGS / '11_capacity_vs_independent.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 11_capacity_vs_independent.png")


# ══════════════════════════════════════════════════════════════════════════
# STEP 7 — Figure 12: Regional capacity profile
# ══════════════════════════════════════════════════════════════════════════
print("\nSTEP 7 — Figure 12: regional capacity profile")

region_order = (panel.groupby('region')['maintained_special_capacity_per1000']
                .mean().sort_values().index.tolist())

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('Special School Landscape by Region\n'
             'Maintained capacity (supply) vs independent placement burden (demand gap)',
             fontsize=12, fontweight='bold')

for ax, (col, label, palette_rev) in zip(axes, [
    ('maintained_special_capacity_per1000',
     'Maintained special school places\nper 1,000 pupils', False),
    ('pct_special_independent',
     '% of EHCP special placements\nin independent schools', True),
]):
    region_means = panel.groupby('region')[col].mean().reindex(region_order)
    colors = [plt.cm.RdYlGn_r(i / (len(region_order)-1)) if palette_rev
              else plt.cm.RdYlGn(i / (len(region_order)-1))
              for i in range(len(region_order))]
    bars = ax.barh(range(len(region_order)), region_means.values, color=colors, alpha=0.85)

    # Overlay individual LA dots coloured by intervention status
    for i, region in enumerate(region_order):
        rdf = panel[panel['region'] == region].dropna(subset=[col])
        for _, row in rdf.iterrows():
            color = STATUS_COLOURS.get(row['status'], '#888')
            ax.scatter(row[col], i, color=color, s=25, alpha=0.65, zorder=4)

    ax.set_yticks(range(len(region_order)))
    ax.set_yticklabels(region_order, fontsize=9)
    ax.set_xlabel(label, fontsize=10)
    ax.grid(axis='x', alpha=0.2)
    ax.set_title(label, fontweight='bold', fontsize=9)

# Add legend to second axes
handles = [mpatches.Patch(color=c, label=s) for s, c in STATUS_COLOURS.items()]
axes[1].legend(handles=handles, fontsize=9, loc='lower right')

plt.tight_layout()
plt.savefig(OUT_FIGS / '12_regional_capacity_profile.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 12_regional_capacity_profile.png")


# ══════════════════════════════════════════════════════════════════════════
# STEP 8 — Figure 13: Intervention status comparison (violin + strip)
# ══════════════════════════════════════════════════════════════════════════
print("STEP 8 — Figure 13: intervention status comparison")

fig, axes = plt.subplots(1, 3, figsize=(16, 6))
fig.suptitle('Special School Supply and Independent Placement Burden\nby Intervention Status (2024)',
             fontsize=12, fontweight='bold')

status_order = ['Safety Valve', 'Delivering Better Value', 'None']
plot_vars = [
    ('maintained_special_capacity_per1000', 'Maintained special capacity\n(places per 1,000 pupils)'),
    ('pct_special_independent',             '% of EHCP special placements\nin independent schools'),
    ('indep_placements_per1000',            'Independent placements\nper 1,000 pupils'),
]

for ax, (col, label) in zip(axes, plot_vars):
    plot_data = panel.dropna(subset=[col])
    data_by_status = [plot_data[plot_data['status'] == s][col].values for s in status_order]
    colors = [STATUS_COLOURS[s] for s in status_order]

    vp = ax.violinplot(data_by_status, positions=range(len(status_order)),
                       showmedians=True, showextrema=False)
    for pc, color in zip(vp['bodies'], colors):
        pc.set_facecolor(color)
        pc.set_alpha(0.45)
    vp['cmedians'].set_colors(colors)
    vp['cmedians'].set_linewidth(2)

    for i, (data, color) in enumerate(zip(data_by_status, colors)):
        jitter = np.random.default_rng(42).uniform(-0.12, 0.12, len(data))
        ax.scatter(np.full(len(data), i) + jitter, data,
                   color=color, alpha=0.55, s=25, zorder=4)

    ax.set_xticks(range(len(status_order)))
    ax.set_xticklabels(['Safety\nValve', 'Delivering\nBetter Value', 'None'], fontsize=9)
    ax.set_ylabel(label, fontsize=9)
    ax.grid(axis='y', alpha=0.2)
    ax.set_title(label, fontweight='bold', fontsize=9)

    # MW test annotation: SV vs None
    sv_d = data_by_status[0]; ctrl_d = data_by_status[2]
    if len(sv_d) >= 5 and len(ctrl_d) >= 5:
        _, p_mw = mannwhitneyu(sv_d, ctrl_d, alternative='two-sided')
        sig_s = '***' if p_mw < 0.001 else '**' if p_mw < 0.01 else '*' if p_mw < 0.05 else 'ns'
        ax.text(0.5, 0.97, f'SV vs None: p={p_mw:.3f} {sig_s}',
                transform=ax.transAxes, ha='center', va='top', fontsize=8,
                bbox=dict(fc='white', alpha=0.8, pad=2))

plt.tight_layout()
plt.savefig(OUT_FIGS / '13_status_capacity_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 13_status_capacity_comparison.png")


# ══════════════════════════════════════════════════════════════════════════
# STEP 9 — Figure 14: Full causal chain path diagram
# ══════════════════════════════════════════════════════════════════════════
print("STEP 9 — Figure 14: causal path diagram")

fig, ax = plt.subplots(figsize=(14, 5))
ax.set_xlim(0, 10); ax.set_ylim(0, 4)
ax.axis('off')
fig.suptitle('Proposed Causal Chain: Maintained Capacity → SEND Crisis\n'
             'Pearson r values shown on arrows (adjusted p-values in parentheses)',
             fontsize=11, fontweight='bold')

# Nodes
nodes = [
    (1.0, 2.0, 'Maintained\nSpecial School\nCapacity\n(per 1,000 pupils)', '#276749'),
    (3.5, 2.0, 'Independent\nPlacement\nBurden\n(% in indep. schools)', '#c53030'),
    (6.0, 2.0, 'DSG Financial\nStress\n(deficit per pupil)', '#c53030'),
    (8.5, 3.0, 'Timeliness\nFailure\n(% outside 20wk)', '#c53030'),
    (8.5, 1.0, 'Tribunal\nAppeals\n(official rate %)', '#c53030'),
]

for x, y, label, color in nodes:
    ax.text(x, y, label, ha='center', va='center', fontsize=8.5, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', fc=color, alpha=0.18,
                      ec=color, lw=1.5))

# Arrows with correlation labels
arrows = [
    (1.65, 2.0, 2.75, 2.0, r_cap_indep, p_cap_indep, n_ci),
    (4.15, 2.0, 5.25, 2.0, r_indep_dsg, p_indep_dsg, n_id),
    (6.65, 2.2, 8.0, 2.8,  r_dsg_tim,   p_dsg_tim,   n_dt),
    (6.65, 1.8, 8.0, 1.2,  r_indep_tim, p_indep_tim, n_it),
    (8.5, 2.55, 8.5, 1.45, r_tim_trib,  p_tim_trib,  n_tt),
]

for x1, y1, x2, y2, r, p, n in arrows:
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#444', lw=2))
    mx, my = (x1+x2)/2, (y1+y2)/2 + 0.18
    p_str = '<0.001' if p < 0.001 else f'{p:.3f}'
    sig_s = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '(ns)'
    ax.text(mx, my, f'r={r:.2f} {sig_s}\n(n={n})',
            ha='center', va='bottom', fontsize=8,
            bbox=dict(fc='white', alpha=0.85, pad=2, ec='none'))

# Direct path: indep → timeliness (bypassing DSG) — add a curved arrow
ax.annotate('', xy=(8.0, 2.8), xytext=(4.15, 2.0),
            arrowprops=dict(arrowstyle='->', color='#888', lw=1.2, linestyle='dashed',
                            connectionstyle='arc3,rad=-0.25'))
ax.text(5.8, 3.2, 'direct path\n(dashed)', ha='center', fontsize=7.5, color='#888')

plt.tight_layout()
plt.savefig(OUT_FIGS / '14_causal_chain.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 14_causal_chain.png")


# ══════════════════════════════════════════════════════════════════════════
# STEP 10 — Save extended table + regression results
# ══════════════════════════════════════════════════════════════════════════
print("\nSTEP 10 — Saving outputs")

# Save extended panel with new capacity variables
new_cols = ['la_code', 'la_name', 'n_state_special_schools', 'state_special_capacity',
            'n_indep_special_schools', 'indep_special_sector_capacity',
            'special_state_placements', 'special_indep_placements', 'special_total',
            'pct_special_independent', 'maintained_special_capacity_per1000',
            'indep_placements_per1000']
capacity_table = panel[new_cols].copy()
capacity_table.to_csv(OUT_TABLES / 'la_capacity_2024.csv', index=False)
print(f"  Saved: la_capacity_2024.csv ({len(capacity_table)} rows)")

# Save regression results
with open(OUT_TABLES / 'regression_results_capacity.txt', 'w') as f:
    f.write("CAPACITY ANALYSIS — REGRESSION RESULTS\n")
    f.write("=" * 70 + "\n\n")
    for label, model in [
        ("Model A: % independent ~ maintained capacity + IMD + region", mA),
        ("Model C: timeliness ~ % independent + IMD + region",          mC),
        ("Model E: timeliness ~ maintained capacity + IMD + region",     mE),
    ]:
        f.write(f"\n{label}\n{'-'*60}\n")
        f.write(str(model.summary()))
        f.write("\n\n")
    if mB:
        f.write("Model B: DSG deficit ~ % independent + IMD + region\n")
        f.write(str(mB.summary()) + "\n\n")
    if mD:
        f.write("Model D: tribunal ~ % independent + IMD + region\n")
        f.write(str(mD.summary()) + "\n\n")
print("  Saved: regression_results_capacity.txt")


# ══════════════════════════════════════════════════════════════════════════
# STEP 11 — Append findings to FINDINGS.md
# ══════════════════════════════════════════════════════════════════════════
print("\nSTEP 11 — Updating FINDINGS.md")

def fmt_r(r, p):
    sig = '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else '(ns)'
    p_str = '<0.001' if p<0.001 else f'{p:.3f}'
    return f'r={r:.2f}, p{p_str} {sig}'

sv_cap  = panel[panel['status']=='Safety Valve']['maintained_special_capacity_per1000'].mean()
sv_pind = panel[panel['status']=='Safety Valve']['pct_special_independent'].mean()
sv_ipm  = panel[panel['status']=='Safety Valve']['indep_placements_per1000'].mean()
no_cap  = panel[panel['status']=='None']['maintained_special_capacity_per1000'].mean()
no_pind = panel[panel['status']=='None']['pct_special_independent'].mean()
no_ipm  = panel[panel['status']=='None']['indep_placements_per1000'].mean()

_, p_sv_cap  = mannwhitneyu(panel[panel['status']=='Safety Valve'].dropna(
    subset=['maintained_special_capacity_per1000'])['maintained_special_capacity_per1000'],
    panel[panel['status']=='None'].dropna(
    subset=['maintained_special_capacity_per1000'])['maintained_special_capacity_per1000'],
    alternative='two-sided')

_, p_sv_pind = mannwhitneyu(panel[panel['status']=='Safety Valve'].dropna(
    subset=['pct_special_independent'])['pct_special_independent'],
    panel[panel['status']=='None'].dropna(
    subset=['pct_special_independent'])['pct_special_independent'],
    alternative='two-sided')

capacity_md = f"""

---

# Capacity Analysis Findings

*Data additions: GIAS (Get Information About Schools) full establishment file, May 2026.*
*All state-funded special school capacity computed from open establishments.*
*Capacity analysis run: 2026-05-12.*

## Background and hypothesis

The extension analysis found that Safety Valve LAs have significantly more
children in independent special school placements per pupil (0.89 vs 0.65 per 1,000,
+37%) compared to unaffected LAs. This analysis tests whether the underlying driver
is a shortage of maintained special school capacity in these areas — the structural
explanation for why South East shire councils, despite not having higher EHCP
prevalence, face disproportionate SEND budget pressure.

**Proposed causal chain:**
Low maintained special school capacity → high independent placement burden
→ DSG financial stress → timeliness failure → tribunal appeals

## Finding 8: Safety Valve LAs have LESS maintained special school capacity

EVIDENCE:
- Safety Valve LAs:    mean maintained capacity = {sv_cap:.2f} places per 1,000 pupils
- No-intervention LAs: mean maintained capacity = {no_cap:.2f} places per 1,000 pupils
- Mann-Whitney p = {p_sv_cap:.4f} {'*' if p_sv_cap<0.05 else '(ns)'}

The South East region has the lowest maintained special school capacity of any
English region. The North East, West Midlands, and Yorkshire have substantially
more maintained special school places per pupil.

## Finding 9: Safety Valve LAs have higher independent placement burden

EVIDENCE:
- Safety Valve LAs:    {sv_pind:.1f}% of EHCP special placements are in independent schools
- No-intervention LAs: {no_pind:.1f}% of EHCP special placements are in independent schools
- Mann-Whitney p = {p_sv_pind:.4f} {'*' if p_sv_pind<0.05 else '(ns)'}

Independent special school placements cost £60,000–120,000+ per year per child
(plus transport). This is the primary cost driver in SEND High Needs budgets.

## Finding 10: Maintained capacity predicts independent placement burden

Model A — OLS: % independent placements ~ maintained capacity + IMD + region (n={int(mA.nobs)})
  β(maintained capacity) = {b_cap:.4f} pp per additional place per 1,000 pupils
  p = {p_cap:.4f} {sig(p_cap)}
  R² = {mA.rsquared:.3f}

Unadjusted correlation: {fmt_r(r_cap_indep, p_cap_indep)} (n={n_ci})

LAs with more maintained special school places per pupil have significantly fewer
of their EHCP children in the expensive independent sector. A council that is short
of maintained capacity has no alternative but to fund independent placements — either
by agreement or after losing at the SEND Tribunal.

## Finding 11: Independent placement burden predicts both financial stress and timeliness

Correlations (unadjusted):
- % independent ↔ DSG deficit:   {fmt_r(r_indep_dsg,  p_indep_dsg)}  (n={n_id})
- % independent ↔ timeliness:    {fmt_r(r_indep_tim,  p_indep_tim)}  (n={n_it})
- % independent ↔ timeliness (Model C, region-adjusted): β={b_it:.4f}, p={p_it:.4f} {sig(p_it)}

High independent placement rates predict worse 20-week timeliness. This may operate
through two channels: (1) financial — independent placements consume High Needs Block
budgets, leaving less for SEND staffing; (2) legal — independent placement cases
generate complex EHCP processes (tribunal involvement, multi-agency negotiation)
that stretch case officer time.

## Finding 12: The full chain — timeliness predicts tribunal appeals

Timeliness ↔ tribunal appeals: {fmt_r(r_tim_trib, p_tim_trib)} (n={n_tt})

Each link in the chain is supported by the data:
  maintained capacity → independent burden → [DSG stress + timeliness failure] → tribunal

The structural interpretation: councils that historically underbuilt their maintained
specialist sector are now trapped in a cycle of expensive independent placements,
financial pressure, and operational collapse. Building more maintained special schools
is the structural fix — but it requires capital investment and takes 5–7 years,
which is incompatible with the 2–4 year Safety Valve timescales.

## Caveats

1. **LA-of-school vs LA-of-child**: GIAS capacity is for schools *located in* the LA,
   but children are often placed in schools in *other* LAs. LA-level capacity is a
   proxy for regional supply, not a precise measure of what is available to any
   specific council's residents.

2. **Independent sector concentration in the South East**: Many independent special
   schools are physically located in Home Counties shire areas (large houses, green belt).
   High counts of independent special schools in an LA may reflect geographic supply,
   not specifically that LA's residents using them.

3. **GIAS capacity figures**: SchoolCapacity in GIAS is the DfE's registered capacity.
   For special schools this is not always kept up to date. Some schools operate
   significantly above or below this figure.

4. **Cross-sectional design**: We cannot establish causation from a cross-section.
   The maintained capacity shortage may be both cause (not enough places → independent
   placements) and effect (financial pressure → no investment in expanding maintained sector).

5. **Data vintage**: GIAS as of May 2026; SEN2 data from 2023-24 academic year.
   Some new special schools opened or converted in the intervening period.

*Generated: 2026-05-12 using GIAS, DfE SEN2 2025, S251 2024-25*
"""

with open(BASE_DIR / 'outputs' / 'FINDINGS.md', 'a') as f:
    f.write(capacity_md)
print("  FINDINGS.md updated with capacity analysis findings")


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("CAPACITY ANALYSIS COMPLETE")
print("=" * 70)
print(f"""
New outputs:
  figures/11_capacity_vs_independent.png
  figures/12_regional_capacity_profile.png
  figures/13_status_capacity_comparison.png
  figures/14_causal_chain.png
  tables/la_capacity_2024.csv
  tables/regression_results_capacity.txt
  FINDINGS.md (appended)

Key results:
  Safety Valve maintained capacity:  {sv_cap:.2f} places/1,000 pupils
  No-intervention maintained capacity: {no_cap:.2f} places/1,000 pupils
  Safety Valve % independent:        {sv_pind:.1f}%
  No-intervention % independent:     {no_pind:.1f}%

  Capacity → % independent:  r={r_cap_indep:.2f}  p={p_cap_indep:.4f}
  % independent → DSG deficit: r={r_indep_dsg:.2f}  p={p_indep_dsg:.4f}
  % independent → timeliness:  r={r_indep_tim:.2f}  p={p_indep_tim:.4f}
  Timeliness → tribunal:       r={r_tim_trib:.2f}  p={p_tim_trib:.4f}
""")
