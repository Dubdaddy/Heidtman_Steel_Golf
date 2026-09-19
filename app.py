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

# Show a sample of the data to verify it works
st.subheader("Raw Data View")
st.dataframe(filtered_df.head(15))

# --- PHASE 2: CORE METRICS & ANALYTICS ---
st.header("Player Profiles & Statistics")

# Exclude substitute rounds to maintain accurate personal statistics
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
