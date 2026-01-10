# Home.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from db_config import DatabaseConfig

st.set_page_config(
    page_title="SportRadar Tennis Explorer - Home",
    layout="wide"
)

# --- Database Connection ---
@st.cache_resource
def get_db_connection():
    """Establishes and caches the database connection. Displays error if connection fails."""
    conn_string = DatabaseConfig.get_connection_string()
    try:
        engine = create_engine(conn_string)
        # Test connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        st.success("Successfully connected to the database!")
        return engine
    except Exception as e:
        st.error(f"Failed to connect to the database. Please check your .env file and ensure the PostgreSQL server is running. Error: {e}")
        st.stop() # Stop the app if DB connection fails
    return None

engine = get_db_connection()

# --- Function to run SQL queries ---
def run_sql_query(query: str, engine_obj=engine) -> pd.DataFrame:
    """Executes an SQL query and returns results as a Pandas DataFrame. Displays errors."""
    if engine_obj is None:
        return pd.DataFrame() # Return empty DataFrame if engine is not initialized
    try:
        with engine_obj.connect() as connection:
            result = connection.execute(text(query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return pd.DataFrame()

# --- Homepage Dashboard ---
st.title("🎾 SportRadar Tennis Event Explorer - Dashboard")
st.markdown("A comprehensive tool for managing, visualizing, and analyzing tennis competition data.")
st.markdown("---")

st.header("Key Insights: At a Glance")

col1, col2, col3 = st.columns(3)

with col1:
    total_competitors_df = run_sql_query("SELECT COUNT(competitor_id) FROM competitors;")
    if not total_competitors_df.empty:
        st.metric("Total Competitors", total_competitors_df.iloc[0, 0])
    else:
        st.metric("Total Competitors", "N/A")

with col2:
    num_countries_represented_df = run_sql_query("SELECT COUNT(DISTINCT country) FROM competitors;")
    if not num_countries_represented_df.empty:
        st.metric("Countries Represented", num_countries_represented_df.iloc[0, 0])
    else:
        st.metric("Countries Represented", "N/A")


with col3:
    highest_points_competitor_data_df = run_sql_query("SELECT c.name, cr.points FROM competitor_rankings cr JOIN competitors c ON cr.competitor_id = c.competitor_id ORDER BY cr.points DESC LIMIT 1;")
    if not highest_points_competitor_data_df.empty:
        highest_points = highest_points_competitor_data_df.iloc[0]['points']
        highest_points_name = highest_points_competitor_data_df.iloc[0]['name']
        st.metric("Highest Points Scored", f"{highest_points} ({highest_points_name})")
    else:
        st.metric("Highest Points Scored", "N/A")

st.markdown("---")

st.info("Use the sidebar navigation to explore Competitions, Complexes & Venues, and Competitor Rankings in more detail.")

# --- Additional summary ---
st.subheader("General Data Overview")
col_overview_1, col_overview_2, col_overview_3 = st.columns(3)

with col_overview_1:
    total_competitions_df = run_sql_query("SELECT COUNT(DISTINCT competition_id) FROM competitions;")
    if not total_competitions_df.empty:
        st.metric("Total Competitions", total_competitions_df.iloc[0, 0])
    else:
        st.metric("Total Competitions", "N/A")

with col_overview_2:
    total_venues_df = run_sql_query("SELECT COUNT(DISTINCT venue_id) FROM venues;")
    if not total_venues_df.empty:
        st.metric("Total Venues", total_venues_df.iloc[0, 0])
    else:
        st.metric("Total Venues", "N/A")

with col_overview_3:
    total_complexes_df = run_sql_query("SELECT COUNT(DISTINCT complex_id) FROM complexes;")
    if not total_complexes_df.empty:
        st.metric("Total Complexes", total_complexes_df.iloc[0, 0])
    else:
        st.metric("Total Complexes", "N/A")