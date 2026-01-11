# pages/3_Competitor_Rankings.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

from db_config import DatabaseConfig

st.set_page_config(
    page_title="Competitor Rankings Analysis",
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
def load_rankings_dataset() -> pd.DataFrame:
    return run_sql_query(
        """
        SELECT cr.rank,
               cr.movement,
               cr.points,
               cr.competitions_played,
               c.competitor_id,
               c.name AS competitor_name,
               c.country,
               c.country_code,
               c.abbreviation
        FROM competitor_rankings cr
        JOIN competitors c ON c.competitor_id = cr.competitor_id;
        """
    )


dataset = load_rankings_dataset()

st.title("🏆 Rankings Performance Studio")
st.markdown("Discover ranking momentum, country strength, and player form with interactive leaderboards.")


if dataset.empty:
    st.warning("No ranking records available. Load competitor rankings data to explore insights.")
    st.stop()


with st.expander("Filters & Search", expanded=True):
    name_search = st.text_input(
        "Search Athlete",
        value="",
        help="Type part of a competitor's name to narrow the view."
    )

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    country_options = sorted([option for option in dataset["country"].dropna().unique()])
    selected_countries = filter_col1.multiselect(
        "Countries",
        options=country_options,
        default=country_options,
        help="Focus on selected national programs."
    ) if country_options else []

    min_rank = int(dataset["rank"].min())
    max_rank = int(dataset["rank"].max())
    rank_range = filter_col2.slider(
        "Rank Range",
        min_value=min_rank,
        max_value=max_rank,
        value=(min_rank, min(max_rank, min_rank + 99)),
        help="Slice the ranking list to a window of interest."
    ) if min_rank < max_rank else (min_rank, max_rank)

    min_points = int(dataset["points"].min())
    max_points = int(dataset["points"].max())
    points_range = filter_col3.slider(
        "Points Range",
        min_value=min_points,
        max_value=max_points,
        value=(min_points, max_points),
        help="Limit the analysis to specific point totals."
    ) if min_points < max_points else (min_points, max_points)

    filter_col4, filter_col5 = st.columns(2)

    movement_min = int(dataset["movement"].min())
    movement_max = int(dataset["movement"].max())
    movement_range = filter_col4.slider(
        "Movement Range",
        min_value=movement_min,
        max_value=movement_max,
        value=(movement_min, movement_max),
        help="Focus on risers, fallers, or steady performers."
    ) if movement_min < movement_max else (movement_min, movement_max)

    competitions_min = int(dataset["competitions_played"].min())
    competitions_max = int(dataset["competitions_played"].max())
    competitions_range = filter_col5.slider(
        "Competitions Played",
        min_value=competitions_min,
        max_value=competitions_max,
        value=(competitions_min, competitions_max),
        help="Filter by season workload."
    ) if competitions_min < competitions_max else (competitions_min, competitions_max)

    line_col1, line_col2 = st.columns(2)
    trajectory_metric = line_col1.selectbox(
        "Trajectory Metric",
        options=[
            ("points", "Points"),
            ("movement", "Movement"),
            ("competitions_played", "Competitions Played")
        ],
        format_func=lambda pair: pair[1],
        help="Choose which measure to plot along the ranking curve."
    )[0]

    max_line_candidates = int(dataset["rank"].nunique())
    default_line_limit = min(25, max_line_candidates)
    if max_line_candidates > 1:
        trajectory_limit = line_col2.slider(
            "Top Ranks to Plot",
            min_value=5 if max_line_candidates >= 5 else max_line_candidates,
            max_value=max_line_candidates,
            value=default_line_limit,
            help="Controls the number of ranked competitors shown in the trajectory line chart."
        )
    else:
        trajectory_limit = max_line_candidates


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    filtered = data.copy()
    if name_search:
        filtered = filtered[filtered["competitor_name"].str.contains(name_search, case=False, na=False)]
    if selected_countries:
        filtered = filtered[filtered["country"].isin(selected_countries)]
    filtered = filtered[
        (filtered["rank"] >= rank_range[0]) &
        (filtered["rank"] <= rank_range[1]) &
        (filtered["points"] >= points_range[0]) &
        (filtered["points"] <= points_range[1]) &
        (filtered["movement"] >= movement_range[0]) &
        (filtered["movement"] <= movement_range[1]) &
        (filtered["competitions_played"] >= competitions_range[0]) &
        (filtered["competitions_played"] <= competitions_range[1])
    ]
    return filtered


filtered_dataset = apply_filters(dataset)


metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric("Competitors in Scope", int(filtered_dataset["competitor_id"].nunique()))

with metric_col2:
    avg_points = filtered_dataset["points"].mean() if not filtered_dataset.empty else 0
    st.metric("Average Points", f"{avg_points:,.0f}")

with metric_col3:
    median_movement = filtered_dataset["movement"].median() if not filtered_dataset.empty else 0
    st.metric("Median Movement", f"{median_movement:+.0f}")

with metric_col4:
    workload = filtered_dataset["competitions_played"].mean() if not filtered_dataset.empty else 0
    st.metric("Avg Competitions Played", f"{workload:.1f}")

st.markdown("---")

if filtered_dataset.empty:
    st.info("No competitors match the current filters. Adjust the selections to reveal insights.")
    st.stop()


tab_overview, tab_country, tab_momentum, tab_profiles = st.tabs([
    "Overview",
    "Country Insights",
    "Momentum Watch",
    "Player Profiles"
])


with tab_overview:
    col_overview_left, col_overview_right = st.columns((3, 2))

    scatter_fig = px.scatter(
        filtered_dataset,
        x="rank",
        y="points",
        color="country",
        hover_data=["competitor_name", "movement", "competitions_played"],
        color_discrete_sequence=px.colors.qualitative.Safe,
        title="Points vs Rank by Country"
    )
    scatter_fig.update_layout(xaxis_title="Rank", yaxis_title="Points")
    col_overview_left.plotly_chart(scatter_fig, use_container_width=True)

    points_hist = px.histogram(
        filtered_dataset,
        x="points",
        nbins=30,
        color="country",
        title="Points Distribution"
    )
    points_hist.update_layout(barmode="overlay", xaxis_title="Points", yaxis_title="Competitors")
    col_overview_right.plotly_chart(points_hist, use_container_width=True)

    st.markdown("### Workload Breakdown")
    workload_fig = px.box(
        filtered_dataset,
        x="country",
        y="competitions_played",
        color="country",
        title="Competitions Played per Country"
    )
    workload_fig.update_layout(xaxis_title="Country", yaxis_title="Competitions Played")
    st.plotly_chart(workload_fig, use_container_width=True)

    st.markdown("### Ranking Trajectory")
    trajectory_df = filtered_dataset.sort_values("rank").head(trajectory_limit).copy()
    if not trajectory_df.empty and trajectory_limit > 0:
        trajectory_df["label"] = trajectory_df["competitor_name"] + " (" + trajectory_df["country"].fillna("-") + ")"
        line_fig = px.line(
            trajectory_df,
            x="rank",
            y=trajectory_metric,
            color="label",
            markers=True,
            title="Top Ranking Trajectory",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        metric_label = {
            "points": "Points",
            "movement": "Movement",
            "competitions_played": "Competitions Played"
        }[trajectory_metric]
        line_fig.update_layout(
            xaxis_title="Rank",
            yaxis_title=metric_label,
            legend_title="Competitor",
            xaxis_autorange="reversed"
        )
        st.plotly_chart(line_fig, use_container_width=True)
    else:
        st.info("Not enough competitors in scope to draw a ranking trajectory.")


with tab_country:
    country_summary = (
        filtered_dataset.groupby(["country", "country_code"], dropna=False)
        .agg(
            competitors=("competitor_id", "nunique"),
            avg_points=("points", "mean")
        )
        .reset_index()
        .sort_values("competitors", ascending=False)
    )

    if not country_summary.empty:
        col_country_left, col_country_right = st.columns((2, 3))

        bar_country = px.bar(
            country_summary,
            x="competitors",
            y="country",
            orientation="h",
            color="avg_points",
            color_continuous_scale="Viridis",
            title="Competitors per Country"
        )
        bar_country.update_layout(xaxis_title="Competitors", yaxis_title="Country")
        col_country_left.plotly_chart(bar_country, use_container_width=True)

        map_country = px.choropleth(
            country_summary,
            locations="country_code",
            color="competitors",
            hover_name="country",
            color_continuous_scale="YlOrRd",
            title="Global Ranking Presence"
        )
        map_country.update_geos(showcoastlines=True, projection_type="natural earth")
        col_country_right.plotly_chart(map_country, use_container_width=True)

        st.markdown("### Country Detail Table")
        detail_table = country_summary.copy()
        detail_table["avg_points"] = detail_table["avg_points"].round(1)
        st.dataframe(detail_table.rename(columns={
            "country": "Country",
            "competitors": "Competitors",
            "avg_points": "Avg Points"
        }), use_container_width=True)
    else:
        st.info("Country aggregation requires competitors in scope.")


with tab_momentum:
    col_momentum_left, col_momentum_right = st.columns(2)

    top_risers = filtered_dataset.sort_values("movement", ascending=False).head(10)
    top_decliners = filtered_dataset.sort_values("movement", ascending=True).head(10)

    if not top_risers.empty:
        fig_risers = px.bar(
            top_risers,
            x="movement",
            y="competitor_name",
            orientation="h",
            color="country",
            title="Top Ranking Risers"
        )
        fig_risers.update_layout(xaxis_title="Movement", yaxis_title="Competitor")
        col_momentum_left.plotly_chart(fig_risers, use_container_width=True)
        col_momentum_left.dataframe(
            top_risers[["competitor_name", "country", "rank", "movement", "points"]],
            use_container_width=True
        )
    else:
        col_momentum_left.info("No positive movement within the filter range.")

    if not top_decliners.empty:
        fig_decliners = px.bar(
            top_decliners,
            x="movement",
            y="competitor_name",
            orientation="h",
            color="country",
            title="Top Ranking Drops"
        )
        fig_decliners.update_layout(xaxis_title="Movement", yaxis_title="Competitor")
        col_momentum_right.plotly_chart(fig_decliners, use_container_width=True)
        col_momentum_right.dataframe(
            top_decliners[["competitor_name", "country", "rank", "movement", "points"]],
            use_container_width=True
        )
    else:
        col_momentum_right.info("No negative movement within the filter range.")


with tab_profiles:
    st.markdown("### Player Lens")
    competitor_options = sorted(filtered_dataset["competitor_name"].unique())
    selected_competitor = st.selectbox(
        "Select Competitor",
        options=competitor_options,
        help="Focus the details section on a single athlete."
    )

    profile = filtered_dataset[filtered_dataset["competitor_name"] == selected_competitor]
    if not profile.empty:
        profile_row = profile.iloc[0]
        detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)
        detail_col1.metric("Rank", int(profile_row["rank"]))
        detail_col2.metric("Points", int(profile_row["points"]))
        detail_col3.metric("Movement", f"{int(profile_row['movement']):+d}")
        detail_col4.metric("Events Played", int(profile_row["competitions_played"]))

        st.markdown("#### Comparable Competitors")
        comparable = filtered_dataset[
            (filtered_dataset["competitor_name"] != selected_competitor) &
            (filtered_dataset["rank"].between(profile_row["rank"] - 5, profile_row["rank"] + 5))
        ].nsmallest(10, "rank")
        if not comparable.empty:
            st.dataframe(
                comparable[[
                    "competitor_name",
                    "country",
                    "rank",
                    "points",
                    "movement",
                    "competitions_played"
                ]],
                use_container_width=True
            )
        else:
            st.info("No peers found in the surrounding ranking window.")
    else:
        st.info("The selected competitor is outside the current filter scope.")

    st.markdown("### Export Current Leaderboard")
    export_df = filtered_dataset[[
        "competitor_name",
        "country",
        "rank",
        "points",
        "movement",
        "competitions_played"
    ]].sort_values("rank")
    csv_blob = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Rankings CSV",
        data=csv_blob,
        file_name="rankings_filtered.csv",
        mime="text/csv"
    )