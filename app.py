import streamlit as st
import pandas as pd
import altair as alt

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
    player_data = primary_scores.sort_values(by='Golf Date', ascending=False).copy()
    
    if not player_data.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        rounds_played = len(player_data)
        avg_score = player_data['Total'].mean()
        
        # Lowest round with most recent date tie-breaker
        lowest_round_df = player_data.sort_values(by=['Total', 'Golf Date'], ascending=[True, False]).iloc[0]
        best_score = lowest_round_df['Total']
        
        # Format date without leading zeros (e.g., 8/6/2025)
        dt = lowest_round_df['Golf Date']
        best_date_str = f"{dt.month}/{dt.day}/{dt.year}"
        
        player_hcp_row = current_handicaps[current_handicaps['Golfer Name'] == selected_player]
        player_hcp = player_hcp_row['Current Handicap Index'].values[0] if not player_hcp_row.empty else "N/A"
        
        col1.metric("Current Handicap", player_hcp)
        col2.metric("Career Avg Score", round(avg_score, 2))
        
        # Custom HTML metric for Lowest Round to make the date smaller subtext next to the score
        col3.markdown(f"""
            <div style="font-size: 14px; font-weight: 400; color: rgb(49, 51, 63); margin-bottom: 2px;">Lowest Round</div>
            <div style="font-size: 2.25rem; font-weight: 600; line-height: 1.2;">
                {int(best_score)} <span style="font-size: 0.95rem; font-weight: 400; color: gray;">{best_date_str}</span>
            </div>
        """, unsafe_allow_html=True)
        
        col4.metric("Rounds Played", rounds_played)
        
        st.markdown("---")
        
        col_split1, col_split2 = st.columns(2)
        with col_split1:
            st.subheader("Course Breakdown (Current Filter)")
            tot_front = player_data[player_data['Front/Back'] == 'Front']['Total'].mean()
            tot_back = player_data[player_data['Front/Back'] == 'Back']['Total'].mean()
            
            st.write(f"**Front 9 Avg:** {tot_front:.2f}" if not pd.isna(tot_front) else "**Front 9 Avg:** N/A")
            st.write(f"**Back 9 Avg:** {tot_back:.2f}" if not pd.isna(tot_back) else "**Back 9 Avg:** N/A")
            
            hole_avgs = player_data[hole_columns].mean()
            st.write(f"**Best Hole:** {hole_avgs.idxmin()} ({hole_avgs.min():.2f} avg)")
            st.write(f"**Hardest Hole:** {hole_avgs.idxmax()} ({hole_avgs.max():.2f} avg)")
            
        with col_split2:
            st.subheader("Recent Form (Last 5 Rounds)")
            recent_5 = player_data.head(5)[['Golf Date', 'Front/Back', 'Total']].copy()
            # Format recent form dates without leading zeros as well
            recent_5['Golf Date'] = recent_5['Golf Date'].dt.month.astype(str) + '/' + recent_5['Golf Date'].dt.day.astype(str) + '/' + recent_5['Golf Date'].dt.year.astype(str)
            st.dataframe(recent_5, use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # SEASON OVER SEASON TABLE
        st.subheader("Season-over-Season Performance")
        season_rows = []
        years = sorted(player_data['Year'].unique())
        
        for y in years:
            y_df = player_data[player_data['Year'] == y]
            if not y_df.empty:
                r_cnt = len(y_df)
                s_avg = y_df['Total'].mean()
                s_min_row = y_df.sort_values(by=['Total', 'Golf Date'], ascending=[True, False]).iloc[0]
                s_dt = s_min_row['Golf Date']
                s_date_str = f"{s_dt.month}/{s_dt.day}/{s_dt.year}"
                
                front_avg = y_df[y_df['Front/Back'] == 'Front']['Total'].mean()
                back_avg = y_df[y_df['Front/Back'] == 'Back']['Total'].mean()
                
                season_rows.append({
                    'Season': str(y),
                    'Rounds': r_cnt,
                    'Avg Score': round(s_avg, 2),
                    'Lowest Round': f"{s_min_row['Total']} ({s_date_str})",
                    'Front 9 Avg': round(front_avg, 2) if not pd.isna(front_avg) else "N/A",
                    'Back 9 Avg': round(back_avg, 2) if not pd.isna(back_avg) else "N/A"
                })
        
        # All Time Row
        season_rows.append({
            'Season': 'All Time',
            'Rounds': rounds_played,
            'Avg Score': round(avg_score, 2),
            'Lowest Round': f"{best_score} ({best_date_str})",
            'Front 9 Avg': round(tot_front, 2) if not pd.isna(tot_front) else "N/A",
            'Back 9 Avg': round(tot_back, 2) if not pd.isna(tot_back) else "N/A"
        })
        
        season_df = pd.DataFrame(season_rows)
        st.dataframe(season_df, use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # Dynamic Scoring Trend (Altair removes winter months and sets custom Y-axis)
        st.subheader(f"{selected_player}'s Scoring Trend")
        chart_data = player_data.sort_values('Golf Date').copy()
        chart_data['Date Label'] = chart_data['Golf Date'].dt.month.astype(str) + '/' + chart_data['Golf Date'].dt.day.astype(str) + '/' + chart_data['Golf Date'].dt.year.astype(str)
        
        min_y = max(0, chart_data['Total'].min() - 3)
        max_y = chart_data['Total'].max() + 3
        
        line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X('Date Label', sort=None, title='Round Date'),
            y=alt.Y('Total', scale=alt.Scale(domain=[min_y, max_y]), title='Gross Score'),
            tooltip=['Date Label', 'Front/Back', 'Total']
        ).properties(height=400)
        
        st.altair_chart(line_chart, use_container_width=True)
        
    else:
        st.warning(f"No primary roster scores found for {selected_player} in the selected time frame.")

else:
    # --- LEAGUE WIDE DASHBOARD ---
    st.header("League Handicaps", help="Calculated using the modern WHS differential formula.")
    with st.expander("ℹ️ How are modern handicaps calculated?"):
        st.markdown("""
        **Modern WHS Calculation Breakdown:**
        1. **Score Differential:** 
           - **Front 9:** Rating = `34.0`, Slope = `118`
           - **Back 9:** Rating = `35.0`, Slope = `125`
           $$\\text{Differential} = \\frac{(\\text{Gross Score} - \\text{Course Rating}) \\times 113}{\\text{Slope Rating}}$$
        2. **Modern WHS Sliding Scale & Adjustments:** Sliding scale applies standard negative adjustments (up to -2.0) for players with fewer than 20 rounds.
        """)
        
    st.dataframe(current_handicaps, use_container_width=True, hide_index=True)

    st.header("Player Profiles & Statistics")
    
    if not primary_scores.empty:
        # Get lowest round with date for the overview table
        lowest_rounds_dict = {}
        grouped = primary_scores.groupby('Golfer Name')
        for name, group in grouped:
            best_row = group.sort_values(by=['Total', 'Golf Date'], ascending=[True, False]).iloc[0]
            b_dt = best_row['Golf Date']
            lowest_rounds_dict[name] = f"{best_row['Total']} ({b_dt.month}/{b_dt.day}/{b_dt.year})"
            
        player_summary = grouped.agg(
            Rounds_Played=('Total', 'count'),
            Average_Score=('Total', 'mean'),
            Highest_Round=('Total', 'max')
        ).reset_index()
        
        # Map the new lowest round string to the dataframe
        player_summary.insert(3, 'Lowest_Round', player_summary['Golfer Name'].map(lowest_rounds_dict))
        
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
        trend_data = primary_scores.groupby('Golf Date')['Total'].mean().reset_index()
        trend_data['Date Label'] = trend_data['Golf Date'].dt.month.astype(str) + '/' + trend_data['Golf Date'].dt.day.astype(str) + '/' + trend_data['Golf Date'].dt.year.astype(str)
        
        min_y = max(0, trend_data['Total'].min() - 3)
        max_y = trend_data['Total'].max() + 3
        
        league_chart = alt.Chart(trend_data).mark_line(point=True).encode(
            x=alt.X('Date Label', sort=None, title='Round Date'),
            y=alt.Y('Total', scale=alt.Scale(domain=[min_y, max_y]), title='Average Gross Score'),
            tooltip=['Date Label', 'Total']
        ).properties(height=400)
        
        st.altair_chart(league_chart, use_container_width=True)

    else:
        st.warning("No data available for the current filter selection.")
