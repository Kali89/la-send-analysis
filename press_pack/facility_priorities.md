# Where to build: a national facility priority list
### Ordered by urgency across need type, demand growth, access, and independent placement pressure

---

## Methodology in brief

For every local authority and every primary need type (ASD, SEMH, MLD, SLD), a priority score is computed as:

**Priority = unmet demand (children) × demand growth to 2030 × independent placement pressure × access distance**

- **Unmet demand**: children whose EHCP need type exceeds the maintained sector's designated capacity share (from DfE SEN2 2025 and GIAS capacity data)
- **Demand growth**: projected demand in 2030 ÷ 2024, continuation scenario
- **Independent pressure**: % of current placements in the independent sector (proxy for what building maintained capacity would save)
- **Access distance**: distance from LA centroid to nearest maintained special school of that type (from LSOA centroids and GIAS)

**Facility type**: if the nearest maintained provision of that type is within 20km (15km for SEMH), a resourced provision unit (RPU) in an existing school is recommended. Beyond that threshold, a new maintained special school is needed.

Full code: `facility_planning.py` (priority scoring) and `facility_location.py` (LSOA-level location drill-down) in the repository.

---

## Top 20 priorities

Recommended areas are derived from LSOA-level distance analysis: the distance-weighted centroid of the worst-served third of LSOAs within the LA, named by the nearest open school in the GIAS register.

| Rank | LA | Region | Need type | Facility type | Recommended area | Lead time | Gap (children) | Demand growth to 2030 |
|---|---|---|---|---|---|---|---|---|
| 1 | Hampshire | South East | SEMH | Resourced provision unit | **Winchester** | 1–2 yrs | 3,602 | ×2.1 |
| 2 | Essex | East of England | ASD | Resourced provision unit | **Braintree** | 1–2 yrs | 2,766 | ×2.1 |
| 3 | Norfolk | East of England | SEMH | Resourced provision unit | **King's Lynn** | 1–2 yrs | 2,663 | ×2.1 |
| 4 | Norfolk | East of England | ASD | Resourced provision unit | **King's Lynn** | 1–2 yrs | 2,422 | ×2.1 |
| 5 | Cornwall | South West | ASD | **New special school** | **Hayle / west Cornwall** | 4–6 yrs | 1,420 | ×2.1 |
| 6 | Norfolk | East of England | MLD | **New special school** | **Dereham** | 4–6 yrs | 1,470 | ×2.1 |
| 7 | Lancashire | North West | ASD | Resourced provision unit | **Lancaster** | 1–2 yrs | 3,517 | ×2.0 |
| 8 | Suffolk | East of England | ASD | **New special school** | **Bury St Edmunds** | 4–6 yrs | 1,952 | ×1.8 |
| 9 | Essex | East of England | SEMH | **New special school** | **Witham** | 4–6 yrs | 1,938 | ×2.1 |
| 10 | Hertfordshire | East of England | MLD | Resourced provision unit | **Hertford** | 1–2 yrs | 2,429 | ×1.6 |
| 11 | Worcestershire | West Midlands | SEMH | **New special school** | **Worcester** | 4–6 yrs | 1,596 | ×2.1 |
| 12 | Cornwall | South West | SEMH | **New special school** | **Hayle / west Cornwall** | 4–6 yrs | 1,074 | ×2.1 |
| 13 | Bradford | Yorkshire and The Humber | SEMH | **New special school** | **North Bradford / Keighley corridor** | 4–6 yrs | 1,746 | ×2.1 |
| 14 | Buckinghamshire | South East | ASD | **New special school** | **Aylesbury** | 4–6 yrs | 2,302 | ×1.4 |
| 15 | Surrey | South East | SEMH | Resourced provision unit | **Dorking** | 1–2 yrs | 2,156 | ×1.5 |
| 16 | Kent | South East | ASD | Resourced provision unit | **Faversham** | 1–2 yrs | 3,355 | ×1.1 |
| 17 | Wiltshire | South West | SEMH | **New special school** | **Salisbury** | 4–6 yrs | 1,487 | ×2.1 |
| 18 | Worcestershire | West Midlands | ASD | **New special school** | **Worcester** | 4–6 yrs | 1,359 | ×2.1 |
| 19 | Nottinghamshire | East Midlands | ASD | Resourced provision unit | **Newark** | 1–2 yrs | 1,761 | ×2.1 |
| 20 | West Sussex | South East | SEMH | **New special school** | **Pulborough / Storrington area** | 4–6 yrs | 1,538 | ×1.9 |

---

## Key findings

**SEMH is the dominant unmet need type.** 16 of the top 50 priorities are new SEMH schools (vs 9 ASD, 5 MLD). SEMH demand has grown fastest and maintained SEMH provision has not kept pace. Many of these gaps could be addressed by adding SEMH designation and specialist resource to existing maintained schools (RPUs), which is faster and cheaper than new builds.

**The single most urgent action is SEMH resourced provision units.** Ranks 1 (Hampshire, 3,602 children), 3 (Norfolk, 2,663 children), and 15 (Surrey, 2,156 children) all require RPUs — maintained schools exist within range, they simply don't have SEMH designation. These can open in 1–2 years.

**Cornwall requires three new special schools** (ASD, SEMH, MLD) because the geography means no maintained school is within reasonable daily travel distance. This is the clearest case for new-build — and given 4–6 year lead times, the decisions need to be made now.

**Norfolk appears in the top 10 three times** (SEMH rank 3, ASD rank 4, MLD rank 6) — suggesting systemic under-supply across all need types, not just one. This is consistent with Norfolk being a Safety Valve LA with one of the highest risk scores in the country (0.98).

**MLD is a quiet crisis.** Moderate learning difficulties provision has been crowded out by ASD/SEMH expansion. The MLD gap in Norfolk (47.7km to nearest maintained MLD school), Worcestershire, West Sussex, and Cornwall represents approximately 7,000 children in the top 50 alone whose needs exceed the designated maintained sector capacity.

**The demand growth multiplier matters most.** Most LAs outside London show 2× demand growth to 2030 on the continuation scenario. Building now for today's demand is insufficient — new facilities need to be sized for 2030 load.

---

## Caveats

- **Gap scores measure designation mismatch**, not the absolute number of children needing a specialist placement. Many EHCP children, including those with ASD and SEMH, are educated in mainstream schools with support. The gap reflects misalignment between what the maintained sector is set up to serve and what it is being asked to serve.
- **Distance is computed at LSOA level** (33,755 areas) using OS National Grid coordinates from GIAS and ONS LSOA 2021 centroids — not from LA centroids. This gives a much more accurate picture of which communities are underserved. Recommended build locations are derived from the distance-weighted centroid of the worst-served third of LSOAs within each LA, then named using the nearest open school in the GIAS register as a place reference.
- **Place names are approximate.** The recommended area is the nearest school town to the geometric centroid — it indicates the part of the LA to target, not a specific site. Detailed site selection requires local planning input.
- **SEN designation data** from GIAS records what schools are designated to provide, which may not match what they actually deliver day-to-day. Maintained schools sometimes admit pupils outside their designation. The distance to "nearest maintained ASD school" is a proxy for the access gap, not a precise count of available places.
- **Independent sector concentration** is used as a cost-pressure proxy, not a measure of quality or appropriateness.
- **Demand projections** are sensitivity scenarios, not forecasts. The continuation scenario assumes current trends persist without policy intervention.

---

*Analysis: Matt Sharpe, Oxford Internet Institute / Automattic*  
*Data: DfE SEN2 2025 (outcomes to academic year 2024/25), GIAS school register snapshot 12 May 2026, S251 2024-25, ONS LSOA 2021 centroids. School supply is current to May 2026; demand and outcome data is current to 2024/25. This represents the best available published evidence as of mid-2026.*  
*Code: github.com/Kali89/la-send-analysis (`facility_planning.py`, `facility_location.py`)*
