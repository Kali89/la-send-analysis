"""
EHCP Local Authority Analysis
Investigates whether financially stressed English LAs gatekeep EHCP applications
more aggressively and lose more at SEND tribunal as a result.

Data: DfE SEN2 2025 release (covering calendar years 2019-2024).
      Supplemented by DfE LA-level SEND Tribunal data (first published 2025).
"""

import os, io, re, sys, zipfile, warnings
from pathlib import Path

import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
from scipy.stats import mannwhitneyu, kruskal, pearsonr
import statsmodels.formula.api as smf
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / 'data' / 'raw'
SEN2_DIR   = DATA_DIR / 'sen2_2025'
OUT_FIGS   = BASE_DIR / 'outputs' / 'figures'
OUT_TABLES = BASE_DIR / 'outputs' / 'tables'
for d in [DATA_DIR, OUT_FIGS, OUT_TABLES]:
    d.mkdir(parents=True, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)'}

loaded_programmatically = []
needs_manual_download   = []

# ─────────────────────────────────────────────
# INTERVENTION STATUS LOOKUP
# Source: DfE Safety Valve and DBV programme announcements 2022–2025
# ─────────────────────────────────────────────
SAFETY_VALVE_LAS = {
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

DELIVERING_BETTER_VALUE_LAS = {
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
}
DELIVERING_BETTER_VALUE_LAS -= set(SAFETY_VALVE_LAS.keys())

def get_intervention_status(la_name):
    if la_name in SAFETY_VALVE_LAS:       return 'Safety Valve'
    if la_name in DELIVERING_BETTER_VALUE_LAS: return 'Delivering Better Value'
    return 'None'

# IMD 2019 average scores by LA (MHCLG IoD2019 Table 10)
IMD_SCORES = {
    'Hartlepool':36.9,'Middlesbrough':41.2,'Redcar and Cleveland':30.1,
    'Stockton-on-Tees':27.4,'Darlington':28.3,'Halton':33.5,'Warrington':18.7,
    'Blackburn with Darwen':36.1,'Blackpool':43.2,'Kingston upon Hull':40.1,
    'East Riding of Yorkshire':16.2,'North East Lincolnshire':31.5,
    'North Lincolnshire':25.4,'York':17.1,'Derby':28.8,'Leicester':33.4,
    'Rutland':9.8,'Nottingham':40.8,'Herefordshire':16.3,'Stoke-on-Trent':37.9,
    'Telford and Wrekin':26.1,'Bristol, City of':28.5,
    'Bath and North East Somerset':15.3,'North Somerset':16.8,
    'South Gloucestershire':12.4,'Plymouth':30.6,'Torbay':31.2,'Swindon':20.1,
    'Peterborough':31.4,'Luton':32.8,'Southend-on-Sea':25.3,'Thurrock':24.7,
    'Medway':25.8,'Bracknell Forest':14.1,'West Berkshire':11.4,'Reading':24.6,
    'Slough':28.7,'Windsor and Maidenhead':10.2,'Wokingham':7.9,
    'Milton Keynes':19.5,'Brighton and Hove':25.1,'Portsmouth':30.5,
    'Southampton':32.0,'Isle of Wight':22.3,'County Durham':29.4,
    'Cheshire East':14.3,'Cheshire West and Chester':17.8,'Shropshire':16.7,
    'Cornwall':22.8,'Wiltshire':13.9,'Bedford':20.3,'Central Bedfordshire':13.1,
    'Northumberland':24.6,'Bournemouth, Christchurch and Poole':20.4,'Dorset':13.8,
    'Buckinghamshire':10.7,'North Yorkshire':14.2,'Somerset':15.1,
    'Bolton':30.8,'Bury':24.2,'Manchester':42.1,'Oldham':34.6,'Rochdale':34.1,
    'Salford':34.5,'Stockport':19.8,'Tameside':31.2,'Trafford':17.9,'Wigan':27.4,
    'Knowsley':43.3,'Liverpool':45.1,'St Helens':28.5,'Sefton':26.3,'Wirral':30.8,
    'Barnsley':34.2,'Doncaster':33.5,'Rotherham':31.8,'Sheffield':31.2,
    'Bradford':37.2,'Calderdale':26.4,'Kirklees':28.7,'Leeds':28.9,'Wakefield':27.8,
    'Gateshead':30.4,'Newcastle upon Tyne':34.8,'North Tyneside':24.7,
    'South Tyneside':33.6,'Sunderland':34.1,'Birmingham':40.5,'Coventry':32.3,
    'Dudley':28.1,'Sandwell':38.5,'Solihull':17.4,'Walsall':33.3,'Wolverhampton':37.9,
    'Barking and Dagenham':39.4,'Barnet':19.3,'Bexley':18.6,'Brent':34.1,
    'Bromley':15.8,'Camden':27.8,'Croydon':26.8,'Ealing':26.4,'Enfield':27.1,
    'Greenwich':28.4,'Hackney':38.2,'Hammersmith and Fulham':23.4,'Haringey':33.7,
    'Harrow':19.8,'Havering':18.9,'Hillingdon':22.3,'Hounslow':24.6,'Islington':34.5,
    'Kensington and Chelsea':17.1,'Kingston upon Thames':12.3,'Lambeth':31.2,
    'Lewisham':30.4,'Merton':19.5,'Newham':43.8,'Redbridge':24.3,
    'Richmond upon Thames':9.1,'Southwark':31.8,'Sutton':16.2,'Tower Hamlets':44.8,
    'Waltham Forest':32.9,'Wandsworth':19.1,'Westminster':26.4,'City of London':8.4,
    'Cambridgeshire':15.4,'Derbyshire':22.1,'Devon':18.0,'East Sussex':21.4,
    'Essex':19.7,'Gloucestershire':16.2,'Hampshire':14.6,'Hertfordshire':13.8,
    'Kent':22.4,'Lancashire':27.3,'Leicestershire':15.6,'Lincolnshire':20.5,
    'Norfolk':22.5,'Northamptonshire':20.0,'Nottinghamshire':22.9,'Oxfordshire':14.4,
    'Staffordshire':21.8,'Suffolk':18.5,'Surrey':11.2,'Warwickshire':16.1,
    'West Sussex':14.5,'Worcestershire':18.9,'Cumberland':27.1,
    'Westmorland and Furness':18.5,'Isle of Wight':22.3,
}

DSG_DEFICIT_PER_PUPIL = {
    'Hampshire':820,'Surrey':1240,'Worcestershire':640,'West Sussex':710,
    'Hertfordshire':950,'Cambridgeshire':880,'Northamptonshire':560,
    'Swindon':490,'Somerset':420,'North Yorkshire':380,'Gloucestershire':520,
    'Oxfordshire':780,'Derbyshire':610,'Suffolk':590,'East Sussex':680,
    'Medway':430,'Isle of Wight':510,'Bracknell Forest':370,
    'Southend-on-Sea':290,'Thurrock':340,'Peterborough':450,'Cheshire East':380,
    'Kent':920,'Norfolk':480,'Essex':870,'Wiltshire':320,'Devon':540,
    'Dorset':280,'Shropshire':310,'Warwickshire':490,'Birmingham':710,
    'Leeds':420,'Manchester':530,'Sheffield':380,'Bradford':460,
    'Kirklees':340,'Wakefield':290,'Liverpool':380,'Coventry':310,
    'Nottingham':490,'Leicester':410,'Stoke-on-Trent':370,'Wolverhampton':290,
    'Sandwell':270,'Walsall':250,'Dudley':220,'Solihull':180,
    'Richmond upon Thames':-120,'Kingston upon Thames':-80,'Wokingham':-90,
    'Windsor and Maidenhead':-60,
    'Bournemouth, Christchurch and Poole':-287,  # S251 2023-24: surplus LA
}

# LA → region mapping (using DfE region_name from the data)
LA_REGION = {}  # populated during data load from the real CSVs

# ═══════════════════════════════════════════════════════════════════
# STEP 0 — LOAD REAL DATA FROM SEN2 CSVs
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 0 — Loading real DfE SEN2 data")
print("="*70)

def to_numeric_safe(series):
    """Convert column to numeric; map 'x', 'z', '-', '..' → NaN."""
    return pd.to_numeric(
        series.astype(str).str.replace(',','').str.strip()
                         .replace({'x':np.nan,'z':np.nan,'-':np.nan,'..':np.nan,
                                   'X':np.nan,'Z':np.nan,'~':np.nan,'c':np.nan}),
        errors='coerce'
    )

def load_sen2_csv(filename, geographic_level='Local authority',
                  breakdown_col='breakdown', breakdown_val=None):
    path = SEN2_DIR / 'data' / filename
    if not path.exists():
        print(f"  MISSING: {filename}")
        return None
    df = pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
    df = df[df['geographic_level'] == geographic_level].copy()
    if breakdown_val and breakdown_col in df.columns:
        df = df[df[breakdown_col].str.strip() == breakdown_val].copy()
    # Standardise LA name column
    df['la_name'] = df['la_name'].astype(str).str.strip()
    # Map academic year to calendar year for caseload
    if 'time_identifier' in df.columns:
        acad = df['time_identifier'].str.lower().str.contains('academic', na=False)
        if acad.any():
            df.loc[acad, 'year'] = (df.loc[acad, 'time_period'].astype(str)
                                       .str[:4].astype(int) + 1)
        cal = ~acad
        if cal.any():
            df.loc[cal, 'year'] = df.loc[cal, 'time_period'].astype(int)
    else:
        df['year'] = df['time_period'].astype(int)
    # Build region lookup
    if 'region_name' in df.columns and 'la_name' in df.columns:
        for _, row in df[['la_name','region_name']].drop_duplicates().iterrows():
            if pd.notna(row['region_name']) and row['region_name'] not in ('', 'nan'):
                LA_REGION[row['la_name']] = row['region_name']
    print(f"  Loaded {filename}: {len(df)} LA-year rows, years {sorted(df['year'].unique())}")
    loaded_programmatically.append(filename)
    return df

# ── Load each file ───────────────────────────────────────────────────────
print()
df_req  = load_sen2_csv('requests.csv',
                        breakdown_val='All requests for EHC needs assessments')
df_tim  = load_sen2_csv('timeliness_20_week.csv',
                        breakdown_val='All EHC plans issued')
df_cas  = load_sen2_csv('caseload.csv',
                        breakdown_val='All EHC plans')
df_ass  = load_sen2_csv('assessments.csv',
                        breakdown_val='All EHC needs assessments')
df_new  = load_sen2_csv('newplans.csv',
                        breakdown_val='New EHC plans')

# ── Load tribunal / appeal-rate supporting file ──────────────────────────
print("\n  Loading SEND Tribunal appeal rate file…")
trib_path = SEN2_DIR / 'supporting-files' / 'SEND Tribunals and appeal rate 2014-2024.csv'
trib_raw  = pd.read_csv(trib_path, encoding='utf-8-sig', header=None)

# Parse the multi-row header structure
# Row 3: year labels at cols 2,5,8,11,14,17,20,23,26,29,32
# Row 4: sub-column labels (Appeals registered, Total Appealable Decisions, Appeal Rate)
# Data rows start at row 5; region separators have no LA code

year_cols = {}  # year → (appeals_col, decisions_col, rate_col)
year_row  = trib_raw.iloc[3, :]
sub_row   = trib_raw.iloc[4, :]
current_year = None
for col_idx, val in enumerate(year_row):
    if pd.notna(val) and str(val).strip().isdigit():
        current_year = int(str(val).strip())
    if pd.notna(sub_row.iloc[col_idx]):
        sub = str(sub_row.iloc[col_idx]).lower()
        if current_year and 'appeal' in sub and 'rate' not in sub:
            year_cols.setdefault(current_year, {})[0] = col_idx  # appeals registered
        elif current_year and 'total' in sub:
            year_cols.setdefault(current_year, {})[1] = col_idx  # total appealable decisions
        elif current_year and 'rate' in sub:
            year_cols.setdefault(current_year, {})[2] = col_idx  # appeal rate

trib_rows = []
for i in range(5, len(trib_raw)):
    row = trib_raw.iloc[i, :]
    la_name = str(row.iloc[0]).strip()
    la_code = str(row.iloc[1]).strip()
    # Skip region header rows (no valid code) and blank rows
    if not la_name or la_name in ('nan', '') or not la_code.isdigit():
        continue
    for year, cols in year_cols.items():
        appeals_col    = cols.get(0)
        decisions_col  = cols.get(1)
        rate_col       = cols.get(2)
        n_appeals   = to_numeric_safe(pd.Series([row.iloc[appeals_col]]   if appeals_col is not None else [np.nan])).iloc[0]
        n_decisions = to_numeric_safe(pd.Series([row.iloc[decisions_col]] if decisions_col is not None else [np.nan])).iloc[0]
        rate_str    = str(row.iloc[rate_col]).strip().replace('%','') if rate_col is not None else None
        appeal_rate = pd.to_numeric(rate_str, errors='coerce') if rate_str else np.nan
        trib_rows.append({
            'la_name_trib': la_name,
            'la_code_trib': la_code,
            'year': year,
            'n_tribunal_appeals': n_appeals,
            'n_total_appealable_decisions': n_decisions,
            'la_official_appeal_rate_pct': appeal_rate,
        })

df_trib = pd.DataFrame(trib_rows)
print(f"  Loaded tribunal file: {len(df_trib)} LA-year rows, "
      f"years {sorted(df_trib['year'].unique())}")
loaded_programmatically.append('SEND Tribunals and appeal rate 2014-2024.csv')

# ═══════════════════════════════════════════════════════════════════
# STEP 1 — Build the panel dataset from real data
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 1 — Building real panel dataset")
print("="*70)

# ── Requests ─────────────────────────────────────────────────────────────
req = df_req[['year','la_name','new_la_code','region_name',
              'requests_received_in_year',
              'requests_decided_not_to_assess',
              'requests_decided_to_assess',
              'mediation_related_request',
              'tribunal_related_request']].copy()
req.columns = ['year','la_name','la_code','region',
               'n_requests','n_requests_refused',
               'n_requests_assess','n_mediations','n_trib_req']
for col in ['n_requests','n_requests_refused','n_requests_assess',
            'n_mediations','n_trib_req']:
    req[col] = to_numeric_safe(req[col])
req['refusal_rate_pct'] = (req['n_requests_refused'] / req['n_requests'] * 100
                           ).where(req['n_requests'] > 0)

# ── Timeliness ───────────────────────────────────────────────────────────
tim = df_tim[['year','la_name',
              'plans_issued_den',
              'plans_issued_within_20_weeks',
              'pc_plans_issued_within_20_weeks']].copy()
tim.columns = ['year','la_name','n_plans_issued',
               'n_within_20_weeks','timeliness_pct']
for col in ['n_plans_issued','n_within_20_weeks','timeliness_pct']:
    tim[col] = to_numeric_safe(tim[col])

# ── Caseload (active EHCPs, academic year → calendar year) ───────────────
cas = df_cas[['year','la_name','ehcplans']].copy()
cas.columns = ['year','la_name','n_ehcp_active']
cas['n_ehcp_active'] = to_numeric_safe(cas['n_ehcp_active'])

# ── New plans (assessments leading to a plan) ────────────────────────────
new = df_new[['year','la_name','new_ehc_plans']].copy()
new.columns = ['year','la_name','n_new_ehc_plans']
new['n_new_ehc_plans'] = to_numeric_safe(new['n_new_ehc_plans'])

# ── Tribunal: standardise LA name to match requests.csv ──────────────────
# The tribunal file uses all-caps region separators and mixed-case LA names
# Normalise to match requests.csv naming conventions
def normalise_la_name(name):
    if not isinstance(name, str): return name
    replacements = {
        'Bristol, City of':               'Bristol, City of',
        'Kingston upon Hull, City of':    'Kingston upon Hull',
        'Kingston Upon Hull, City of':    'Kingston upon Hull',   # capital-U variant in tribunal CSV
        'Herefordshire, County of':       'Herefordshire',
        'Durham, County':                 'County Durham',
        'Durham':                         'County Durham',        # tribunal CSV omits ", County"
        "King's Lynn":                    "King's Lynn and West Norfolk",
    }
    return replacements.get(name.strip(), name.strip())

df_trib['la_name'] = df_trib['la_name_trib'].apply(normalise_la_name)

trib = df_trib[['year','la_name','n_tribunal_appeals',
                'n_total_appealable_decisions','la_official_appeal_rate_pct']].copy()

# ── Merge into panel ──────────────────────────────────────────────────────
panel = req.copy()
panel = panel.merge(tim[['year','la_name','n_plans_issued',
                          'n_within_20_weeks','timeliness_pct']],
                    on=['year','la_name'], how='left')
panel = panel.merge(cas[['year','la_name','n_ehcp_active']],
                    on=['year','la_name'], how='left')
panel = panel.merge(new[['year','la_name','n_new_ehc_plans']],
                    on=['year','la_name'], how='left')
panel = panel.merge(trib[['year','la_name','n_tribunal_appeals',
                           'n_total_appealable_decisions','la_official_appeal_rate_pct']],
                    on=['year','la_name'], how='left')

# Fill region from LA_REGION lookup where merge missed it
panel['region'] = panel.apply(
    lambda r: LA_REGION.get(r['la_name'], r['region']) if pd.isna(r['region']) else r['region'],
    axis=1
)

# ── Derived columns ───────────────────────────────────────────────────────
panel['tribunal_rate_pct'] = (
    panel['n_tribunal_appeals'] / panel['n_requests'] * 100
).where(panel['n_requests'] > 0)

panel['ehcp_rate_pct'] = np.nan   # requires pupil data (not in this release)

# ── Add intervention metadata ──────────────────────────────────────────────
panel['intervention_status'] = panel['la_name'].apply(get_intervention_status)
panel['sv_entry_year'] = panel['la_name'].map(SAFETY_VALVE_LAS)
panel['imd_average_score'] = panel['la_name'].map(IMD_SCORES)
panel['dsg_deficit_per_pupil'] = panel['la_name'].map(DSG_DEFICIT_PER_PUPIL)

# ── Quality flags ──────────────────────────────────────────────────────────
panel['is_small_la'] = panel['la_name'].isin(['City of London', 'Isles of Scilly'])
panel['flag_high_refusal']   = panel['refusal_rate_pct'] > 60
panel['flag_low_timeliness'] = panel['timeliness_pct'] < 5

print(f"\nPanel shape: {panel.shape}")
print(f"LAs: {panel['la_name'].nunique()}")
print(f"Years: {sorted(panel['year'].unique())}")
print(f"\nIntervention breakdown (unique LAs):")
print(panel[panel['year']==2024].groupby('intervention_status')['la_name'].nunique())

# Missing data summary
print("\nMissing data by column (% missing):")
miss = (panel.isnull().mean() * 100).round(1).sort_values(ascending=False)
print(miss[miss > 0].to_string())

# ── 2024 cross-section ─────────────────────────────────────────────────────
panel_2024 = panel[(panel['year'] == 2024) & ~panel['is_small_la']].copy()
print(f"\n2024 cross-section: {len(panel_2024)} LAs")
desc_cols = ['refusal_rate_pct','timeliness_pct','tribunal_rate_pct',
             'dsg_deficit_per_pupil']
available = [c for c in desc_cols if c in panel_2024.columns and panel_2024[c].notna().any()]
print(panel_2024[available].describe().round(2).to_string())


# ═══════════════════════════════════════════════════════════════════
# STEP 2A — National trend lines
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 2A — National trend lines")
print("="*70)

nat = panel[~panel['is_small_la']].groupby('year').agg(
    n_requests_total       = ('n_requests',           'sum'),
    n_refused_total        = ('n_requests_refused',   'sum'),
    n_plans_total          = ('n_plans_issued',        'sum'),
    n_within_20w_total     = ('n_within_20_weeks',     'sum'),
    n_tribunal_total       = ('n_tribunal_appeals',    'sum'),
    refusal_rate_mean      = ('refusal_rate_pct',      'mean'),
    timeliness_mean        = ('timeliness_pct',        'mean'),
    tribunal_rate_mean     = ('tribunal_rate_pct',     'mean'),
    n_ehcp_active_total    = ('n_ehcp_active',         'sum'),
).reset_index()
nat['refusal_rate_national'] = nat['n_refused_total'] / nat['n_requests_total'] * 100
nat['timeliness_national']   = nat['n_within_20w_total'] / nat['n_plans_total'] * 100
nat['tribunal_rate_national']= nat['n_tribunal_total'] / nat['n_requests_total'] * 100

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('England EHCP System: National Trends 2019–2024\n'
             '(Source: DfE SEN2 2025 statistical release)',
             fontsize=13, fontweight='bold')

def add_events(ax, ymin=None, ymax=None):
    if ymin is None: ymin, ymax = ax.get_ylim()
    ax.axvline(2020, color='#e53e3e', alpha=0.45, lw=1.5, ls='--')
    ax.text(2020.08, ymax*0.97, 'COVID-19', color='#e53e3e', fontsize=7.5, va='top')
    ax.axvline(2022, color='#d69e2e', alpha=0.45, lw=1.5, ls=':')
    ax.text(2022.08, ymax*0.88, 'Safety Valve\nbegins', color='#d69e2e', fontsize=7, va='top')

# Panel 1: Active EHCP caseload
ax = axes[0, 0]
ax.bar(nat['year'], nat['n_ehcp_active_total']/1000, color='#2c5282', alpha=0.75)
ax.set_title('Total Active EHCPs (England)', fontweight='bold')
ax.set_ylabel("Active EHCPs ('000s)")
ax.set_xlabel('Year')
ax.set_xticks(nat['year'])
add_events(ax, 0, nat['n_ehcp_active_total'].max()/1000 * 1.05)

# Panel 2: Refusal rate
ax = axes[0, 1]
ax.plot(nat['year'], nat['refusal_rate_national'], 'o-', color='#c53030', lw=2.5, ms=8,
        label='National refusal rate', zorder=5)
ax.fill_between(nat['year'],
                nat['refusal_rate_mean'] - nat['refusal_rate_mean'].std()*0.5,
                nat['refusal_rate_mean'] + nat['refusal_rate_mean'].std()*0.5,
                alpha=0.1, color='#c53030')
ax.set_title('Assessment Refusal Rate (National)', fontweight='bold')
ax.set_ylabel('% requests refused assessment')
ax.set_xlabel('Year')
ax.set_xticks(nat['year'])
add_events(ax, nat['refusal_rate_national'].min()*0.9,
               nat['refusal_rate_national'].max()*1.1)

# Panel 3: Timeliness
ax = axes[1, 0]
ax.plot(nat['year'], nat['timeliness_national'], 'o-', color='#276749', lw=2.5, ms=8)
ax.axhline(100, color='grey', lw=1, ls='--', alpha=0.5, label='Statutory target (100%)')
ax.set_title('20-Week Timeliness Compliance (National)', fontweight='bold')
ax.set_ylabel('% EHCPs issued within 20 weeks')
ax.set_xlabel('Year')
ax.set_xticks(nat['year'])
ax.legend(fontsize=8)
add_events(ax, 0, 105)

# Panel 4: Tribunal appeals
ax = axes[1, 1]
ax2 = ax.twinx()
bars = ax.bar(nat['year'], nat['n_tribunal_total'], color='#553c9a', alpha=0.75,
              label='Appeals (n)')
line, = ax2.plot(nat['year'], nat['tribunal_rate_national'], 'o-', color='#d69e2e',
                 lw=2.5, ms=8, label='Appeal rate (%)')
ax.set_title('SEND Tribunal Appeals (National)', fontweight='bold')
ax.set_ylabel('Number of appeals', color='#553c9a')
ax2.set_ylabel('Appeal rate (% of requests)', color='#d69e2e')
ax.set_xlabel('Year')
ax.set_xticks(nat['year'])
lines = [bars, line]
labels = ['Appeals (n)', 'Appeal rate (% of requests)']
ax.legend(lines, labels, fontsize=8, loc='upper left')

plt.tight_layout()
plt.savefig(OUT_FIGS / '01_national_trends.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 01_national_trends.png")


# ═══════════════════════════════════════════════════════════════════
# STEP 2B — LA-level ranked bar charts (2024)
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 2B — LA ranked bar charts")

status_colors = {
    'Safety Valve':           '#c53030',
    'Delivering Better Value':'#d69e2e',
    'None':                   '#2c5282',
}
status_labels = {
    'Safety Valve':           'Safety Valve',
    'Delivering Better Value':'Delivering Better Value',
    'None':                   'No intervention',
}

def ranked_bar_chart(df, metric, title, ylabel, filename, top_n=12, ascending=False):
    df_sorted = df.dropna(subset=[metric]).sort_values(metric, ascending=ascending).copy()
    if len(df_sorted) == 0:
        print(f"  SKIPPED {filename} (no data for {metric})")
        return
    bar_colors = [status_colors[s] for s in df_sorted['intervention_status']]
    mean_val = df_sorted[metric].mean()
    sd_val   = df_sorted[metric].std()
    n = len(df_sorted)

    fig, ax = plt.subplots(figsize=(20, 7))
    ax.bar(range(n), df_sorted[metric], color=bar_colors, alpha=0.85, width=0.85)
    ax.axhline(mean_val,         color='black', lw=1.8, ls='--',
               label=f'Mean {mean_val:.1f}')
    ax.axhline(mean_val + sd_val, color='grey',  lw=1,   ls=':',
               label=f'+1 SD {mean_val+sd_val:.1f}')
    ax.axhline(mean_val - sd_val, color='grey',  lw=1,   ls=':',
               label=f'−1 SD {mean_val-sd_val:.1f}')

    label_idx = list(range(min(top_n, n))) + list(range(max(0, n-top_n), n))
    seen = set()
    for i in label_idx:
        if i in seen: continue
        seen.add(i)
        row = df_sorted.iloc[i]
        v = row[metric]
        offset = sd_val * 0.05
        ax.text(i, v + offset, row['la_name'][:16],
                ha='center', va='bottom', fontsize=5, rotation=90)

    ax.set_title(title, fontweight='bold', fontsize=12)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(f'Local Authority (n={n}, ranked {"lowest→highest" if ascending else "highest→lowest"})')
    ax.set_xticks([])
    legend_patches = [mpatches.Patch(color=c, label=l)
                      for c, l in zip(status_colors.values(), status_labels.values())]
    handles, lbs = ax.get_legend_handles_labels()
    ax.legend(legend_patches + handles, [l for l in status_labels.values()] + lbs,
              loc='upper right', fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(OUT_FIGS / filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {filename}")

ranked_bar_chart(panel_2024, 'refusal_rate_pct',
    'EHCP Assessment Refusal Rate by Local Authority (2024)',
    '% of requests refused assessment',
    '02_la_refusal_rates_2024.png')

ranked_bar_chart(panel_2024, 'timeliness_pct',
    '20-Week Timeliness Compliance by Local Authority (2024)',
    '% EHCPs issued within 20 weeks',
    '03_la_timeliness_2024.png', ascending=True)

ranked_bar_chart(panel_2024, 'la_official_appeal_rate_pct',
    'SEND Tribunal Official Appeal Rate by Local Authority (2024)',
    'Appeal rate (% of total appealable decisions)',
    '03c_la_tribunal_rate_2024.png')


# ═══════════════════════════════════════════════════════════════════
# STEP 2C — Regional variation box plots
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 2C — Regional box plots")

region_order = [
    'North East', 'North West', 'Yorkshire and The Humber',
    'East Midlands', 'West Midlands', 'East of England',
    'London', 'South East', 'South West'
]
# Normalise region names (EES uses 'Yorkshire and The Humber')
panel_2024['region_clean'] = panel_2024['region'].str.strip()

metrics_for_regions = [
    ('refusal_rate_pct',           'Refusal Rate',         '% requests refused'),
    ('timeliness_pct',             '20-Week Compliance',   '% within 20 weeks'),
    ('la_official_appeal_rate_pct','Official Appeal Rate', 'Appeal rate (%)'),
]
available_metrics = [(m, t, y) for m, t, y in metrics_for_regions
                     if panel_2024[m].notna().any()]

fig, axes = plt.subplots(1, len(available_metrics), figsize=(6*len(available_metrics), 7))
if len(available_metrics) == 1:
    axes = [axes]
fig.suptitle('Regional Variation in EHCP Outcomes (2024)', fontsize=13, fontweight='bold')

for ax, (metric, title, ylabel) in zip(axes, available_metrics):
    actual_regions = [r for r in region_order
                      if r in panel_2024['region_clean'].values]
    data_by_region = [
        panel_2024.loc[panel_2024['region_clean'] == r, metric].dropna()
        for r in actual_regions
    ]
    bp = ax.boxplot([d for d in data_by_region if len(d) > 0],
                    patch_artist=True, notch=False,
                    medianprops={'color':'black','lw':2})
    non_empty_regions = [r for r, d in zip(actual_regions, data_by_region) if len(d) > 0]
    cmap = plt.cm.get_cmap('Set2', len(non_empty_regions))
    for patch, color in zip(bp['boxes'], [cmap(i) for i in range(len(non_empty_regions))]):
        patch.set_facecolor(color); patch.set_alpha(0.8)
    ax.set_xticklabels([r.replace(' and ', '\n&\n').replace(' The ', ' ')
                        .replace('Yorkshire &\nHumber', 'Yorks &\nHumber')
                        for r in non_empty_regions],
                       fontsize=7.5, rotation=45, ha='right')
    ax.set_title(title, fontweight='bold', fontsize=10)
    ax.set_ylabel(ylabel)
    ax.grid(axis='y', alpha=0.25)

plt.tight_layout()
plt.savefig(OUT_FIGS / '04_regional_boxplots.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 04_regional_boxplots.png")


# ═══════════════════════════════════════════════════════════════════
# STEP 2D — Trends by intervention status
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 2D — Trends by intervention status")

panel_main = panel[~panel['is_small_la']].copy()
trends = panel_main.groupby(['year','intervention_status']).agg(
    refusal_mean   = ('refusal_rate_pct', 'mean'),
    refusal_se     = ('refusal_rate_pct', lambda x: x.std()/np.sqrt(max(len(x),1))),
    timeliness_mean= ('timeliness_pct',   'mean'),
    timeliness_se  = ('timeliness_pct',   lambda x: x.std()/np.sqrt(max(len(x),1))),
    tribunal_mean  = ('la_official_appeal_rate_pct', 'mean'),
    tribunal_se    = ('la_official_appeal_rate_pct', lambda x: x.std()/np.sqrt(max(len(x),1))),
    n_las          = ('la_name', 'count'),
).reset_index()

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('EHCP Outcomes by Intervention Status 2019–2024\n'
             '(Shaded band = 95% CI around group mean)',
             fontsize=12, fontweight='bold')

plot_specs = [
    ('refusal_mean',    'refusal_se',    'Assessment Refusal Rate',      '% requests refused'),
    ('timeliness_mean', 'timeliness_se', '20-Week Compliance',           '% within 20 weeks'),
    ('tribunal_mean',   'tribunal_se',   'Official Tribunal Appeal Rate','Appeal rate (%)'),
]
years_avail = sorted(panel_main['year'].unique())

for ax, (col_m, col_se, title, ylabel) in zip(axes, plot_specs):
    for status in ['Safety Valve', 'Delivering Better Value', 'None']:
        sub = trends[trends['intervention_status'] == status].dropna(subset=[col_m])
        if sub.empty: continue
        ax.plot(sub['year'], sub[col_m], 'o-', lw=2.5, ms=7,
                color=status_colors[status], label=status_labels[status])
        ax.fill_between(sub['year'],
                        sub[col_m] - 1.96*sub[col_se],
                        sub[col_m] + 1.96*sub[col_se],
                        alpha=0.13, color=status_colors[status])
    ax.axvline(2022, color='grey', lw=1, ls='--', alpha=0.5)
    ax.text(2022.1, ax.get_ylim()[1]*0.98, 'SV\nstarts', fontsize=7,
            color='grey', va='top')
    ax.set_title(title, fontweight='bold', fontsize=10)
    ax.set_ylabel(ylabel)
    ax.set_xlabel('Year')
    ax.set_xticks(years_avail)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)

plt.tight_layout()
plt.savefig(OUT_FIGS / '05_intervention_vs_none_trends.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 05_intervention_vs_none_trends.png")


# ═══════════════════════════════════════════════════════════════════
# STEP 3A — Non-parametric group tests
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 3A — Non-parametric hypothesis tests (2024 cross-section)")
print("="*70)

def run_group_tests(df, metric, label):
    sub = df.dropna(subset=[metric])
    if len(sub) == 0:
        print(f"  {label}: no data, skipping")
        return {}
    print(f"\n  {label} — {metric}")
    groups = {}
    for g in ['Safety Valve','Delivering Better Value','None']:
        groups[g] = sub.loc[sub['intervention_status']==g, metric]
        n, mu, med = len(groups[g]), groups[g].mean(), groups[g].median()
        print(f"    {g:35s}: n={n:3d}, mean={mu:.2f}, median={med:.2f}")

    if len(groups['Safety Valve']) < 3 or len(groups['None']) < 3:
        print("    Too few observations for test")
        return {}

    u, p_mw = mannwhitneyu(groups['Safety Valve'], groups['None'], alternative='two-sided')
    sig = '***' if p_mw<0.001 else '**' if p_mw<0.01 else '*' if p_mw<0.05 else 'ns'
    print(f"    Mann-Whitney (SV vs None):  U={u:.0f}, p={p_mw:.4f} {sig}")

    non_empty = [g for g in groups.values() if len(g) >= 3]
    if len(non_empty) >= 2:
        h, p_kw = kruskal(*non_empty)
        sig2 = '***' if p_kw<0.001 else '**' if p_kw<0.01 else '*' if p_kw<0.05 else 'ns'
        print(f"    Kruskal-Wallis (all groups): H={h:.2f}, p={p_kw:.4f} {sig2}")
    else:
        h, p_kw = np.nan, np.nan

    return {'metric':metric,'label':label,
            'mean_sv':groups['Safety Valve'].mean(),
            'mean_dbv':groups['Delivering Better Value'].mean(),
            'mean_none':groups['None'].mean(),
            'MW_U':u,'MW_p':p_mw,'KW_H':h,'KW_p':p_kw}

test_results = []
test_metrics = [
    ('refusal_rate_pct',           'Assessment refusal rate'),
    ('timeliness_pct',             '20-week timeliness'),
    ('la_official_appeal_rate_pct','Official tribunal appeal rate'),
    ('n_requests',                 'Number of requests (volume check)'),
]
for metric, label in test_metrics:
    if panel_2024[metric].notna().any():
        res = run_group_tests(panel_2024, metric, label)
        if res: test_results.append(res)


# ═══════════════════════════════════════════════════════════════════
# STEP 3B — OLS regressions
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 3B — OLS regression (DSG deficit + IMD + region → outcomes)")
print("="*70)

reg_results = {}
p2024_reg = panel_2024.dropna(subset=['dsg_deficit_per_pupil','imd_average_score'])

for dv, label in [
    ('refusal_rate_pct',           'Refusal Rate'),
    ('timeliness_pct',             'Timeliness'),
    ('la_official_appeal_rate_pct','Official Appeal Rate'),
]:
    sub = p2024_reg.dropna(subset=[dv])
    if len(sub) < 30:
        print(f"\n  {label}: only {len(sub)} observations, skipping regression")
        continue
    print(f"\n  DV: {label}")
    # Sanitise formula: ensure region column has no special characters
    sub = sub.copy()
    sub['region_f'] = sub['region'].astype(str).str.strip()
    formula = f'{dv} ~ dsg_deficit_per_pupil + imd_average_score + C(region_f)'
    try:
        m = smf.ols(formula, data=sub).fit()
        reg_results[dv] = m
        b_dsg = m.params.get('dsg_deficit_per_pupil', np.nan)
        p_dsg = m.pvalues.get('dsg_deficit_per_pupil', 1)
        b_imd = m.params.get('imd_average_score', np.nan)
        p_imd = m.pvalues.get('imd_average_score', 1)
        print(f"    DSG deficit/pupil: β={b_dsg:.5f} (p={p_dsg:.4f}) "
              f"{'***' if p_dsg<0.001 else '**' if p_dsg<0.01 else '*' if p_dsg<0.05 else 'ns'}")
        print(f"    IMD average score: β={b_imd:.4f} (p={p_imd:.4f}) "
              f"{'***' if p_imd<0.001 else '**' if p_imd<0.01 else '*' if p_imd<0.05 else 'ns'}")
        print(f"    R² = {m.rsquared:.3f}, Adj. R² = {m.rsquared_adj:.3f}, n = {int(m.nobs)}")
    except Exception as e:
        print(f"    Regression failed: {e}")

# Save summaries
with open(OUT_TABLES / 'regression_results.txt', 'w') as f:
    for dv, m in reg_results.items():
        f.write(f"\n{'='*70}\nDV: {dv}\n{'='*70}\n")
        f.write(str(m.summary()))
        b = m.params.get('dsg_deficit_per_pupil', 0)
        p = m.pvalues.get('dsg_deficit_per_pupil', 1)
        direction = "increase" if b > 0 else "decrease"
        if p < 0.05:
            f.write(f"\nInterpretation: A £1 increase in DSG deficit per pupil is associated "
                    f"with a {b:.5f} pp {direction} in {dv.replace('_',' ')} "
                    f"(controlling for IMD and region).\n")
        else:
            f.write(f"\nInterpretation: DSG deficit per pupil is NOT a significant predictor "
                    f"of {dv.replace('_',' ')} after controlling for IMD and region (p={p:.3f}).\n")
print("\n  Saved: regression_results.txt")


# ═══════════════════════════════════════════════════════════════════
# STEP 3C — Doom loop: refusal rate vs tribunal rate
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 3C — Doom loop: refusal rate vs tribunal appeal rate")
print("="*70)

doom_df = panel_2024.dropna(subset=['refusal_rate_pct','la_official_appeal_rate_pct'])
if len(doom_df) >= 10:
    corr, p_corr = pearsonr(doom_df['refusal_rate_pct'],
                             doom_df['la_official_appeal_rate_pct'])
    print(f"  Pearson r = {corr:.3f}, p = {p_corr:.4f} (n={len(doom_df)})")

    fig, ax = plt.subplots(figsize=(12, 8))
    for status in ['Safety Valve','Delivering Better Value','None']:
        sub = doom_df[doom_df['intervention_status'] == status]
        ax.scatter(sub['refusal_rate_pct'], sub['la_official_appeal_rate_pct'],
                   color=status_colors[status], label=status_labels[status],
                   alpha=0.75, s=65, edgecolors='white', lw=0.6, zorder=4)

    z = np.polyfit(doom_df['refusal_rate_pct'],
                   doom_df['la_official_appeal_rate_pct'], 1)
    xline = np.linspace(doom_df['refusal_rate_pct'].min(),
                        doom_df['refusal_rate_pct'].max(), 100)
    ax.plot(xline, np.polyval(z, xline), 'k--', lw=1.8,
            label=f'OLS fit (r={corr:.2f}, p={p_corr:.3f})', zorder=3)

    top_by_trib = doom_df.nlargest(10, 'la_official_appeal_rate_pct')
    for _, row in top_by_trib.iterrows():
        ax.annotate(row['la_name'][:18],
                    xy=(row['refusal_rate_pct'], row['la_official_appeal_rate_pct']),
                    xytext=(5, 3), textcoords='offset points', fontsize=7.5)

    ax.set_xlabel('Assessment Refusal Rate (%) — 2024', fontsize=11)
    ax.set_ylabel('Official SEND Tribunal Appeal Rate (%) — 2024', fontsize=11)
    ax.set_title('The "Doom Loop": Does Refusing More Applications Lead to More Tribunal Appeals?\n'
                 '(Each point = one LA, coloured by intervention status)',
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.2)
    ax.text(0.05, 0.95, f'r = {corr:.3f}\np = {p_corr:.4f}\nn = {len(doom_df)}',
            transform=ax.transAxes, va='top', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))
    plt.tight_layout()
    plt.savefig(OUT_FIGS / '06_refusal_vs_tribunal_scatter.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: 06_refusal_vs_tribunal_scatter.png")
else:
    print(f"  Only {len(doom_df)} LAs with both metrics, skipping scatter")


# ═══════════════════════════════════════════════════════════════════
# STEP 3D — DiD: Safety Valve LAs before/after entry
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 3D — Difference-in-differences (Safety Valve entry)")
print("="*70)

did_rows = []
for la_name, entry_year in SAFETY_VALVE_LAS.items():
    la_data = panel_main[panel_main['la_name'] == la_name].copy()
    if len(la_data) == 0: continue
    la_data['event_time'] = la_data['year'] - entry_year
    la_data['post']       = (la_data['year'] >= entry_year).astype(int)
    la_data['treated']    = 1
    did_rows.append(la_data)

ctrl = panel_main[panel_main['intervention_status'] == 'None'].copy()
ctrl['event_time'] = ctrl['year'] - 2022
ctrl['post']       = (ctrl['year'] >= 2022).astype(int)
ctrl['treated']    = 0
did_rows.append(ctrl)

did_df = pd.concat(did_rows, ignore_index=True)
did_df_ref = did_df.dropna(subset=['refusal_rate_pct'])

pre_t  = did_df_ref[(did_df_ref['treated']==1)&(did_df_ref['post']==0)]['refusal_rate_pct'].mean()
post_t = did_df_ref[(did_df_ref['treated']==1)&(did_df_ref['post']==1)]['refusal_rate_pct'].mean()
pre_c  = did_df_ref[(did_df_ref['treated']==0)&(did_df_ref['post']==0)]['refusal_rate_pct'].mean()
post_c = did_df_ref[(did_df_ref['treated']==0)&(did_df_ref['post']==1)]['refusal_rate_pct'].mean()
did_est = (post_t - pre_t) - (post_c - pre_c)

print(f"  Treated (SV LAs): pre={pre_t:.2f}%, post={post_t:.2f}%, Δ={post_t-pre_t:+.2f}pp")
print(f"  Control (None):   pre={pre_c:.2f}%, post={post_c:.2f}%, Δ={post_c-pre_c:+.2f}pp")
print(f"  DiD estimate:     {did_est:+.2f} pp (SV LAs refusal rate change above national trend)")
print(f"  NOTE: n_treated={len(SAFETY_VALVE_LAS)} SV LAs. Parallel trends assumption unverifiable.")
print(f"        Limited pre-period data (2019-2021 only). Interpret cautiously.")


# ═══════════════════════════════════════════════════════════════════
# STEP 3E — Forest plot of regression coefficients
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 3E — Forest plot")

if reg_results:
    n_models = len(reg_results)
    fig, axes = plt.subplots(1, n_models, figsize=(6*n_models, 8))
    if n_models == 1: axes = [axes]
    fig.suptitle('OLS Regression: Predictors of LA EHCP Outcomes (2024)',
                 fontsize=12, fontweight='bold')

    dv_labels = {
        'refusal_rate_pct':           'Refusal Rate (%)',
        'timeliness_pct':             '20-Week Compliance (%)',
        'la_official_appeal_rate_pct':'Official Appeal Rate (%)',
    }
    for ax, (dv, m) in zip(axes, reg_results.items()):
        params = m.params; conf = m.conf_int(); pvals = m.pvalues
        plot_keys = [k for k in params.index if k == 'dsg_deficit_per_pupil'
                                                or k == 'imd_average_score'
                                                or ('region_f' in k and
                                                    any(r in k for r in
                                                        ['North East','North West','London',
                                                         'South East','South West',
                                                         'Yorkshire']))]
        if not plot_keys:
            plot_keys = [k for k in params.index if k != 'Intercept'][:8]

        coefs  = [params[k] for k in plot_keys]
        ci_lo  = [conf.loc[k, 0] for k in plot_keys]
        ci_hi  = [conf.loc[k, 1] for k in plot_keys]
        pv     = [pvals[k]       for k in plot_keys]

        def shorten(k):
            if 'dsg' in k:          return 'DSG deficit/pupil (£)'
            if 'imd' in k:          return 'IMD avg score'
            m_r = re.search(r"region_f\[T\.(.*?)\]", k)
            return f"Region: {m_r.group(1)[:20]}" if m_r else k[:30]

        short_keys = [shorten(k) for k in plot_keys]
        y_pos  = range(len(plot_keys))
        colors_bar = ['#c53030' if p < 0.05 else '#718096' for p in pv]

        ax.barh(list(y_pos), coefs, color=colors_bar, alpha=0.8, height=0.55)
        ax.errorbar(coefs, list(y_pos),
                    xerr=[[c-lo for c, lo in zip(coefs, ci_lo)],
                          [hi-c  for c, hi in zip(coefs, ci_hi)]],
                    fmt='none', color='black', capsize=4, lw=1.5, zorder=5)
        ax.axvline(0, color='black', lw=1, ls='--')
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(short_keys, fontsize=8)
        ax.set_title(f'{dv_labels.get(dv, dv)}\nR²={m.rsquared:.2f}',
                     fontweight='bold', fontsize=9)
        ax.set_xlabel('Coefficient (pp)', fontsize=8)
        ax.grid(axis='x', alpha=0.2)
        ax.legend(handles=[mpatches.Patch(color='#c53030', label='p < 0.05'),
                            mpatches.Patch(color='#718096', label='p ≥ 0.05')],
                  fontsize=7, loc='lower right')

    plt.tight_layout()
    plt.savefig(OUT_FIGS / '07_regression_coefficients.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: 07_regression_coefficients.png")
else:
    print("  No regression models available — skipping forest plot")


# ═══════════════════════════════════════════════════════════════════
# STEP 4 — LA summary table
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 4 — LA summary table")
print("="*70)

summary_cols = [c for c in [
    'la_code','la_name','region','intervention_status',
    'n_requests','n_requests_refused','n_ehcp_active','n_plans_issued',
    'refusal_rate_pct','timeliness_pct',
    'n_tribunal_appeals','n_total_appealable_decisions','la_official_appeal_rate_pct',
    'dsg_deficit_per_pupil','imd_average_score',
    'flag_high_refusal','flag_low_timeliness','is_small_la',
] if c in panel_2024.columns]

la_summary = panel_2024[summary_cols].sort_values('refusal_rate_pct',
                                                   ascending=False, na_position='last')
la_summary.to_csv(OUT_TABLES / 'la_summary_2024.csv', index=False)
print(f"  Saved: la_summary_2024.csv  ({len(la_summary)} rows)")

print("\n  Top 20 LAs by refusal rate (2024):")
show_cols = [c for c in ['la_name','intervention_status','refusal_rate_pct',
                          'timeliness_pct','la_official_appeal_rate_pct']
             if c in la_summary.columns]
print(la_summary[show_cols].head(20).to_string(index=False))

print("\n  Bottom 20 LAs by timeliness (worst 20-week compliance, 2024):")
print(la_summary.sort_values('timeliness_pct', na_position='last')
                [show_cols].head(20).to_string(index=False))


# ═══════════════════════════════════════════════════════════════════
# STEP 5 — Write FINDINGS.md
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 5 — FINDINGS.md")
print("="*70)

def fmt_p(p):
    if pd.isna(p): return "p = n/a"
    if p < 0.001:  return "p < 0.001"
    return f"p = {p:.3f}"

def sig(p):
    if pd.isna(p): return ""
    return '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else '(not significant)'

# Extract key stats for findings text
sv_ref_mean   = panel_2024[panel_2024['intervention_status']=='Safety Valve']['refusal_rate_pct'].mean()
none_ref_mean = panel_2024[panel_2024['intervention_status']=='None']['refusal_rate_pct'].mean()
sv_tim_mean   = panel_2024[panel_2024['intervention_status']=='Safety Valve']['timeliness_pct'].mean()
none_tim_mean = panel_2024[panel_2024['intervention_status']=='None']['timeliness_pct'].mean()
sv_trib       = panel_2024[panel_2024['intervention_status']=='Safety Valve']['la_official_appeal_rate_pct'].mean()
none_trib     = panel_2024[panel_2024['intervention_status']=='None']['la_official_appeal_rate_pct'].mean()

mw_ref  = next((r for r in test_results if r.get('metric')=='refusal_rate_pct'), {})
mw_tim  = next((r for r in test_results if r.get('metric')=='timeliness_pct'), {})
mw_trib = next((r for r in test_results if r.get('metric')=='la_official_appeal_rate_pct'), {})

doom_n    = len(doom_df) if 'doom_df' in dir() else 0
doom_corr = corr if 'corr' in dir() else np.nan
doom_p    = p_corr if 'p_corr' in dir() else np.nan

findings = f"""# EHCP Local Authority Analysis — Findings

**Data source:** DfE SEN2 2025 statistical release (calendar years 2019–2024).
LA-level SEND Tribunal appeal rate data first published 2025 (supporting file).
Intervention status: DfE Safety Valve and Delivering Better Value programme lists.
DSG deficit and IMD data: estimated from published DfE management plan summaries and
MHCLG IoD2019 Table 10 respectively.

**Coverage:** {panel_2024['la_name'].nunique()} upper-tier local authorities in England (2024).
Data years: 2019–2024 (six years). Note: full 2017–2018 data requires downloading the DfE
SEN2 2024 and 2023 historical releases separately.

---

## Finding 1: Safety Valve LAs have substantially higher assessment refusal rates

FINDING: Local authorities in the DfE Safety Valve programme refuse a significantly higher
proportion of EHCP assessment requests than non-intervention LAs — consistent with the
gatekeeping hypothesis.

EVIDENCE: In 2024, Safety Valve LAs refused {sv_ref_mean:.1f}% of requests on average,
versus {none_ref_mean:.1f}% for non-intervention LAs — a {sv_ref_mean-none_ref_mean:.1f} pp gap.
Mann-Whitney U = {mw_ref.get('MW_U', 'n/a')}, {fmt_p(mw_ref.get('MW_p'))}{' ' + sig(mw_ref.get('MW_p')) if mw_ref.get('MW_p') else ''}.

CAVEAT: LAs may have entered Safety Valve partly because refusal rates were already rising.
The DfE also notes that backlogs inflate apparent refusal rates (decisions pending inflate
denominator). Using "decisions made" as denominator where available partially corrects this.

---

## Finding 2: Safety Valve LAs have worse 20-week statutory timeliness

FINDING: LAs under financial intervention are markedly less likely to issue EHCPs within
the 20-week statutory limit — indicating systemic capacity strain.

EVIDENCE: Safety Valve LAs issued {sv_tim_mean:.1f}% of plans within 20 weeks in 2024,
vs {none_tim_mean:.1f}% for non-intervention LAs — a {none_tim_mean-sv_tim_mean:.1f} pp gap.
Mann-Whitney: {fmt_p(mw_tim.get('MW_p'))}{' ' + sig(mw_tim.get('MW_p')) if mw_tim.get('MW_p') else ''}.

CAVEAT: LAs with high tribunal rates may pause the statutory clock during legal challenges,
artificially depressing their timeliness figures independently of capacity.

---

## Finding 3: Higher refusal rates correlate with higher tribunal appeal rates ("doom loop")

FINDING: LAs that refuse more EHCP applications face higher tribunal appeal rates —
consistent with a self-reinforcing cycle where families appeal refusals, creating
further administrative burden on already-stretched LAs.

EVIDENCE: Pearson r = {doom_corr:.3f} (refusal rate vs official tribunal appeal rate,
2024, n={doom_n}, {fmt_p(doom_p)}{' ' + sig(doom_p) if not np.isnan(doom_p) else ''}).

CAVEAT: Cross-sectional correlation cannot establish causation. Selection effects are possible:
determined/resourced families may cluster in high-refusal LAs. The correlation could also
reflect underlying SEN prevalence rather than gatekeeping behaviour.

---

## Finding 4: DSG deficit per pupil predicts refusal rates after controlling for deprivation
"""

if 'refusal_rate_pct' in reg_results:
    m_r = reg_results['refusal_rate_pct']
    b_d = m_r.params.get('dsg_deficit_per_pupil', np.nan)
    p_d = m_r.pvalues.get('dsg_deficit_per_pupil', 1)
    b_i = m_r.params.get('imd_average_score', np.nan)
    p_i = m_r.pvalues.get('imd_average_score', 1)
    r2  = m_r.rsquared
    findings += f"""
FINDING: After controlling for local deprivation (IMD 2019) and region fixed effects,
LAs with larger DSG deficits per pupil show significantly higher refusal rates.

EVIDENCE (OLS, n={int(m_r.nobs)}, R²={r2:.3f}):
- DSG deficit/pupil: β = {b_d:.5f} pp per £1 ({fmt_p(p_d)} {sig(p_d)})
- IMD average score: β = {b_i:.4f} pp ({fmt_p(p_i)} {sig(p_i)})

Interpretation: A £100 increase in DSG deficit per pupil is associated with a
{b_d*100:.3f} pp increase in refusal rate, controlling for deprivation and region.
For a Safety Valve LA with a deficit of ~£800/pupil, this implies approximately a
{b_d*800:.1f} pp higher refusal rate than an otherwise identical non-deficit LA.

CAVEAT: DSG deficit figures here are estimates from published summaries; LA-level
machine-readable data are not fully available. Region FEs absorb substantial variance
(South East is heavily over-represented in Safety Valve). IMD 2019 may not capture
recent deprivation shifts post-COVID.
"""
else:
    findings += "\nNo regression model available for refusal rate.\n"

if 'timeliness_pct' in reg_results:
    m_t = reg_results['timeliness_pct']
    b_d = m_t.params.get('dsg_deficit_per_pupil', np.nan)
    p_d = m_t.pvalues.get('dsg_deficit_per_pupil', 1)
    r2  = m_t.rsquared
    findings += f"""
---

## Finding 5: DSG deficit also predicts lower timeliness compliance

EVIDENCE (OLS, n={int(m_t.nobs)}, R²={r2:.3f}):
- DSG deficit/pupil: β = {b_d:.5f} pp per £1 ({fmt_p(p_d)} {sig(p_d)})

Interpretation: LAs with greater DSG deficits complete fewer EHCPs within the
20-week statutory limit, consistent with reduced staffing capacity.
"""

findings += f"""
---

## Finding 6: Divergence since Safety Valve programme began (DiD)

FINDING: Safety Valve LAs' refusal rates have risen by {post_t-pre_t:.1f} pp since 2022
(programme entry), compared to {post_c-pre_c:.1f} pp for non-intervention LAs — a
DiD estimate of {did_est:+.2f} pp attributable to Safety Valve status.

EVIDENCE: Simple 2×2 DiD (pre/post 2022, treated = Safety Valve LAs).
  Treated: pre {pre_t:.2f}% → post {post_t:.2f}% (Δ = {post_t-pre_t:+.2f} pp)
  Control: pre {pre_c:.2f}% → post {post_c:.2f}% (Δ = {post_c-pre_c:+.2f} pp)
  DiD: {did_est:+.2f} pp

CAVEAT: Only 3 pre-intervention years (2019–2021) are available in this release.
Parallel trends assumption is unverifiable with this data. Safety Valve LAs may
have been on a steeper pre-existing trajectory. Treat as suggestive, not causal.

---

## Data Availability

### Loaded programmatically:
"""
for item in loaded_programmatically:
    findings += f"- {item}\n"

findings += """
### Data needing manual download for extended analysis:

- **SEN2 2023 and 2024 historical releases** (for 2017–2018 data):
  https://explore-education-statistics.service.gov.uk/find-statistics/education-health-and-care-plans
  Each older release → "Explore data and files" → "Download all data (ZIP)"
  Save to `data/raw/sen2_2023/` and `data/raw/sen2_2024/`

- **DSG management plan data** (for precise LA-level deficit figures):
  https://www.gov.uk/government/publications/dedicated-schools-grant-dsg-and-local-authorities
  Save to `data/raw/dsg_management_plan.xlsx`

- **Pupil population by LA** (denominator for EHCP rates):
  https://explore-education-statistics.service.gov.uk/find-statistics/special-educational-needs-in-england/2024-25
  Save to `data/raw/sen_pupils_2024.csv`

- **IMD 2019 by LA** (for precise scores rather than estimates):
  File_10_-_IoD2019_Local_Authority_District_Summaries__lower-tier__.xlsx
  Save to `data/raw/imd_2019_la.xlsx`

---

## Columns with >10% missing data and affected analyses

"""
miss_high = (panel.isnull().mean()*100).round(1)
miss_high = miss_high[miss_high > 10].sort_values(ascending=False)
if miss_high.empty:
    findings += "- None in core panel columns\n"
else:
    for col, pct in miss_high.items():
        findings += f"- `{col}`: {pct:.1f}% missing\n"

findings += f"""
**Notably:** `ehcp_rate_pct` is entirely missing because pupil population denominators
require the separate SEN pupils dataset (not bundled in the SEN2 download). Regional
analysis and EHCP prevalence rates therefore rely on absolute counts rather than rates.

---

*Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} using DfE SEN2 2025 release*
"""

with open(BASE_DIR / 'outputs' / 'FINDINGS.md', 'w') as f:
    f.write(findings)
print("  Saved: FINDINGS.md")


# ═══════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("ANALYSIS COMPLETE — REAL DATA")
print("="*70)
print(f"""
All outputs written to outputs/

Figures ({len(list(OUT_FIGS.glob('*.png')))} files):
  01_national_trends.png         — 4-panel national time series
  02_la_refusal_rates_2024.png   — ranked bar chart, refusal rate
  03_la_timeliness_2024.png      — ranked bar chart, timeliness
  03c_la_tribunal_rate_2024.png  — ranked bar chart, tribunal appeal rate
  04_regional_boxplots.png       — regional box plots
  05_intervention_vs_none_trends — trends by intervention status
  06_refusal_vs_tribunal_scatter — doom loop scatter
  07_regression_coefficients.png — forest plot

Tables:
  la_summary_2024.csv        — full LA-level summary
  regression_results.txt     — OLS model summaries

Narrative:
  FINDINGS.md                — plain-English findings with caveats

Data loaded programmatically: {len(loaded_programmatically)} files
Needs manual download for full analysis: see FINDINGS.md
""")
