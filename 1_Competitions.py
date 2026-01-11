# pages/1_Competitions.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

from db_config import DatabaseConfig

st.set_page_config(
    page_title="Competitions Analysis",
    layout="wide"
)


@st.cache_resource
def get_db_connection():
    conn_string = DatabaseConfig.get_connection_string()
    try:
        DatabaseConfig.ensure_database_exists()
        engine = create_engine(conn_string)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except Exception:
        st.error("Unable to connect to the database. Check your credentials and server state.")
        st.stop()


engine = get_db_connection()


def run_sql_query(query: str, params=None, engine_obj=engine) -> pd.DataFrame:
    if engine_obj is None:
        return pd.DataFrame()
    try:
        with engine_obj.connect() as connection:
            result = connection.execute(text(query), params or {})
            rows = result.fetchall()
            return pd.DataFrame(rows, columns=result.keys())
    except Exception as exc:
        st.error(f"Error executing query: {exc}")
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_competitions() -> pd.DataFrame:
    return run_sql_query(
        """
        SELECT c.competition_id,
               c.competition_name,
               c.parent_id,
               p.competition_name AS parent_name,
               c.type,
               c.gender,
               c.level,
               cat.category_name
        FROM competitions c
        LEFT JOIN competitions p ON p.competition_id = c.parent_id
        LEFT JOIN categories cat ON cat.category_id = c.category_id;
        """
    )


competitions_df = load_competitions()

st.title("📊 Competition Intelligence Studio")
st.markdown("Slice the global tennis competition ecosystem with multi-layered filters and interactive visuals.")


if competitions_df.empty:
    st.warning("No competitions are currently stored. Load data via the data loader to explore this page.")
    st.stop()


with st.expander("Filters", expanded=True):
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    category_options = sorted([option for option in competitions_df["category_name"].dropna().unique()])
    type_options = sorted([option for option in competitions_df["type"].dropna().unique()])
    gender_options = sorted([option for option in competitions_df["gender"].dropna().unique()])
    level_options = sorted([option for option in competitions_df["level"].dropna().unique()])

    selected_categories = filter_col1.multiselect(
        "Categories",
        options=category_options,
        default=category_options,
        help="Filter by governing body or geography."
    ) if category_options else []

    selected_types = filter_col2.multiselect(
        "Competition Types",
        options=type_options,
        default=type_options,
        help="Select formats such as tours, qualifiers, cups."
    ) if type_options else []

    selected_genders = filter_col3.multiselect(
        "Gender Divisions",
        options=gender_options,
        default=gender_options,
        help="Include men's, women's, or mixed draws."
    ) if gender_options else []

    selected_levels = filter_col4.multiselect(
        "Level Tags",
        options=level_options,
        default=level_options,
        help="Highlight tiers like ATP 250 or WTA 1000."
    ) if level_options else []

    parent_filter = st.radio(
        "Hierarchy Focus",
        options=["All", "Top Level", "Sub-competition"],
        horizontal=True,
        help="Focus on competitions with or without parents."
    )


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    filtered = data.copy()
    if selected_categories:
        filtered = filtered[filtered["category_name"].isin(selected_categories)]
    if selected_types:
        filtered = filtered[filtered["type"].isin(selected_types)]
    if selected_genders:
        filtered = filtered[filtered["gender"].isin(selected_genders)]
    if selected_levels:
        filtered = filtered[filtered["level"].isin(selected_levels)]
    if parent_filter == "Top Level":
        filtered = filtered[filtered["parent_id"].isna()]
    elif parent_filter == "Sub-competition":
        filtered = filtered[filtered["parent_id"].notna()]
    return filtered


filtered_competitions = apply_filters(competitions_df)


summary_col1, summary_col2, summary_col3 = st.columns(3)

with summary_col1:
    st.metric("Competitions in Scope", int(filtered_competitions["competition_id"].nunique()))

with summary_col2:
    top_category = (
        filtered_competitions.groupby("category_name", dropna=False)["competition_id"].nunique()
        .reset_index()
        .sort_values("competition_id", ascending=False)
        .head(1)
    )
    if not top_category.empty:
        st.metric("Leading Category", f"{top_category.iloc[0]['category_name']} ({int(top_category.iloc[0]['competition_id'])})")
    else:
        st.metric("Leading Category", "N/A")

with summary_col3:
    sub_ratio = (
        filtered_competitions["parent_id"].notna().sum(),
        len(filtered_competitions)
    )
    sub_percentage = (sub_ratio[0] / sub_ratio[1] * 100) if sub_ratio[1] else 0
    st.metric("Sub-competition Share", f"{sub_percentage:.1f}%")

st.markdown("---")

tab_overview, tab_hierarchy, tab_table = st.tabs([
    "Category & Format View",
    "Hierarchy Analytics",
    "Curated Table"
])


with tab_overview:
    col1, col2 = st.columns((3, 2))

    if not filtered_competitions.empty:
        category_summary = (
            filtered_competitions.groupby("category_name", dropna=False)["competition_id"].nunique()
            .reset_index(name="competitions")
            .sort_values("competitions", ascending=False)
        )
        fig_category = px.bar(
            category_summary,
            x="competitions",
            y="category_name",
            orientation="h",
            color="competitions",
            color_continuous_scale="Rocket",
            title="Competitions by Category"
        )
        fig_category.update_layout(xaxis_title="Competitions", yaxis_title="Category")
        col1.plotly_chart(fig_category, use_container_width=True)

        type_gender_summary = (
            filtered_competitions.groupby(["type", "gender"], dropna=False)["competition_id"].nunique()
            .reset_index(name="competitions")
        )
        fig_type_gender = px.bar(
            type_gender_summary,
            x="type",
            y="competitions",
            color="gender",
            barmode="group",
            title="Format Split by Gender"
        )
        fig_type_gender.update_layout(xaxis_title="Competition Type", yaxis_title="Competitions")
        col2.plotly_chart(fig_type_gender, use_container_width=True)

        st.markdown("### Level Heatmap")
        level_gender_heatmap = (
            filtered_competitions.groupby(["level", "gender"], dropna=False)["competition_id"].nunique()
            .reset_index(name="competitions")
        )
        level_gender_heatmap["level"].fillna("Unspecified", inplace=True)
        fig_heatmap = px.density_heatmap(
            level_gender_heatmap,
            x="gender",
            y="level",
            z="competitions",
            color_continuous_scale="Viridis",
            title="Competition Density Across Levels"
        )
        fig_heatmap.update_layout(xaxis_title="Gender", yaxis_title="Level")
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.info("No competitions satisfy the selected filters.")


with tab_hierarchy:
    if not filtered_competitions.empty:
        hierarchy_df = filtered_competitions.copy()
        hierarchy_df["category_name"].fillna("Unassigned", inplace=True)
        hierarchy_df["level"].fillna("Unspecified", inplace=True)
        fig_sunburst = px.sunburst(
            hierarchy_df,
            path=["category_name", "parent_name", "competition_name"],
            values="competition_id",
            title="Competition Hierarchy Explorer",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_sunburst, use_container_width=True)

        chain_df = hierarchy_df[hierarchy_df["parent_id"].notna()][[
            "parent_name",
            "competition_name",
            "type",
            "gender",
            "level"
        ]].rename(columns={
            "parent_name": "Parent Competition",
            "competition_name": "Child Competition",
            "type": "Type",
            "gender": "Gender",
            "level": "Level"
        })

        st.markdown("### Parent-Child Chains")
        if not chain_df.empty:
            st.dataframe(chain_df.sort_values("Parent Competition"), use_container_width=True)
        else:
            st.info("No sub-competition relationships within the current filters.")
    else:
        st.info("Expand your filters to analyse hierarchies.")


with tab_table:
    st.markdown("### Filtered Competition Catalogue")
    presentation_df = filtered_competitions[[
        "competition_name",
        "category_name",
        "parent_name",
        "type",
        "gender",
        "level"
    ]].rename(columns={
        "competition_name": "Competition",
        "category_name": "Category",
        "parent_name": "Parent",
        "type": "Type",
        "gender": "Gender",
        "level": "Level"
    }).sort_values("Competition")
    st.dataframe(presentation_df, use_container_width=True)

    csv_buffer = presentation_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download as CSV",
        data=csv_buffer,
        file_name="competitions_filtered.csv",
        mime="text/csv"
    )