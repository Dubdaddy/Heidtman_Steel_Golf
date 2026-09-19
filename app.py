import streamlit as st
import pandas as pd
import altair as alt

# Set page configuration for the dashboard
st.set_page_config(
    page_title="Heidtman Steel Golf League", 
    layout="wide",
    initial_sidebar_state="auto"
)

# --- MOBILE-FRIENDLY CSS OPTIMIZATIONS ---
st.markdown("""
    <style>
    /* Adjust main container padding for mobile screens */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Make metric cards look clean and mobile-friendly */
    div[data-testid="stMetric"] {
        background-color: rgba(28, 131, 246, 0.04);
        border: 1px solid rgba(28, 131, 246, 0.1);
        padding: 12px 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    /* Ensure tables and dataframes wrap and fit nicely */
    [data-testid="stDataFrame"] {
        width: 100% !important;
    }
    
    /* Improve subheader spacing on mobile */
    h2, h3 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATA INGESTION ---
@st.cache_data
def load_data():
    df = pd.read_excel('Golf League Data.xlsx', sheet_name='Historical Scores')
    df['Golf Date'] = pd.to_datetime(df['Golf Date'])
    df['Year'] = df['Golf Date'].dt.year
    df['Golfer Name'] = df['Golfer Name'].str.strip().str.title()
    
    try:
        members_df = pd.read_excel('Golf League Data.xlsx', sheet_name='Members')
        col_name = members_df.columns[0]
        members_set = set(members_df[col_name].dropna().astype(str).str.strip().str.title())
    except Exception:
        members_set = set()
        
    return df, members_set

df, members_set = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.title("League Filters")

# Filter by Player only
players = sorted(df['Golfer Name'].unique())
selected_player = st.sidebar.selectbox("Select Player", ["All Players"] + players)

filtered_df = df if selected_player == "All Players" else df[df['Golfer Name'] == selected_player]

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

def get_handicap_for_subset(player_rounds):
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

# Overall / Combined Handicaps (used for player profile metric & sorting)
current_handicaps = (
    hcp_df.groupby('Golfer Name')
    .apply(get_handicap_for_subset)
    .dropna()
    .reset_index(name='Current Handicap Index')
)
current_handicaps['Current Handicap Index'] = current_handicaps['Current Handicap Index'].astype(int)

# Front 9 Handicaps
front_hcp_df = hcp_df[hcp_df['Front/Back'] == 'Front']
front_handicaps = (
    front_hcp_df.groupby('Golfer Name')
    .apply(get_handicap_for_subset)
    .dropna()
    .reset_index(name='Front 9 HCP')
)
front_handicaps['Front 9 HCP'] = front_handicaps['Front 9 HCP'].astype(int)

# Back 9 Handicaps
back_hcp_df = hcp_df[hcp_df['Front/Back'] == 'Back']
back_handicaps = (
    back_hcp_df.groupby('Golfer Name')
    .apply(get_handicap_for_subset)
    .dropna()
    .reset_index(name='Back 9 HCP')
)
back_handicaps['Back 9 HCP'] = back_handicaps['Back 9 HCP'].astype(int)

# Merge overall, front 9, and back 9 handicaps for league display
split_handicaps = (
    current_handicaps[['Golfer Name', 'Current Handicap Index']]
    .merge(front_handicaps, on='Golfer Name', how='left')
    .merge(back_handicaps, on='Golfer Name', how='left')
    .sort_values('Current Handicap Index')
)

display_handicaps = split_handicaps[['Golfer Name', 'Front 9 HCP', 'Back 9 HCP']]

# Split into Members and Former Members
members_hcp = display_handicaps[display_handicaps['Golfer Name'].isin(members_set)].reset_index(drop=True)
former_members_hcp = display_handicaps[~display_handicaps['Golfer Name'].isin(members_set)].reset_index(drop=True)

primary_scores = filtered_df[filtered_df['Had Sub?'] == 'No']
hole_columns = ['Hole 1', 'Hole 2', 'Hole 3', 'Hole 4', 'Hole 5', 'Hole 6', 'Hole 7', 'Hole 8', 'Hole 9']

# --- PAR MAPPINGS FOR BREAKDOWN ---
FRONT_PARS = {'Hole 1': 4, 'Hole 2': 4, 'Hole 3': 5, 'Hole 4': 4, 'Hole 5': 4, 'Hole 6': 3, 'Hole 7': 5, 'Hole 8': 3, 'Hole 9': 4}
BACK_PARS = {'Hole 1': 4, 'Hole 2': 5, 'Hole 3': 4, 'Hole 4': 3, 'Hole 5': 5, 'Hole 6': 4, 'Hole 7': 3, 'Hole 8': 4, 'Hole 9': 4}

def calculate_breakdown(sub_df):
    stats = []
    for name, group in sub_df.groupby('Golfer Name'):
        eagles, birdies, pars, bogeys, double_plus = 0, 0, 0, 0, 0
        for _, row in group.iterrows():
            fb = row['Front/Back']
            p_dict = FRONT_PARS if fb == 'Front' else BACK_PARS
            for h_col in hole_columns:
                score = row[h_col]
                if pd.isna(score): continue
                diff = score - p_dict[h_col]
                if diff <= -2: eagles += 1
                elif diff == -1: birdies += 1
                elif diff == 0: pars += 1
                elif diff == 1: bogeys += 1
                else: double_plus += 1
        stats.append({
            'Golfer Name': name,
            'Eagles': eagles,
            'Birdies': birdies,
            'Pars': pars,
            'Bogeys': bogeys,
            'Double Bogey+': double_plus
        })
    return pd.DataFrame(stats)

def calculate_par_tier_performance(sub_df):
    tier_stats = []
    for name, group in sub_df.groupby('Golfer Name'):
        par3_diffs, par4_diffs, par5_diffs = [], [], []
        for _, row in group.iterrows():
            fb = row['Front/Back']
            p_dict = FRONT_PARS if fb == 'Front' else BACK_PARS
            for h in range(1, 10):
                h_col = f'Hole {h}'
                score = row[h_col]
                if pd.isna(score): continue
                par = p_dict[h_col]
                diff = score - par
                if par == 3: par3_diffs.append(diff)
                elif par == 4: par4_diffs.append(diff)
                elif par == 5: par5_diffs.append(diff)
        tier_stats.append({
            'Golfer Name': name,
            'Par 3 Avg (+/-)': round(sum(par3_diffs)/len(par3_diffs), 2) if par3_diffs else 0,
            'Par 4 Avg (+/-)': round(sum(par4_diffs)/len(par4_diffs), 2) if par4_diffs else 0,
            'Par 5 Avg (+/-)': round(sum(par5_diffs)/len(par5_diffs), 2) if par5_diffs else 0,
        })
    return pd.DataFrame(tier_stats)

def calculate_volatility(sub_df):
    vol_stats = []
    for name, group in sub_df.groupby('Golfer Name'):
        scores = group['Total'].dropna()
        if len(scores) < 2: continue
        vol_stats.append({
            'Golfer Name': name,
            'Rounds': len(scores),
            'Avg Score': round(scores.mean(), 2),
            'Std Deviation': round(scores.std(), 2),
            'Min Score': int(scores.min()),
            'Max Score': int(scores.max()),
            'Score Range': int(scores.max() - scores.min())
        })
    return pd.DataFrame(vol_stats).sort_values(by='Std Deviation')


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
        
        lowest_round_df = player_data.sort_values(by=['Total', 'Golf Date'], ascending=[True, False]).iloc[0]
        best_score = lowest_round_df['Total']
        dt = lowest_round_df['Golf Date']
        # Shortened date format for mobile
        best_date_str = f"{dt.month}/{dt.day}/{dt.strftime('%y')}"
        
        player_hcp_row = current_handicaps[current_handicaps['Golfer Name'] == selected_player]
        player_hcp = player_hcp_row['Current Handicap Index'].values[0] if not player_hcp_row.empty else "N/A"
        
        col1.metric("Current Handicap", player_hcp)
        col2.metric("Career Avg Score", round(avg_score, 2))
        col3.metric("Lowest Round", f"{int(best_score)} ({best_date_str})")
        col4.metric("Rounds Played", rounds_played)
        
        st.markdown("---")
        
        col_split1, col_split2 = st.columns(2)
        with col_split1:
            st.subheader("Course Breakdown")
            
            front_data = player_data[player_data['Front/Back'] == 'Front']
            back_data = player_data[player_data['Front/Back'] == 'Back']
            
            tot_front = front_data['Total'].mean()
            tot_back = back_data['Total'].mean()
            
            # Nested columns to sit side-by-side inside col_split1
            cb_col1, cb_col2 = st.columns(2)
            
            with cb_col1:
                st.markdown("**Front 9**")
                st.write(f"**Avg Score:** {tot_front:.2f}" if not pd.isna(tot_front) else "**Avg Score:** N/A")
                
                if not front_data.empty:
                    # Subtract par to get over/under numbers
                    f_over_par = front_data[hole_columns].mean().sub(pd.Series(FRONT_PARS))
                    best_f = f_over_par.idxmin()
                    hardest_f = f_over_par.idxmax()
                    
                    # Format with explicit '+' for over par
                    best_f_str = f"+{f_over_par[best_f]:.2f}" if f_over_par[best_f] > 0 else f"{f_over_par[best_f]:.2f}"
                    hardest_f_str = f"+{f_over_par[hardest_f]:.2f}" if f_over_par[hardest_f] > 0 else f"{f_over_par[hardest_f]:.2f}"
                    
                    st.write(f"**Best Hole:** {best_f} ({best_f_str})")
                    st.write(f"**Hardest Hole:** {hardest_f} ({hardest_f_str})")
                else:
                    st.write("**Best Hole:** N/A")
                    st.write("**Hardest Hole:** N/A")
                    
            with cb_col2:
                st.markdown("**Back 9**")
                st.write(f"**Avg Score:** {tot_back:.2f}" if not pd.isna(tot_back) else "**Avg Score:** N/A")
                
                if not back_data.empty:
                    # Subtract par to get over/under numbers
                    b_over_par = back_data[hole_columns].mean().sub(pd.Series(BACK_PARS))
                    best_b = b_over_par.idxmin()
                    hardest_b = b_over_par.idxmax()
                    
                    # Format with explicit '+' for over par
                    best_b_str = f"+{b_over_par[best_b]:.2f}" if b_over_par[best_b] > 0 else f"{b_over_par[best_b]:.2f}"
                    hardest_b_str = f"+{b_over_par[hardest_b]:.2f}" if b_over_par[hardest_b] > 0 else f"{b_over_par[hardest_b]:.2f}"
                    
                    # Shift naming to map to actual Back 9 holes (Hole 10-18)
                    best_b_display = f"Hole {int(best_b.split(' ')[1]) + 9}"
                    hardest_b_display = f"Hole {int(hardest_b.split(' ')[1]) + 9}"
                    
                    st.write(f"**Best Hole:** {best_b_display} ({best_b_str})")
                    st.write(f"**Hardest Hole:** {hardest_b_display} ({hardest_b_str})")
                else:
                    st.write("**Best Hole:** N/A")
                    st.write("**Hardest Hole:** N/A")
            
        with col_split2:
            st.subheader("Recent Form (Last 5 Rounds)")
            recent_5 = player_data.head(5)[['Golf Date', 'Front/Back', 'Total']].copy()
            recent_5['Golf Date'] = recent_5['Golf Date'].dt.month.astype(str) + '/' + recent_5['Golf Date'].dt.day.astype(str) + '/' + recent_5['Golf Date'].dt.strftime('%y')
            st.dataframe(recent_5, use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # SCORING BREAKDOWN TABLE (PLAYER)
        st.subheader("Scoring Breakdown")
        breakdown_df = calculate_breakdown(player_data)
        if not breakdown_df.empty:
            st.dataframe(breakdown_df.drop(columns=['Golfer Name']), use_container_width=True, hide_index=True)
            
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
                s_date_str = f"{s_dt.month}/{s_dt.day}/{s_dt.strftime('%y')}"
                
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

        # Dynamic Scoring Trend
        st.subheader(f"{selected_player}'s Scoring Trend")
        chart_data = player_data.sort_values('Golf Date').copy()
        chart_data['Date Label'] = chart_data['Golf Date'].dt.month.astype(str) + '/' + chart_data['Golf Date'].dt.day.astype(str) + '/' + chart_data['Golf Date'].dt.strftime('%y')
        
        min_y = max(0, chart_data['Total'].min() - 3)
        max_y = chart_data['Total'].max() + 3
        
        line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X('Date Label', sort=None, title='Round Date'),
            y=alt.Y('Total', scale=alt.Scale(domain=[min_y, max_y]), title='Gross Score'),
            tooltip=['Date Label', 'Front/Back', 'Total']
        ).properties(height=400)
        
        st.altair_chart(line_chart, use_container_width=True, theme="streamlit")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- PLAYER ADVANCED ANALYTICS (BELOW SCORING TREND) ---
        col_pan1, col_pan2 = st.columns(2)
        
        with col_pan1:
            st.subheader("Par 3 vs 4 vs 5")
            par_tier_df = calculate_par_tier_performance(player_data)
            if not par_tier_df.empty:
                p_row = par_tier_df.iloc[0]
                p_chart_df = pd.DataFrame({
                    'Par Type': ['Par 3', 'Par 4', 'Par 5'],
                    'Score Over Par': [p_row['Par 3 Avg (+/-)'], p_row['Par 4 Avg (+/-)'], p_row['Par 5 Avg (+/-)']]
                })
                
                p_min, p_max = p_chart_df['Score Over Par'].min(), p_chart_df['Score Over Par'].max()
                p_domain = [max(0, p_min - 0.1), p_max + 0.3]
                
                base_p = alt.Chart(p_chart_df).encode(
                    x=alt.X('Par Type:N', sort=['Par 3', 'Par 4', 'Par 5'], title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('Score Over Par:Q', scale=alt.Scale(domain=p_domain, zero=False), title='Avg Over Par')
                )
                bars_p = base_p.mark_bar().encode(
                    color=alt.Color('Score Over Par:Q', legend=None, scale=alt.Scale(scheme='greens')),
                    tooltip=['Par Type', 'Score Over Par']
                )
                par_chart = bars_p.properties(height=300).configure_view(stroke=None)
                st.altair_chart(par_chart, use_container_width=True, theme="streamlit")
                
        with col_pan2:
            st.subheader("Score Dispersion (Frequency)")
            scores_list = player_data['Total'].dropna()
            if not scores_list.empty:
                disp_df = scores_list.value_counts().reset_index()
                disp_df.columns = ['Score', 'Frequency']
                disp_df = disp_df.sort_values('Score')
                disp_df['Score_Str'] = disp_df['Score'].astype(str)
                
                d_min, d_max = disp_df['Frequency'].min(), disp_df['Frequency'].max()
                d_domain = [0, d_max + 1.5]
                
                base_d = alt.Chart(disp_df).encode(
                    x=alt.X('Score_Str:N', sort=disp_df['Score_Str'].tolist(), title='Gross Score', axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('Frequency:Q', scale=alt.Scale(domain=d_domain, zero=True), title='Frequency', axis=alt.Axis(tickMinStep=1))
                )
                bars_d = base_d.mark_bar(width=35).encode(
                    color=alt.Color('Frequency:Q', legend=None, scale=alt.Scale(scheme='blues')),
                    tooltip=['Score', 'Frequency']
                )
                disp_chart = bars_d.properties(height=300).configure_view(stroke=None)
                st.altair_chart(disp_chart, use_container_width=True, theme="streamlit")
        
    else:
        st.warning(f"No primary roster scores found for {selected_player}.")

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
        
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        st.subheader("Members")
        st.dataframe(
            members_hcp, 
            use_container_width=True, 
            hide_index=True, 
            height=int((len(members_hcp) + 1) * 35 + 3)
        )
    with h_col2:
        st.subheader("Former Members")
        st.dataframe(
            former_members_hcp, 
            use_container_width=True, 
            hide_index=True, 
            height=int((len(former_members_hcp) + 1) * 35 + 3)
        )

    st.header("Player Profiles & Statistics")
    
    if not primary_scores.empty:
        lowest_rounds_dict = {}
        grouped = primary_scores.groupby('Golfer Name')
        for name, group in grouped:
            best_row = group.sort_values(by=['Total', 'Golf Date'], ascending=[True, False]).iloc[0]
            b_dt = best_row['Golf Date']
            lowest_rounds_dict[name] = f"{best_row['Total']} ({b_dt.month}/{b_dt.day}/{b_dt.strftime('%y')})"
            
        player_summary = grouped.agg(
            Rounds_Played=('Total', 'count'),
            Average_Score=('Total', 'mean'),
            Highest_Round=('Total', 'max')
        ).reset_index()
        
        player_summary.insert(3, 'Lowest_Round', player_summary['Golfer Name'].map(lowest_rounds_dict))
        player_summary['Average_Score'] = player_summary['Average_Score'].round(2)
        player_summary = player_summary.sort_values(by='Average_Score')
        
        st.subheader("Performance Overview")
        st.dataframe(player_summary, use_container_width=True, hide_index=True)

        st.subheader("Hole-by-Hole Scoring Averages (Relative to Par)")
        
        # Toggle button for Front 9 vs Back 9
        nine_selection = st.radio(
            "Select Nine:", 
            options=["Front 9", "Back 9"], 
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # Helper function to format the relative-to-par floats
        def format_relative(val):
            if pd.isna(val): return ""
            return f"+{val:.2f}" if val > 0 else f"{val:.2f}"
            
        # Filter the data and calculate metrics based on the toggle selection
        if nine_selection == "Front 9":
            side_scores = primary_scores[primary_scores['Front/Back'] == 'Front']
            hole_averages = side_scores.groupby('Golfer Name')[hole_columns].mean()
            
            # Subtract Par
            for col in hole_columns:
                hole_averages[col] = hole_averages[col] - FRONT_PARS[col]
            
            hole_averages = hole_averages.round(2).reset_index()
            
            # Rename columns to map Hole + Par
            new_cols = {'Golfer Name': 'Golfer Name'}
            for col in hole_columns:
                new_cols[col] = f"{col} | Par {FRONT_PARS[col]}"
            hole_averages = hole_averages.rename(columns=new_cols)
            
        else:
            side_scores = primary_scores[primary_scores['Front/Back'] == 'Back']
            hole_averages = side_scores.groupby('Golfer Name')[hole_columns].mean()
            
            # Subtract Par
            for col in hole_columns:
                hole_averages[col] = hole_averages[col] - BACK_PARS[col]
            
            hole_averages = hole_averages.round(2).reset_index()
            
            # Rename columns to map Hole (10-18) + Par
            new_cols = {'Golfer Name': 'Golfer Name'}
            for i, col in enumerate(hole_columns, start=1):
                new_cols[col] = f"Hole {i+9} | Par {BACK_PARS[col]}"
            hole_averages = hole_averages.rename(columns=new_cols)
            
        # Apply Heatmap styling (row-wise axis=1 to highlight a specific golfer's hardest holes)
        numeric_cols = [c for c in hole_averages.columns if c != 'Golfer Name']
        styled_averages = hole_averages.style.background_gradient(
            cmap='Reds', 
            axis=1, 
            subset=numeric_cols
        ).format(format_relative, subset=numeric_cols)
            
        st.dataframe(styled_averages, use_container_width=True, hide_index=True)
        
        # SCORING BREAKDOWN TABLE (LEAGUE)
        st.subheader("League Scoring Breakdown Summary")
        league_breakdown = calculate_breakdown(primary_scores).sort_values(by='Pars', ascending=False)
        st.dataframe(league_breakdown, use_container_width=True, hide_index=True)
        
        # --- PHASE 4: VISUALIZATIONS & TRENDS ---
        st.header("Visualizations & Trends")
        
        # Side-by-side Dynamic Over-Par Hole Difficulty Charts
        col1, col2 = st.columns(2)
        
        front_scores = primary_scores[primary_scores['Front/Back'] == 'Front']
        back_scores = primary_scores[primary_scores['Front/Back'] == 'Back']
        
        front_over_par = front_scores[hole_columns].mean().sub(pd.Series(FRONT_PARS)).round(2).reset_index()
        front_over_par.columns = ['Hole', 'Score Over Par']
        
        back_over_par = back_scores[hole_columns].mean().sub(pd.Series(BACK_PARS)).round(2).reset_index()
        back_over_par.columns = ['Hole', 'Score Over Par']
        
        f_min, f_max = front_over_par['Score Over Par'].min(), front_over_par['Score Over Par'].max()
        b_min, b_max = back_over_par['Score Over Par'].min(), back_over_par['Score Over Par'].max()
        
        front_domain = [max(0, f_min - 0.15), f_max + 0.2]
        back_domain = [max(0, b_min - 0.15), b_max + 0.2]
        
        hole_order = ['Hole 1', 'Hole 2', 'Hole 3', 'Hole 4', 'Hole 5', 'Hole 6', 'Hole 7', 'Hole 8', 'Hole 9']
        
        with col1:
            st.subheader("Front 9 Hole Difficulty (Over Par)")
            
            base_f = alt.Chart(front_over_par).encode(
                x=alt.X('Hole:N', sort=hole_order, title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y('Score Over Par:Q', scale=alt.Scale(domain=front_domain, zero=False), title='Score Over Par')
            )
            bars_f = base_f.mark_bar().encode(
                color=alt.Color('Score Over Par:Q', legend=None, scale=alt.Scale(scheme='blues')),
                tooltip=['Hole', 'Score Over Par']
            )
            front_chart = bars_f.properties(height=380).configure_view(stroke=None)
            st.altair_chart(front_chart, use_container_width=True, theme="streamlit")
            
        with col2:
            st.subheader("Back 9 Hole Difficulty (Over Par)")
            
            base_b = alt.Chart(back_over_par).encode(
                x=alt.X('Hole:N', sort=hole_order, title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y('Score Over Par:Q', scale=alt.Scale(domain=back_domain, zero=False), title='Score Over Par')
            )
            bars_b = base_b.mark_bar().encode(
                color=alt.Color('Score Over Par:Q', legend=None, scale=alt.Scale(scheme='oranges')),
                tooltip=['Hole', 'Score Over Par']
            )
            back_chart = bars_b.properties(height=380).configure_view(stroke=None)
            st.altair_chart(back_chart, use_container_width=True, theme="streamlit")
            
        st.markdown("<br>", unsafe_allow_html=True)
            
        # League Score Distribution in between
        st.subheader("League Score Distribution")
        score_dist = primary_scores['Total'].value_counts().sort_index()
        st.bar_chart(score_dist)
        
        st.markdown("<br>", unsafe_allow_html=True)
            
        # League Scoring Trend at the top/middle, moving analytics below it
        st.subheader("League Scoring Trend (Daily Average)")
        trend_data = primary_scores.groupby('Golf Date')['Total'].mean().reset_index()
        trend_data['Date Label'] = trend_data['Golf Date'].dt.month.astype(str) + '/' + trend_data['Golf Date'].dt.day.astype(str) + '/' + trend_data['Golf Date'].dt.strftime('%y')
        
        min_y = max(0, trend_data['Total'].min() - 3)
        max_y = trend_data['Total'].max() + 3
        
        league_chart = alt.Chart(trend_data).mark_line(point=True).encode(
            x=alt.X('Date Label', sort=None, title='Round Date'),
            y=alt.Y('Total', scale=alt.Scale(domain=[min_y, max_y], zero=False), title='Average Gross Score'),
            tooltip=['Date Label', 'Total']
        ).properties(height=400)
        
        st.altair_chart(league_chart, use_container_width=True, theme="streamlit")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- ADVANCED LEAGUE ANALYTICS (BELOW SCORING TREND) ---
        st.header("Advanced League Analytics")
        
        col_an1, col_an2 = st.columns(2)
        
        with col_an1:
            st.subheader("Par Performance Breakdown (Avg Relative to Par)")
            par_tier_league = calculate_par_tier_performance(primary_scores)
            st.dataframe(par_tier_league, use_container_width=True, hide_index=True)
            
        with col_an2:
            st.subheader("Scoring Consistency & Volatility Index")
            volatility_league = calculate_volatility(primary_scores)
            st.dataframe(volatility_league, use_container_width=True, hide_index=True)

    else:
        st.warning("No data available.")
