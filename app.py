import streamlit as st
import pandas as pd

# Set page configuration for the dashboard
st.set_page_config(page_title="Heidtman Steel Golf League", layout="wide")

# --- DATA INGESTION ---
# Streamlit caches this so it doesn't reload the Excel file on every click
@st.cache_data
def load_data():
    # Read the main historical scores sheet
    df = pd.read_excel('Golf League Data.xlsx', sheet_name='Historical Scores')
    
    # Convert 'Golf Date' to proper datetime format
    df['Golf Date'] = pd.to_datetime(df['Golf Date'])
    
    # Extract the Year for easy filtering later
    df['Year'] = df['Golf Date'].dt.year
    
    # Optional: Filter out sub scores if you only want main roster stats
    # df_roster = df[df['Had Sub?'] == 'No']
    
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
