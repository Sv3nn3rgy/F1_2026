# %%
import pandas as pd
import argparse
import os
import sys

# Console on Windows defaults to cp1252, which can't encode the report's
# arrow/checkmark glyphs. Force UTF-8 so printing the report doesn't crash.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

import requests
import numpy as np
import re
import unicodedata
import fastf1


def strip_accents(value):
    """Normalize a driver name to plain ASCII so accented FastF1 names
    (e.g. 'Pérez', 'Hülkenberg') match the ASCII predictions."""
    if not isinstance(value, str):
        return value
    return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
import logging
# Suppress FastF1 verbose output
logging.getLogger('fastf1').setLevel(logging.WARNING)

# Get race Results
season_results = []

# check how many rounds and sessions are available for 2026 season in the API and load them
race_left = len(fastf1.get_events_remaining()) + 1
race_done = 24 - race_left

# use API to get results for a specific event (e.g., 2026, round 2, Race)
for round_num in range(1,race_done):
    for session_type in ['Sprint', 'Race']:
        try:
            print(f"Loading Round {round_num} - {session_type}...")
            session = fastf1.get_session(2026, round_num, session_type)
            session.load()

            results = session.results.copy()
            results['RaceName'] = session.event['EventName']
            results['RaceType'] = session_type
            season_results.append(results)
       
        except:
            continue

season_results_df = pd.concat(season_results, ignore_index=True)

# Get Player Predictions
predictions_df = pd.read_csv('Input_Predictions.txt', header=0)

race_name_mapping = {
    'Australian GP': 'Australian Grand Prix',
    'China GP': 'Chinese Grand Prix',
    'Japanese GP': 'Japanese Grand Prix',
    'Miami GP': 'Miami Grand Prix',
    'Canada GP': 'Canadian Grand Prix',
    'Monaco GP': 'Monaco Grand Prix',
    'Barcelona GP': 'Barcelona Grand Prix',
    'Spanish GP': 'Spanish Grand Prix',
    'Austria GP': 'Austrian Grand Prix',
    'British GP': 'British Grand Prix',
    'Hungarian GP': 'Hungarian Grand Prix',
    'Dutch GP': 'Dutch Grand Prix',
    'Italian GP': 'Italian Grand Prix',
}
 
# Create a list to store all scoring records
scoring_records = []
 
# Iterate through each prediction row
for idx, pred_row in predictions_df.iterrows():
    player_name = pred_row['Player Name']
    grand_prix = pred_row['Grand prix name']
    race_type = pred_row['Race/Sprint']
    
    # Get the predicted drivers and pole position
    pole_pred = pred_row['Pole position']
    p1_pred = pred_row['P1']
    p2_pred = pred_row['P2']
    p3_pred = pred_row['P3']
    random_driver_pred = pred_row['RandomDriver']
    random_driver_pos_pred = pred_row['RandomDriverPos']
    
    # Filter season results to get the actual race results
    # Use the mapping to convert prediction race name to season results race name
    race_name_in_results = race_name_mapping.get(grand_prix, grand_prix)
    
    race_results = season_results_df[
        (season_results_df['RaceName'] == race_name_in_results) &
        (season_results_df['RaceType'] == race_type)
    ].copy()
    
    if race_results.empty:
        print(f"Warning: No results found for {grand_prix} {race_type} for {player_name}")
        continue

    # Strip accents so names like 'Pérez'/'Hülkenberg' match ASCII predictions
    race_results['LastName'] = race_results['LastName'].map(strip_accents)

    # Sort by actual position to get the finishing order
    race_results_sorted = race_results.sort_values('Position').reset_index(drop=True)
    
    # Get the actual pole position (grid position 1)
    pole_actual_rows = race_results[race_results['GridPosition'] == 1.0]
    if not pole_actual_rows.empty:
        pole_actual = pole_actual_rows.iloc[0]['LastName']
    else:
        pole_actual = None
    
    # Get the actual top 3 finishers
    top3_actual = race_results_sorted[race_results_sorted['Position'] <= 3]['LastName'].tolist()
    
    # Get the actual random driver position if it exists
    random_driver_actual_rows = race_results[race_results['LastName'] == random_driver_pred]
    if not random_driver_actual_rows.empty:
        random_driver_actual_pos = random_driver_actual_rows.iloc[0]['Position']
        random_driver_pos_match = str(int(random_driver_actual_pos)) if pd.notna(random_driver_actual_pos) else None
    else:
        random_driver_actual_pos = None
        random_driver_pos_match = None
    
    # ===== SCORING LOGIC =====
    
    # 1. Pole position scoring
    pole_score = 0
    if pole_pred == pole_actual:
        if race_type == 'Sprint':
            pole_score = 1
        else:  # Race
            pole_score = 3
    
    # 2. P1 (1st place) scoring
    p1_score = 0
    if p1_pred in top3_actual:
        if p1_pred == top3_actual[0] if len(top3_actual) > 0 else False:
            if race_type == 'Sprint':
                p1_score = 3
            else:  # Race
                p1_score = 5
        else:  # Predicted P1 but finished in top3
            if race_type == 'Sprint':
                p1_score = 0
            else:  # Race
                p1_score = 2
    
    # 3. P2 (2nd place) scoring
    p2_score = 0
    if p2_pred in top3_actual:
        if p2_pred == top3_actual[1] if len(top3_actual) > 1 else False:
            if race_type == 'Sprint':
                p2_score = 3
            else:  # Race
                p2_score = 5
        else:  # Predicted P2 but finished in top3
            if race_type == 'Sprint':
                p2_score = 0
            else:  # Race
                p2_score = 2
    
    # 4. P3 (3rd place) scoring
    p3_score = 0
    if p3_pred in top3_actual:
        if p3_pred == top3_actual[2] if len(top3_actual) > 2 else False:
            if race_type == 'Sprint':
                p3_score = 3
            else:  # Race
                p3_score = 5
        else:  # Predicted P3 but finished in top3
            if race_type == 'Sprint':
                p3_score = 0
            else:  # Race
                p3_score = 2
    
    # 5. Random driver scoring (only for Race, not Sprint)
    random_score = 0
    if race_type == 'Race':
        # Extract position number from random_driver_pos_pred (e.g., "P2" -> "2")
        if isinstance(random_driver_pos_pred, str) and random_driver_pos_pred.startswith('P'):
            random_pred_pos_num = random_driver_pos_pred[1:]
        else:
            random_pred_pos_num = None
        
        # Check if random driver prediction matches actual position
        if random_driver_pos_match and random_pred_pos_num:
            if random_pred_pos_num == random_driver_pos_match:
                random_score = 3
    
    # Calculate total score for this prediction
    total_score = pole_score + p1_score + p2_score + p3_score + random_score
    
    # Create a detailed record
    record = {
        'Player': player_name,
        'Grand Prix': grand_prix,
        'Race Type': race_type,
        'Pole Pred': pole_pred,
        'Pole Actual': pole_actual,
        'Pole Score': pole_score,
        'P1 Pred': p1_pred,
        'P1 Actual': top3_actual[0] if len(top3_actual) > 0 else None,
        'P1 Score': p1_score,
        'P2 Pred': p2_pred,
        'P2 Actual': top3_actual[1] if len(top3_actual) > 1 else None,
        'P2 Score': p2_score,
        'P3 Pred': p3_pred,
        'P3 Actual': top3_actual[2] if len(top3_actual) > 2 else None,
        'P3 Score': p3_score,
        'Random Driver Pred': random_driver_pred,
        'Random Pos Pred': random_driver_pos_pred,
        'Random Actual Pos': random_driver_pos_match,
        'Random Score': random_score,
        'Total Score': total_score
    }
    
    scoring_records.append(record)
 
# Create a dataframe from all scoring records
scoring_df = pd.DataFrame(scoring_records)
 
print("=" * 80)
print("DETAILED SCORING BREAKDOWN - All Predictions with Scores")
print("=" * 80)
print(scoring_df.to_string(index=False))
print("\n")

# Compute leaderboard totals per player
player_totals = scoring_df.groupby('Player')['Total Score'].sum().sort_values(ascending=False)

# Save the detailed results to a CSV file for further analysis
scoring_df.to_csv('detailed_scoring.csv', index=False)
print("Detailed scoring results saved to: detailed_scoring.csv")
 
# ===== CREATE COMPREHENSIVE TEXT REPORT =====
print("\n")
print("=" * 80)
print("COMPREHENSIVE PREDICTION REPORT")
print("=" * 80)
print("\n")
 
report_lines = []
 
report_lines.append("=" * 80)
report_lines.append("RACE PREDICTION SCORING REPORT")
report_lines.append("=" * 80)
report_lines.append("")
 
# Overall leaderboard
report_lines.append("FINAL LEADERBOARD")
report_lines.append("-" * 80)
for rank, (player, score) in enumerate(player_totals.items(), 1):
    report_lines.append(f"{rank}. {player:20} {int(score):3} POINTS")
report_lines.append("")
report_lines.append("")
 
# Detailed breakdown for each player
for player in scoring_df['Player'].unique():
    player_data = scoring_df[scoring_df['Player'] == player]
    total_player_score = player_data['Total Score'].sum()
    
    report_lines.append("=" * 80)
    report_lines.append(f"{player.upper()} - TOTAL SCORE: {int(total_player_score)} POINTS")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    for idx, row in player_data.iterrows():
        race_info = f"{row['Grand Prix']} ({row['Race Type']})"
        report_lines.append(f"{race_info}")
        report_lines.append("-" * 80)
        
        # Pole position
        pole_match = "✓ CORRECT" if row['Pole Score'] > 0 else "✗ Incorrect"
        report_lines.append(f"Pole Position: {row['Pole Pred']:12} → Actual: {str(row['Pole Actual']):12} {pole_match:15} {int(row['Pole Score'])} pts")
        
        # P1 (1st place)
        p1_match = "✓ CORRECT" if row['P1 Pred'] == row['P1 Actual'] else "• In top 3" if row['P1 Score'] > 0 else "✗ Incorrect"
        report_lines.append(f"P1 Predicted: {row['P1 Pred']:12} → Actual: {str(row['P1 Actual']):12} {p1_match:15} {int(row['P1 Score'])} pts")
        
        # P2 (2nd place)
        p2_match = "✓ CORRECT" if row['P2 Pred'] == row['P2 Actual'] else "• In top 3" if row['P2 Score'] > 0 else "✗ Incorrect"
        report_lines.append(f"P2 Predicted: {row['P2 Pred']:12} → Actual: {str(row['P2 Actual']):12} {p2_match:15} {int(row['P2 Score'])} pts")
        
        # P3 (3rd place)
        p3_match = "✓ CORRECT" if row['P3 Pred'] == row['P3 Actual'] else "• In top 3" if row['P3 Score'] > 0 else "✗ Incorrect"
        report_lines.append(f"P3 Predicted: {row['P3 Pred']:12} \t→ Actual: {str(row['P3 Actual']):12}  {p3_match:15} {int(row['P3 Score'])} pts")
        
        # Random driver (only for races)
        if row['Race Type'] == 'Race':
            random_match = "✓ CORRECT" if row['Random Score'] > 0 else "✗ Incorrect"
            report_lines.append(f"Predicted: {row['Random Driver Pred']:6} {str(row['Random Pos Pred']):5} → Actual: {str(row['Random Actual Pos']):5} \t {random_match:15} {int(row['Random Score'])} pts")
        
        report_lines.append(f"{'RACE TOTAL':20} {int(row['Total Score'])} POINTS")
        report_lines.append("")
    

report_lines.append("")
 
# Write the report to file
report_text = "\n".join(report_lines)
print(report_text)
 
with open('prediction_report.txt', 'w', encoding='utf-8') as f:
    f.write(report_text)
 
print("\nFull report saved to: prediction_report.txt")
# 


# %%
