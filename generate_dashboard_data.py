# %%
import pandas as pd
import json

# Read the detailed scoring data
scoring_df = pd.read_csv('detailed_scoring.csv')

# Define color palette for players (can be easily adjusted)
player_colors = {
    'Veerle': "#00D9FF",
    'Sven': "#390BE1",
    'Bernadette': "#DC0000",
    'Milan': "#0AA44E"
}

# Static metadata per Grand Prix (round/date/circuit) for the race-by-race view
race_meta = {
    'Australian GP': {'round': 1, 'date': '2026-03-08', 'name': 'Australian Grand Prix', 'circuit': 'Albert Park, Melbourne'},
    'China GP':      {'round': 2, 'date': '2026-03-15', 'name': 'Chinese Grand Prix',   'circuit': 'Shanghai'},
    'Japanese GP':   {'round': 3, 'date': '2026-03-29', 'name': 'Japanese Grand Prix',  'circuit': 'Suzuka'},
    'Miami GP':      {'round': 4, 'date': '2026-05-03', 'name': 'Miami Grand Prix',     'circuit': 'Miami International'},
    'Canada GP':     {'round': 5, 'date': '2026-05-24', 'name': 'Canadian Grand Prix',  'circuit': 'Circuit Gilles Villeneuve'},
    'Monaco GP':     {'round': 6, 'date': '2026-06-07', 'name': 'Monaco Grand Prix',    'circuit': 'Circuit de Monaco'},
    'Barcelona GP':  {'round': 7, 'date': '2026-06-14', 'name': 'Barcelona Grand Prix', 'circuit': 'Circuit de Barcelona-Catalunya'},
}


def _clean(value):
    """Return a trimmed string, or None for missing/NaN values."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    return None if text == '' or text.lower() == 'nan' else text


def _pos_label(value):
    """Format a finishing position like '16.0' -> 'P16'."""
    text = _clean(value)
    if text is None:
        return None
    try:
        return 'P' + str(int(float(text)))
    except ValueError:
        return text if text.upper().startswith('P') else 'P' + text

# 1. LEADERBOARD DATA - Overall standings with last race points
print("=" * 80)
print("GENERATING VISUALIZATION DATA")
print("=" * 80)
print()

overall_standings = []
for player in scoring_df['Player'].unique():
    player_data = scoring_df[scoring_df['Player'] == player]
    total_points = int(player_data['Total Score'].sum())
    last_race_points = int(player_data.iloc[-1]['Total Score']) if len(player_data) > 0 else 0
    
    overall_standings.append({
        'player': player,
        'total_points': total_points,
        'last_race_points': last_race_points,
        'color': player_colors[player]
    })

# Sort by total points descending
overall_standings.sort(key=lambda x: x['total_points'], reverse=True)

print("LEADERBOARD DATA:")
for rank, entry in enumerate(overall_standings, 1):
    print(f"{rank}. {entry['player']:15} Total: {entry['total_points']:3} pts | Last Race: {entry['last_race_points']:2} pts")
print()

# 2. RACE-BY-RACE BREAKDOWN
print("RACE-BY-RACE POINTS:")
races = scoring_df[['Grand Prix', 'Race Type']].drop_duplicates().reset_index(drop=True)
races['Race ID'] = races.index

race_points_data = []
for _, race in races.iterrows():
    race_id = race['Race ID']
    race_name = f"{race['Grand Prix']} ({race['Race Type']})"
    
    race_data = {
        'race_id': race_id,
        'race_name': race_name,
        'grand_prix': race['Grand Prix'],
        'race_type': race['Race Type'],
        'points_by_player': {}
    }
    
    for player in scoring_df['Player'].unique():
        player_race = scoring_df[
            (scoring_df['Player'] == player) &
            (scoring_df['Grand Prix'] == race['Grand Prix']) &
            (scoring_df['Race Type'] == race['Race Type'])
        ]
        
        if not player_race.empty:
            points = int(player_race.iloc[0]['Total Score'])
            race_data['points_by_player'][player] = points
            print(f"  {race_name}: {player} = {points} pts")
    
    race_points_data.append(race_data)

print()

# 3. CUMULATIVE PROGRESSION DATA
print("CUMULATIVE PROGRESSION:")
progression_data = []
cumulative_points = {player: 0 for player in scoring_df['Player'].unique()}

for race_data in race_points_data:
    race_entry = {
        'race_id': race_data['race_id'],
        'race_name': race_data['race_name'],
        'cumulative_by_player': {}
    }
    
    for player, points in race_data['points_by_player'].items():
        cumulative_points[player] += points
        race_entry['cumulative_by_player'][player] = cumulative_points[player]
    
    progression_data.append(race_entry)
    
    print(f"{race_data['race_name']}: {cumulative_points}")

print()

# 4. PREDICTION ACCURACY HEATMAP DATA 
print("PREDICTION ACCURACY HEATMAP:")
accuracy_heatmap = []
for _, race in races.iterrows():
    race_id = race['Race ID']
    race_name = f"{race['Grand Prix']} ({race['Race Type']})"
    
    for player in scoring_df['Player'].unique():
        player_race = scoring_df[
            (scoring_df['Player'] == player) &
            (scoring_df['Grand Prix'] == race['Grand Prix']) &
            (scoring_df['Race Type'] == race['Race Type'])
        ]
        
        if not player_race.empty:
            row = player_race.iloc[0]
            # Count correct predictions (score > 0 for each category)
            correct_count = 0
            total_categories = 5  # pole, P1, P2, P3, random
            
            if row['Pole Score'] > 0:
                correct_count += 1
            if row['P1 Score'] > 0:
                correct_count += 1
            if row['P2 Score'] > 0:
                correct_count += 1
            if row['P3 Score'] > 0:
                correct_count += 1
            if row['Random Score'] > 0:
                correct_count += 1
            
            accuracy = (correct_count / total_categories) * 100
            accuracy_heatmap.append({
                'player': player,
                'race_id': race_id,
                'race_name': race_name,
                'accuracy': round(accuracy, 1)
            })
            print(f"  {race_name} - {player}: {correct_count}/{total_categories} correct ({accuracy:.1f}%)")

print()

# 5. RACE-BY-RACE DETAIL DATA (actual result + each player's picks with scores)
print("RACE-BY-RACE DETAIL:")
race_details = []
for race_data in race_points_data:
    gp = race_data['grand_prix']
    rtype = race_data['race_type']
    sub = scoring_df[
        (scoring_df['Grand Prix'] == gp) &
        (scoring_df['Race Type'] == rtype)
    ]
    if sub.empty:
        continue

    first = sub.iloc[0]
    actual = {
        'pole': _clean(first['Pole Actual']),
        'p1': _clean(first['P1 Actual']),
        'p2': _clean(first['P2 Actual']),
        'p3': _clean(first['P3 Actual']),
    }
    # The "random driver" is the same for everyone in a race; expose its result
    bonus_driver = _clean(first['Random Driver Pred'])
    bonus_actual_pos = _pos_label(first['Random Actual Pos'])

    players = []
    for _, row in sub.iterrows():
        picks = []
        # Pole + podium slots
        for slot, pred_col, actual_key, score_col in [
            ('POLE', 'Pole Pred', 'pole', 'Pole Score'),
            ('P1', 'P1 Pred', 'p1', 'P1 Score'),
            ('P2', 'P2 Pred', 'p2', 'P2 Score'),
            ('P3', 'P3 Pred', 'p3', 'P3 Score'),
        ]:
            pred = _clean(row[pred_col])
            score = int(row[score_col]) if pd.notna(row[score_col]) else 0
            act = actual[actual_key]
            if slot == 'POLE':
                state = 'hit' if score > 0 else 'miss'
            elif pred is not None and act is not None and pred == act:
                state = 'hit'
            elif score > 0:
                state = 'partial'
            else:
                state = 'miss'
            picks.append({'slot': slot, 'pred': pred, 'score': score, 'state': state})

        # Bonus / random-driver slot (Race only)
        if rtype == 'Race':
            r_score = int(row['Random Score']) if pd.notna(row['Random Score']) else 0
            picks.append({
                'slot': 'BONUS',
                'pred': _clean(row['Random Driver Pred']),
                'predPos': _pos_label(row['Random Pos Pred']),
                'actualPos': _pos_label(row['Random Actual Pos']),
                'score': r_score,
                'state': 'hit' if r_score > 0 else 'miss',
            })

        players.append({
            'name': row['Player'],
            'total': int(row['Total Score']) if pd.notna(row['Total Score']) else 0,
            'picks': picks,
        })

    players.sort(key=lambda x: x['total'], reverse=True)

    meta = race_meta.get(gp, {'round': None, 'date': '', 'name': gp, 'circuit': ''})
    race_details.append({
        'race_id': race_data['race_id'],
        'grand_prix': gp,
        'display_name': meta['name'],
        'race_type': rtype,
        'round': meta['round'],
        'date': meta['date'],
        'circuit': meta['circuit'],
        'actual': actual,
        'bonus_driver': bonus_driver,
        'bonus_actual_pos': bonus_actual_pos,
        'players': players,
    })
    print(f"  {race_data['race_name']}: {len(players)} players, "
          f"pole={actual['pole']} P1={actual['p1']} P2={actual['p2']} P3={actual['p3']}")

print()

# Save all data as JSON for the dashboard
dashboard_data = {
    'players': list(scoring_df['Player'].unique()),
    'player_colors': player_colors,
    'leaderboard': overall_standings,
    'races': [
        {
            'id': r['race_id'],
            'name': r['race_name'],
            'grand_prix': r['grand_prix'],
            'race_type': r['race_type']
        }
        for r in race_points_data
    ],
    'race_points': [
        {
            'race_id': r['race_id'],
            'race_name': r['race_name'],
            'points_by_player': r['points_by_player']
        }
        for r in race_points_data
    ],
    'progression': [
        {
            'race_id': p['race_id'],
            'race_name': p['race_name'],
            'cumulative_by_player': p['cumulative_by_player']
        }
        for p in progression_data
    ],
    'accuracy_heatmap': accuracy_heatmap,
    'race_details': race_details
}

# Save to JSON file
with open('dashboard_data.json', 'w') as f:
    json.dump(dashboard_data, f, indent=2)

print("Dashboard data saved to: dashboard_data.json")

# Also save as a JS file so the dashboard works when opened directly via
# file:// (double-click in Explorer), where fetch() of a .json is blocked.
# A <script> tag is not subject to that restriction.
with open('dashboard_data.js', 'w', encoding='utf-8') as f:
    f.write('window.DASHBOARD_DATA = ')
    json.dump(dashboard_data, f, indent=2)
    f.write(';\n')

print("Dashboard data saved to: dashboard_data.js")
print()

# Also create a simple CSV for reference
race_points_export = []
for race_data in race_points_data:
    row = {
        'Race': race_data['race_name'],
        'Grand Prix': race_data['grand_prix'],
        'Type': race_data['race_type']
    }
    for player in scoring_df['Player'].unique():
        row[player] = race_data['points_by_player'].get(player, 0)
    race_points_export.append(row)

race_points_df = pd.DataFrame(race_points_export)
race_points_df.to_csv('race_points_summary.csv', index=False)
print("Race points summary saved to: race_points_summary.csv")

# %%
