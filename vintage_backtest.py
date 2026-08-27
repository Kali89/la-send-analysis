#!/usr/bin/env python3
"""
vintage_backtest.py

"When could the SEND crisis have been foreseen, and how?"

Replays the analysis a competent analyst could have run at each year from 2016
to 2021, using ONLY statistics that had actually been published by that date.
This is the direct test of foreseeability that the forecastability study
(forecastability_analysis.py) does not provide: that study measures
cross-sectional LA ranking with features truncated from 2025-vintage files;
this one reconstructs the true information set at each date from the original
publications and projects forward.

Vintage sources (verified against the original documents):
  - SFR 17/2016 "Statements of SEN and EHC plans: England 2016" (pub. 26 May
    2016) - data/raw/vintage/SFR17_2016_tables.xlsx
    https://assets.publishing.service.gov.uk/media/5a80d383ed915d74e6230aa5/SFR17-2016_Main_Tables.xlsx
  - SEN2 2019 "Statements of SEN and EHC plans: England 2019" (pub. 30 May
    2019) - data/raw/vintage/SEN2_2019_tables.xlsx
    https://assets.publishing.service.gov.uk/media/5e5e794086650c5145db34da/SEN2_2019_tables.xlsx
    Table 1: national caseload by age, Jan 2010-2019
    Table 3: caseload by LA, Jan 2010-2019
    Table 4: new plans by LA, calendar 2010-2018
    Table 9: 20-week timeliness by LA, calendar 2014-2018
  - S251 outturn 2015/16-2024/25 (repo data, published annually with ~8 month lag)
  - SEN2 2025 machine-readable data (repo) for actual outcomes 2019-2025
  - DfE SEND tribunal supporting file (repo; NOTE: this LA-level series was
    first published in 2025 and is NOT treated as vintage-available)

Outputs
-------
outputs/figures/47_vintage_projections.png
outputs/figures/48_growth_decomposition.png
outputs/figures/49_stress_test_2017.png
outputs/figures/50_vintage_la_signals.png
outputs/tables/vintage_national_series.csv
outputs/tables/vintage_backtest_forecasts.csv
outputs/tables/vintage_detection_tests.csv
outputs/tables/vintage_la_signals.csv
outputs/tables/stress_test_2017.csv
outputs/tables/publication_audit.csv
"""

from __future__ import annotations
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

warnings.filterwarnings('ignore')

ROOT      = Path(__file__).parent
FIG_DIR   = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'
VINTAGE   = ROOT / 'data' / 'raw' / 'vintage'
FIGURE_DPI = 150

C_ACTUAL   = '#222222'
C_EXP      = '#d62728'   # exponential / EHCP-era model
C_LINEAR   = '#1f77b4'   # linear-recent model
C_NULL     = '#7f7f7f'   # 2014 impact-assessment null
C_SCHOOL   = '#1f77b4'   # school-age growth component
C_POST16   = '#ff7f0e'   # 16-25 growth component
C_BAND     = '#2ca02c'


def to_num(s):
    return pd.to_numeric(
        pd.Series(s).astype(str).str.strip().str.replace(',', '')
          .replace({'x': np.nan, 'z': np.nan, '-': np.nan, '.': np.nan,
                    '..': np.nan, 'c': np.nan, 'nan': np.nan, 'None': np.nan}),
        errors='coerce'
    )


def auc_rank(y_true: np.ndarray, score: np.ndarray) -> float:
    m = np.isfinite(score) & np.isfinite(y_true)
    y, s = y_true[m].astype(int), score[m]
    n_pos, n_neg = y.sum(), len(y) - y.sum()
    if n_pos == 0 or n_neg == 0:
        return np.nan
    ranks = stats.rankdata(s)
    return (ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: NATIONAL SERIES FROM VINTAGE + CURRENT PUBLICATIONS
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("Assembling verified national series...")
print("=" * 70)

# ── 1a. Caseload (statements + EHC plans, January) ───────────────────────────
# 2010-2019 from SEN2 2019 Table 1 (single consistent vintage document).
t1 = pd.read_excel(VINTAGE / 'SEN2_2019_tables.xlsx', sheet_name='Table 1', header=None)

# Column blocks in Table 1: 2010-2014 single cols 3-7; then (Statements, EHC,
# Total) triplets for 2015-2018 at total-cols 11/15/19/23; 2019 EHC-only col 25.
T1_TOTAL_COLS = {2010: 3, 2011: 4, 2012: 5, 2013: 6, 2014: 7,
                 2015: 11, 2016: 15, 2017: 19, 2018: 23, 2019: 25}
T1_AGE_ROWS   = {'age_0_4': 9, 'age_5_10': 10, 'age_11_15': 11,
                 'age_16_19': 12, 'age_20_25': 13, 'total': 14}

caseload_hist = {}
age_hist = {k: {} for k in T1_AGE_ROWS}
for yr, col in T1_TOTAL_COLS.items():
    for k, row in T1_AGE_ROWS.items():
        v = to_num([t1.iloc[row, col]]).iloc[0]
        age_hist[k][yr] = v
    caseload_hist[yr] = age_hist['total'][yr]

assert caseload_hist[2016] == 256315 and caseload_hist[2019] == 353995, \
    "Vintage Table 1 parse failed sanity check"

# 2020-2025 from SEN2 2025 machine-readable caseload (actuals).
cas_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/caseload.csv', low_memory=False)
cas_nat = cas_raw[cas_raw['geographic_level'] == 'National'].copy()
if 'breakdown_topic' in cas_nat.columns:
    m = cas_nat['breakdown_topic'].eq('All EHC plans')
    if m.any():
        cas_nat = cas_nat[m]
cas_nat['jan_year'] = cas_nat['time_period'].astype(str).str[:4].astype(int) + 1
cas_nat['ehcplans'] = to_num(cas_nat['ehcplans']).values
cas_nat_yr = cas_nat.groupby('jan_year')['ehcplans'].sum()

for yr in range(2019, 2026):
    if yr in cas_nat_yr.index:
        v = float(cas_nat_yr.loc[yr])
        if yr == 2019:
            diff = abs(v - caseload_hist[2019]) / caseload_hist[2019]
            print(f"  2019 overlap check: vintage {caseload_hist[2019]:,} vs "
                  f"SEN2-2025 {v:,.0f} ({diff:.1%} difference)")
        caseload_hist.setdefault(yr, v)

caseload = pd.Series(caseload_hist).sort_index()
print("  Caseload (Jan):")
print('   ', ', '.join(f"{y}: {v:,.0f}" for y, v in caseload.items()))

# School-age (0-15) subtotal for the age-extension decomposition
school_age = pd.Series({yr: age_hist['age_0_4'][yr] + age_hist['age_5_10'][yr] +
                        age_hist['age_11_15'][yr] for yr in T1_TOTAL_COLS}).sort_index()
post16 = (pd.Series({yr: caseload_hist[yr] for yr in T1_TOTAL_COLS}).sort_index()
          - school_age)

# ── 1b. New plans per calendar year ──────────────────────────────────────────
# 2010-2018 from SEN2 2019 Table 4 ENGLAND row (generic year->column scan).
t4 = pd.read_excel(VINTAGE / 'SEN2_2019_tables.xlsx', sheet_name='Table 4', header=None)

def scan_year_cols(df, header_row=5, sub_row=6):
    """Map year -> column, preferring the 'Total' sub-column of each block."""
    years = {}
    current_year = None
    for col in range(df.shape[1]):
        hv = df.iloc[header_row, col]
        if pd.notna(hv) and str(hv).strip().rstrip('.0').isdigit():
            current_year = int(float(hv))
            years.setdefault(current_year, col)   # provisional: first col of block
        sv = str(df.iloc[sub_row, col]).strip().lower()
        if current_year is not None and sv.startswith('total'):
            years[current_year] = col
    return years

t4_cols = scan_year_cols(t4)
eng_row_t4 = t4.index[t4.iloc[:, 3].astype(str).str.strip() == 'ENGLAND'][0]
new_plans_hist = {yr: float(to_num([t4.iloc[eng_row_t4, col]]).iloc[0])
                  for yr, col in t4_cols.items()}

# 2019-2024 from SEN2 2025 machine-readable newplans (actuals).
np_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/newplans.csv', low_memory=False)
np_nat = np_raw[np_raw['geographic_level'] == 'National'].copy()
np_nat['n'] = to_num(np_nat['new_ehc_plans']).values
np_nat_yr = {}
for yr, grp in np_nat.groupby('time_period'):
    total_rows = grp[grp['breakdown_topic'] == 'New EHC plans']
    if not total_rows.empty:
        np_nat_yr[int(yr)] = float(total_rows['n'].sum())
    else:   # only age breakdowns published for this year
        age_rows = grp[grp['breakdown_topic'].str.contains('Age', na=False)]
        np_nat_yr[int(yr)] = float(age_rows['n'].sum())
for yr, v in np_nat_yr.items():
    new_plans_hist.setdefault(yr, v)

new_plans = pd.Series(new_plans_hist).sort_index()
print("  New plans (calendar yr):")
print('   ', ', '.join(f"{y}: {v:,.0f}" for y, v in new_plans.items()))

# ── 1c. National 20-week timeliness (excluding exceptions) ───────────────────
t9 = pd.read_excel(VINTAGE / 'SEN2_2019_tables.xlsx', sheet_name='Table 9', header=None)
eng_row_t9 = t9.index[t9.iloc[:, 3].astype(str).str.strip() == 'ENGLAND'][0]
timeliness_hist = {}
for i, yr in enumerate(range(2014, 2019)):
    timeliness_hist[yr] = float(to_num([t9.iloc[eng_row_t9, 9 + i]]).iloc[0])

tl_raw = pd.read_csv(ROOT / 'data/raw/sen2_2025/data/timeliness_20_week.csv', low_memory=False)
tl_nat = tl_raw[(tl_raw['geographic_level'] == 'National') &
                (tl_raw['breakdown_topic'] == 'All EHC plans issued')].copy()
late_actual = {}
for _, r in tl_nat.iterrows():
    yr = int(r['time_period'])
    # PC_plans_issued_20_weeks_ex = % within 20 weeks excluding exception cases
    # (the definition used in the vintage Table 9 series)
    if yr not in timeliness_hist:
        timeliness_hist[yr] = float(to_num([r['PC_plans_issued_20_weeks_ex']]).iloc[0])
    den    = float(to_num([r['plans_issued_den']]).iloc[0])
    within = float(to_num([r['plans_issued_within_20_weeks']]).iloc[0])
    late_actual[yr] = den - within
timeliness = pd.Series(timeliness_hist).sort_index()
print("  20-week timeliness (excl. exceptions):")
print('   ', ', '.join(f"{y}: {v:.1f}%" for y, v in timeliness.items()))

# Late plans for the vintage era (2014-2018): plans issued x (1 - timeliness)
for yr in new_plans.index:
    if yr in timeliness.index and 2014 <= yr <= 2018:
        late_actual.setdefault(yr, new_plans[yr] * (1 - timeliness[yr] / 100))
late_actual = pd.Series(late_actual).sort_index()
print("  Late plans (issued > 20 weeks):")
print('   ', ', '.join(f"{y}: {v:,.0f}" for y, v in late_actual.items()))

# ── 1d. S251 independent top-up spend (line 1.2.3), national ────────────────
s251_raw = pd.read_csv(
    ROOT / 'data/raw/s251_2025/data/s251_alleducation_la_regional_national.csv',
    encoding='latin-1', low_memory=False
)
s251_la = s251_raw[s251_raw['geographic_level'] == 'Local authority'].copy()
s251_la['gross'] = to_num(s251_la['gross_expenditure']).values
s251_la['fy_end'] = s251_la['time_period'].astype(str).str[:4].astype(int) + 1

def s251_national(prefix):
    sub = s251_la[s251_la['category_of_expenditure'].str.startswith(prefix, na=False)]
    return sub.groupby('fy_end')['gross'].sum() / 1e6   # £m

indep_topup = s251_national('1.2.3')
maint_topup = s251_national('1.2.1')
print("  S251 1.2.3 independent top-up (£m, FY ending):")
print('   ', ', '.join(f"{y}: {v:,.0f}" for y, v in indep_topup.items()))

# ── 1e. Tribunal appeals registered, national (context only; the LA-level
#        series was first published in 2025 and is NOT vintage-available) ────
trib_raw = pd.read_csv(
    ROOT / 'data/raw/sen2_2025/supporting-files/SEND Tribunals and appeal rate 2014-2024.csv',
    header=None, low_memory=False)
trib_years = list(range(2014, 2025))
la_rows = trib_raw[to_num(trib_raw[1]).notna()].index
appeals_nat = {}
for i, yr in enumerate(trib_years):
    col = 2 + 3 * i
    if col < trib_raw.shape[1]:
        appeals_nat[yr] = to_num(trib_raw.loc[la_rows, col]).sum()
appeals_nat = pd.Series(appeals_nat).sort_index()
print("  Tribunal appeals registered (national sum of LA rows):")
print('   ', ', '.join(f"{y}: {v:,.0f}" for y, v in appeals_nat.items()))

# ── 1f. Save the assembled series ────────────────────────────────────────────
nat = pd.DataFrame({
    'caseload_jan': caseload,
    'school_age_0_15': school_age.reindex(caseload.index),
    'post16_16_25': post16.reindex(caseload.index),
    'new_plans_calendar': new_plans.reindex(caseload.index),
    'timeliness_pct': timeliness.reindex(caseload.index),
    'late_plans': late_actual.reindex(caseload.index),
    's251_indep_topup_gbp_m': indep_topup.reindex(caseload.index),
    'tribunal_appeals': appeals_nat.reindex(caseload.index),
})
nat.index.name = 'year'
nat.to_csv(TABLE_DIR / 'vintage_national_series.csv', float_format='%.1f')
print("  Saved vintage_national_series.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: PUBLICATION AUDIT
# ─────────────────────────────────────────────────────────────────────────────
print("\nWriting publication audit...")

audit_rows = [
    # (series, level, first LA-level publication, lag, notes)
    ('EHCP/statement caseload (SEN2)', 'LA + national',
     'Annual since 2011; current-format SFR from May 2015. Jan census published each May.',
     '~4 months',
     'Jan 2016 count published 26 May 2016 (SFR 17/2016). Full LA back-series to 2010 in every release (Table 3).'),
    ('New plans per year (SEN2)', 'LA + national',
     'Annual since 2011; LA-level Table 4 in each May release.',
     '~17 months after calendar year start',
     '2016 calendar-year count (the first unambiguous demand signal) published May 2017.'),
    ('20-week timeliness (SEN2)', 'LA + national',
     'May 2015 release onward (calendar 2014 data; EHCP volumes small in 2014).',
     '~5 months',
     'LA-level Table 9 in each May release. First fully meaningful LA year: calendar 2015, published May 2016.'),
    ('Refused assessment requests (SEN2)', 'National (LA later)',
     'National from May 2016 release (2015 data, new item).',
     '~5 months',
     '10,935 refusals in 2015 vs 8,870 in 2014 was in the May 2016 release text.'),
    ('S251 high-needs spend incl. line 1.2.3 (independent top-ups)', 'LA',
     'Annual; outturn ~8 months after FY end; budget in-year.',
     '~8 months',
     'FY2015/16 outturn available from ~Dec 2016. Independent top-up trend computable from Dec 2017 (2 outturns), robust by Dec 2018.'),
    ('DSG balances / carry-forward', 'LA',
     'S251 outturn + LA accounts, annual.',
     '~8 months',
     'Deficits visible in published outturns from ~2018.'),
    ('SEND tribunal appeals: national volume', 'National',
     'MoJ Tribunal Statistics Quarterly, since before 2014.',
     '~6 months',
     'Rising registrations visible annually throughout.'),
    ('SEND tribunal appeal rate by LA (consistent series)', 'LA',
     'DfE supporting file, first published 2025.',
     'n/a',
     'NOT available to a contemporaneous analyst. Any early-warning design built on LA-level tribunal rates is anachronistic before 2025; SEN2 Table 10 carried partial LA tribunal counts from ~2018.'),
    ('EHCP caseload by primary need type', 'LA (school-age proxy)',
     'School census "SEN in England" each July (school-age only). SEN2 all-age need-type from 2025.',
     '~6 months',
     'ASD/SEMH growth was visible in the school-census series from 2016/17 onward.'),
]
audit = pd.DataFrame(audit_rows, columns=[
    'series', 'geographic_level', 'first_publication', 'publication_lag', 'notes'])
audit.to_csv(TABLE_DIR / 'publication_audit.csv', index=False)
print("  Saved publication_audit.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: VINTAGE PROJECTIONS OF THE NATIONAL CASELOAD
# ─────────────────────────────────────────────────────────────────────────────
print("\nRunning vintage caseload projections...")

# The 2014 impact-assessment null: statements-era trend (2010-2014), i.e. the
# assumption that EHCPs would track the statement population ~1:1.
ia_years = np.arange(2010, 2015)
ia_vals  = caseload.loc[2010:2014].values
ia_slope, ia_icpt = np.polyfit(ia_years, ia_vals, 1)
ia_resid_sd = np.std(ia_vals - (ia_slope * ia_years + ia_icpt), ddof=2)
print(f"  IA null: {ia_slope:,.0f}/yr (+{ia_slope/ia_vals.mean():.1%}/yr), "
      f"residual sd {ia_resid_sd:,.0f}")

def project(vintage_year: int, horizon_end: int = 2025) -> pd.DataFrame:
    """Project caseload from data available at the May release of vintage_year."""
    hist = caseload.loc[:vintage_year]
    yrs_f = np.arange(vintage_year, horizon_end + 1)
    out = {}

    # Model 1: IA null (statements-era linear trend)
    out['ia_null'] = ia_slope * yrs_f + ia_icpt

    # Model 2: linear on the last 4 observations
    recent = hist.tail(4)
    sl, ic = np.polyfit(recent.index.values, recent.values, 1)
    out['linear_recent'] = sl * yrs_f + ic

    # Model 3: exponential on the EHCP era (2015 onward, needs >= 2 points)
    ehcp_era = hist.loc[2015:]
    if len(ehcp_era) >= 2:
        sl_e, ic_e = np.polyfit(ehcp_era.index.values, np.log(ehcp_era.values), 1)
        out['exp_ehcp_era'] = np.exp(sl_e * yrs_f + ic_e)
        out['_growth_rate'] = np.full(len(yrs_f), sl_e)
    proj = pd.DataFrame(out, index=yrs_f)
    proj.index.name = 'year'
    return proj

VINTAGES = [2016, 2017, 2018, 2019, 2020, 2021]
forecast_rows = []
projections = {}
for T in VINTAGES:
    proj = project(T)
    projections[T] = proj
    for model in ['ia_null', 'linear_recent', 'exp_ehcp_era']:
        if model not in proj.columns:
            continue
        for target_yr in [2022, 2023, 2024, 2025]:
            actual = caseload.get(target_yr, np.nan)
            pred = proj.loc[target_yr, model]
            forecast_rows.append({
                'vintage': T, 'model': model, 'target_year': target_yr,
                'predicted': pred, 'actual': actual,
                'error_pct': (pred - actual) / actual * 100 if pd.notna(actual) else np.nan,
            })

forecasts = pd.DataFrame(forecast_rows)
forecasts.to_csv(TABLE_DIR / 'vintage_backtest_forecasts.csv', index=False,
                 float_format='%.1f')
print("  Saved vintage_backtest_forecasts.csv")

print("\n  2024 caseload: predicted vs actual "
      f"({caseload[2024]:,.0f} actual):")
for T in VINTAGES:
    sub = forecasts[(forecasts.vintage == T) & (forecasts.target_year == 2024)]
    parts = [f"{r.model}: {r.predicted:,.0f} ({r.error_pct:+.1f}%)"
             for r in sub.itertuples()]
    print(f"    vintage {T}: " + ' | '.join(parts))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: DETECTION TESTS — WHEN DID THE DATA REJECT "NO CRISIS"?
# ─────────────────────────────────────────────────────────────────────────────
print("\nRunning detection tests...")

det_rows = []
stmt_era_new_max = new_plans.loc[2010:2014].max()   # statements-era peak
for release_yr in range(2016, 2022):
    jan_yr = release_yr           # Jan count published in May of same year
    cal_yr = release_yr - 1       # calendar-year flows published in May
    obs = caseload.get(jan_yr, np.nan)
    ia_pred = ia_slope * jan_yr + ia_icpt
    dev_sigma = (obs - ia_pred) / ia_resid_sd if pd.notna(obs) else np.nan
    yoy = (obs / caseload.get(jan_yr - 1, np.nan) - 1) * 100

    sa = school_age.get(jan_yr, np.nan)
    sa_yoy = (sa / school_age.get(jan_yr - 1, np.nan) - 1) * 100 \
        if pd.notna(sa) else np.nan

    npl = new_plans.get(cal_yr, np.nan)
    npl_vs_peak = (npl / stmt_era_new_max - 1) * 100 if pd.notna(npl) else np.nan

    tl = timeliness.get(cal_yr, np.nan)

    spend_fy = release_yr - 1     # outturn FY ending Mar (release_yr-1), ~Dec lag
    sp = indep_topup.get(spend_fy, np.nan)
    sp_prev = indep_topup.get(spend_fy - 1, np.nan)
    sp_yoy = (sp / sp_prev - 1) * 100 if pd.notna(sp) and pd.notna(sp_prev) else np.nan

    det_rows.append({
        'release_year': release_yr,
        'caseload_jan': obs,
        'caseload_yoy_pct': yoy,
        'dev_from_ia_null_sigma': dev_sigma,
        'school_age_yoy_pct': sa_yoy,
        'new_plans_cal_yr': npl,
        'new_plans_vs_statements_era_peak_pct': npl_vs_peak,
        'timeliness_pct': tl,
        's251_indep_topup_fy_end': spend_fy,
        's251_indep_topup_gbp_m': sp,
        's251_indep_topup_yoy_pct': sp_yoy,
    })

detection = pd.DataFrame(det_rows)
detection.to_csv(TABLE_DIR / 'vintage_detection_tests.csv', index=False,
                 float_format='%.1f')
print(detection.to_string(index=False, float_format='{:.1f}'.format))
print("  Saved vintage_detection_tests.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: LA-LEVEL VINTAGE SIGNALS (all strictly from the May 2019 tables)
# ─────────────────────────────────────────────────────────────────────────────
print("\nTesting LA-level vintage early-warning signals...")

def parse_la_table(sheet: str, xlsx=VINTAGE / 'SEN2_2019_tables.xlsx'):
    df = pd.read_excel(xlsx, sheet_name=sheet, header=None)
    la_mask = df[1].astype(str).str.match(r'^E\d{8}$', na=False)
    return df, df.index[la_mask]

# Table 3: caseload by LA 2010-2019
t3, t3_rows = parse_la_table('Table 3')
t3_cols = scan_year_cols(t3)
la_caseload = pd.DataFrame({'la_code': t3.loc[t3_rows, 1].values})
for yr, col in sorted(t3_cols.items()):
    la_caseload[yr] = to_num(t3.loc[t3_rows, col]).values

# Table 4: new plans by LA 2010-2018
t4_rows = t4.index[t4[1].astype(str).str.match(r'^E\d{8}$', na=False)]
la_newplans = pd.DataFrame({'la_code': t4.loc[t4_rows, 1].values})
for yr, col in sorted(t4_cols.items()):
    la_newplans[yr] = to_num(t4.loc[t4_rows, col]).values

# Table 9: timeliness by LA 2014-2018 (pct cols 9-13)
t9_rows = t9.index[t9[1].astype(str).str.match(r'^E\d{8}$', na=False)]
la_timeliness = pd.DataFrame({'la_code': t9.loc[t9_rows, 1].values})
for i, yr in enumerate(range(2014, 2019)):
    la_timeliness[yr] = to_num(t9.loc[t9_rows, 9 + i]).values

print(f"  Parsed LA tables: caseload {la_caseload.shape}, "
      f"newplans {la_newplans.shape}, timeliness {la_timeliness.shape}")

# Outcomes: 2022-24 collapse labels from the existing pipeline
collapse = pd.read_csv(TABLE_DIR / 'la_collapse_labels.csv')

# Vintage feature sets. Everything below was on gov.uk by 30 May of the vintage
# year shown.
feat = collapse[['la_code', 'la_name', 'y_timeliness', 'y_composite',
                 'mean_timeliness']].copy()

lc = la_caseload.set_index('la_code')
ln = la_newplans.set_index('la_code')
lt = la_timeliness.set_index('la_code')

# vintage 2017: caseload growth 2015->2017; timeliness mean 2015-2016
feat['caseload_growth_15_17'] = feat['la_code'].map(
    (lc[2017] - lc[2015]) / lc[2015] * 100)
feat['timeliness_15_16'] = feat['la_code'].map(lt[[2015, 2016]].mean(axis=1))

# vintage 2019: caseload growth 2015->2019; new-plan growth 2015->2018;
# timeliness mean 2016-2018
feat['caseload_growth_15_19'] = feat['la_code'].map(
    (lc[2019] - lc[2015]) / lc[2015] * 100)
feat['newplan_growth_15_18'] = feat['la_code'].map(
    (ln[2018] - ln[2015]) / ln[2015] * 100)
feat['timeliness_16_18'] = feat['la_code'].map(lt[[2016, 2017, 2018]].mean(axis=1))

signal_defs = [
    ('caseload_growth_15_17', 2017, 'Caseload growth 2015-17 (May 2017 tables)', +1),
    ('timeliness_15_16',      2017, 'Mean 20wk timeliness 2015-16 (May 2017 tables)', -1),
    ('caseload_growth_15_19', 2019, 'Caseload growth 2015-19 (May 2019 tables)', +1),
    ('newplan_growth_15_18',  2019, 'New-plan growth 2015-18 (May 2019 tables)', +1),
    ('timeliness_16_18',      2019, 'Mean 20wk timeliness 2016-18 (May 2019 tables)', -1),
]

sig_rows = []
for col, vint, label, sign in signal_defs:
    score = sign * feat[col].values
    for target in ['y_timeliness', 'y_composite']:
        y = feat[target].values
        a = auc_rank(y, score)
        sig_rows.append({'signal': label, 'vintage': vint, 'target': target,
                         'auc': a, 'n': int(np.isfinite(feat[col]).sum())})

# Persistence check: Spearman between vintage timeliness and 2022-24 timeliness
rho, rho_p = stats.spearmanr(feat['timeliness_16_18'], feat['mean_timeliness'],
                             nan_policy='omit')
print(f"  Spearman(timeliness 2016-18, timeliness 2022-24) = {rho:.2f} (p={rho_p:.1e})")

# Contrast: once the crisis was underway, did timeliness become persistent?
# 2019-21 LA timeliness (published June 2020-June 2022) vs 2022-24.
panel_ts = pd.read_csv(TABLE_DIR / 'panel_timeseries.csv')
tl_1921 = (panel_ts[panel_ts['year'].between(2019, 2021)]
           .groupby('la_code_static')['timeliness_pct'].mean())
feat['timeliness_19_21'] = feat['la_code'].map(tl_1921)
rho_late, rho_late_p = stats.spearmanr(feat['timeliness_19_21'],
                                       feat['mean_timeliness'], nan_policy='omit')
print(f"  Spearman(timeliness 2019-21, timeliness 2022-24) = {rho_late:.2f} "
      f"(p={rho_late_p:.1e})")
for target in ['y_timeliness', 'y_composite']:
    a = auc_rank(feat[target].values, -feat['timeliness_19_21'].values)
    sig_rows.append({'signal': 'Mean 20wk timeliness 2019-21 (crisis underway; pub. by mid-2022)',
                     'vintage': 2022, 'target': target, 'auc': a,
                     'n': int(np.isfinite(feat['timeliness_19_21']).sum())})

signals = pd.DataFrame(sig_rows)
signals.to_csv(TABLE_DIR / 'vintage_la_signals.csv', index=False, float_format='%.3f')
print(signals.to_string(index=False, float_format='{:.3f}'.format))
print("  Saved vintage_la_signals.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: STRESS-TEST REPLAY FROM MID-2017
# ─────────────────────────────────────────────────────────────────────────────
print("\nReplaying the stress test a 2017 analyst could have run...")

# Information set at mid-2017 (all published):
#   caseload Jan 2017 = 287,290; growth 2015->2017 = 9.4%/yr (log)
#   new plans 2016 = ~36k, timeliness 2016 = 58.6%
#   S251 FY2015/16 outturn: independent top-up spend (earliest published line)
BASE_YEAR = 2017
c0  = caseload[2017]
n0  = new_plans[2016]
tl0 = timeliness[2016] / 100
ehcp_era_growth = float(np.polyfit([2015, 2016, 2017],
                                   np.log(caseload.loc[2015:2017].values), 1)[0])
sp0_year = int(min(indep_topup.index))
sp0 = float(indep_topup.loc[sp0_year])
print(f"  Base: caseload {c0:,.0f}, new plans {n0:,.0f}, timeliness {tl0:.1%}, "
      f"EHCP-era growth {ehcp_era_growth:.1%}/yr, "
      f"indep top-up FY-end {sp0_year}: £{sp0:,.0f}m")

DEMAND = {'reversion_3pct': 0.03, 'half_observed': ehcp_era_growth / 2,
          'observed': ehcp_era_growth, 'accelerate_plus25': ehcp_era_growth * 1.25}
THROUGHPUT = {'flat_capacity': 'flat', 'grow_3pct': 'grow3', 'track_demand': 'track'}
COST_INFL = {'flat': 0.00, 'plus5pct': 0.05, 'plus10pct': 0.10}

stress_rows = []
H = 2024 - BASE_YEAR
for d_name, g in DEMAND.items():
    for t_name, t_mode in THROUGHPUT.items():
        for c_name, infl in COST_INFL.items():
            n_t  = n0 * np.exp(g * H)                    # new plans 2024
            timely0 = n0 * tl0
            if t_mode == 'flat':
                timely_t = timely0
            elif t_mode == 'grow3':
                timely_t = timely0 * np.exp(0.03 * H)
            else:
                timely_t = n_t * tl0
            late_t = max(0.0, n_t - min(timely_t, n_t))
            # spend: caseload-driven, share of caseload placed independent held
            # at base; unit costs inflate
            c_t = c0 * np.exp(g * H)
            sp_t = sp0 * (c_t / c0) * (1 + infl) ** H
            stress_rows.append({
                'demand': d_name, 'throughput': t_name, 'cost': c_name,
                'demand_growth_pa': g,
                'caseload_2024': c_t, 'new_plans_2024': n_t,
                'late_plans_2024': late_t,
                'timeliness_2024_pct': min(timely_t, n_t) / n_t * 100,
                'indep_topup_2024_gbp_m': sp_t,
            })

stress = pd.DataFrame(stress_rows)
stress.to_csv(TABLE_DIR / 'stress_test_2017.csv', index=False, float_format='%.1f')

actual_2024 = {
    'caseload': caseload.get(2024, np.nan),
    'new_plans': new_plans.get(2024, np.nan),
    'late_plans': late_actual.get(2024, np.nan),
    'timeliness': timeliness.get(2024, np.nan),
    'indep_topup': indep_topup.get(2024, np.nan),
}
print(f"  Scenario grid: {len(stress)} cells")
print(f"  Actual 2024: caseload {actual_2024['caseload']:,.0f}, "
      f"late plans {actual_2024['late_plans']:,.0f}, "
      f"indep top-up £{actual_2024['indep_topup']:,.0f}m")
for metric, actual_key in [('caseload_2024', 'caseload'),
                            ('late_plans_2024', 'late_plans'),
                            ('indep_topup_2024_gbp_m', 'indep_topup')]:
    lo, hi = stress[metric].min(), stress[metric].max()
    a = actual_2024[actual_key]
    inside = lo <= a <= hi if pd.notna(a) else None
    print(f"    {metric}: envelope [{lo:,.0f}, {hi:,.0f}] vs actual {a:,.0f} "
          f"-> {'INSIDE' if inside else 'OUTSIDE'}")

pct_worse = {}
if pd.notna(actual_2024['indep_topup']):
    pct_worse['spend_scenarios_at_least_2x'] = float(
        (stress['indep_topup_2024_gbp_m'] >= 2 * sp0).mean())
    print(f"  Share of scenarios with indep top-up >= 2x base by 2024: "
          f"{pct_worse['spend_scenarios_at_least_2x']:.0%}")
print("  Saved stress_test_2017.csv")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: FIGURES
# ─────────────────────────────────────────────────────────────────────────────
print("\nProducing figures 47-50...")

# ── Figure 47: vintage projections vs actual ─────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey=True)
axes = axes.flatten()
for ax, T in zip(axes, [2016, 2017, 2018, 2019]):
    proj = projections[T]
    hist = caseload.loc[:T]
    ax.plot(caseload.index, caseload.values / 1000, color=C_ACTUAL, lw=2.2,
            marker='o', ms=4, label='Actual', zorder=5)
    ax.plot(hist.index, hist.values / 1000, color=C_ACTUAL, lw=0, marker='o',
            ms=5, zorder=6)
    ax.axvspan(caseload.index.min() - 0.5, T + 0.02, alpha=0.06, color='gray')
    ax.plot(proj.index, proj['ia_null'] / 1000, color=C_NULL, lw=1.8,
            linestyle=':', label='2014 impact-assessment trend')
    ax.plot(proj.index, proj['linear_recent'] / 1000, color=C_LINEAR, lw=1.8,
            linestyle='--', label='Linear (last 4 years)')
    if 'exp_ehcp_era' in proj.columns:
        ax.plot(proj.index, proj['exp_ehcp_era'] / 1000, color=C_EXP, lw=2.0,
                label='Exponential (EHCP era)')
        pred24 = proj.loc[2024, 'exp_ehcp_era'] / 1000
        err = (proj.loc[2024, 'exp_ehcp_era'] - caseload[2024]) / caseload[2024] * 100
        ax.annotate(f"2024: {pred24:.0f}k ({err:+.0f}%)",
                    xy=(2024, pred24), xytext=(-86, 8),
                    textcoords='offset points', fontsize=8, color=C_EXP,
                    fontweight='bold')
    ax.set_title(f"Analyst in mid-{T}\n(data published by May {T} only)",
                 fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(2010, 2025.5)
    if T == 2016:
        ax.legend(fontsize=8, loc='upper left')
axes[0].set_ylabel('Statements + EHCPs (thousands)')
axes[2].set_ylabel('Statements + EHCPs (thousands)')
plt.suptitle('What simple extrapolation of published data predicted, by vintage year\n'
             'Shaded region = data available at that date. All series from the original publications.',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(FIG_DIR / '47_vintage_projections.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 47")

# ── Figure 48: growth decomposition + new-plans detection ────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

ax = axes[0]
yrs = [y for y in range(2011, 2020)]
sa_delta = [school_age[y] - school_age[y - 1] for y in yrs]
p16_delta = [post16[y] - post16[y - 1] for y in yrs]
ax.bar(yrs, np.array(sa_delta) / 1000, color=C_SCHOOL, label='School age (0-15)',
       width=0.7)
ax.bar(yrs, np.array(p16_delta) / 1000, bottom=np.array(sa_delta) / 1000,
       color=C_POST16, label='Post-16 (16-25)', width=0.7)
ax.axhline(ia_slope / 1000, color=C_NULL, lw=1.6, linestyle=':',
           label=f'Statements-era trend (+{ia_slope/1000:.1f}k/yr)')
ax.set_title('Annual growth in caseload, decomposed by age\n'
             '(the "it\'s just the new 16-25 age range" test)',
             fontsize=10, fontweight='bold')
ax.set_ylabel('Year-on-year change (thousands)')
ax.legend(fontsize=8)
ax.grid(True, axis='y', alpha=0.3)

ax2 = axes[1]
np_yrs = [y for y in new_plans.index if 2010 <= y <= 2024]
np_vals = [new_plans[y] / 1000 for y in np_yrs]
colors = [C_NULL if y <= 2015 else C_EXP for y in np_yrs]
ax2.bar(np_yrs, np_vals, color=colors, width=0.7)
ax2.axhspan(new_plans.loc[2010:2014].min() / 1000,
            new_plans.loc[2010:2014].max() / 1000, alpha=0.15, color=C_NULL)
ax2.text(2010.2, new_plans.loc[2010:2014].max() / 1000 + 1.2,
         'Statements-era range 2010-14', fontsize=8, color='dimgray')
for y in [2016, 2017, 2018]:
    ax2.annotate(f"+{(new_plans[y]/new_plans[y-1]-1)*100:.0f}%",
                 xy=(y, new_plans[y] / 1000), xytext=(0, 4),
                 textcoords='offset points', ha='center', fontsize=8,
                 fontweight='bold', color=C_EXP)
ax2.set_title('New plans per calendar year\n(gray = statements era, red = EHCP era)',
              fontsize=10, fontweight='bold')
ax2.set_ylabel('New statements/EHCPs (thousands)')
ax2.grid(True, axis='y', alpha=0.3)

plt.suptitle('When the two standard defences failed: age-range extension and one-off conversion',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(FIG_DIR / '48_growth_decomposition.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 48")

# ── Figure 49: stress-test replay ────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

years_h = np.arange(BASE_YEAR, 2025)
ax = axes[0]
for _, row in stress.drop_duplicates(['demand', 'throughput']).iterrows():
    g = row['demand_growth_pa']
    n_path = n0 * np.exp(g * (years_h - BASE_YEAR))
    timely0 = n0 * tl0
    if row['throughput'] == 'flat_capacity':
        timely_path = np.full_like(n_path, timely0)
    elif row['throughput'] == 'grow_3pct':
        timely_path = timely0 * np.exp(0.03 * (years_h - BASE_YEAR))
    else:
        timely_path = n_path * tl0
    late_path = np.maximum(0, n_path - np.minimum(timely_path, n_path))
    ax.plot(years_h, late_path / 1000, color='#bbbbbb', lw=1.0, alpha=0.8, zorder=1)
al = late_actual.loc[[y for y in late_actual.index if 2017 <= y <= 2024]]
ax.plot(al.index, al.values / 1000, color=C_ACTUAL, lw=2.5, marker='o', ms=5,
        label='Actual', zorder=5)
ax.set_title('Late plans per year: 2017 stress-test scenarios (gray)\nvs what happened',
             fontsize=10, fontweight='bold')
ax.set_ylabel('Plans issued outside 20 weeks (thousands)')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

ax2 = axes[1]
for _, row in stress.drop_duplicates(['demand', 'cost']).iterrows():
    g, infl = row['demand_growth_pa'], \
        {'flat': 0.0, 'plus5pct': 0.05, 'plus10pct': 0.10}[row['cost']]
    sp_path = sp0 * np.exp(g * (years_h - BASE_YEAR)) * (1 + infl) ** (years_h - BASE_YEAR)
    ax2.plot(years_h, sp_path / 1000, color='#bbbbbb', lw=1.0, alpha=0.8, zorder=1)
asp = indep_topup.loc[[y for y in indep_topup.index if 2017 <= y <= 2025]]
ax2.plot(asp.index, asp.values / 1000, color=C_ACTUAL, lw=2.5, marker='o', ms=5,
         label='Actual (S251 outturn)', zorder=5)
ax2.set_title('Independent top-up spend: 2017 scenarios (gray)\nvs S251 outturns',
              fontsize=10, fontweight='bold')
ax2.set_ylabel('S251 line 1.2.3 (£bn, FY ending)')
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

plt.suptitle('The stress test nobody ran: scenarios constructible in mid-2017 from published data',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(FIG_DIR / '49_stress_test_2017.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 49")

# ── Figure 50: LA-level vintage signals ──────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

ax = axes[0]
sc = feat.dropna(subset=['timeliness_16_18', 'mean_timeliness', 'y_timeliness'])
coll = sc['y_timeliness'] == 1
ax.scatter(sc.loc[~coll, 'timeliness_16_18'], sc.loc[~coll, 'mean_timeliness'],
           c='#aec7e8', s=32, alpha=0.75, label='No timeliness collapse')
ax.scatter(sc.loc[coll, 'timeliness_16_18'], sc.loc[coll, 'mean_timeliness'],
           c=C_EXP, s=44, marker='D', alpha=0.85, label='Collapsed 2022-24 (<40%)')
ax.axhline(40, color=C_EXP, lw=1, linestyle=':', alpha=0.6)
ax.set_xlabel('Mean 20-week timeliness 2016-18 (%, published May 2019)')
ax.set_ylabel('Mean 20-week timeliness 2022-24 (%)')
ax.set_title(f'Pre-crisis rank order did NOT persist: Spearman rho = {rho:.2f}\n'
             f'(vs rho = {rho_late:.2f} once the crisis was underway, 2019-21)',
             fontsize=10, fontweight='bold')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

ax2 = axes[1]
plot_sig = signals.copy()
plot_sig['label'] = (plot_sig['signal'].str.replace(r' \(May \d{4} tables\)', '',
                                                    regex=True)
                     + '\n(' + plot_sig['vintage'].astype(str) + ')')
tgt_colors = {'y_timeliness': C_LINEAR, 'y_composite': C_POST16}
w = 0.38
labels = plot_sig['label'].unique()
for i, tgt in enumerate(['y_timeliness', 'y_composite']):
    sub = plot_sig[plot_sig['target'] == tgt].set_index('label').reindex(labels)
    ax2.barh(np.arange(len(labels)) + (i - 0.5) * w, sub['auc'], height=w,
             color=tgt_colors[tgt],
             label={'y_timeliness': 'Timeliness collapse',
                    'y_composite': 'Composite collapse'}[tgt])
ax2.axvline(0.5, color='black', lw=1, linestyle='--', alpha=0.6)
ax2.set_yticks(np.arange(len(labels)))
ax2.set_yticklabels(labels, fontsize=8)
ax2.set_xlabel('AUC (univariate, rank-based; 0.5 = random)')
ax2.set_xlim(0.35, 1.0)
ax2.invert_yaxis()
ax2.set_title('Predicting 2022-24 collapse from genuinely vintage LA data',
              fontsize=10, fontweight='bold')
ax2.legend(fontsize=8, loc='lower right')
ax2.grid(True, axis='x', alpha=0.3)

plt.suptitle('LA-level early warning from genuinely vintage data: largely NOT possible before 2019\n'
             'The national crisis was predictable; which councils would fail was not',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(FIG_DIR / '50_vintage_la_signals.png', dpi=FIGURE_DPI, bbox_inches='tight')
plt.close()
print("  Saved Figure 50")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("VINTAGE BACKTEST SUMMARY")
print("=" * 70)
best24 = forecasts[(forecasts.model == 'exp_ehcp_era') & (forecasts.target_year == 2024)]
for r in best24.itertuples():
    print(f"  Vintage {r.vintage}: EHCP-era exponential predicts 2024 caseload "
          f"{r.predicted:,.0f} vs actual {r.actual:,.0f} ({r.error_pct:+.1f}%)")
print("\nDone.")
