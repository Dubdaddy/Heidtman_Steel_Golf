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

# --- DYNAMIC HANDICAP TRACKER (Modern WHS) ---
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
    if rounds_played < 3: return None
        
    adjustment = 0.0
    if rounds_played == 3: count = 1; adjustment = -2.0
    elif rounds_played == 4: count = 1; adjustment = -1.0
    elif rounds_played == 5: count = 1
    elif rounds_played == 6: count = 2; adjustment = -1.0
    elif rounds_played <= 8: count = 2
    elif rounds_played <= 11: count = 3
    elif rounds_played <= 14: count = 4
    elif rounds_played <= 16: count = 5
    elif rounds_played <= 18: count = 6
    elif rounds_played == 19: count = 7
    else: count = 8
        
    best_diffs = recent_rounds.nsmallest(count, 'Differential')
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

primary_scores = filtered_df[filtered_df['Had Sub?'] == 'No']
hole_columns = ['Hole 1', 'Hole 2', 'Hole 3', 'Hole 4', 'Hole 5', 'Hole 6', 'Hole 7', 'Hole 8', 'Hole 9']


# ==========================================
# UI RENDERING LOGIC (Player Profile vs League)
# ==========================================

if selected_player != "All Players":
    # --- INDIVIDUAL PLAYER PROFILE ---
    st.header(f"🏌️ Player Profile: {selected_player}")
    player_data = primary_scores.sort_values(by='Golf Date', ascending=False)
    
    if not player_data.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        rounds_played = len(player_data)
        avg_score = player_data['Total'].mean()
        best_score = player_data['Total'].min()
        
        player_hcp_row = current_handicaps[current_handicaps['Golfer Name'] == selected_player]
        player_hcp = player_hcp_row['Current Handicap Index'].values[0] if not player_hcp_row.empty else "N/A"
        
        col1.metric("Current Handicap", player_hcp)
        col2.metric("Career Avg Score", round(avg_score, 2))
        col3.metric("Lowest Round", int(best_score))
        col4.metric("Rounds Played", rounds_played)
        
        st.markdown("---")
        
        col_split1, col_split2 = st.columns(2)
        with col_split1:
            st.subheader("Course Breakdown")
            front_avg = player_data[player_data['Front/Back'] == 'Front']['Total'].mean()
            back_avg = player_data[player_data['Front/Back'] == 'Back']['Total'].mean()
            
            st.write(f"**Front 9 Avg:** {front_avg:.2f}" if not pd.isna(front_avg) else "**Front 9 Avg:** N/A")
            st.write(f"**Back 9 Avg:** {back_avg:.2f}" if not pd.isna(back_avg) else "**Back 9 Avg:** N/A")
            
            hole_avgs = player_data[hole_columns].mean()
            st.write(f"**Best Hole:** {hole_avgs.idxmin()} ({hole_avgs.min():.2f} avg)")
            st.write(f"**Hardest Hole:** {hole_avgs.idxmax()} ({hole_avgs.max():.2f} avg)")
            
        with col_split2:
            st.subheader("Recent Form (Last 5 Rounds)")
            recent_5 = player_data.head(5)[['Golf Date', 'Front/Back', 'Total']].copy()
            recent_5['Golf Date'] = recent_5['Golf Date'].dt.strftime('%m/%d/%Y')
            st.dataframe(recent_5, use_container_width=True, hide_index=True)

        # Player Specific Charts
        st.subheader(f"{selected_player}'s Scoring Trend")
        chart_data = player_data.sort_values('Golf Date').set_index('Golf Date')['Total']
        st.line_chart(chart_data)
        
    else:
        st.warning(f"No primary roster scores found for {selected_player} in the selected time frame.")

else:
    # --- LEAGUE WIDE DASHBOARD ---
    st.header("League Handicaps", help="Calculated using the modern WHS differential formula.")
    st.dataframe(current_handicaps, use_container_width=True, hide_index=True)

    st.header("Player Profiles & Statistics")
    
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
        hole_averages = primary_scores.groupby('Golfer Name')[hole_columns].mean().round(2).reset_index()
        st.dataframe(hole_averages, use_container_width=True, hide_index=True)
        
        # --- PHASE 4: VISUALIZATIONS & TRENDS ---
        st.header("Visualizations & Trends")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("League Hole Difficulty")
            hole_diff = primary_scores[hole_columns].mean().rename("Average Score")
            st.bar_chart(hole_diff)
            
        with col2:
            st.subheader("League Score Distribution")
            score_dist = primary_scores['Total'].value_counts().sort_index()
            st.bar_chart(score_dist)
            
        st.subheader("League Scoring Trend (Daily Average)")
        trend_data = primary_scores.sort_values('Golf Date')
        chart_data = trend_data.groupby('Golf Date')['Total'].mean()
        st.line_chart(chart_data)

    else:
        st.warning("No data available for the current filter selection.")
