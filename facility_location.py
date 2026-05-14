#!/usr/bin/env python3
"""
facility_location.py

Drills from LA-level facility priorities to specific within-LA locations.

For each top-priority (LA × need type) combination:
  1. Identifies the worst-served LSOAs (those farthest from maintained provision)
  2. Computes the distance-weighted centroid of those LSOAs as the recommended
     build location
  3. Reports how many LSOAs would fall within the access threshold if a school
     were built at that location
  4. Names the location using the nearest existing school town from GIAS

Outputs:
  outputs/tables/lsoa_distances_by_type.csv      — per-LSOA distances (all types)
  outputs/tables/facility_locations.csv           — priority list with specific locations
  outputs/figures/45_facility_location_maps.png   — within-LA maps for top 12
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.spatial import cKDTree
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT      = Path(__file__).parent
FIG_DIR   = ROOT / 'outputs' / 'figures'
TABLE_DIR = ROOT / 'outputs' / 'tables'
DATA_DIR  = ROOT / 'data' / 'raw'

# Access threshold: if nearest maintained provision is beyond this, a new school
# is needed rather than an RPU. Same thresholds as facility_planning.py.
THRESH_KM = {'ASD': 20, 'SEMH': 15, 'MLD': 20, 'SLD': 20}

# LA code remapping: old county codes → new unitary authority codes (LSOA 2021 uses new codes)
LA_CODE_REMAP = {
    'E10000002': 'E06000060',  # Buckinghamshire became unitary authority in 2020
}

# Worst-served fraction: use the top N% most underserved LSOAs to anchor the
# recommended location (rather than all LSOAs, which pulls toward LA centre)
WORST_PCT = 0.33

STATE_TYPES = [
    'Community special school', 'Academy special converter',
    'Academy special sponsor led', 'Foundation special school',
    'Free schools special',
]
KEY_SEN = ['ASD', 'SEMH', 'MLD', 'SLD', 'SLCN']

EN_REGIONS = [
    'East Midlands', 'East of England', 'London', 'North East', 'North West',
    'South East', 'South West', 'West Midlands', 'Yorkshire and The Humber',
]

# ═══════════════════════════════════════════════════════════════════════════
# PART 1: LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════
print("Loading data...")

lsoa = pd.read_csv(DATA_DIR / 'lsoa_centroids_2021.csv')
lsoa = lsoa[lsoa['la_code'].str.startswith('E', na=False)].copy()
print(f"  LSOAs: {len(lsoa):,}  |  LAs: {lsoa['la_code'].nunique()}")

gias_raw = pd.read_csv(DATA_DIR / 'edubasealldata20260512.csv',
                       encoding='latin-1', low_memory=False)
gias_raw.columns = [c.lower().strip() for c in gias_raw.columns]
gias_raw['easting']  = pd.to_numeric(gias_raw['easting'],  errors='coerce')
gias_raw['northing'] = pd.to_numeric(gias_raw['northing'], errors='coerce')

open_eng = gias_raw[
    gias_raw['gor (name)'].isin(EN_REGIONS) &
    gias_raw['establishmentstatus (name)'].isin(['Open', 'Open, but proposed to close']) &
    gias_raw['easting'].notna() & gias_raw['northing'].notna()
].copy()

state_sp = open_eng[open_eng['typeofestablishment (name)'].isin(STATE_TYPES)].copy()
state_sp['sen_primary'] = (
    state_sp['sen1 (name)'].fillna('Other')
    .str.split(' - ').str[0].str.strip()
    .where(state_sp['sen1 (name)'].fillna('').str.split(' - ').str[0].str.strip().isin(KEY_SEN), 'Other')
)

# All open schools (any type) for place-name lookup
all_schools = open_eng[open_eng['easting'].notna() & open_eng['northing'].notna()].copy()
all_tree = cKDTree(all_schools[['easting', 'northing']].values)

print(f"  State special schools: {len(state_sp):,}")

# ═══════════════════════════════════════════════════════════════════════════
# PART 2: COMPUTE PER-LSOA DISTANCES TO NEAREST MAINTAINED SCHOOL BY TYPE
# ═══════════════════════════════════════════════════════════════════════════
print("\nBuilding KD-trees and computing per-LSOA distances...")

lsoa_xy = lsoa[['easting', 'northing']].values
state_trees = {}
for sen in KEY_SEN:
    sub = state_sp[state_sp['sen_primary'] == sen].copy()
    if len(sub) > 0:
        state_trees[sen] = (cKDTree(sub[['easting', 'northing']].values), sub)
        print(f"  {sen}: {len(sub)} maintained schools → computing distances")
        dists, idxs = state_trees[sen][0].query(lsoa_xy)
        lsoa[f'dist_state_{sen}_km'] = dists / 1000
        # Store nearest school info for each LSOA
        nearest_school = state_trees[sen][1].iloc[idxs]
        lsoa[f'nearest_{sen}_town'] = nearest_school['town'].values
        lsoa[f'nearest_{sen}_name'] = nearest_school['establishmentname'].values
        lsoa[f'nearest_{sen}_la']   = nearest_school['la (name)'].values

# Save full per-LSOA table
dist_cols = ['la_code', 'la_name', 'LSOA21CD', 'easting', 'northing']
dist_cols += [f'dist_state_{s}_km' for s in KEY_SEN if f'dist_state_{s}_km' in lsoa.columns]
lsoa[dist_cols].to_csv(TABLE_DIR / 'lsoa_distances_by_type.csv', index=False)
print(f"  Saved lsoa_distances_by_type.csv ({len(lsoa):,} rows)")

# ═══════════════════════════════════════════════════════════════════════════
# PART 3: FIND RECOMMENDED BUILD LOCATION FOR EACH PRIORITY
# ═══════════════════════════════════════════════════════════════════════════
print("\nFinding recommended build locations...")

priorities = pd.read_csv(TABLE_DIR / 'facility_priority_list.csv')

def recommended_location(la_code, need_type, lsoa_df, all_tree_ref, all_schools_ref,
                          thresh_km, worst_pct=WORST_PCT):
    """
    For a given (LA, need type), find the distance-weighted centroid of the
    worst-served LSOAs and return location metadata.
    """
    dist_col = f'dist_state_{need_type}_km'
    if dist_col not in lsoa_df.columns:
        return {}

    la_code = LA_CODE_REMAP.get(la_code, la_code)
    la_lsoas = lsoa_df[lsoa_df['la_code'] == la_code].copy()
    if len(la_lsoas) == 0:
        return {}

    la_lsoas = la_lsoas.dropna(subset=[dist_col])
    if len(la_lsoas) == 0:
        return {}

    # Worst-served = top WORST_PCT by distance
    cutoff = la_lsoas[dist_col].quantile(1 - worst_pct)
    worst = la_lsoas[la_lsoas[dist_col] >= cutoff].copy()

    if len(worst) == 0:
        worst = la_lsoas

    # Distance-weighted centroid (farther LSOAs pull location more strongly)
    weights = worst[dist_col].values
    w_sum   = weights.sum()
    rec_e   = (worst['easting'].values  * weights).sum() / w_sum
    rec_n   = (worst['northing'].values * weights).sum() / w_sum

    # Count LSOAs that would fall within threshold if school built here
    all_la_xy  = la_lsoas[['easting', 'northing']].values
    dists_from_rec = np.sqrt((all_la_xy[:, 0] - rec_e)**2 + (all_la_xy[:, 1] - rec_n)**2) / 1000
    lsoas_within   = (dists_from_rec <= thresh_km).sum()
    lsoas_total    = len(la_lsoas)

    # Name the location using nearest open school (any type) as place proxy
    _, nearest_idx = all_tree_ref.query([[rec_e, rec_n]])
    nearest_row     = all_schools_ref.iloc[nearest_idx[0]]
    place_town      = nearest_row.get('town', '')
    place_name      = nearest_row.get('establishmentname', '')

    # Mean distance of worst-served LSOAs (before hypothetical new school)
    mean_dist_worst = worst[dist_col].mean()
    max_dist_worst  = worst[dist_col].max()

    # What fraction of the LA is currently beyond the threshold?
    pct_beyond_thresh = (la_lsoas[dist_col] > thresh_km).mean() * 100

    # Convert BNG to approximate lat/lon (accuracy ~500m, sufficient for area-level planning)
    # Using Helmert transformation approximation
    E, N = rec_e, rec_n
    lat = 49.00 + (N - 100000) / 111320
    lon = -2.00 + (E - 400000) / (111320 * np.cos(np.radians(lat)))

    return {
        'rec_easting':         round(rec_e),
        'rec_northing':        round(rec_n),
        'rec_lat':             round(lat, 3),
        'rec_lon':             round(lon, 3),
        'nearest_place':       place_town if pd.notna(place_town) and place_town else 'Unknown',
        'nearest_school_name': place_name,
        'n_lsoas_worst_served':       len(worst),
        'n_lsoas_within_threshold':   int(lsoas_within),
        'pct_lsoas_within_threshold': round(lsoas_within / lsoas_total * 100, 1),
        'pct_la_currently_beyond':    round(pct_beyond_thresh, 1),
        'mean_dist_worst_km':         round(mean_dist_worst, 1),
        'max_dist_worst_km':          round(max_dist_worst, 1),
    }


location_rows = []
top_n = 40
for _, row in priorities.head(top_n).iterrows():
    thresh = THRESH_KM.get(row['need_type'], 20)
    loc = recommended_location(
        row['la_code'] if 'la_code' in priorities.columns else None,
        row['need_type'], lsoa, all_tree, all_schools, thresh
    )
    combined = {**row.to_dict(), **loc}
    location_rows.append(combined)
    if loc:
        print(f"  #{int(row['priority_rank']):>2}  {row['la_name']:<28} {row['need_type']:<5}  "
              f"→ {loc.get('nearest_place','?'):<20}  "
              f"{loc.get('pct_la_currently_beyond',0):.0f}% of LA beyond threshold  "
              f"{loc.get('n_lsoas_within_threshold',0)} LSOAs within {thresh}km of rec. point")

# Need la_code in priorities — merge it in if missing
if 'la_code' not in priorities.columns:
    risk = pd.read_csv(TABLE_DIR / 'la_risk_scores_2024.csv')[['la_name','la_code']]
    priorities = priorities.merge(risk, on='la_name', how='left')

location_rows = []
for _, row in priorities.head(top_n).iterrows():
    thresh = THRESH_KM.get(row['need_type'], 20)
    loc = recommended_location(
        row['la_code'], row['need_type'], lsoa, all_tree, all_schools, thresh
    )
    combined = {**row.to_dict(), **loc}
    location_rows.append(combined)
    if loc:
        print(f"  #{int(row['priority_rank']):>2}  {row['la_name']:<28} {row['need_type']:<5}  "
              f"→ {loc.get('nearest_place','?'):<20}  "
              f"{loc.get('pct_la_currently_beyond',0):.0f}% of LA beyond threshold  "
              f"{loc.get('n_lsoas_within_threshold',0)} LSOAs within {thresh}km of rec. point")

locations = pd.DataFrame(location_rows)

# Save
save_cols = [
    'priority_rank', 'la_name', 'region', 'need_type', 'facility_type',
    'lead_time', 'gap_abs_children', 'demand_growth_to_2030',
    'nearest_place', 'nearest_school_name',
    'rec_lat', 'rec_lon', 'rec_easting', 'rec_northing',
    'pct_la_currently_beyond', 'n_lsoas_within_threshold',
    'pct_lsoas_within_threshold', 'mean_dist_worst_km', 'max_dist_worst_km',
]
save_cols = [c for c in save_cols if c in locations.columns]
locations[save_cols].to_csv(TABLE_DIR / 'facility_locations.csv', index=False)
print(f"\n  Saved facility_locations.csv")

# ═══════════════════════════════════════════════════════════════════════════
# PART 4: PRINT SUMMARY TABLE
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 120)
print("FACILITY PRIORITIES WITH SPECIFIC LOCATION RECOMMENDATIONS")
print("=" * 120)
print(f"{'Rk':<4} {'LA':<26} {'NT':<5} {'Facility type':<12} {'Recommended area':<22} "
      f"{'Gap (n)':<8} {'x2030':<6} {'% LA>thresh':<12} {'LSOAs served'}")
print("-" * 120)
for _, row in locations.head(30).iterrows():
    ft = 'New school' if 'New' in str(row.get('facility_type','')) else 'RPU'
    place = str(row.get('nearest_place', 'Unknown'))
    print(f"{int(row['priority_rank']):<4} {str(row['la_name']):<26} {row['need_type']:<5} "
          f"{ft:<12} {place:<22} "
          f"{int(row.get('gap_abs_children',0)):<8} "
          f"×{row.get('demand_growth_to_2030',1):<5.2f} "
          f"{row.get('pct_la_currently_beyond',0):>6.0f}%       "
          f"{row.get('n_lsoas_within_threshold',0)} LSOAs within threshold")

# ═══════════════════════════════════════════════════════════════════════════
# PART 5: WITHIN-LA MAPS FOR TOP 12
# ═══════════════════════════════════════════════════════════════════════════
print("\nGenerating within-LA maps for top 12 priorities...")

top12 = locations.dropna(subset=['rec_easting']).head(12)
fig, axes = plt.subplots(3, 4, figsize=(20, 15))
axes = axes.flatten()

NEED_COLORS = {'ASD': '#2c7bb6', 'SEMH': '#d7191c', 'MLD': '#fdae61', 'SLD': '#1a9641'}

for ax_i, (_, row) in enumerate(top12.iterrows()):
    ax = axes[ax_i]
    la_code   = row.get('la_code', None)
    need_type = row['need_type']
    dist_col  = f'dist_state_{need_type}_km'
    thresh    = THRESH_KM.get(need_type, 20)
    color     = NEED_COLORS.get(need_type, '#888888')

    la_lsoas = lsoa[lsoa['la_code'] == la_code].copy() if la_code else pd.DataFrame()
    if len(la_lsoas) == 0 or dist_col not in la_lsoas.columns:
        ax.set_visible(False)
        continue

    la_lsoas = la_lsoas.dropna(subset=[dist_col])

    # Plot LSOAs coloured by distance
    sc = ax.scatter(la_lsoas['easting'] / 1000, la_lsoas['northing'] / 1000,
                    c=la_lsoas[dist_col], cmap='YlOrRd', s=4, alpha=0.8,
                    vmin=0, vmax=max(thresh * 2, la_lsoas[dist_col].max()))
    plt.colorbar(sc, ax=ax, label='km to nearest maintained', fraction=0.035, pad=0.04)

    # Plot existing maintained schools of this type in the vicinity
    # (within 50km of LA centroid)
    la_e_mean = la_lsoas['easting'].mean()
    la_n_mean = la_lsoas['northing'].mean()
    nearby_schools = state_sp[state_sp['sen_primary'] == need_type].copy()
    nearby_schools['d_from_la'] = np.sqrt(
        (nearby_schools['easting'] - la_e_mean)**2 +
        (nearby_schools['northing'] - la_n_mean)**2
    ) / 1000
    nearby_in_range = nearby_schools[nearby_schools['d_from_la'] < 50]
    if len(nearby_in_range) > 0:
        ax.scatter(nearby_in_range['easting'] / 1000, nearby_in_range['northing'] / 1000,
                   marker='s', s=40, color='navy', zorder=5, label='Existing school', alpha=0.9)

    # Plot recommended build location
    if pd.notna(row.get('rec_easting')):
        ax.scatter(row['rec_easting'] / 1000, row['rec_northing'] / 1000,
                   marker='*', s=250, color='white', edgecolors='black',
                   linewidths=1.5, zorder=10, label='Recommended location')
        # Draw approximate access radius
        circle = plt.Circle((row['rec_easting'] / 1000, row['rec_northing'] / 1000),
                             thresh, color='green', fill=False, lw=1.5, alpha=0.7,
                             linestyle='--')
        ax.add_patch(circle)

    place = str(row.get('nearest_place', ''))
    n_served = int(row.get('n_lsoas_within_threshold', 0))
    pct_beyond = row.get('pct_la_currently_beyond', 0)
    ax.set_title(
        f"#{int(row['priority_rank'])} {row['la_name']} — {need_type}\n"
        f"{place}  |  {pct_beyond:.0f}% of LA beyond {thresh}km  |  {n_served} LSOAs served",
        fontsize=7.5, fontweight='bold', color=color
    )
    ax.set_xlabel('Easting (km)', fontsize=6)
    ax.set_ylabel('Northing (km)', fontsize=6)
    ax.tick_params(labelsize=6)
    ax.set_aspect('equal')

    if ax_i == 0:
        ax.legend(fontsize=6, loc='lower right')

fig.suptitle(
    'Within-LA facility location recommendations — top 12 priorities\n'
    'Colour = LSOA distance to nearest maintained provision  '
    '★ = recommended build location  □ = existing maintained school  '
    '- - = access threshold radius',
    fontsize=10, fontweight='bold'
)
plt.tight_layout()
fig.savefig(FIG_DIR / '45_facility_location_maps.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved figure 45")

print("\nDone.")
