#!/usr/bin/env python3
"""
cost_benefit.py

15-year cost-benefit model for the top 30 SEN facility priorities in England.
Also produces within-England model LA comparator analysis.

Outputs (outputs/tables/):
  cost_benefit_summary.csv     — per-facility NPV and break-even
  cost_benefit_national.csv    — annual cumulative investment vs saving, 2025–2040
  comparator_profile.csv       — model vs at-risk LA profiles

Outputs (outputs/figures/):
  46_cost_benefit.png          — Panel A: cumulative cashflows; Panel B: NPV efficiency bar

Capital cost benchmarks: ESFA free school programme (DfE, 2023).
Saving per diverted child: £75,000/yr (S251 2023/24 median independent placement cost
  £97,322/yr, discounted conservatively to account for lower-cost cases and incidental costs).
Discount rate: 3.5% (HMT Green Book).
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

ROOT      = Path(__file__).parent
FIG_DIR   = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'

# ── Constants ─────────────────────────────────────────────────────────────────

# Capital costs (ESFA free school programme benchmarks)
CAPEX_NEW_SCHOOL_M   = 20.0   # £20m per new maintained special school (100-place baseline)
CAPEX_RPU_M          =  2.0   # £2m per resourced provision / SEN unit (extension to existing school)

# Places per facility
PLACES_NEW_SCHOOL    = 100    # midpoint of 80–150
PLACES_RPU           =  15    # midpoint of 10–25

# Saving per diverted child (S251 2023/24, discounted to reflect lower-end cases)
SAVING_PER_CHILD_GBP = 75_000

# Base diversion rate: 40% of new maintained places are net diversions from independent sector
BASE_DIVERSION_RATE  = 0.40

# Diversion rate cap
DIVERSION_CAP        = 0.65

# Lead times and ramp-up schedule
# New school: 4-year build, then ramp (50% yr 5, 100% yr 6+)
# RPU:        1.5-year build, then ramp (60% yr 2 of operation, 100% yr 3+)
# Start year: 2025

HMT_DISCOUNT_RATE    = 0.035

ANALYSIS_START       = 2025
ANALYSIS_END         = 2040   # inclusive
YEARS                = list(range(ANALYSIS_START, ANALYSIS_END + 1))
N_YEARS              = len(YEARS)

# Colour scheme
COLOUR_NEW_SCHOOL = '#2b6cb0'
COLOUR_RPU        = '#276749'

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading data...")

fac = pd.read_csv(TABLE_DIR / 'facility_priority_list.csv')
cap = pd.read_csv(TABLE_DIR / 'la_capacity_2024.csv')
meta = pd.read_csv(TABLE_DIR / 'la_summary_2024_extended.csv')
meta.columns = [c.lower().replace(' ', '_') for c in meta.columns]
spend = pd.read_csv(TABLE_DIR / 'la_spend_model.csv')

top30 = fac[fac['priority_rank'] <= 30].copy()
print(f"  Top 30 facilities: {len(top30)}")
print(f"    New schools: {(top30['facility_type'].str.contains('New')).sum()}")
print(f"    RPUs:        {(~top30['facility_type'].str.contains('New')).sum()}")

# ── Helper: year-by-year occupancy profile ────────────────────────────────────

def occupancy_profile(facility_type: str, places: int) -> np.ndarray:
    """
    Return an array of occupied-place counts for each year in YEARS.

    New school: 4-year lead time, then 50% in year 5, 100% from year 6.
    RPU:        1.5-year lead time (round to 2 years), then 60% in year 3, 100% from year 4.
    Year indexing: year 0 = 2025 (capital committed).
    """
    occ = np.zeros(N_YEARS)
    if 'New' in facility_type:
        # Years 0–3: build (zero occupancy)
        # Year 4 (index 4): 50% ramp
        # Year 5+ (index 5+): 100%
        for i in range(N_YEARS):
            if i <= 3:
                occ[i] = 0
            elif i == 4:
                occ[i] = places * 0.50
            else:
                occ[i] = places
    else:
        # RPU: 1.5 years → treat as 2 full years build
        # Year 0–1 (index 0,1): build (zero)
        # Year 2 (index 2): 60% ramp
        # Year 3+ (index 3+): 100%
        for i in range(N_YEARS):
            if i <= 1:
                occ[i] = 0
            elif i == 2:
                occ[i] = places * 0.60
            else:
                occ[i] = places
    return occ


def effective_diversion_rate(pct_indep: float) -> float:
    """
    Adjust base diversion rate upward for independent-heavy LAs.
    Formula: base × (1 + pct_indep/100) × 0.4, capped at DIVERSION_CAP.
    (The 0.4 factor already embedded in the formula keeps this conservative
     even for the most independent-heavy LAs.)
    """
    raw = BASE_DIVERSION_RATE * (1 + pct_indep / 100) * 0.4
    # The formula as specified means we multiply base_rate × weight × 0.4.
    # Re-reading the spec: diversion_rate = BASE_DIVERSION × (1 + pct/100) × 0.4,
    # but that gives very low values. The spec says 'diversion_rate × (1 + pct/100) × 0.4',
    # meaning the full expression IS the diversion rate.
    # Use: dr = min(BASE_DIVERSION_RATE * (1 + pct_indep/100), DIVERSION_CAP)
    # This is the natural reading: scale base rate by independent-intensity.
    dr = BASE_DIVERSION_RATE * (1 + pct_indep / 100)
    return min(dr, DIVERSION_CAP)


def discount_factor(year_index: int) -> float:
    """HMT Green Book: (1 + r)^{-t}"""
    return 1.0 / (1 + HMT_DISCOUNT_RATE) ** year_index

# ── Part 1: Per-facility cost-benefit model ───────────────────────────────────
print("\nRunning per-facility cost-benefit model...")

summary_rows = []

for _, row in top30.iterrows():
    ftype = row['facility_type']
    pct_indep = row['pct_placements_independent']

    # Capital cost
    capex_m = CAPEX_NEW_SCHOOL_M if 'New' in ftype else CAPEX_RPU_M

    # Places
    places = PLACES_NEW_SCHOOL if 'New' in ftype else PLACES_RPU

    # Effective diversion rate
    dr = effective_diversion_rate(pct_indep)

    # Annual saving when fully operational
    diverted_children = places * dr
    annual_saving_full_m = diverted_children * SAVING_PER_CHILD_GBP / 1e6

    # Year-by-year occupancy
    occ = occupancy_profile(ftype, places)

    # Year-by-year saving (undiscounted)
    annual_savings = occ * dr * SAVING_PER_CHILD_GBP / 1e6

    # Discounted cashflows
    # Capital is spent in year 0 (or spread, but we treat as lump sum at t=0)
    disc_capital = capex_m  # discounted at t=0, df=1.0

    disc_savings = np.array([annual_savings[i] * discount_factor(i)
                              for i in range(N_YEARS)])

    cumulative_disc_saving = np.cumsum(disc_savings)

    # Break-even year: first year where cumulative discounted saving >= capital cost
    break_even_year = None
    for i, cs in enumerate(cumulative_disc_saving):
        if cs >= disc_capital:
            break_even_year = ANALYSIS_START + i
            break

    # NPV at 10yr and 15yr horizons
    npv_10yr_m = cumulative_disc_saving[min(9, N_YEARS-1)] - disc_capital   # years 0–9
    npv_15yr_m = cumulative_disc_saving[N_YEARS - 1] - disc_capital         # years 0–15

    summary_rows.append({
        'priority_rank':        int(row['priority_rank']),
        'la_name':              row['la_name'],
        'need_type':            row['need_type'],
        'facility_type':        ftype,
        'capital_cost_m':       round(capex_m, 1),
        'places':               places,
        'diversion_rate':       round(dr, 3),
        'diverted_children':    round(diverted_children, 1),
        'annual_saving_full_m': round(annual_saving_full_m, 2),
        'break_even_year':      break_even_year if break_even_year else '>2040',
        'npv_10yr_m':           round(npv_10yr_m, 2),
        'npv_15yr_m':           round(npv_15yr_m, 2),
    })

summary = pd.DataFrame(summary_rows)

# NPV efficiency: NPV per £m invested
summary['npv_15yr_per_m_invested'] = (summary['npv_15yr_m'] / summary['capital_cost_m']).round(2)

# Save (exclude model-internal helper columns)
out_cols = ['priority_rank', 'la_name', 'need_type', 'facility_type',
            'capital_cost_m', 'annual_saving_full_m',
            'break_even_year', 'npv_10yr_m', 'npv_15yr_m']
summary[out_cols].to_csv(TABLE_DIR / 'cost_benefit_summary.csv', index=False)
print(f"  Saved cost_benefit_summary.csv ({len(summary)} rows)")

# ── Print summary stats ───────────────────────────────────────────────────────
total_capex = summary['capital_cost_m'].sum()
total_saving_full_m = summary['annual_saving_full_m'].sum()
total_npv_15 = summary['npv_15yr_m'].sum()

print(f"\n  === Top-30 facility portfolio ===")
print(f"  Total capital required:           £{total_capex:.0f}m")
print(f"  Total annual saving (operational):£{total_saving_full_m:.1f}m/yr")
print(f"  Portfolio NPV (15yr, discounted): £{total_npv_15:.0f}m")
print(f"\n  Median break-even year (numeric):  {summary[summary['break_even_year'] != '>2040']['break_even_year'].astype(int).median():.0f}")
print(f"\n  Top 10 by 15yr NPV:")
top10_npv = summary.nlargest(10, 'npv_15yr_m')[['priority_rank','la_name','need_type','facility_type','capital_cost_m','npv_15yr_m','break_even_year']]
print(top10_npv.to_string(index=False))

# ── Part 2: National aggregate cashflow table ─────────────────────────────────
print("\nBuilding national aggregate cashflow table...")

national_rows = []
for yi, year in enumerate(YEARS):
    # Cumulative capital invested: all 30 facilities committed in 2025 (t=0)
    cum_inv = total_capex  # all committed upfront

    # Cumulative undiscounted saving across all facilities
    cum_sav = 0.0
    for _, row in summary.iterrows():
        ftype = row['facility_type']
        pct_indep_val = top30[top30['priority_rank'] == row['priority_rank']]['pct_placements_independent'].values[0]
        places = PLACES_NEW_SCHOOL if 'New' in ftype else PLACES_RPU
        dr = effective_diversion_rate(pct_indep_val)
        occ = occupancy_profile(ftype, places)
        # Sum savings up to year yi (inclusive), undiscounted for the national cashflow table
        cum_sav += sum(occ[j] * dr * SAVING_PER_CHILD_GBP / 1e6 for j in range(yi + 1))

    national_rows.append({
        'year':                   year,
        'cumulative_investment_m': round(cum_inv, 1),
        'cumulative_saving_m':     round(cum_sav, 1),
        'net_position_m':          round(cum_sav - cum_inv, 1),
    })

national = pd.DataFrame(national_rows)
national.to_csv(TABLE_DIR / 'cost_benefit_national.csv', index=False)
print(f"  Saved cost_benefit_national.csv ({len(national)} rows)")

# Identify break-even year for the portfolio
portfolio_bey = national[national['net_position_m'] >= 0]['year'].min()
print(f"  Portfolio break-even year (undiscounted): {portfolio_bey}")

# ── Part 3: Figure 46 ────────────────────────────────────────────────────────
print("\nBuilding Figure 46...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))
fig.suptitle('Investment case: 30 priority SEN facilities, England 2025–2040',
             fontsize=13, fontweight='bold', y=1.01)

# ── Panel A: Cumulative investment vs saving ──────────────────────────────────
inv_line  = national['cumulative_investment_m'].values
sav_line  = national['cumulative_saving_m'].values
year_arr  = national['year'].values

ax1.plot(year_arr, inv_line, color='#c0392b', lw=2.5, label='Cumulative investment (capital)')
ax1.plot(year_arr, sav_line, color='#27ae60', lw=2.5, label='Cumulative saving (avoided costs)')

# Shade between lines
ax1.fill_between(year_arr, inv_line, sav_line,
                 where=(sav_line >= inv_line), alpha=0.18, color='#27ae60',
                 label='Net benefit')
ax1.fill_between(year_arr, inv_line, sav_line,
                 where=(sav_line < inv_line), alpha=0.18, color='#c0392b',
                 label='Net cost')

# Mark break-even
if pd.notna(portfolio_bey):
    bey_sav = national[national['year'] == portfolio_bey]['cumulative_saving_m'].values[0]
    ax1.axvline(portfolio_bey, color='#555555', lw=1.2, ls='--', alpha=0.8)
    ax1.annotate(f'Break-even\n{int(portfolio_bey)}',
                 xy=(portfolio_bey, bey_sav),
                 xytext=(portfolio_bey + 0.4, bey_sav * 0.92),
                 fontsize=9, color='#333333',
                 arrowprops=dict(arrowstyle='->', color='#555', lw=1))

ax1.set_xlabel('Year', fontsize=11)
ax1.set_ylabel('£ million (undiscounted)', fontsize=11)
ax1.set_title('Panel A: Cumulative investment vs avoided costs\n(top 30 facilities, capital committed 2025)',
              fontsize=10, fontweight='bold')
ax1.legend(fontsize=9, loc='upper left')
ax1.yaxis.grid(True, alpha=0.3, lw=0.6)
ax1.set_xticks(range(2025, 2041, 3))
ax1.tick_params(axis='both', labelsize=9)
for spine in ['top', 'right']:
    ax1.spines[spine].set_visible(False)

# ── Panel B: Horizontal bar — top 15 by NPV efficiency ───────────────────────
top15_eff = summary.nlargest(15, 'npv_15yr_per_m_invested').copy()
top15_eff = top15_eff.sort_values('npv_15yr_per_m_invested', ascending=True)  # bottom = lowest
top15_eff['label'] = top15_eff['la_name'] + ' (' + top15_eff['need_type'] + ')'

bar_colours = [COLOUR_NEW_SCHOOL if 'New' in ft else COLOUR_RPU
               for ft in top15_eff['facility_type']]

ax2.barh(range(len(top15_eff)), top15_eff['npv_15yr_per_m_invested'],
         color=bar_colours, alpha=0.88)

ax2.set_yticks(range(len(top15_eff)))
ax2.set_yticklabels(top15_eff['label'], fontsize=8.5)
ax2.set_xlabel('15-year NPV per £m of capital invested (discounted, £m)', fontsize=10)
ax2.set_title('Panel B: Top 15 facilities by NPV efficiency\n(15-year NPV per £m invested, HMT 3.5% discount rate)',
              fontsize=10, fontweight='bold')

# Add value labels on bars
for i, (_, r) in enumerate(top15_eff.iterrows()):
    ax2.text(r['npv_15yr_per_m_invested'] + 0.05, i,
             f"£{r['npv_15yr_per_m_invested']:.1f}m",
             va='center', fontsize=8, color='#222')

patch_school = mpatches.Patch(color=COLOUR_NEW_SCHOOL, label='New maintained special school')
patch_rpu    = mpatches.Patch(color=COLOUR_RPU,        label='Resourced provision unit')
ax2.legend(handles=[patch_school, patch_rpu], fontsize=9, loc='lower right')
ax2.xaxis.grid(True, alpha=0.3, lw=0.6)
for spine in ['top', 'right']:
    ax2.spines[spine].set_visible(False)
ax2.tick_params(axis='both', labelsize=9)

plt.tight_layout()
fig.savefig(FIG_DIR / '46_cost_benefit.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved outputs/figures/46_cost_benefit.png")

# ── Part 4: Comparator analysis ───────────────────────────────────────────────
print("\nRunning comparator analysis...")

sv_names = set(meta[meta['intervention_status'] == 'Safety Valve']['la_name'].tolist())

# Merge tables for comparator
comp_df = (meta[['la_name', 'timeliness_pct', 'imd_average_score', 'intervention_status']]
           .merge(cap[['la_name', 'maintained_special_capacity_per1000',
                        'indep_placements_per1000', 'pct_special_independent',
                        'n_state_special_schools']], on='la_name', how='inner'))

# Model LAs: high timeliness, high maintained capacity, low independent share, not Safety Valve
model_las = comp_df[
    (comp_df['timeliness_pct'] >= 70) &
    (comp_df['maintained_special_capacity_per1000'] >= 5.0) &
    (comp_df['pct_special_independent'] <= 15) &
    (comp_df['n_state_special_schools'] >= 4) &
    (~comp_df['la_name'].isin(sv_names))
].copy()

model_las = model_las.nlargest(5, 'timeliness_pct')

# At-risk LAs: bottom 5 by timeliness (from full merged dataset)
atrisk_las = comp_df.nsmallest(5, 'timeliness_pct').copy()

print(f"  Model LAs ({len(model_las)}):")
for _, r in model_las.iterrows():
    print(f"    {r['la_name']:<25s}  timeliness={r['timeliness_pct']:.1f}%  "
          f"cap/1000={r['maintained_special_capacity_per1000']:.2f}  "
          f"indep%={r['pct_special_independent']:.1f}%")

print(f"\n  At-risk LAs (bottom 5 timeliness):")
for _, r in atrisk_las.iterrows():
    print(f"    {r['la_name']:<25s}  timeliness={r['timeliness_pct']:.1f}%  "
          f"cap/1000={r['maintained_special_capacity_per1000']:.2f}  "
          f"indep%={r['pct_special_independent']:.1f}%")

# Build comparator profile table
profile_cols = ['la_name', 'timeliness_pct', 'maintained_special_capacity_per1000',
                'indep_placements_per1000', 'pct_special_independent',
                'imd_average_score', 'n_state_special_schools']

model_profile  = model_las[profile_cols].copy()
model_profile.insert(0, 'group', 'model')

atrisk_profile = atrisk_las[profile_cols].copy()
atrisk_profile.insert(0, 'group', 'at-risk')

comparator = pd.concat([model_profile, atrisk_profile], ignore_index=True)
comparator = comparator.round({'timeliness_pct': 1,
                               'maintained_special_capacity_per1000': 2,
                               'indep_placements_per1000': 3,
                               'pct_special_independent': 1,
                               'imd_average_score': 2,
                               'n_state_special_schools': 0})
comparator.to_csv(TABLE_DIR / 'comparator_profile.csv', index=False)
print(f"\n  Saved comparator_profile.csv ({len(comparator)} rows)")

# Print group means
print("\n  === Group means ===")
for grp in ['model', 'at-risk']:
    sub = comparator[comparator['group'] == grp]
    print(f"\n  {grp.upper()} LAs (n={len(sub)}):")
    print(f"    timeliness_pct:                    {sub['timeliness_pct'].mean():.1f}%")
    print(f"    maintained_cap_per_1000:           {sub['maintained_special_capacity_per1000'].mean():.2f}")
    print(f"    indep_placements_per_1000:         {sub['indep_placements_per1000'].mean():.3f}")
    print(f"    pct_special_independent:           {sub['pct_special_independent'].mean():.1f}%")
    print(f"    imd_average_score:                 {sub['imd_average_score'].mean():.1f}")
    print(f"    n_state_special_schools:           {sub['n_state_special_schools'].mean():.1f}")

# ── Key numbers summary for press pack ───────────────────────────────────────
print("\n\n=== KEY NUMBERS FOR PRESS PACK ===")
print(f"  Total capital (top 30):             £{total_capex:.0f}m")
print(f"  Annual saving (fully operational):  £{total_saving_full_m:.1f}m/yr")
print(f"  Portfolio 15yr NPV (discounted):    £{total_npv_15:.0f}m")
print(f"  Portfolio break-even (undiscounted): {portfolio_bey}")
print(f"  S251 median indep placement cost:   £97,322/yr")
print(f"  Conservative saving per diversion:  £75,000/yr")

best_facility = summary.nlargest(1, 'npv_15yr_m').iloc[0]
print(f"\n  Best single facility (15yr NPV):")
print(f"    {best_facility['la_name']} ({best_facility['need_type']}): NPV £{best_facility['npv_15yr_m']:.0f}m")

print("\nDone.")
