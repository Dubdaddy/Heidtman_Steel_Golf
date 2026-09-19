import streamlit as st
import pandas as pd

# Set page configuration for the dashboard
st.set_page_config(page_title="Heidtman Steel Golf League", layout="wide")

# --- DATA INGESTION ---
@st.cache_data
def load_data():
    df = pd.read_excel('Golf League Data.xlsx', sheet_name='Historical Scores')
    df['Golf Date'] = pd.to_datetime(df['Golf Date'])
    df['Year'] = df['Golf Date'].dt.year
    df['Golfer Name'] = df['Golfer Name'].str.strip().str.title()
    return df

df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.title("League Filters")
available_years = df['Year'].unique()
selected_year = st.sidebar.selectbox("Select Season", ["All Time"] + list(available_years))

if selected_year != "All Time":
    filtered_df = df[df['Year'] == selected_year]
else:
    filtered_df = df

players = sorted(filtered_df['Golfer Name'].unique())
selected_player = st.sidebar.selectbox("Select Player", ["All Players"] + players)

if selected_player != "All Players":
    filtered_df = filtered_df[filtered_df['Golfer Name'] == selected_player]

# --- MAIN DASHBOARD AREA ---
st.title("Heidtman Steel Golf League Dashboard")
st.markdown("Welcome to the league stat tracker.")

# --- PHASE 3: DYNAMIC HANDICAP TRACKER ---
st.header("League Handicaps", help="Click the info box below to see the modern WHS differential formula.")

with st.expander("ℹ️ How are modern handicaps calculated?"):
    st.markdown("""
    **Modern WHS Calculation Breakdown:**
    
    1. **Score Differential:** 
       - **Front 9:** Rating = `34.0`, Slope = `118`
       - **Back 9:** Rating = `35.0`, Slope = `125`
       
       $$\\text{Differential} = \\frac{(\\text{Gross Score} - \\text{Course Rating}) \\times 113}{\\text{Slope Rating}}$$
       
    2. **Modern WHS Sliding Scale & Adjustments:** 
       - **3 scores:** Lowest 1 differential ($-2.0$ adjustment)
       - **4 scores:** Lowest 1 differential ($-1.0$ adjustment)
       - **5 scores:** Lowest 1 differential 
       - **6 scores:** Average of lowest 2 ($-1.0$ adjustment)
       - **7-8 scores:** Average of lowest 2 
       - **9-11 scores:** Average of lowest 3
       - **12-14 scores:** Average of lowest 4
       - **15-16 scores:** Average of lowest 5
       - **17-18 scores:** Average of lowest 6
       - **19 scores:** Average of lowest 7
       - **20 scores:** Average of lowest 8
       
    3. **Final Index:** 
       The 0.96 legacy multiplier has been eliminated. The raw average (plus any adjustment) forms the index, truncated to a whole integer for league play.
    """)

hcp_df = df[df['Had Sub?'] == 'No'].copy()

def calculate_differential(row):
    score = row['Total']
    if row['Front/Back'] == 'Front':
        cr, sr = 34.0, 118.0
    elif row['Front/Back'] == 'Back':
        cr, sr = 35.0, 125.0
    else:
        cr, sr = 34.5, 121.5 
    diff = (score - cr) * 113.0 / sr
    return max(0, diff) 

hcp_df['Differential'] = hcp_df.apply(calculate_differential, axis=1)

def get_handicap(player_rounds):
    recent_rounds = player_rounds.sort_values(by='Golf Date', ascending=False).head(20)
    rounds_played = len(recent_rounds)
    
    if rounds_played < 3:
        return None
        
    adjustment = 0.0
    if rounds_played == 3: 
        count = 1
        adjustment = -2.0
    elif rounds_played == 4: 
        count = 1
        adjustment = -1.0
    elif rounds_played == 5: 
        count = 1
    elif rounds_played == 6: 
        count = 2
        adjustment = -1.0
    elif rounds_played <= 8: count = 2
    elif rounds_played <= 11: count = 3
    elif rounds_played <= 14: count = 4
    elif rounds_played <= 16: count = 5
    elif rounds_played <= 18: count = 6
    elif rounds_played == 19: count = 7
    else: count = 8
        
    best_diffs = recent_rounds.nsmallest(count, 'Differential')
    
    # Modern WHS Index
    handicap_index = (best_diffs['Differential'].mean()) + adjustment
    
    return max(0, int(handicap_index)) 

current_handicaps = (
    hcp_df.groupby('Golfer Name')
    .apply(get_handicap)
    .dropna()
    .reset_index(name='Current Handicap Index')
)

current_handicaps['Current Handicap Index'] = current_handicaps['Current Handicap Index'].astype(int)
current_handicaps = current_handicaps.sort_values('Current Handicap Index')

st.dataframe(current_handicaps, use_container_width=True, hide_index=True)


# --- PHASE 2: CORE METRICS & ANALYTICS ---
st.header("Player Profiles & Statistics")
primary_scores = filtered_df[filtered_df['Had Sub?'] == 'No']

if not primary_scores.empty:
    player_summary = primary_scores.groupby('Golfer Name').agg(
        Rounds_Played=('Total', 'count'),
        Average_Score=('Total', 'mean'),
        Lowest_Round=('Total', 'min'),
        Highest_Round=('Total', 'max')
    ).reset_index()
    
    player_summary['Average_Score'] = player_summary['Average_Score'].round(2)
    player_summary = player_summary.sort_values(by='Average_Score')
    
    st.subheader("Performance Overview")
    st.dataframe(player_summary, use_container_width=True, hide_index=True)

    st.subheader("Hole-by-Hole Scoring Averages")
    hole_columns = ['Hole 1', 'Hole 2', 'Hole 3', 'Hole 4', 'Hole 5', 'Hole 6', 'Hole 7', 'Hole 8', 'Hole 9']
    hole_averages = primary_scores.groupby('Golfer Name')[hole_columns].mean().round(2).reset_index()
    
    st.dataframe(hole_averages, use_container_width=True, hide_index=True)
    
    # --- PHASE 4: VISUALIZATIONS & TRENDS ---
    st.header("Visualizations & Trends")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Hole Difficulty (Average Score)")
        hole_diff = primary_scores[hole_columns].mean().rename("Average Score")
        st.bar_chart(hole_diff)
        
    with col2:
        st.subheader("Score Distribution")
        score_dist = primary_scores['Total'].value_counts().sort_index()
        st.bar_chart(score_dist)
        
    st.subheader("Scoring Trend Over Time")
    trend_data = primary_scores.sort_values('Golf Date')
    
    if selected_player != "All Players":
        # Plot individual player's scores chronologically
        chart_data = trend_data.set_index('Golf Date')['Total']
        st.line_chart(chart_data)
    else:
        # Plot the league average per day to avoid a messy chart
        chart_data = trend_data.groupby('Golf Date')['Total'].mean()
        st.line_chart(chart_data)

else:
    st.warning("No data available for the current filter selection.")
