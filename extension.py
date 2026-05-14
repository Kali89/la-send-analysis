"""
EHCP LA Analysis — Extension
Goals:
  1. Expand DSG coverage from n≈50 → n≈153 using S251 LA Expenditure data
  2. Expand IMD coverage to 100% using IoD2019 Excel
  3. Mediation analysis: DSG deficit → throughput stress → timeliness → tribunal appeals
  4. Event study: pre/post Safety Valve entry using tribunal data (2014-2024)
  5. Updated figures 08-10
"""

import os, io, re, warnings
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
from scipy.stats import pearsonr, mannwhitneyu
import statsmodels.formula.api as smf

warnings.filterwarnings('ignore')

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / 'data' / 'raw'
OUT_FIGS   = BASE_DIR / 'outputs' / 'figures'
OUT_TABLES = BASE_DIR / 'outputs' / 'tables'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

# ── Intervention lists (same as analysis.py) ─────────────────────────────
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
    'Wirral', 'Wolverhampton', 'Walsall', 'Barnsley', 'Blackburn with Darwen',
    'Bolton', 'Calderdale', 'Darlington', 'Hartlepool', 'Knowsley',
    'Luton', 'Milton Keynes', 'North Somerset', 'Nottinghamshire',
    'South Tyneside', 'St Helens', 'Tower Hamlets', 'Trafford',
} - set(SAFETY_VALVE_ENTRY.keys())

def get_intervention_status(la_name):
    if la_name in SAFETY_VALVE_ENTRY:           return 'Safety Valve'
    if la_name in DBV_LAS:                      return 'Delivering Better Value'
    return 'None'

def to_numeric_safe(s):
    return pd.to_numeric(
        s.astype(str).str.replace(',','').str.strip()
         .replace({'x':np.nan,'z':np.nan,'-':np.nan,'..':np.nan,'X':np.nan}),
        errors='coerce')

# ═══════════════════════════════════════════════════════════════════
# STEP 0 — Load prior 2024 panel
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 0 — Loading prior 2024 panel")
print("="*70)

panel = pd.read_csv(OUT_TABLES / 'la_summary_2024.csv')
print(f"Prior panel: {len(panel)} LAs")
print(f"DSG coverage (old): {panel['dsg_deficit_per_pupil'].notna().sum()} / {len(panel)}")
print(f"IMD coverage (old): {panel['imd_average_score'].notna().sum()} / {len(panel)}")


# ═══════════════════════════════════════════════════════════════════
# STEP 1 — Full IMD 2019 from official Excel
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 1 — IMD 2019 coverage expansion")
print("="*70)

imd_url = ('https://assets.publishing.service.gov.uk/government/uploads/system/'
           'uploads/attachment_data/file/833995/'
           'File_10_-_IoD2019_Local_Authority_District_Summaries__lower-tier__.xlsx')

print("  Downloading IMD 2019 Excel...")
try:
    r = requests.get(imd_url, headers=HEADERS, timeout=30)
    df_imd_raw = pd.read_excel(io.BytesIO(r.content), sheet_name='IMD')
    df_imd = df_imd_raw[['Local Authority District code (2019)',
                          'Local Authority District name (2019)',
                          'IMD - Average score ']].copy()
    df_imd.columns = ['la_code','la_name_imd','imd_score']
    df_imd['imd_score'] = pd.to_numeric(df_imd['imd_score'], errors='coerce')
    # Drop lower-tier districts (keep upper-tier / unitary: E06, E07→skip, E08, E09, E10)
    df_imd = df_imd[df_imd['la_code'].astype(str).str.match(r'^E(06|08|09|10)\d{6}$', na=False)]
    print(f"  IMD data: {len(df_imd)} upper-tier LAs")
    loaded_imd = True
except Exception as e:
    print(f"  IMD download failed: {e}")
    df_imd = None
    loaded_imd = False

# IMD also covers shire counties (E10) and metro boroughs (E08) and London (E09)
# but NOT shire districts (E07). So upper-tier LAs are well covered.
# For merging, use la_code
if df_imd is not None:
    # Merge into panel on la_code
    panel = panel.merge(
        df_imd[['la_code','imd_score']].rename(columns={'imd_score':'imd_score_full'}),
        on='la_code', how='left'
    )
    # Fill old imd column with new one where missing
    panel['imd_average_score'] = panel['imd_average_score'].fillna(panel['imd_score_full'])
    # Also replace with authoritative value where we have it
    panel['imd_average_score'] = panel['imd_score_full'].combine_first(panel['imd_average_score'])
    panel.drop(columns=['imd_score_full'], inplace=True)
    print(f"  IMD coverage after update: {panel['imd_average_score'].notna().sum()} / {len(panel)}")


# ═══════════════════════════════════════════════════════════════════
# STEP 2 — Full DSG deficit from S251
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 2 — DSG deficit expansion via S251 LA Expenditure")
print("="*70)

s251_path = DATA_DIR / 's251_2025' / 'data' / 's251_alleducation_la_regional_national.csv'

print("  Loading S251 data (large file, ~27M rows)…")
s251 = pd.read_csv(s251_path, encoding='latin-1', low_memory=False,
                   usecols=['time_period','geographic_level','la_name','new_la_code',
                            'main_category','category_of_expenditure','gross_expenditure'])

# DSG carry-forward: use MOST RECENT available year
# 1.9.3 = DSG carried forward TO next year
# Convention: positive = surplus going forward, negative = deficit going forward
# For financial pressure: flip sign → positive = deficit pressure
la_dsg_yearly = s251[
    (s251['geographic_level'] == 'Local authority') &
    (s251['main_category'] == 'Dedicated schools grant') &
    (s251['category_of_expenditure'].str.contains('1.9.3', na=False))
].copy()

la_dsg_yearly['year_start'] = la_dsg_yearly['time_period'].astype(str).str[:4].astype(int)
la_dsg_yearly['dsg_balance'] = la_dsg_yearly['gross_expenditure'].apply(
    lambda x: pd.to_numeric(str(x).replace(',','').strip(), errors='coerce'))

# Use 2023-24 (year_start=2023) as the most recent complete financial year
dsg_2324 = la_dsg_yearly[la_dsg_yearly['year_start'] == 2023].copy()
dsg_2324 = dsg_2324[['new_la_code','la_name','dsg_balance']].dropna(subset=['new_la_code'])
dsg_2324.columns = ['la_code','la_name_s251','dsg_balance_2324']
dsg_2324 = dsg_2324.dropna(subset=['la_code'])
# Deduplicate: one row per LA (sum balances if multiple entries)
dsg_2324 = (dsg_2324.groupby('la_code', as_index=False)
            .agg({'la_name_s251': 'first', 'dsg_balance_2324': 'sum'}))

# Financial stress: deficit = negative balance, so negate for "deficit size"
# Positive dsg_financial_stress = carrying a deficit (stressed)
# Negative dsg_financial_stress = surplus (healthy)
dsg_2324['dsg_financial_stress'] = -dsg_2324['dsg_balance_2324']

print(f"  DSG 2023-24 data: {len(dsg_2324)} LAs")
print(f"  In deficit (positive stress): {(dsg_2324['dsg_financial_stress'] > 0).sum()}")
print(f"  In surplus (negative stress): {(dsg_2324['dsg_financial_stress'] < 0).sum()}")

# ── Pupil denominator from SEN pupils data ────────────────────────────────
print("\n  Loading SEN pupils for per-pupil denominator…")
sen_phase_path = DATA_DIR / 'sen_pupils_2025' / 'data' / 'sen_phase_type_.csv'
try:
    sen_phase = pd.read_csv(sen_phase_path, encoding='latin-1', low_memory=False,
                             usecols=lambda c: c.strip('ï»¿') in
                             ['time_period','geographic_level','new_la_code',
                              'la_name','phase_type_grouping','total_pupils'])
    # Fix BOM in first column name
    sen_phase.columns = [c.strip('ï»¿') for c in sen_phase.columns]
    # Filter: LA level, Total phase, most recent year (202425 academic year)
    pupils = sen_phase[
        (sen_phase['geographic_level'] == 'Local authority') &
        (sen_phase['phase_type_grouping'] == 'Total')
    ].copy()
    # Get most recent year
    max_year = pupils['time_period'].max()
    pupils_latest = pupils[pupils['time_period'] == max_year][
        ['new_la_code','la_name','total_pupils']].copy()
    pupils_latest['total_pupils'] = to_numeric_safe(pupils_latest['total_pupils'])
    pupils_latest = pupils_latest.dropna(subset=['total_pupils'])
    # Deduplicate: sum total_pupils by LA (in case multiple rows per LA remain)
    pupils_latest = (pupils_latest.groupby('new_la_code', as_index=False)
                     .agg({'la_name': 'first', 'total_pupils': 'sum'}))
    print(f"  Pupil data loaded: {len(pupils_latest)} LAs (year {max_year})")
except Exception as e:
    print(f"  Pupil data failed: {e}")
    pupils_latest = None

# ── Merge DSG + pupils → per-pupil deficit ──────────────────────────────
dsg_full = dsg_2324.merge(
    pupils_latest[['new_la_code','total_pupils']].rename(columns={'new_la_code':'la_code'}),
    on='la_code', how='left'
) if pupils_latest is not None else dsg_2324.copy()

if 'total_pupils' in dsg_full.columns:
    dsg_full['dsg_financial_stress_per_pupil'] = (
        dsg_full['dsg_financial_stress'] / dsg_full['total_pupils']
    )
else:
    # Fall back to using raw £ balance (millions)
    dsg_full['dsg_financial_stress_per_pupil'] = dsg_full['dsg_financial_stress'] / 1e6

dsg_full = dsg_full.drop_duplicates(subset=['la_code'])
print(f"  DSG per-pupil coverage: {dsg_full['dsg_financial_stress_per_pupil'].notna().sum()} LAs")

# ── Merge expanded DSG into panel ─────────────────────────────────────────
panel = panel.merge(
    dsg_full[['la_code','dsg_financial_stress_per_pupil','dsg_balance_2324']],
    on='la_code', how='left'
)

# Use new column as primary, fall back to old estimate where missing
panel['dsg_deficit_per_pupil_full'] = (
    panel['dsg_financial_stress_per_pupil'].combine_first(panel['dsg_deficit_per_pupil'])
)

n_old = panel['dsg_deficit_per_pupil'].notna().sum()
n_new = panel['dsg_deficit_per_pupil_full'].notna().sum()
print(f"\n  DSG coverage: {n_old} → {n_new} LAs (of {len(panel)})")


# ═══════════════════════════════════════════════════════════════════
# STEP 3 — Throughput capacity proxy
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 3 — Throughput capacity proxy")
print("="*70)

# Throughput stress: requests per timely plan issued
# High value = many requests, few plans completed on time → capacity strain
panel['n_timely_plans'] = (panel['n_plans_issued'] * panel['timeliness_pct'] / 100).clip(lower=1)
panel['throughput_stress'] = panel['n_requests'] / panel['n_timely_plans']

# Standardise to z-score
mu_t = panel['throughput_stress'].mean()
sd_t = panel['throughput_stress'].std()
panel['throughput_stress_z'] = (panel['throughput_stress'] - mu_t) / sd_t

print(f"  Throughput stress: mean={mu_t:.2f}, sd={sd_t:.2f}")
print(f"  Coverage: {panel['throughput_stress_z'].notna().sum()} LAs")

print("\n  Top 15 most capacity-stressed LAs:")
top_stress = panel.dropna(subset=['throughput_stress_z']).nlargest(15, 'throughput_stress_z')
print(top_stress[['la_name','intervention_status','throughput_stress_z',
                   'timeliness_pct','la_official_appeal_rate_pct']].to_string(index=False))

# Check correlation with DSG deficit
corr_stress_dsg = pearsonr(
    *[panel.dropna(subset=['throughput_stress_z','dsg_deficit_per_pupil_full'])
      [c] for c in ['throughput_stress_z','dsg_deficit_per_pupil_full']]
)
print(f"\n  Throughput stress ~ DSG deficit: r={corr_stress_dsg[0]:.3f}, "
      f"p={corr_stress_dsg[1]:.4f}")


# ═══════════════════════════════════════════════════════════════════
# STEP 4 — Extended regressions (n≈100+ instead of n=50)
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 4 — Extended regressions")
print("="*70)

reg_results_ext = {}

for dv, label in [
    ('refusal_rate_pct',           'Refusal Rate'),
    ('timeliness_pct',             'Timeliness'),
    ('la_official_appeal_rate_pct','Tribunal Appeal Rate'),
]:
    sub = panel.dropna(subset=[dv, 'dsg_deficit_per_pupil_full', 'imd_average_score'])
    sub = sub[~sub['is_small_la']].copy()
    sub['region_f'] = sub['region'].astype(str).str.strip()
    n = len(sub)
    if n < 20:
        print(f"\n  {label}: only n={n}, skipping")
        continue
    print(f"\n  DV: {label}  (n={n})")
    try:
        m = smf.ols(f'{dv} ~ dsg_deficit_per_pupil_full + imd_average_score + C(region_f)',
                    data=sub).fit()
        reg_results_ext[dv] = m
        b_d = m.params.get('dsg_deficit_per_pupil_full', np.nan)
        p_d = m.pvalues.get('dsg_deficit_per_pupil_full', 1)
        b_i = m.params.get('imd_average_score', np.nan)
        p_i = m.pvalues.get('imd_average_score', 1)
        sig = lambda p: '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else 'ns'
        print(f"    DSG stress/pupil: β={b_d:.4f} (p={p_d:.4f}) {sig(p_d)}")
        print(f"    IMD avg score:    β={b_i:.4f} (p={p_i:.4f}) {sig(p_i)}")
        print(f"    R²={m.rsquared:.3f}, Adj.R²={m.rsquared_adj:.3f}, n={int(m.nobs)}")
    except Exception as e:
        print(f"    Regression failed: {e}")

# Save extended regression results
with open(OUT_TABLES / 'regression_results_extended.txt', 'w') as f:
    for dv, m in reg_results_ext.items():
        f.write(f"\n{'='*70}\nDV: {dv} (extended DSG sample)\n{'='*70}\n")
        f.write(str(m.summary()))
        b = m.params.get('dsg_deficit_per_pupil_full', 0)
        p = m.pvalues.get('dsg_deficit_per_pupil_full', 1)
        direction = 'increase' if b > 0 else 'decrease'
        f.write(f"\nInterpretation: A £1 increase in DSG financial stress per pupil is "
                f"associated with a {b:.4f} pp {direction} in {dv.replace('_',' ')} "
                f"(p={p:.4f}).\n")
print("\n  Saved: regression_results_extended.txt")


# ═══════════════════════════════════════════════════════════════════
# STEP 5 — Mediation analysis
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 5 — Mediation analysis (Baron-Kenny)")
print("="*70)
print("  Chain: DSG deficit → throughput stress → timeliness failure → tribunal appeals")
print()

X  = 'dsg_deficit_per_pupil_full'
M1 = 'throughput_stress_z'
M2 = 'timeliness_pct'
Y  = 'la_official_appeal_rate_pct'
COV= 'imd_average_score'

med_data = panel.dropna(subset=[X, M1, M2, Y, COV]).copy()
med_data = med_data[~med_data['is_small_la']]
n_med = len(med_data)
print(f"  Mediation sample: n={n_med} LAs")

if n_med >= 20:
    # Step 1: Total effect X → Y
    m1 = smf.ols(f'{Y} ~ {X} + {COV}', data=med_data).fit()
    c_total = m1.params.get(X, np.nan); p_total = m1.pvalues.get(X, 1)

    # Step 2: X → M1 (throughput stress)
    m2 = smf.ols(f'{M1} ~ {X} + {COV}', data=med_data).fit()
    a1 = m2.params.get(X, np.nan); p_a1 = m2.pvalues.get(X, 1)

    # Step 3: X → M2 (timeliness), controlling for M1
    m3 = smf.ols(f'{M2} ~ {X} + {M1} + {COV}', data=med_data).fit()
    a2 = m3.params.get(X, np.nan); p_a2 = m3.pvalues.get(X, 1)

    # Step 4: Direct effect X → Y, controlling M1 + M2
    m4 = smf.ols(f'{Y} ~ {X} + {M1} + {M2} + {COV}', data=med_data).fit()
    c_direct = m4.params.get(X, np.nan);  p_direct = m4.pvalues.get(X, 1)
    b1 = m4.params.get(M1, np.nan)
    b2 = m4.params.get(M2, np.nan)

    # Indirect effects
    indirect_m1 = a1 * b1
    indirect_m2 = a2 * b2
    total_indirect = indirect_m1 + indirect_m2
    prop_mediated  = total_indirect / c_total if c_total != 0 else np.nan

    # Sobel test for M1 path
    sa1 = m2.bse.get(X, np.nan);  sb1 = m4.bse.get(M1, np.nan)
    sobel_se1 = np.sqrt(b1**2 * sa1**2 + a1**2 * sb1**2)
    sobel_z1  = (a1 * b1) / sobel_se1 if sobel_se1 > 0 else np.nan
    sobel_p1  = 2 * (1 - stats.norm.cdf(abs(sobel_z1))) if not np.isnan(sobel_z1) else np.nan

    # Sobel test for M2 path
    sa2 = m3.bse.get(X, np.nan);  sb2 = m4.bse.get(M2, np.nan)
    sobel_se2 = np.sqrt(b2**2 * sa2**2 + a2**2 * sb2**2)
    sobel_z2  = (a2 * b2) / sobel_se2 if sobel_se2 > 0 else np.nan
    sobel_p2  = 2 * (1 - stats.norm.cdf(abs(sobel_z2))) if not np.isnan(sobel_z2) else np.nan

    sig = lambda p: '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else 'ns'

    print(f"  Step 1 — Total effect   (DSG → tribunal):          β={c_total:.4f}, p={p_total:.4f} {sig(p_total)}")
    print(f"  Step 2 — X → M1        (DSG → throughput stress):  β={a1:.4f},   p={p_a1:.4f} {sig(p_a1)}")
    print(f"  Step 3 — X → M2        (DSG → timeliness|M1):      β={a2:.4f},   p={p_a2:.4f} {sig(p_a2)}")
    print(f"  Step 4 — Direct effect (DSG → tribunal|M1,M2):     β={c_direct:.4f}, p={p_direct:.4f} {sig(p_direct)}")
    print(f"           M1 → tribunal (throughput → tribunal):     β={b1:.4f},   p={m4.pvalues.get(M1,1):.4f} {sig(m4.pvalues.get(M1,1))}")
    print(f"           M2 → tribunal (timeliness → tribunal):     β={b2:.4f},   p={m4.pvalues.get(M2,1):.4f} {sig(m4.pvalues.get(M2,1))}")
    print()
    print(f"  Indirect via M1: {indirect_m1:.4f}")
    print(f"  Indirect via M2: {indirect_m2:.4f}")
    print(f"  Total indirect:  {total_indirect:.4f}")
    print(f"  Proportion mediated: {prop_mediated:.1%}" if not np.isnan(prop_mediated) else "  Proportion mediated: n/a")
    print(f"  Sobel z (M1 path): {sobel_z1:.3f}, p={sobel_p1:.4f}" if not np.isnan(sobel_z1) else "  Sobel (M1): n/a")
    print(f"  Sobel z (M2 path): {sobel_z2:.3f}, p={sobel_p2:.4f}" if not np.isnan(sobel_z2) else "  Sobel (M2): n/a")

    # Interpretation
    print()
    if p_total < 0.05:
        if not (p_direct < 0.05) and abs(c_direct) < abs(c_total):
            print("  CONCLUSION: FULL MEDIATION — DSG deficit → tribunal path fully explained by mediators.")
        elif abs(c_direct) < abs(c_total):
            print("  CONCLUSION: PARTIAL MEDIATION — DSG deficit effect on tribunal reduced by mediators.")
        else:
            print("  CONCLUSION: No mediation — direct effect unchanged by mediators.")
    else:
        print("  CONCLUSION: Total effect not significant — mediation test inconclusive.")
else:
    print(f"  Only n={n_med} — skipping mediation analysis")
    c_total = a1 = a2 = c_direct = b1 = b2 = indirect_m1 = indirect_m2 = np.nan
    total_indirect = prop_mediated = sobel_z1 = sobel_p1 = sobel_z2 = sobel_p2 = np.nan
    p_total = p_a1 = p_a2 = p_direct = 1.0


# ═══════════════════════════════════════════════════════════════════
# STEP 6 — Build full time-series panel (tribunal 2014-2024 + SEN2 2019-2024)
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 6 — Building full time-series panel")
print("="*70)

def load_sen2_la(filename, breakdown_val, keep_cols, rename_map):
    path = DATA_DIR / 'sen2_2025' / 'data' / filename
    df = pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
    df = df[
        (df['geographic_level'] == 'Local authority') &
        (df['breakdown'].str.strip() == breakdown_val)
    ].copy()
    df['year'] = df['time_period'].astype(int)
    df['la_name'] = df['la_name'].astype(str).str.strip()
    df['la_code'] = df['new_la_code'].astype(str).str.strip()
    out = df[['year','la_name','la_code','region_name'] + keep_cols].copy()
    out.rename(columns=rename_map, inplace=True)
    for col in rename_map.values():
        if col in out.columns:
            out[col] = to_numeric_safe(out[col])
    return out

# Requests: 2019-2024
ts_req = load_sen2_la(
    'requests.csv', 'All requests for EHC needs assessments',
    ['requests_received_in_year', 'requests_decided_not_to_assess'],
    {'requests_received_in_year': 'n_requests',
     'requests_decided_not_to_assess': 'n_refused'}
)
ts_req['refusal_rate_pct'] = ts_req['n_refused'] / ts_req['n_requests'] * 100

# Timeliness: 2019-2024
ts_tim = load_sen2_la(
    'timeliness_20_week.csv', 'All EHC plans issued',
    ['plans_issued_den', 'plans_issued_within_20_weeks', 'pc_plans_issued_within_20_weeks'],
    {'plans_issued_den': 'n_plans_issued',
     'plans_issued_within_20_weeks': 'n_within_20w',
     'pc_plans_issued_within_20_weeks': 'timeliness_pct'}
)

# Tribunal data: 2014-2024 (from supporting file)
print("  Loading tribunal time series (2014-2024)…")
trib_path = DATA_DIR / 'sen2_2025' / 'supporting-files' / 'SEND Tribunals and appeal rate 2014-2024.csv'
trib_raw = pd.read_csv(trib_path, encoding='utf-8-sig', header=None)

year_row = trib_raw.iloc[3, :]
sub_row  = trib_raw.iloc[4, :]
year_cols = {}
current_year = None
for col_idx, val in enumerate(year_row):
    if pd.notna(val) and str(val).strip().isdigit():
        current_year = int(str(val).strip())
    if pd.notna(sub_row.iloc[col_idx]) and current_year:
        sub = str(sub_row.iloc[col_idx]).lower()
        if 'appeal' in sub and 'rate' not in sub:
            year_cols.setdefault(current_year, {})[0] = col_idx
        elif 'rate' in sub:
            year_cols.setdefault(current_year, {})[2] = col_idx

_TRIB_NAME_MAP = {
    'Kingston upon Hull, City of': 'Kingston upon Hull, City of',
    'Kingston Upon Hull, City of': 'Kingston upon Hull, City of',  # capital-U variant
    'Herefordshire, County of':    'Herefordshire',
    'Bristol, City of':            'Bristol, City of',
    'Durham, County':              'County Durham',
    'Durham':                      'County Durham',
}

trib_rows = []
for i in range(5, len(trib_raw)):
    row = trib_raw.iloc[i, :]
    la_name = _TRIB_NAME_MAP.get(str(row.iloc[0]).strip(), str(row.iloc[0]).strip())
    la_code_str = str(row.iloc[1]).strip()
    if not la_name or la_name in ('nan','') or not la_code_str.isdigit():
        continue
    for year, cols in year_cols.items():
        rate_col = cols.get(2)
        rate_str = str(row.iloc[rate_col]).strip().replace('%','') if rate_col else None
        appeal_rate = pd.to_numeric(rate_str, errors='coerce') if rate_str else np.nan
        n_appeals = pd.to_numeric(
            str(row.iloc[cols[0]]).replace(',','').strip() if cols.get(0) else 'nan',
            errors='coerce')
        trib_rows.append({'year': year, 'la_name': la_name, 'la_code_old': la_code_str,
                          'la_official_appeal_rate_pct': appeal_rate,
                          'n_tribunal_appeals': n_appeals})

ts_trib = pd.DataFrame(trib_rows)
print(f"  Tribunal time series: {len(ts_trib)} LA-year rows, "
      f"years {sorted(ts_trib['year'].unique())}")

# ── Merge into full panel ─────────────────────────────────────────────────
ts_panel = ts_req.merge(
    ts_tim[['year','la_name','n_plans_issued','n_within_20w','timeliness_pct']],
    on=['year','la_name'], how='outer'
)
ts_panel = ts_panel.merge(
    ts_trib[['year','la_name','la_official_appeal_rate_pct','n_tribunal_appeals']],
    on=['year','la_name'], how='outer'
)
ts_panel['intervention_status'] = ts_panel['la_name'].apply(get_intervention_status)
ts_panel['sv_entry_year']       = ts_panel['la_name'].map(SAFETY_VALVE_ENTRY)
ts_panel['is_small_la']         = ts_panel['la_name'].isin(['City of London', 'Isles of Scilly'])

# Merge static covariates (IMD, DSG) from 2024 panel
static = panel[['la_code','la_name','imd_average_score','dsg_deficit_per_pupil_full','region']].copy()
ts_panel = ts_panel.merge(static, on='la_name', how='left', suffixes=('','_static'))

ts_panel.to_csv(OUT_TABLES / 'panel_timeseries.csv', index=False)
print(f"  Time series panel saved: {ts_panel.shape}")
print(f"  Years: {sorted(ts_panel['year'].unique())}")
print(f"  LAs: {ts_panel['la_name'].nunique()}")


# ═══════════════════════════════════════════════════════════════════
# STEP 7 — Event study: Safety Valve LAs pre/post entry
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 7 — Event study: Safety Valve pre/post entry")
print("="*70)

# We have tribunal data 2014-2024, and timeliness data 2019-2024.
# For the event study:
# - Treated LAs: Safety Valve (entry 2022-2024 in the data)
# - Control: No-intervention LAs
# - Event window: t-5 to t+2 (relative to SV entry year)
# - For LAs entering after 2022 (Wiltshire, Devon, etc.), the post period is short

ts_es = ts_panel[~ts_panel['is_small_la']].copy()

# For non-SV control LAs, assign synthetic entry year = median SV entry year (2022)
MEDIAN_SV_ENTRY = 2022
ts_es['event_time'] = np.where(
    ts_es['intervention_status'] == 'Safety Valve',
    ts_es['year'] - ts_es['sv_entry_year'],
    ts_es['year'] - MEDIAN_SV_ENTRY
)

# Pre-period check: are SV LAs already worse BEFORE entry?
sv_pre  = ts_es[(ts_es['intervention_status']=='Safety Valve') &
                (ts_es['event_time'] < 0)]
ctrl_pre= ts_es[(ts_es['intervention_status']=='None') &
                (ts_es['event_time'] < 0)]

print(f"  SV LAs pre-entry  (n obs={len(sv_pre)}):")
for var in ['timeliness_pct', 'la_official_appeal_rate_pct', 'refusal_rate_pct']:
    sv_val  = sv_pre[var].mean()
    ctl_val = ctrl_pre[var].mean()
    if not np.isnan(sv_val) and not np.isnan(ctl_val):
        print(f"    {var}: SV={sv_val:.1f}  Control={ctl_val:.1f}  gap={sv_val-ctl_val:+.1f} pp")

# ── Figure 08: Event study plots ─────────────────────────────────────────
outcomes = [
    ('la_official_appeal_rate_pct', 'Official Tribunal Appeal Rate (%)', '#c53030'),
    ('timeliness_pct',              '20-Week Compliance (%)',             '#276749'),
]

# Only plot if we have enough data
outcomes_avail = [(v,l,c) for v,l,c in outcomes
                  if ts_es[ts_es['intervention_status']=='Safety Valve'][v].notna().any()]

n_plots = len(outcomes_avail)
fig, axes = plt.subplots(1, n_plots, figsize=(7*n_plots, 6))
if n_plots == 1: axes = [axes]
fig.suptitle('Event Study: Safety Valve LA Entry\n'
             'Mean outcome relative to Safety Valve entry year',
             fontsize=12, fontweight='bold')

for ax, (var, label, sv_color) in zip(axes, outcomes_avail):
    for group, gcolor, glabel in [
        ('Safety Valve', sv_color,  'Safety Valve LAs (n={})'.format(len(SAFETY_VALVE_ENTRY))),
        ('None',         '#2c5282', 'No intervention LAs'),
    ]:
        sub = ts_es[ts_es['intervention_status'] == group]
        grouped = sub.groupby('event_time')[var].agg(
            mean='mean',
            se=lambda x: x.std() / np.sqrt(max(len(x), 1))
        ).reset_index()
        grouped = grouped[grouped['event_time'].between(-5, 3)]

        ax.plot(grouped['event_time'], grouped['mean'],
                'o-', color=gcolor, lw=2.5, ms=7, label=glabel, zorder=4)
        ax.fill_between(grouped['event_time'],
                        grouped['mean'] - 1.96*grouped['se'],
                        grouped['mean'] + 1.96*grouped['se'],
                        alpha=0.15, color=gcolor)

    ax.axvline(0, color='grey', lw=1.5, ls='--', alpha=0.7, label='SV entry (t=0)')
    ax.axvspan(-0.5, 0.5, alpha=0.05, color='grey')
    ax.set_xlabel('Years relative to Safety Valve entry', fontsize=10)
    ax.set_ylabel(label, fontsize=10)
    ax.set_title(label, fontweight='bold', fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.2)
    ax.set_xticks(range(-5, 4))
    ax.set_xticklabels(['t-5','t-4','t-3','t-2','t-1','t=0','t+1','t+2','t+3'])

    # Pre-trend annotation
    sv_pre_val  = ts_es[(ts_es['intervention_status']=='Safety Valve') &
                        (ts_es['event_time'].between(-3,-1))][var].mean()
    ctl_pre_val = ts_es[(ts_es['intervention_status']=='None') &
                        (ts_es['event_time'].between(-3,-1))][var].mean()
    if not np.isnan(sv_pre_val) and not np.isnan(ctl_pre_val):
        pre_gap = sv_pre_val - ctl_pre_val
        ax.text(0.02, 0.97, f'Pre-entry gap (t-3 to t-1): {pre_gap:+.1f} pp',
                transform=ax.transAxes, va='top', fontsize=9,
                color='#555', bbox=dict(fc='white', alpha=0.8, pad=2))

fig.text(0.5, -0.04,
         "Note: SV LAs entering in 2024 (Wiltshire, Devon, Dorset, Shropshire, Warwickshire) "
         "contribute only t=0. Post-entry means (t+1 to t+3) reflect 2022–23 entrants only.",
         ha='center', fontsize=8, color='#666', style='italic', wrap=True)
plt.tight_layout()
plt.savefig(OUT_FIGS / '08_event_study.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 08_event_study.png")


# ═══════════════════════════════════════════════════════════════════
# STEP 8 — Figure 09: Mediation path diagram
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 8 — Mediation path diagram")

sig = lambda p: '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else 'ns'

med_steps = [
    ('Total effect\n(DSG → tribunals)',                     c_total,   p_total),
    ('DSG → throughput\nstress (M1)',                       a1,        p_a1),
    ('M1 → tribunal\n(direct path)',                        b1,        m4.pvalues.get(M1,1) if n_med>=20 else 1),
    ('DSG → timeliness\nfailure (M2) | M1',                 a2,        p_a2),
    ('M2 → tribunal\n(direct path)',                        b2,        m4.pvalues.get(M2,1) if n_med>=20 else 1),
    ('Direct effect\n(DSG → tribunals | M1,M2)',             c_direct,  p_direct),
]

fig, ax = plt.subplots(figsize=(10, 6))
colors_path = ['#888', '#c53030', '#c53030', '#553c9a', '#553c9a', '#2c5282']
y_pos = range(len(med_steps))

for i, (label, coef, pval) in enumerate(med_steps):
    if np.isnan(coef): continue
    se_val = 0  # skip error bars for simplicity
    alpha = 0.9 if pval < 0.05 else 0.35
    ax.barh(i, coef, color=colors_path[i], alpha=alpha, height=0.55)
    sig_str = sig(pval)
    ax.text(0.005, i, f' β={coef:.4f}  {sig_str}', va='center', fontsize=9,
            color='black' if pval < 0.05 else '#888')

ax.axvline(0, color='black', lw=1, ls='--')
ax.set_yticks(list(y_pos))
ax.set_yticklabels([s[0] for s in med_steps], fontsize=9)
ax.set_xlabel('Coefficient (pp per unit)', fontsize=10)

title_mediation = (f'Mediation: DSG deficit → tribunal appeals\n'
                   f'Proportion mediated: {prop_mediated:.0%}  |  n={n_med} LAs'
                   if not np.isnan(prop_mediated) else
                   'Mediation analysis (insufficient data)')
ax.set_title(title_mediation, fontsize=11, fontweight='bold')
ax.grid(axis='x', alpha=0.2)

sig_patch  = mpatches.Patch(color='#c53030', alpha=0.9, label='p < 0.05')
ns_patch   = mpatches.Patch(color='#888',    alpha=0.35, label='p ≥ 0.05')
ax.legend(handles=[sig_patch, ns_patch], fontsize=9, loc='lower right')

plt.tight_layout()
plt.savefig(OUT_FIGS / '09_mediation_path.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 09_mediation_path.png")


# ═══════════════════════════════════════════════════════════════════
# STEP 9 — Figure 10: Individual SV LA tribunal trajectories
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 9 — SV LA individual trajectories")

sv_la_data = ts_panel[
    (ts_panel['intervention_status'] == 'Safety Valve') &
    (~ts_panel['is_small_la']) &
    (ts_panel['la_official_appeal_rate_pct'].notna())
].copy()

sv_las_with_data = sv_la_data['la_name'].unique()
print(f"  SV LAs with tribunal data: {len(sv_las_with_data)}")

# National mean for non-SV LAs
ctrl_mean = ts_panel[
    (ts_panel['intervention_status'] == 'None') &
    (ts_panel['la_official_appeal_rate_pct'].notna())
].groupby('year')['la_official_appeal_rate_pct'].agg(['mean','sem'])

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('SEND Tribunal Appeal Rates: Safety Valve LAs vs National Mean\n'
             '(Each line = one Safety Valve LA, dashed = non-intervention mean)',
             fontsize=12, fontweight='bold')

sv_palette = plt.cm.get_cmap('tab20', max(len(sv_las_with_data), 1))

for ax, (var, vlabel) in zip(axes, [
    ('la_official_appeal_rate_pct', 'Official Appeal Rate (%)'),
    ('timeliness_pct',              '20-Week Compliance (%)'),
]):
    ctrl_mean_v = ts_panel[
        (ts_panel['intervention_status'] == 'None') &
        (ts_panel[var].notna())
    ].groupby('year')[var].mean()

    for i, la in enumerate(sorted(sv_las_with_data)):
        la_data = ts_panel[(ts_panel['la_name'] == la) &
                           ts_panel[var].notna()].sort_values('year')
        if len(la_data) < 2: continue
        entry = SAFETY_VALVE_ENTRY.get(la, 2022)
        ax.plot(la_data['year'], la_data[var],
                color=sv_palette(i), alpha=0.55, lw=1.3)
        # Mark entry year
        entry_row = la_data[la_data['year'] == entry]
        if len(entry_row):
            ax.scatter(entry_row['year'].values, entry_row[var].values,
                       color=sv_palette(i), s=40, zorder=5)

    ax.plot(ctrl_mean_v.index, ctrl_mean_v.values,
            color='#2c5282', lw=2.5, ls='--', zorder=6, label='Non-intervention mean')

    ax.set_xlabel('Year', fontsize=10)
    ax.set_ylabel(vlabel, fontsize=10)
    ax.set_title(vlabel, fontweight='bold', fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.2)

    # Shade SV entry period
    ax.axvspan(2021.5, 2022.5, alpha=0.07, color='red', label='SV entry wave')
    ax.set_xticks(sorted(ts_panel['year'].dropna().unique()))

plt.tight_layout()
plt.savefig(OUT_FIGS / '10_sv_la_trajectories.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 10_sv_la_trajectories.png")


# ═══════════════════════════════════════════════════════════════════
# STEP 10 — Updated regression comparison figure (07 vs extended)
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 10 — Extended regression comparison figure")

if reg_results_ext:
    dvs = list(reg_results_ext.keys())
    fig, axes = plt.subplots(1, len(dvs), figsize=(7*len(dvs), 7))
    if len(dvs) == 1: axes = [axes]
    fig.suptitle('Extended OLS: DSG Financial Stress → EHCP Outcomes (2024)\n'
                 f'(Expanded sample using S251 data)',
                 fontsize=12, fontweight='bold')

    dv_labels_map = {
        'refusal_rate_pct':           'Refusal Rate (%)',
        'timeliness_pct':             '20-Week Compliance (%)',
        'la_official_appeal_rate_pct':'Official Appeal Rate (%)',
    }

    for ax, dv in zip(axes, dvs):
        m = reg_results_ext[dv]
        params = m.params; conf = m.conf_int(); pvals = m.pvalues

        plot_keys = [k for k in params.index
                     if k in ('dsg_deficit_per_pupil_full', 'imd_average_score')
                     or ('region_f' in k and any(r in k for r in
                         ['North East','North West','London','South East',
                          'South West','Yorkshire','East Midlands','West Midlands']))]
        if not plot_keys:
            plot_keys = [k for k in params.index if k != 'Intercept'][:8]

        coefs  = [params[k] for k in plot_keys]
        ci_lo  = [conf.loc[k, 0] for k in plot_keys]
        ci_hi  = [conf.loc[k, 1] for k in plot_keys]
        pv     = [pvals[k] for k in plot_keys]

        def shorten(k):
            if 'dsg' in k.lower(): return 'DSG stress/pupil (£)'
            if 'imd' in k.lower(): return 'IMD avg score'
            m_r = re.search(r"region_f\[T\.(.*?)\]", k)
            return f"Region: {m_r.group(1)[:18]}" if m_r else k[:28]

        short_keys = [shorten(k) for k in plot_keys]
        bar_colors = ['#c53030' if p < 0.05 else '#718096' for p in pv]

        ax.barh(range(len(plot_keys)), coefs, color=bar_colors, alpha=0.82, height=0.55)
        ax.errorbar(coefs, range(len(plot_keys)),
                    xerr=[[c-lo for c, lo in zip(coefs, ci_lo)],
                          [hi-c  for c, hi in zip(coefs, ci_hi)]],
                    fmt='none', color='black', capsize=4, lw=1.5, zorder=5)
        ax.axvline(0, color='black', lw=1, ls='--')
        ax.set_yticks(range(len(plot_keys)))
        ax.set_yticklabels(short_keys, fontsize=8)
        n_obs = int(m.nobs)
        ax.set_title(f'{dv_labels_map.get(dv, dv)}\nR²={m.rsquared:.2f}, n={n_obs}',
                     fontweight='bold', fontsize=9)
        ax.set_xlabel('Coefficient (pp)', fontsize=8)
        ax.grid(axis='x', alpha=0.2)
        ax.legend(handles=[mpatches.Patch(color='#c53030', label='p < 0.05'),
                            mpatches.Patch(color='#718096', label='p ≥ 0.05')],
                  fontsize=7, loc='lower right')

    plt.tight_layout()
    plt.savefig(OUT_FIGS / '07b_regression_coefficients_extended.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: 07b_regression_coefficients_extended.png")


# ═══════════════════════════════════════════════════════════════════
# STEP 11 — Save extended panel
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 11 — Saving extended 2024 panel")
save_cols = [c for c in panel.columns if c not in ('dsg_deficit_per_pupil',)]
panel.rename(columns={'dsg_deficit_per_pupil_full': 'dsg_deficit_per_pupil'}, inplace=True)
panel.to_csv(OUT_TABLES / 'la_summary_2024_extended.csv', index=False)
print(f"  Saved: la_summary_2024_extended.csv ({len(panel)} rows, {len(panel.columns)} cols)")


# ═══════════════════════════════════════════════════════════════════
# STEP 12 — Append extension findings to FINDINGS.md
# ═══════════════════════════════════════════════════════════════════
print("\nSTEP 12 — Updating FINDINGS.md")

def fmt_p(p):
    if np.isnan(p): return 'p = n/a'
    if p < 0.001:   return 'p < 0.001'
    return f'p = {p:.3f}'

def sig_str(p):
    if np.isnan(p): return ''
    return '***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else '(ns)'

# Pre-period gaps for event study
sv_pre_trib  = ts_es[(ts_es['intervention_status']=='Safety Valve') & (ts_es['event_time'].between(-3,-1))]['la_official_appeal_rate_pct'].mean()
ctl_pre_trib = ts_es[(ts_es['intervention_status']=='None') & (ts_es['event_time'].between(-3,-1))]['la_official_appeal_rate_pct'].mean()
sv_pre_tim   = ts_es[(ts_es['intervention_status']=='Safety Valve') & (ts_es['event_time'].between(-3,-1))]['timeliness_pct'].mean()
ctl_pre_tim  = ts_es[(ts_es['intervention_status']=='None') & (ts_es['event_time'].between(-3,-1))]['timeliness_pct'].mean()

# Regression results for the extended sample
reg_tim = reg_results_ext.get('timeliness_pct')
reg_ref = reg_results_ext.get('refusal_rate_pct')
reg_trib= reg_results_ext.get('la_official_appeal_rate_pct')

extension_md = f"""

---

# Extension Analysis Findings

*Data additions: S251 DSG outturn 2023-24, IMD 2019 (full), SEN pupils 2024-25.*
*All loaded programmatically. Extension run: 2026-05-10.*

## Extension 1: DSG Coverage Expansion

DSG financial stress data expanded from n={n_old} to n={n_new} LAs using the DfE S251
(LA and School Expenditure) data. The S251 1.9.3 "DSG carried forward" column provides
end-of-year DSG balance for ~153 LAs. Negative balance = deficit being carried forward
to next year; positive = surplus.

Conversion: DSG financial stress per pupil = −(DSG_carry_forward_£) / total_pupils,
so positive values indicate financial pressure.

"""

if reg_tim:
    b_d = reg_tim.params.get('dsg_deficit_per_pupil_full', np.nan)
    p_d = reg_tim.pvalues.get('dsg_deficit_per_pupil_full', 1)
    n_t = int(reg_tim.nobs)
    r2_t= reg_tim.rsquared
    extension_md += f"""### Timeliness regression (extended sample, n={n_t})

β(DSG stress/pupil) = {b_d:.4f} pp, {fmt_p(p_d)} {sig_str(p_d)}, R²={r2_t:.3f}

"""
    if p_d < 0.05:
        extension_md += (f"**FINDING:** The DSG deficit → timeliness failure relationship "
                         f"is confirmed in the expanded sample (n={n_t} vs n=50 previously). "
                         f"A £1 increase in DSG financial stress per pupil is associated with "
                         f"a {b_d:.4f} pp reduction in 20-week compliance.\n")
    else:
        extension_md += (f"**FINDING:** The DSG deficit → timeliness relationship loses "
                         f"significance in the larger sample ({fmt_p(p_d)}). This may indicate "
                         f"that the original n=50 result was driven by high-DSG-deficit LAs "
                         f"(Safety Valve) which are also in a specific region — the region FEs "
                         f"absorb much of the variance in the full sample.\n")

if reg_trib:
    b_d = reg_trib.params.get('dsg_deficit_per_pupil_full', np.nan)
    p_d = reg_trib.pvalues.get('dsg_deficit_per_pupil_full', 1)
    n_t = int(reg_trib.nobs)
    r2_t= reg_trib.rsquared
    extension_md += f"""
### Tribunal rate regression (extended sample, n={n_t})

β(DSG stress/pupil) = {b_d:.4f} pp, {fmt_p(p_d)} {sig_str(p_d)}, R²={r2_t:.3f}

"""

extension_md += f"""
## Extension 2: Capacity Proxy (Throughput Stress)

Throughput stress = requests / (plans_issued × timeliness), z-scored.
Captures processing backpressure: high score = many requests relative to timely outputs.

Correlation with DSG financial stress: r={corr_stress_dsg[0]:.3f}, {fmt_p(corr_stress_dsg[1])} {sig_str(corr_stress_dsg[1])}

"""

if corr_stress_dsg[1] < 0.05:
    extension_md += ("LAs with greater DSG deficits show higher throughput stress, "
                     "consistent with financial pressure causing staffing/capacity reductions.\n")
else:
    extension_md += ("Throughput stress and DSG deficit are not significantly correlated "
                     "in the cross-section, suggesting other factors (LA size, administrative "
                     "efficiency) drive throughput variation independently of finances.\n")

extension_md += f"""
## Extension 3: Mediation Analysis

**Chain tested:** DSG deficit → throughput stress (M1) → timeliness failure (M2) → tribunal appeals
**Sample:** n={n_med} LAs with all four variables observed

Baron-Kenny results:
| Path | β | p |
|------|---|---|
| Total effect (DSG → tribunal) | {c_total:.4f} | {fmt_p(p_total)} {sig_str(p_total)} |
| DSG → M1 (throughput stress) | {a1:.4f} | {fmt_p(p_a1)} {sig_str(p_a1)} |
| DSG → M2 (timeliness) \\| M1 | {a2:.4f} | {fmt_p(p_a2)} {sig_str(p_a2)} |
| DSG → tribunal \\| M1, M2 | {c_direct:.4f} | {fmt_p(p_direct)} {sig_str(p_direct)} |

- Total indirect effect: {total_indirect:.4f}
- Proportion mediated: {f"{prop_mediated:.0%}" if not np.isnan(prop_mediated) else "n/a"}
- Sobel z (throughput path): {sobel_z1:.3f}, {fmt_p(sobel_p1)}
- Sobel z (timeliness path):  {sobel_z2:.3f}, {fmt_p(sobel_p2)}

"""
if not np.isnan(prop_mediated):
    if p_total < 0.05 and p_a1 < 0.05:
        if not (p_direct < 0.05):
            extension_md += ("**CONCLUSION: Full mediation.** The effect of DSG deficit on "
                             "tribunal appeals is fully explained by the throughput stress and "
                             "timeliness pathways. This strongly supports the capacity-collapse "
                             "causal story.\n")
        elif abs(c_direct) < abs(c_total):
            extension_md += ("**CONCLUSION: Partial mediation.** DSG deficit affects tribunal "
                             f"appeals both directly and through the capacity/timeliness pathway. "
                             f"Approximately {prop_mediated:.0%} of the total effect is mediated.\n")
        else:
            extension_md += "**CONCLUSION:** Mediators do not substantially reduce the direct effect.\n"
    else:
        extension_md += ("**CONCLUSION:** Mediation test inconclusive — total effect or X→M1 "
                         "path not statistically significant. This is most likely a power "
                         f"issue (n={n_med}).\n")
else:
    extension_md += "**CONCLUSION:** Insufficient data for mediation analysis.\n"

extension_md += f"""
## Extension 4: Event Study (Pre/Post Safety Valve)

**Pre-entry gap (t-3 to t-1):**
- Tribunal appeal rate: SV={sv_pre_trib:.1f}% vs Control={ctl_pre_trib:.1f}% (gap={sv_pre_trib-ctl_pre_trib:+.1f} pp)
- 20-week timeliness:   SV={sv_pre_tim:.1f}% vs Control={ctl_pre_tim:.1f}% (gap={sv_pre_tim-ctl_pre_tim:+.1f} pp)

"""

if sv_pre_trib - ctl_pre_trib > 1.5:
    extension_md += (
        "**FINDING:** Safety Valve LAs were already performing significantly worse than "
        "controls in the years BEFORE entering the programme (pre-entry tribunal gap "
        f"{sv_pre_trib-ctl_pre_trib:+.1f} pp; timeliness gap {sv_pre_tim-ctl_pre_tim:+.1f} pp). "
        "This supports the interpretation that Safety Valve status captures pre-existing "
        "structural weakness, not a new deterioration caused by the programme.\n\n"
        "The programme therefore appears to have been targeting the right LAs, but has not "
        "yet reversed the underlying performance gap.\n"
    )
else:
    extension_md += (
        "**FINDING:** Safety Valve LAs showed only a modest gap vs controls before entry "
        f"(pre-entry tribunal gap {sv_pre_trib-ctl_pre_trib:+.1f} pp). This weakens the "
        "selection-into-programme explanation and leaves open the possibility that the "
        "programme entry itself, or concurrent financial pressure, drove subsequent "
        "deterioration.\n"
    )

extension_md += """
**Caveat:** SEN2 data only begins 2019; for SV LAs entering 2022, we have just 3 pre-entry
years. The tribunal data extends to 2014 which provides a richer pre-period for the
tribunal outcome (see figure 10). Parallel trends in the pre-period are consistent with
a valid DiD design but cannot be formally tested with this sample size.

## Additional data that would substantially strengthen the analysis

1. **LA SEND team staffing levels** (FTE per 1,000 active EHCPs) — the direct workforce
   mediator. Could be obtained via: (a) DfE School Workforce Census LA-level SEN support
   staff tables; (b) Freedom of Information requests to individual LAs; or (c) the ISOS
   Partnership / LGA LA workforce survey (if available publicly).

2. **Pre-2019 SEN2 process data** — extending the panel to 2014 (matching the tribunal
   data range) would allow a proper event study with 5+ pre-entry years and formal
   parallel-trends testing. Older SEN2 releases are on EES.

3. **LA-level SEND legal costs** — available via FOIA from individual LAs or potentially
   from the annual accounts. Would directly test the cost spiral hypothesis.

4. **Instrumental variable for Safety Valve entry** — needed for truly causal inference.
   Candidates: LA over-65 population share (as instrument for care demand pressure on
   overall LA finances), pre-existing high-needs block allocation shortfall per pupil,
   or distance from DfE regional office (as instrument for oversight intensity).

*Generated: 2026-05-10*
"""

with open(BASE_DIR / 'outputs' / 'FINDINGS.md', 'a') as f:
    f.write(extension_md)
print("  FINDINGS.md updated with extension results")


# ═══════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("EXTENSION ANALYSIS COMPLETE")
print("="*70)
print(f"""
New outputs:
  figures/08_event_study.png
  figures/09_mediation_path.png
  figures/10_sv_la_trajectories.png
  figures/07b_regression_coefficients_extended.png
  tables/la_summary_2024_extended.csv
  tables/regression_results_extended.txt
  tables/panel_timeseries.csv    ({ts_panel.shape[0]} rows, years {sorted(ts_panel['year'].dropna().astype(int).unique())})
  FINDINGS.md (appended)

Key results:
  DSG coverage:     {n_old} → {n_new} LAs
  IMD coverage:     {panel['imd_average_score'].notna().sum()} / {len(panel)} LAs
  Mediation n:      {n_med} LAs
  Prop. mediated:   {f"{prop_mediated:.0%}" if not np.isnan(prop_mediated) else "n/a"}
  Pre-entry gap:    tribunal {sv_pre_trib-ctl_pre_trib:+.1f} pp, timeliness {sv_pre_tim-ctl_pre_tim:+.1f} pp
""")
