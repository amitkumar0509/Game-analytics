# pages/2_Complexes_Venues.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
# pages/2_Complexes_Venues.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

from db_config import DatabaseConfig

st.set_page_config(
    page_title="Complexes & Venues Analysis",
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
def load_complexes_and_venues() -> pd.DataFrame:
    return run_sql_query(
        """
        SELECT c.complex_id,
               c.complex_name,
               v.venue_id,
               v.venue_name,
               v.city_name,
               v.country_name,
               v.country_code,
               v.timezone
        FROM complexes c
        LEFT JOIN venues v ON v.complex_id = c.complex_id;
        """
    )


dataset = load_complexes_and_venues()

st.title("🏟️ Venue Network Command Center")
st.markdown("Inspect venue footprints, timezone coverage, and complex utilization with interactive visuals.")


if dataset.empty:
    st.warning("No venue data is available. Run the data loader to populate complexes and venues.")
    st.stop()


with st.expander("Filters", expanded=True):
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    country_options = sorted([option for option in dataset["country_name"].dropna().unique()])
    timezone_options = sorted([option for option in dataset["timezone"].dropna().unique()])
    complex_options = sorted([option for option in dataset["complex_name"].dropna().unique()])

    selected_countries = filter_col1.multiselect(
        "Countries",
        options=country_options,
        default=country_options,
        help="Limit analytics to specific host nations."
    ) if country_options else []

    selected_timezones = filter_col2.multiselect(
        "Timezones",
        options=timezone_options,
        default=timezone_options,
        help="Focus on the timezones where tournaments are held."
    ) if timezone_options else []

    selected_complexes = filter_col3.multiselect(
        "Complexes",
        options=complex_options,
        default=complex_options,
        help="Zoom into selected facilities."
    ) if complex_options else []


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    filtered = data.copy()
    if selected_countries:
        filtered = filtered[filtered["country_name"].isin(selected_countries)]
    if selected_timezones:
        filtered = filtered[filtered["timezone"].isin(selected_timezones)]
    if selected_complexes:
        filtered = filtered[filtered["complex_name"].isin(selected_complexes)]
    return filtered


filtered_dataset = apply_filters(dataset)


metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    st.metric("Complexes", int(filtered_dataset["complex_id"].nunique()))

with metric_col2:
    st.metric("Venues", int(filtered_dataset["venue_id"].nunique()))

with metric_col3:
    venues_per_complex = (
        filtered_dataset.groupby("complex_id")["venue_id"].nunique().reset_index(drop=True)
    )
    avg_venues = venues_per_complex.mean() if not venues_per_complex.empty else 0
    st.metric("Avg Venues per Complex", f"{avg_venues:.1f}")

st.markdown("---")

tab_overview, tab_complex, tab_geo = st.tabs([
    "Network Overview",
    "Complex Spotlight",
    "Geographic Coverage"
])


with tab_overview:
    col1, col2 = st.columns((3, 2))

    venue_country_summary = (
        filtered_dataset.groupby(["country_name", "country_code"], dropna=False)["venue_id"].nunique()
        .reset_index(name="venues")
        .sort_values("venues", ascending=False)
    )

    if not venue_country_summary.empty:
        fig_country = px.bar(
            venue_country_summary.head(15),
            x="venues",
            y="country_name",
            orientation="h",
            color="venues",
            color_continuous_scale="Cividis",
            title="Venues by Country"
        )
        fig_country.update_layout(xaxis_title="Venues", yaxis_title="Country")
        col1.plotly_chart(fig_country, use_container_width=True)
    else:
        col1.info("No venues match the selected filters.")

    timezone_summary = (
        filtered_dataset.groupby("timezone", dropna=False)["venue_id"].nunique()
        .reset_index(name="venues")
        .sort_values("venues", ascending=False)
    )

    if not timezone_summary.empty:
        fig_timezone = px.bar(
            timezone_summary.head(15),
            x="venues",
            y="timezone",
            orientation="h",
            color="venues",
            color_continuous_scale="Magma",
            title="Venues by Timezone"
        )
        fig_timezone.update_layout(xaxis_title="Venues", yaxis_title="Timezone")
        col2.plotly_chart(fig_timezone, use_container_width=True)
    else:
        col2.info("No timezone data in scope.")

    st.markdown("### Venue Composition by Complex")
    complex_tree = filtered_dataset.copy()
    complex_tree["country_name"].fillna("Unspecified", inplace=True)
    complex_tree["venue_name"].fillna("Unnamed Venue", inplace=True)
    fig_tree = px.treemap(
        complex_tree,
        path=["country_name", "complex_name", "venue_name"],
        values="venue_id",
        title="Drilldown of Venues by Complex"
    )
    st.plotly_chart(fig_tree, use_container_width=True)


with tab_complex:
    spotlight_col1, spotlight_col2 = st.columns((2, 3))

    complex_picker_options = sorted(
        filtered_dataset["complex_name"].dropna().unique() if not filtered_dataset.empty else []
    )
    selected_complex = spotlight_col1.selectbox(
        "Select Complex",
        options=["Show All"] + complex_picker_options,
        help="Choose a complex to inspect its venues and distribution."
    )

    if selected_complex != "Show All":
        complex_subset = filtered_dataset[filtered_dataset["complex_name"] == selected_complex]
    else:
        complex_subset = filtered_dataset

    spotlight_col1.metric(
        "Venues in Selection",
        int(complex_subset["venue_id"].nunique())
    )
    spotlight_col1.metric(
        "Countries Represented",
        int(complex_subset["country_name"].nunique())
    )

    venue_table = complex_subset[[
        "venue_name",
        "city_name",
        "country_name",
        "timezone"
    ]].rename(columns={
        "venue_name": "Venue",
        "city_name": "City",
        "country_name": "Country",
        "timezone": "Timezone"
    }).sort_values("Venue")

    st.dataframe(venue_table, use_container_width=True)

    if not complex_subset.empty:
        venues_per_complex_chart = (
            complex_subset.groupby("complex_name")["venue_id"].nunique().reset_index(name="venues")
        )
        fig_complex_bar = px.bar(
            venues_per_complex_chart,
            x="complex_name",
            y="venues",
            color="venues",
            color_continuous_scale="Sunset",
            title="Venue Count per Complex"
        )
        fig_complex_bar.update_layout(
            xaxis_title="Complex",
            yaxis_title="Venues",
            xaxis_tickangle=-45
        )
        spotlight_col2.plotly_chart(fig_complex_bar, use_container_width=True)
    else:
        spotlight_col2.info("No venues in the current selection.")


with tab_geo:
    if not venue_country_summary.empty:
        fig_map = px.choropleth(
            venue_country_summary,
            locations="country_code",
            color="venues",
            hover_name="country_name",
            color_continuous_scale="Bluered",
            title="Global Venue Footprint"
        )
        fig_map.update_geos(showcoastlines=True, projection_type="natural earth")
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No geographic data after applying filters.")

    st.markdown("### Export Current View")
    export_df = filtered_dataset[[
        "complex_name",
        "venue_name",
        "city_name",
        "country_name",
        "timezone"
    ]].rename(columns={
        "complex_name": "Complex",
        "venue_name": "Venue",
        "city_name": "City",
        "country_name": "Country",
        "timezone": "Timezone"
    }).sort_values(["Country", "Complex", "Venue"])
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Venues CSV",
        data=csv_data,
        file_name="venues_filtered.csv",
        mime="text/csv"
    )