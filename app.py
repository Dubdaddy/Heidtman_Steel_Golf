import streamlit as st
import pandas as pd

# Set page configuration for the dashboard
st.set_page_config(page_title="Heidtman Steel Golf League", layout="wide")

# --- DATA INGESTION ---
@st.cache_data
def load_data():
    # Read the main historical scores sheet
    df = pd.read_excel('Golf League Data.xlsx', sheet_name='Historical Scores')
    
    # Convert 'Golf Date' to proper datetime format
    df['Golf Date'] = pd.to_datetime(df['Golf Date'])
    
    # Extract the Year for easy filtering later
    df['Year'] = df['Golf Date'].dt.year
    
    # CLEANING: Fix capitalization and spacing typos in player names
    df['Golfer Name'] = df['Golfer Name'].str.strip().str.title()
    
    return df

# Load the data
df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.title("League Filters")

# Filter by Year
available_years = df['Year'].unique()
selected_year = st.sidebar.selectbox("Select Season", ["All Time"] + list(available_years))

# Apply the Year filter to the dataframe
if selected_year != "All Time":
    filtered_df = df[df['Year'] == selected_year]
else:
    filtered_df = df

# Filter by Player
players = sorted(filtered_df['Golfer Name'].unique())
selected_player = st.sidebar.selectbox("Select Player", ["All Players"] + players)

if selected_player != "All Players":
    filtered_df = filtered_df[filtered_df['Golfer Name'] == selected_player]

# --- MAIN DASHBOARD AREA ---
st.title("Heidtman Steel Golf League Dashboard")
st.markdown("Welcome to the league stat tracker.")

# --- PHASE 3: DYNAMIC HANDICAP TRACKER ---
st.header("League Handicaps", help="Click the info box below to see the exact differential formula and sliding scale.")

# Explanatory info box / expander
with st.expander("ℹ️ How are handicaps calculated?"):
    st.markdown("""
    **Handicap Calculation Breakdown:**
    
    1. **Score Differential:** Each round's 9-hole differential is calculated using The Legacy Golf Club's rating and slope:
       - **Front 9:** Rating = `34.0`, Slope = `118`
       - **Back 9:** Rating = `35.0`, Slope = `125`
       
       $$\\text{Differential} = \\frac{(\\text{Gross Score} - \\text{Course Rating}) \\times 113}{\\text{Slope Rating}}$$
       
    2. **Sliding Scale Selection:** The algorithm evaluates up to a player's last 20 primary rounds:
       - **3–5 rounds:** Lowest 1 differential
       - **6–8 rounds:** Lowest 2 differentials
       - **9–11 rounds:** Lowest 3 differentials
       - **12–14 rounds:** Lowest 4 differentials
       - **15–16 rounds:** Lowest 5 differentials
       - **17–18 rounds:** Lowest 6 differentials
       - **19 rounds:** Lowest 7 differentials
       - **20 rounds:** Lowest 8 differentials
       
    3. **Final Calculation:** 
       $$\\text{Handicap Index} = (\\text{Average of Lowest Differentials}) \\times 0.96$$
       *The index is truncated to a whole integer for league strokes.*
    """)

# We use the unfiltered dataframe for handicaps so it always looks at the last 20 rounds 
# regardless of what year is selected in the sidebar, ensuring handicaps are current.
hcp_df = df[df['Had Sub?'] == 'No'].copy()

# Function to calculate 9-hole USGA differential
def calculate_differential(row):
    score = row['Total']
    # Apply course and slope ratings based on the nine played
    if row['Front/Back'] == 'Front':
        cr, sr = 34.0, 118.0
    elif row['Front/Back'] == 'Back':
        cr, sr = 35.0, 125.0
    else:
        cr, sr = 34.5, 121.5 # Fallback average
        
    diff = (score - cr) * 113.0 / sr
    return max(0, diff) # Prevent negative differentials

# Calculate differential for every round historically
hcp_df['Differential'] = hcp_df.apply(calculate_differential, axis=1)

def get_handicap(player_rounds):
    # Sort by date to ensure we get the most recent rounds
    recent_rounds = player_rounds.sort_values(by='Golf Date', ascending=False).head(20)
    rounds_played = len(recent_rounds)
    
    # Require at least 3 rounds to establish a baseline handicap
    if rounds_played < 3:
        return None
        
    # USGA sliding scale for fewer than 20 rounds
    if rounds_played <= 5: count = 1
    elif rounds_played <= 8: count = 2
    elif rounds_played <= 11: count = 3
    elif rounds_played <= 14: count = 4
    elif rounds_played <= 16: count = 5
    elif rounds_played <= 18: count = 6
    elif rounds_played == 19: count = 7
    else: count = 8
        
    # Get the lowest differentials based on the sliding scale
    best_diffs = recent_rounds.nsmallest(count, 'Differential')
    
    # Calculate legacy USGA index (average of best differentials * 0.96)
    handicap_index = (best_diffs['Differential'].mean()) * 0.96
    
    return int(handicap_index) # League format uses whole integers

# Apply the logic and create the handicap leaderboard
current_handicaps = (
    hcp_df.groupby('Golfer Name')
    .apply(get_handicap)
    .dropna()
    .reset_index(name='Current Handicap Index')
)

current_handicaps['Current Handicap Index'] = current_handicaps['Current Handicap Index'].astype(int)
current_handicaps = current_handicaps.sort_values('Current Handicap Index')

# Display the handicap table
st.dataframe(current_handicaps, use_container_width=True, hide_index=True)


# --- PHASE 2: CORE METRICS & ANALYTICS ---
st.header("Player Profiles & Statistics")

# Exclude substitute rounds to maintain accurate personal statistics for the filtered view
primary_scores = filtered_df[filtered_df['Had Sub?'] == 'No']

if not primary_scores.empty:
    # Build the performance summary table
    player_summary = primary_scores.groupby('Golfer Name').agg(
        Rounds_Played=('Total', 'count'),
        Average_Score=('Total', 'mean'),
        Lowest_Round=('Total', 'min'),
        Highest_Round=('Total', 'max')
    ).reset_index()
    
    # Clean up the formatting for display
    player_summary['Average_Score'] = player_summary['Average_Score'].round(2)
    player_summary = player_summary.sort_values(by='Average_Score')
    
    st.subheader("Performance Overview")
    st.dataframe(player_summary, use_container_width=True, hide_index=True)

    # Build the hole-by-hole breakdown
    st.subheader("Hole-by-Hole Scoring Averages")
    
    hole_columns = ['Hole 1', 'Hole 2', 'Hole 3', 'Hole 4', 'Hole 5', 'Hole 6', 'Hole 7', 'Hole 8', 'Hole 9']
    hole_averages = primary_scores.groupby('Golfer Name')[hole_columns].mean().round(2).reset_index()
    
    st.dataframe(hole_averages, use_container_width=True, hide_index=True)
else:
    st.warning("No data available for the current filter selection.")
