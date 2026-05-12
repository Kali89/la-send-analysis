#!/usr/bin/env python3.12
"""
mapping_analysis.py
Interactive map and distance-based access metrics for special schools in England.

Outputs:
  outputs/figures/22_special_school_map.html  — interactive folium map
  outputs/figures/23_school_access_boxplots.png — access capacity by LA type
  outputs/figures/24_access_vs_placements.png   — ASD/SEMH access vs indep rate
  outputs/figures/25_distance_by_specialism.png — distance to nearest school by type
  outputs/tables/la_school_access.csv           — LA-level access metrics
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.spatial import cKDTree
from scipy import stats
from pyproj import Transformer
import folium

warnings.filterwarnings('ignore')

DATA_DIR = 'data/raw'
OUT_FIG  = 'outputs/figures'
OUT_TAB  = 'outputs/tables'

KEY_SEN = ['ASD', 'SEMH', 'SLD', 'MLD', 'SLCN', 'SpLD', 'PD', 'VI', 'HI', 'PMLD']

STATE_TYPES = [
    'Community special school', 'Academy special converter',
    'Academy special sponsor led', 'Foundation special school',
    'Free schools special', 'Non-maintained special school',
]
INDEP_TYPES = ['Other independent special school']
ALL_SPECIAL = STATE_TYPES + INDEP_TYPES + ['Special post 16 institution']

STATUS_COLORS = {
    'Safety Valve':           '#d73027',
    'Delivering Better Value':'#fc8d59',
    'None':                   '#4575b4',
}

# ── 1. Load and prepare GIAS ──────────────────────────────────────────────────
print("Loading GIAS…")
gias = pd.read_csv(
    f'{DATA_DIR}/edubasealldata20260512.csv',
    encoding='latin-1', low_memory=False
)
gias.columns = [c.lower().strip() for c in gias.columns]
gias['easting']  = pd.to_numeric(gias['easting'],  errors='coerce')
gias['northing'] = pd.to_numeric(gias['northing'], errors='coerce')
gias['schoolcapacity'] = pd.to_numeric(gias['schoolcapacity'], errors='coerce')

ENGLAND_REGIONS = {
    'South East', 'North West', 'London', 'West Midlands',
    'Yorkshire and the Humber', 'South West', 'East of England',
    'East Midlands', 'North East',
}

# Open England schools with valid coordinates
open_england = gias[
    gias['gor (name)'].isin(ENGLAND_REGIONS) &
    gias['establishmentstatus (name)'].isin(['Open', 'Open, but proposed to close']) &
    gias['easting'].notna() &
    gias['northing'].notna()
].copy()
print(f"  open England establishments with coords: {len(open_england):,}")

# ── 2. LA centroids (from ALL establishments) ─────────────────────────────────
la_centroids = (
    open_england.groupby('la (name)')[['easting', 'northing']]
    .mean().reset_index()
    .rename(columns={'la (name)': 'la_name_gias'})
)

# ── 3. Special schools ────────────────────────────────────────────────────────
special = open_england[
    open_england['typeofestablishment (name)'].isin(ALL_SPECIAL)
].copy()

special['is_independent'] = special['typeofestablishment (name)'].isin(INDEP_TYPES)
special['sector'] = special['is_independent'].map({True: 'Independent', False: 'State'})

# Primary SEN type abbreviation
special['sen1_raw']    = special['sen1 (name)'].fillna('')
special['sen_primary'] = (
    special['sen1_raw'].str.split(' - ').str[0].str.strip()
    .where(special['sen1_raw'].str.split(' - ').str[0].str.strip().isin(KEY_SEN), 'Other')
)

print(f"  open special schools: {len(special):,}  "
      f"(state: {(~special['is_independent']).sum()}, "
      f"indep: {special['is_independent'].sum()})")
print(f"  with capacity data: {special['schoolcapacity'].notna().sum()}")

# ── 4. Total pupils by LA (for per-pupil normalisation) ──────────────────────
print("Loading pupil counts…")
pupils_raw = pd.read_csv(f'{DATA_DIR}/sen_pupils_2025/data/sen_phase_type_.csv')
pupils_raw['new_la_code'] = pupils_raw['new_la_code'].fillna(
    pupils_raw['old_la_code'].astype(str).str.zfill(3))
# Grand total across all phases and establishment types
total_pupils = (
    pupils_raw[pupils_raw['geographic_level'] == 'Local authority']
    .groupby('new_la_code', as_index=False)['total_pupils'].sum()
    .rename(columns={'new_la_code': 'la_code', 'total_pupils': 'total_pupils'})
)

# ── 5. Meta data ──────────────────────────────────────────────────────────────
meta = pd.read_csv(f'{OUT_TAB}/la_summary_2024_extended.csv')
meta.columns = [c.lower().replace(' ', '_') for c in meta.columns]
meta['intervention_status'] = meta['intervention_status'].fillna('No intervention')

cap = pd.read_csv(f'{OUT_TAB}/la_capacity_2024.csv')
cap.columns = [c.lower().replace(' ', '_') for c in cap.columns]

# ── 6. Convert school coords to lat/lon for folium ────────────────────────────
transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
lons, lats = transformer.transform(special['easting'].values, special['northing'].values)
special = special.copy()
special['lat'] = lats
special['lon'] = lons

# ── 7. Compute access metrics per LA ─────────────────────────────────────────
print("Computing access metrics…")

state_sp = special[~special['is_independent'] & special['schoolcapacity'].notna()].copy()
indep_sp = special[special['is_independent']  & special['schoolcapacity'].notna()].copy()

state_xy = state_sp[['easting', 'northing']].values
indep_xy = indep_sp[['easting', 'northing']].values
state_tree = cKDTree(state_xy)
indep_tree = cKDTree(indep_xy)

def cap_within(xy, tree, school_df, radius_km):
    idx = tree.query_ball_point(xy, radius_km * 1000)
    return school_df.iloc[idx]['schoolcapacity'].sum()

def dist_to_nearest(xy, sub_df):
    if len(sub_df) == 0:
        return np.nan
    t = cKDTree(sub_df[['easting', 'northing']].values)
    d, _ = t.query(xy)
    return d / 1000  # km

records = []
for _, la in la_centroids.iterrows():
    xy = [la['easting'], la['northing']]
    r = {'la_name_gias': la['la_name_gias']}

    for km in [20, 40, 60]:
        r[f'state_cap_{km}km']  = cap_within(xy, state_tree, state_sp, km)
        r[f'indep_cap_{km}km']  = cap_within(xy, indep_tree, indep_sp, km)

    for sen in ['ASD', 'SEMH', 'SLD', 'MLD', 'SLCN']:
        s_sub = state_sp[state_sp['sen_primary'] == sen]
        i_sub = indep_sp[indep_sp['sen_primary'] == sen]
        r[f'dist_state_{sen}_km'] = dist_to_nearest(xy, s_sub)
        r[f'dist_indep_{sen}_km'] = dist_to_nearest(xy, i_sub)

    records.append(r)

access = pd.DataFrame(records)
print(f"  access metrics for {len(access)} LAs")

# ── 8. Merge access with meta ─────────────────────────────────────────────────
# Build a 3-digit LEA code → ONS E-code crosswalk from the pupil data
# (pupils_raw has both old_la_code [3-digit] and new_la_code [ONS 9-char])
pupils_la = (
    pupils_raw[pupils_raw['geographic_level'] == 'Local authority']
    [['old_la_code', 'new_la_code', 'la_name']].drop_duplicates()
    .rename(columns={'old_la_code': 'lea_code', 'new_la_code': 'la_code_ons',
                     'la_name': 'la_name_pupils'})
)
# Also store GIAS lea code on access from la_centroids (GIAS groupby 'la (name)')
# Add 3-digit code to la_centroids via GIAS 'la (code)' column
lea_codes = (
    open_england.groupby('la (name)')['la (code)']
    .first().reset_index()
    .rename(columns={'la (name)': 'la_name_gias', 'la (code)': 'lea_code'})
)
lea_codes['lea_code'] = pd.to_numeric(lea_codes['lea_code'], errors='coerce')
pupils_la['lea_code'] = pd.to_numeric(pupils_la['lea_code'], errors='coerce')

access = access.merge(lea_codes, on='la_name_gias', how='left')
access = access.merge(pupils_la[['lea_code', 'la_code_ons']].drop_duplicates(),
                      on='lea_code', how='left')
access = access.rename(columns={'la_code_ons': 'la_code'})

merged = access.merge(
    meta[['la_code', 'la_name', 'region', 'intervention_status', 'n_ehcp_active']],
    on='la_code', how='left'
).merge(
    cap[['la_code', 'indep_placements_per1000', 'pct_special_independent']],
    on='la_code', how='left'
).merge(
    total_pupils, on='la_code', how='left'
)

merged['intervention_status'] = merged['intervention_status'].fillna('No intervention')

# Per-1000-EHCP normalisation
for km in [20, 40, 60]:
    for sec in ['state', 'indep']:
        col = f'{sec}_cap_{km}km'
        merged[f'{col}_per_ehcp'] = merged[col] / merged['n_ehcp_active'].replace(0, np.nan)

print(f"  merged: {len(merged)} rows, matched meta for "
      f"{(merged['la_name'].notna()).sum()}")
print("  Status counts:", merged['intervention_status'].value_counts().to_dict())

merged.to_csv(f'{OUT_TAB}/la_school_access.csv', index=False)
print(f"  saved: la_school_access.csv")

# ── 9. Interactive folium map ─────────────────────────────────────────────────
print("Building interactive map…")

m = folium.Map(location=[52.5, -1.5], zoom_start=6,
               tiles='CartoDB positron', prefer_canvas=True)

SECTOR_COL = {'State': '#2166ac', 'Independent': '#d6604d'}
SEN_COL = {
    'ASD':  '#e41a1c', 'SEMH': '#ff7f00', 'SLD':  '#4daf4a',
    'MLD':  '#984ea3', 'SLCN': '#a65628', 'SpLD': '#f781bf',
    'PD':   '#888888', 'VI':   '#377eb8', 'HI':   '#e6ab02',
    'PMLD': '#66c2a5', 'Other':'#cccccc',
}

state_fg = folium.FeatureGroup(name='State-funded special schools', show=True)
indep_fg = folium.FeatureGroup(name='Independent special schools', show=True)

for _, row in special.dropna(subset=['lat', 'lon']).iterrows():
    cap_val = row['schoolcapacity']
    cap_str = f"{int(cap_val)}" if pd.notna(cap_val) else 'n/a'
    radius  = max(3, min(10, np.sqrt(cap_val) / 3)) if pd.notna(cap_val) else 4

    popup_html = (
        f"<b>{row['establishmentname']}</b><br>"
        f"Type: {row['typeofestablishment (name)']}<br>"
        f"Primary SEN: {row['sen1_raw'] or 'not specified'}<br>"
        f"Also caters for: "
        + ', '.join([
            str(row[f'sen{i} (name)']).split(' - ')[0]
            for i in range(2, 6)
            if pd.notna(row.get(f'sen{i} (name)'))
        ])
        + f"<br>Capacity: {cap_str}<br>LA: {row['la (name)']}"
    )

    marker = folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=radius,
        color=SECTOR_COL[row['sector']],
        fill=True,
        fill_color=SEN_COL.get(row['sen_primary'], '#cccccc'),
        fill_opacity=0.75,
        weight=1.5,
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=f"{row['establishmentname']} ({row['sen_primary']})",
    )
    if row['is_independent']:
        marker.add_to(indep_fg)
    else:
        marker.add_to(state_fg)

state_fg.add_to(m)
indep_fg.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

legend = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:12px 16px;border-radius:6px;border:1px solid #bbb;font-size:12px;
     line-height:1.8">
<b>Sector (border colour)</b><br>
<span style="color:#2166ac;font-size:16px">●</span> State-funded<br>
<span style="color:#d6604d;font-size:16px">●</span> Independent<br><br>
<b>Primary SEN (fill colour)</b><br>
<span style="color:#e41a1c">●</span> ASD &nbsp;
<span style="color:#ff7f00">●</span> SEMH &nbsp;
<span style="color:#4daf4a">●</span> SLD<br>
<span style="color:#984ea3">●</span> MLD &nbsp;
<span style="color:#a65628">●</span> SLCN &nbsp;
<span style="color:#f781bf">●</span> SpLD<br>
<span style="color:#888">●</span> PD &nbsp;
<span style="color:#377eb8">●</span> VI &nbsp;
<span style="color:#e6ab02">●</span> HI<br>
<span style="color:#66c2a5">●</span> PMLD &nbsp;
<span style="color:#ccc">●</span> Other<br><br>
<i>Circle size ~ school capacity</i>
</div>
"""
m.get_root().html.add_child(folium.Element(legend))
m.save(f'{OUT_FIG}/22_special_school_map.html')
print(f"  saved: 22_special_school_map.html")

# ── 10. Static figures ────────────────────────────────────────────────────────
sv_data   = merged[merged['intervention_status'] == 'Safety Valve']
dbv_data  = merged[merged['intervention_status'] == 'Delivering Better Value']
none_data = merged[merged['intervention_status'].isin(['No intervention', 'None'])]
groups = [
    ('Safety Valve',            sv_data,   '#d73027'),
    ('Delivering Better Value', dbv_data,  '#fc8d59'),
    ('No intervention',         none_data, '#4575b4'),
]

# ── Fig 23: England map — all special school locations ────────────────────────
print("Building figure 23 (location map)…")
fig, axes = plt.subplots(1, 2, figsize=(14, 12))
fig.suptitle('Special schools in England', fontsize=16, fontweight='bold', y=1.01)

for ax, (grp_name, grp_df, sec_col, sec_label) in zip(axes, [
    ('State-funded special schools',  state_sp, '#2166ac', 'state'),
    ('Independent special schools',   indep_sp, '#d6604d', 'indep'),
]):
    cap_vals = grp_df['schoolcapacity'].fillna(20)
    sizes = (cap_vals / cap_vals.max() * 40).clip(2, 40)
    sc = ax.scatter(grp_df['easting'], grp_df['northing'],
                    s=sizes, c=grp_df['sen_primary'].map(SEN_COL),
                    alpha=0.65, linewidths=0)
    ax.set_aspect('equal')
    ax.set_title(grp_name, fontsize=13, fontweight='bold')
    ax.set_xlabel('Easting (BNG m)')
    ax.set_ylabel('Northing (BNG m)')
    ax.tick_params(labelsize=8)

    sen_handles = [
        mpatches.Patch(color=SEN_COL[s], label=s)
        for s in KEY_SEN + ['Other']
        if s in grp_df['sen_primary'].values
    ]
    ax.legend(handles=sen_handles, title='Primary SEN', loc='lower right',
              fontsize=7, title_fontsize=8, framealpha=0.9)

plt.tight_layout()
plt.savefig(f'{OUT_FIG}/23_school_locations_england.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 23_school_locations_england.png")

# ── Fig 24: State special school capacity within 40km, by intervention status ─
print("Building figure 24 (access by LA type)…")
fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=False)
fig.suptitle('Special school capacity within 40 km of LA centroid',
             fontsize=14, fontweight='bold')

metrics = [
    ('state_cap_40km',  'State places within 40 km', '#2166ac'),
    ('indep_cap_40km',  'Independent places within 40 km', '#d6604d'),
    ('state_cap_40km_per_ehcp', 'State places per active EHCP (40 km)', '#4dac26'),
]
labels = ['Safety\nValve', 'Delivering\nBetter Value', 'No\nintervention']
data_sets = [sv_data, dbv_data, none_data]
colors = ['#d73027', '#fc8d59', '#4575b4']

for ax, (col, title, _col) in zip(axes, metrics):
    vals = [d[col].dropna().values for d in data_sets]
    bp = ax.boxplot(vals, patch_artist=True, notch=False,
                    medianprops=dict(color='black', linewidth=2))
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)

    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_ylabel('')
    ax.yaxis.grid(True, alpha=0.4)

    # Mann-Whitney p between SV and None
    sv_v  = sv_data[col].dropna()
    no_v  = none_data[col].dropna()
    if len(sv_v) > 3 and len(no_v) > 3:
        _, p = stats.mannwhitneyu(sv_v, no_v, alternative='two-sided')
        ax.set_xlabel(f'SV vs None: p = {p:.3f}', fontsize=9)

plt.tight_layout()
plt.savefig(f'{OUT_FIG}/24_school_access_by_status.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 24_school_access_by_status.png")

# ── Fig 25: Distance to nearest school by specialism ─────────────────────────
print("Building figure 25 (distance to nearest by specialism)…")
sen_focus = ['ASD', 'SEMH', 'SLD', 'MLD', 'SLCN']
fig, axes = plt.subplots(1, len(sen_focus), figsize=(16, 6), sharey=False)
fig.suptitle('Distance (km) from LA centroid to nearest STATE special school\nby primary SEN specialism',
             fontsize=13, fontweight='bold')

for ax, sen in zip(axes, sen_focus):
    col = f'dist_state_{sen}_km'
    vals = [d[col].dropna().values for d in data_sets]
    bp = ax.boxplot(vals, patch_artist=True, notch=False,
                    medianprops=dict(color='black', linewidth=2))
    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)

    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(['SV', 'DBV', 'None'], fontsize=9)
    ax.set_title(sen, fontsize=12, fontweight='bold')
    ax.yaxis.grid(True, alpha=0.4)
    if ax == axes[0]:
        ax.set_ylabel('Distance to nearest school (km)')

    sv_v  = sv_data[col].dropna()
    no_v  = none_data[col].dropna()
    if len(sv_v) > 3 and len(no_v) > 3:
        _, p = stats.mannwhitneyu(sv_v, no_v, alternative='two-sided')
        p_str = f'p={p:.3f}' if p >= 0.01 else f'p={p:.4f}'
        ax.set_xlabel(f'SV vs None: {p_str}', fontsize=8)

plt.tight_layout()
plt.savefig(f'{OUT_FIG}/25_distance_to_nearest_by_specialism.png', dpi=150, bbox_inches='tight')
plt.close()
print("  saved: 25_distance_to_nearest_by_specialism.png")

# ── Summary stats for the key question ───────────────────────────────────────
print("\n=== Key summary statistics ===")
for col, label in [
    ('state_cap_40km',         'State capacity within 40km (median)'),
    ('indep_cap_40km',         'Indep capacity within 40km (median)'),
    ('state_cap_40km_per_ehcp','State cap/EHCP within 40km (median)'),
]:
    print(f"\n{label}:")
    for status, d in [('Safety Valve', sv_data), ('DBV', dbv_data), ('None', none_data)]:
        print(f"  {status}: {d[col].median():.1f}")

print("\nDistance to nearest STATE school by specialism (median km):")
for sen in sen_focus:
    col = f'dist_state_{sen}_km'
    print(f"\n  {sen}:")
    for status, d in [('SV', sv_data), ('DBV', dbv_data), ('None', none_data)]:
        print(f"    {status}: {d[col].median():.1f} km")

print("\nDistance to nearest INDEPENDENT school by specialism (median km):")
for sen in sen_focus:
    col = f'dist_indep_{sen}_km'
    print(f"\n  {sen}:")
    for status, d in [('SV', sv_data), ('DBV', dbv_data), ('None', none_data)]:
        print(f"    {status}: {d[col].median():.1f} km")
