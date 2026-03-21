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
    'accuracy_heatmap': accuracy_heatmap
}

# Save to JSON file
with open('dashboard_data.json', 'w') as f:
    json.dump(dashboard_data, f, indent=2)

print("Dashboard data saved to: dashboard_data.json")
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
