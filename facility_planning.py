#!/usr/bin/env python3
"""
facility_planning.py

Ranks every LA × need-type combination by the urgency of building new
maintained provision. Recommends facility type (new special school vs
resourced provision unit) based on distance to nearest maintained provision.

Outputs:
  outputs/tables/facility_priority_list.csv   — full scored list
  outputs/figures/44_facility_priority.png    — top-30 visual
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT      = Path(__file__).parent
FIG_DIR   = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'

# ── Need types to analyse ────────────────────────────────────────────────────
# Maps: (mismatch gap col, access distance col, display label, facility label,
#        distance threshold km above which a new school is needed)
NEED_TYPES = {
    'ASD':  ('asd_gap',  'dist_state_ASD_km',  'ASD',  'Autistic Spectrum Disorder', 20),
    'SEMH': ('semh_gap', 'dist_state_SEMH_km', 'SEMH', 'Social, Emotional & Mental Health', 15),
    'MLD':  ('mld_gap',  'dist_state_MLD_km',  'MLD',  'Moderate Learning Difficulties', 20),
    'SLD':  ('sld_gap',  'dist_state_SLD_km',  'SLD',  'Severe Learning Difficulties', 20),
}

NEED_COLORS = {
    'ASD':  '#2c7bb6',
    'SEMH': '#d7191c',
    'MLD':  '#fdae61',
    'SLD':  '#1a9641',
}

print("Loading tables...")

# ─── 1. Load and merge source tables ─────────────────────────────────────────
mismatch  = pd.read_csv(TABLE_DIR / 'la_mismatch_2024.csv')
capacity  = pd.read_csv(TABLE_DIR / 'la_capacity_2024.csv')
access    = pd.read_csv(TABLE_DIR / 'la_school_access.csv')
forecasts = pd.read_csv(TABLE_DIR / 'la_scenario_forecasts.csv')
risk      = pd.read_csv(TABLE_DIR / 'la_risk_scores_2024.csv')

# Compute SLD gap (not pre-computed in mismatch table)
mismatch['sld_gap'] = mismatch['pct_SLD_now'] - mismatch['supply_pct_SLD']

# Scenario: continuation, years 2024 and 2030
cont = forecasts[forecasts['scenario'] == 'continuation']
base2024 = cont[cont['year'] == 2024][['la_code', 'demand_projected',
                                        'indep_placements_projected', 'cost_projected_m']].copy()
base2030 = cont[cont['year'] == 2030][['la_code', 'demand_projected',
                                        'indep_placements_projected', 'cost_projected_m']].copy()
base2024.columns = ['la_code', 'demand_2024', 'indep_2024', 'cost_2024_m']
base2030.columns = ['la_code', 'demand_2030', 'indep_2030', 'cost_2030_m']

# ─── 2. Build per-LA base frame ───────────────────────────────────────────────
base = (mismatch[['la_code', 'la_name', 'region', 'intervention_status',
                   'total_ehcp_now',
                   'asd_gap', 'semh_gap', 'mld_gap', 'sld_gap',
                   'pct_ASD_now', 'pct_SEMH_now', 'pct_MLD_now', 'pct_SLD_now']]
        .merge(capacity[['la_code', 'pct_special_independent',
                          'maintained_special_capacity_per1000',
                          'indep_placements_per1000']], on='la_code', how='left')
        .merge(access[['la_code',
                        'dist_state_ASD_km', 'dist_state_SEMH_km',
                        'dist_state_MLD_km', 'dist_state_SLD_km']], on='la_code', how='left')
        .merge(base2024, on='la_code', how='left')
        .merge(base2030, on='la_code', how='left')
        .merge(risk[['la_code', 'risk_score']], on='la_code', how='left'))

base['demand_growth_2030'] = np.where(
    base['demand_2024'] > 0,
    base['demand_2030'] / base['demand_2024'],
    np.nan
)

print(f"  Base frame: {len(base)} LAs")

# ─── 3. Compute priority score per (LA × need type) ─────────────────────────
rows = []
for nt_key, (gap_col, dist_col, nt_short, nt_long, dist_thresh) in NEED_TYPES.items():
    for _, la in base.iterrows():
        gap_pp = la[gap_col]
        if pd.isna(gap_pp) or gap_pp <= 0:
            continue  # no gap → no unmet need

        # Absolute unmet demand: EHCP children whose need type exceeds maintained supply
        gap_abs = la['total_ehcp_now'] * gap_pp / 100

        # Distance to nearest maintained provision of this type
        dist_km = la[dist_col] if pd.notna(la[dist_col]) else 30.0

        # Demand growth to 2030 (how much worse will it get)
        growth = la['demand_growth_2030'] if pd.notna(la['demand_growth_2030']) else 1.0

        # Independent placement pressure (proxy for cost of doing nothing)
        indep_pct = la['pct_special_independent'] if pd.notna(la['pct_special_independent']) else 0

        # Priority score: unmet demand × growth × cost pressure × access problem
        # log(dist+1) downweights marginal distance gains non-linearly
        priority = (gap_abs
                    * growth
                    * (1 + indep_pct / 100)
                    * np.log1p(dist_km))

        # Facility type recommendation
        if dist_km > dist_thresh:
            facility_type  = 'New maintained special school'
            lead_time      = '4–6 years'
            typical_places = '80–150'
        else:
            facility_type  = 'Resourced provision unit / SEN unit'
            lead_time      = '1–2 years'
            typical_places = '10–25'

        rows.append({
            'la_code':             la['la_code'],
            'la_name':             la['la_name'],
            'region':              la['region'],
            'intervention_status': la['intervention_status'],
            'need_type':           nt_short,
            'need_type_full':      nt_long,
            'gap_pp':              round(gap_pp, 1),
            'gap_abs_children':    round(gap_abs),
            'dist_nearest_maintained_km': round(dist_km, 1),
            'demand_growth_to_2030':      round(growth, 2),
            'pct_placements_independent': round(indep_pct, 1),
            'indep_cost_2030_m':  round(la['cost_2030_m'], 1) if pd.notna(la['cost_2030_m']) else None,
            'risk_score':          round(la['risk_score'], 2) if pd.notna(la['risk_score']) else None,
            'facility_type':       facility_type,
            'lead_time':           lead_time,
            'typical_places':      typical_places,
            'priority_score':      priority,
        })

results = pd.DataFrame(rows)
results['priority_rank'] = results['priority_score'].rank(ascending=False, method='min').astype(int)
results = results.sort_values('priority_rank')

print(f"  Scored {len(results)} LA × need-type combinations")

# ─── 4. Save full table ───────────────────────────────────────────────────────
out_cols = ['priority_rank', 'la_name', 'region', 'intervention_status',
            'need_type', 'facility_type', 'lead_time', 'typical_places',
            'gap_pp', 'gap_abs_children', 'dist_nearest_maintained_km',
            'demand_growth_to_2030', 'pct_placements_independent',
            'indep_cost_2030_m', 'risk_score']
results[out_cols].to_csv(TABLE_DIR / 'facility_priority_list.csv', index=False)
print("  Saved facility_priority_list.csv")

# ─── 5. Print top 40 ─────────────────────────────────────────────────────────
print("\n" + "=" * 110)
print("TOP 40 FACILITY PRIORITIES (LA × need type)")
print("=" * 110)
print(f"{'Rank':<5} {'LA':<28} {'Region':<24} {'Need':<5} {'Facility type':<38} {'Gap (pp)':<9} "
      f"{'Gap (n)':<9} {'Dist km':<8} {'Growth':<7} {'Indep%':<7}")
print("-" * 110)
for _, row in results.head(40).iterrows():
    ft_short = 'New school' if 'New' in row['facility_type'] else 'RPU/SEN unit'
    print(f"{int(row['priority_rank']):<5} {str(row['la_name']):<28} {str(row['region']):<24} "
          f"{row['need_type']:<5} {ft_short:<38} "
          f"{row['gap_pp']:<9.1f} {int(row['gap_abs_children']):<9} "
          f"{row['dist_nearest_maintained_km']:<8.1f} "
          f"{row['demand_growth_to_2030']:<7.2f} {row['pct_placements_independent']:<7.1f}")

# ─── 6. Summary statistics ────────────────────────────────────────────────────
print("\n\n── Summary: need type breakdown of top 50 ──")
top50 = results.head(50)
print(top50.groupby(['need_type', 'facility_type'])[['gap_abs_children']].agg(['count', 'sum', 'mean']).round(0).to_string())

print("\n── Summary: regional breakdown of top 50 ──")
print(top50.groupby('region')['priority_rank'].count().sort_values(ascending=False).to_string())

# ─── 7. Figure 44: Top-30 ranked bar chart ────────────────────────────────────
top30 = results.head(30).copy()
top30['label'] = top30['la_name'] + '\n(' + top30['need_type'] + ')'
top30 = top30[::-1]  # reverse for horizontal bar chart (rank 1 at top)

fig, ax = plt.subplots(figsize=(14, 12))

bar_colors = [NEED_COLORS[nt] for nt in top30['need_type']]
bars = ax.barh(range(len(top30)), top30['priority_score'], color=bar_colors, alpha=0.85)

# Hatching for facility type
for i, (_, row) in enumerate(top30.iterrows()):
    if 'New' in row['facility_type']:
        bars[i].set_hatch('///')
        bars[i].set_edgecolor('white')

ax.set_yticks(range(len(top30)))
ax.set_yticklabels(top30['label'], fontsize=8)
ax.set_xlabel('Priority score (unmet demand × demand growth × independent cost pressure × access distance)',
              fontsize=9)
ax.set_title('Where to build next: top 30 LA × need-type combinations\n'
             'Hatched bars = new special school needed (distance > threshold); '
             'solid = resourced provision unit sufficient',
             fontsize=11, fontweight='bold')

# Annotate rank on each bar
for i, (_, row) in enumerate(top30.iterrows()):
    ax.text(row['priority_score'] * 0.01, i,
            f"#{int(row['priority_rank'])}  {row['facility_type'].split('/')[0].strip()[:15]}",
            va='center', fontsize=6.5, color='white' if row['priority_score'] > top30['priority_score'].max() * 0.3 else 'black')

# Legend: need type
need_patches = [mpatches.Patch(color=NEED_COLORS[k], label=k) for k in NEED_COLORS]
# Legend: facility type
hatch_patch = mpatches.Patch(facecolor='grey', hatch='///', edgecolor='white', label='New special school')
solid_patch  = mpatches.Patch(facecolor='grey', label='Resourced provision unit')
ax.legend(handles=need_patches + [hatch_patch, solid_patch],
          loc='lower right', fontsize=8, ncol=2)

ax.grid(True, axis='x', alpha=0.3)
plt.tight_layout()
fig.savefig(FIG_DIR / '44_facility_priority.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n  Saved figure 44")

# ─── 8. Summary table for press pack ─────────────────────────────────────────
press_top = results.head(20)[['priority_rank', 'la_name', 'region',
                               'need_type', 'need_type_full',
                               'facility_type', 'lead_time', 'typical_places',
                               'gap_abs_children', 'demand_growth_to_2030',
                               'indep_cost_2030_m']].copy()
press_top.to_csv(TABLE_DIR / 'facility_priority_top20.csv', index=False)
print("  Saved facility_priority_top20.csv")

print("\nDone.")
