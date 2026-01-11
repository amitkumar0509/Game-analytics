# Home.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sqlalchemy import create_engine, text

from db_config import DatabaseConfig

st.set_page_config(
    page_title="SportRadar Tennis Explorer - Home",
    layout="wide"
)


@st.cache_resource
def get_db_connection():
    """Build and cache the SQLAlchemy engine."""
    conn_string = DatabaseConfig.get_connection_string()
    try:
        DatabaseConfig.ensure_database_exists()
        engine = create_engine(conn_string)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except Exception as exc:
        st.error(
            "Failed to connect to the database. Please verify your .env settings and ensure the "
            f"{DatabaseConfig.DB_TYPE.upper()} server is accepting connections. Error: {exc}"
        )
        st.stop()


engine = get_db_connection()


def run_sql_query(query: str, params: dict | None = None, engine_obj=engine) -> pd.DataFrame:
    """Execute SQL and return a DataFrame."""
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
def load_competitions_dataset() -> pd.DataFrame:
    return run_sql_query(
        """
        SELECT c.competition_id,
               c.competition_name,
               c.parent_id,
               c.type,
               c.gender,
               c.level,
               cat.category_name
        FROM competitions c
        LEFT JOIN categories cat ON cat.category_id = c.category_id;
        """
    )


@st.cache_data(show_spinner=False)
def load_competitor_rankings_dataset() -> pd.DataFrame:
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


@st.cache_data(show_spinner=False)
def load_venues_dataset() -> pd.DataFrame:
    return run_sql_query(
        """
        SELECT v.venue_id,
               v.venue_name,
               v.city_name,
               v.country_name,
               v.country_code,
               v.timezone,
               c.complex_name,
               c.complex_id
        FROM venues v
        LEFT JOIN complexes c ON c.complex_id = v.complex_id;
        """
    )


competitions_df = load_competitions_dataset()
rankings_df = load_competitor_rankings_dataset()
venues_df = load_venues_dataset()

st.title("🎾 Tennis Intelligence Hub")
st.markdown("Dive into global tennis activity with real-time competition coverage, venue insights, and rankings dynamics.")


category_options = sorted([option for option in competitions_df["category_name"].dropna().unique()])
type_options = sorted([option for option in competitions_df["type"].dropna().unique()])
gender_options = sorted([option for option in competitions_df["gender"].dropna().unique()])
level_options = sorted([option for option in competitions_df["level"].dropna().unique()])
countries_options = sorted([option for option in rankings_df["country"].dropna().unique()])

with st.container(border=True):
    st.markdown("#### Quick Filters")
    quick_col1, quick_col2, quick_col3 = st.columns((2, 2, 1.5))

    selected_categories = quick_col1.multiselect(
        "Categories",
        options=category_options,
        placeholder="All categories"
    ) if category_options else []

    selected_countries = quick_col2.multiselect(
        "Countries",
        options=countries_options,
        placeholder="All countries"
    ) if countries_options else []

    min_rank = int(rankings_df["rank"].min()) if not rankings_df.empty else 1
    max_rank = int(rankings_df["rank"].max()) if not rankings_df.empty else 1
    if min_rank < max_rank:
        selected_rank_range = quick_col3.slider(
            "Rank Band",
            min_value=min_rank,
            max_value=max_rank,
            value=(min_rank, min(max_rank, min_rank + 99))
        )
    else:
        selected_rank_range = (min_rank, max_rank)
        quick_col3.caption("Only one ranking position loaded.")

with st.expander("Advanced Filters", expanded=False):
    adv_col1, adv_col2, adv_col3 = st.columns(3)

    selected_types = adv_col1.multiselect(
        "Competition Types",
        options=type_options,
        placeholder="Any type"
    ) if type_options else []

    selected_genders = adv_col2.multiselect(
        "Gender Divisions",
        options=gender_options,
        placeholder="Any gender"
    ) if gender_options else []

    selected_levels = adv_col3.multiselect(
        "Competition Levels",
        options=level_options,
        placeholder="Any level"
    ) if level_options else []


def apply_competition_filters(data: pd.DataFrame) -> pd.DataFrame:
    filtered = data.copy()
    if selected_categories:
        filtered = filtered[filtered["category_name"].isin(selected_categories)]
    if selected_types:
        filtered = filtered[filtered["type"].isin(selected_types)]
    if selected_genders:
        filtered = filtered[filtered["gender"].isin(selected_genders)]
    if selected_levels:
        filtered = filtered[filtered["level"].isin(selected_levels)]
    return filtered


def apply_ranking_filters(data: pd.DataFrame) -> pd.DataFrame:
    filtered = data.copy()
    if selected_countries:
        filtered = filtered[filtered["country"].isin(selected_countries)]
    if selected_rank_range:
        filtered = filtered[
            (filtered["rank"] >= selected_rank_range[0]) &
            (filtered["rank"] <= selected_rank_range[1])
        ]
    return filtered


filtered_competitions = apply_competition_filters(competitions_df)
filtered_rankings = apply_ranking_filters(rankings_df)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric(
        "Filtered Competitions",
        int(filtered_competitions["competition_id"].nunique()) if not filtered_competitions.empty else 0
    )

with metric_col2:
    st.metric(
        "Active Venues",
        int(venues_df["venue_id"].nunique()) if not venues_df.empty else 0
    )

with metric_col3:
    st.metric(
        "Countries Represented",
        int(filtered_rankings["country"].nunique()) if not filtered_rankings.empty else 0
    )

with metric_col4:
    top_points = filtered_rankings.sort_values("points", ascending=False).head(1)
    if not top_points.empty:
        st.metric(
            "Top Performer",
            f"{top_points.iloc[0]['competitor_name']} ({int(top_points.iloc[0]['points'])} pts)"
        )
    else:
        st.metric("Top Performer", "N/A")

st.markdown("---")

tab_overview, tab_competitions, tab_competitors, tab_trends = st.tabs([
    "Overview Pulse",
    "Competition Landscape",
    "Competitor Spotlight",
    "Trend Explorer"
])


with tab_overview:
    st.markdown("#### Pulse Filters")
    pulse_city_options = sorted([opt for opt in venues_df["city_name"].dropna().unique()]) if not venues_df.empty else []
    pulse_country_options = sorted([opt for opt in filtered_rankings["country"].dropna().unique()]) if not filtered_rankings.empty else []
    filter_city_col, filter_country_col = st.columns(2)

    selected_pulse_cities = filter_city_col.multiselect(
        "Cities",
        options=pulse_city_options,
        default=pulse_city_options,
        help="Limit the venue visuals to specific host cities."
    ) if pulse_city_options else []

    selected_pulse_countries = filter_country_col.multiselect(
        "Countries",
        options=pulse_country_options,
        default=pulse_country_options,
        help="Highlight ranking momentum for selected nations."
    ) if pulse_country_options else []

    st.markdown("---")

    overview_cols = st.columns((2, 1))

    with overview_cols[0]:
        if not filtered_competitions.empty:
            timeline_df = (
                filtered_competitions.assign(has_parent=filtered_competitions["parent_id"].notna())
                .groupby(["category_name", "gender", "has_parent"], dropna=False, observed=False)["competition_id"]
                .nunique()
                .reset_index(name="competitions")
            )
            timeline_df["category_name"].fillna("Unassigned", inplace=True)
            timeline_df["gender"].fillna("Unspecified", inplace=True)
            timeline_fig = px.bar(
                timeline_df,
                x="category_name",
                y="competitions",
                color="gender",
                animation_frame="has_parent",
                barmode="group",
                title="Competition Mix by Category (Toggle: Parent vs Top Level)",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            timeline_fig.update_layout(
                xaxis_title="Category",
                yaxis_title="Competitions",
                legend_title="Gender",
                updatemenus=[
                    {
                        "type": "buttons",
                        "buttons": [
                            {
                                "label": "Play",
                                "method": "animate",
                                "args": [None, {"frame": {"duration": 800, "redraw": True}, "fromcurrent": True}]
                            },
                            {
                                "label": "Pause",
                                "method": "animate",
                                "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]
                            }
                        ]
                    }
                ]
            )
            st.plotly_chart(timeline_fig, width="stretch")
        else:
            st.info("No competition data satisfies the current filters.")

    with overview_cols[1]:
        if not venues_df.empty:
            venues_focus = venues_df.copy()
            if selected_pulse_cities:
                venues_focus = venues_focus[venues_focus["city_name"].isin(selected_pulse_cities)]
            venue_summary = (
                venues_focus.groupby(["country_name", "city_name"], dropna=False, observed=False)["venue_id"]
                .nunique()
                .reset_index(name="venues")
                .sort_values("venues", ascending=False)
                .head(25)
            )
            if venue_summary.empty:
                st.info("No venues match the selected city filter.")
            else:
                fig_venues = px.bar(
                    venue_summary,
                    x="venues",
                    y="city_name",
                    orientation="h",
                    color="country_name",
                    title="Venue Density by City",
                    color_discrete_sequence=px.colors.qualitative.Antique
                )
                fig_venues.update_layout(yaxis_title="City", xaxis_title="Venues", legend_title="Country")
                st.plotly_chart(fig_venues, width="stretch")
        else:
            st.info("Venue catalogue is empty.")

    st.markdown("---")

    if not filtered_rankings.empty:
        momentum_focus = filtered_rankings.copy()
        if selected_pulse_countries:
            momentum_focus = momentum_focus[momentum_focus["country"].isin(selected_pulse_countries)]
        movement_summary = (
            momentum_focus.groupby(pd.cut(
                momentum_focus["movement"],
                bins=[-50, -10, -5, 0, 5, 10, 50],
                labels=["≤-10", "-9 to -5", "-4 to 0", "1 to 5", "6 to 10", "≥11"]
            ), observed=False)["competitor_id"].nunique().reset_index(name="competitors")
        )
        movement_summary = movement_summary.dropna()
        if movement_summary.empty:
            st.info("No competitors fall within the selected country filter.")
        else:
            fig_movement = px.bar(
                movement_summary,
                x="movement",
                y="competitors",
                color="competitors",
                color_continuous_scale="Tealgrn",
                title="Ranking Momentum Buckets"
            )
            fig_movement.update_layout(xaxis_title="Movement", yaxis_title="Competitors")
            st.plotly_chart(fig_movement, width="stretch")

        st.markdown("---")
        st.markdown("#### Line Pulse Insights")

        line_control_col1, line_control_col2 = st.columns(2)

        smoothing_window = line_control_col1.slider(
            "Rolling Window (Ranks)",
            min_value=1,
            max_value=min(25, len(filtered_rankings)),
            value=min(5, len(filtered_rankings)) if len(filtered_rankings) >= 5 else 1,
            help="Smooth the points curve using a rolling rank window."
        )

        line_country_options = sorted([option for option in filtered_rankings["country"].dropna().unique()])
        popular_countries = [
            country for country in filtered_rankings["country"].dropna().value_counts().head(4).index
            if country in line_country_options
        ]
        selected_line_countries = line_control_col2.multiselect(
            "Line Focus Countries",
            options=line_country_options,
            default=popular_countries,
            help="Overlay country trajectories across the ranking curve."
        ) if line_country_options else []

        line_cols = st.columns(2)

        with line_cols[0]:
            rank_line_df = filtered_rankings.sort_values("rank").copy()
            if not rank_line_df.empty:
                rank_line_df["rolling_points"] = (
                    rank_line_df["points"].rolling(window=smoothing_window, min_periods=1).mean()
                )
                fig_points_curve = px.line(
                    rank_line_df,
                    x="rank",
                    y="rolling_points",
                    hover_data=["competitor_name", "points", "movement"],
                    markers=True,
                    title="Smoothed Points Curve by Rank",
                    labels={"rolling_points": "Rolling Avg Points"}
                )
                fig_points_curve.update_layout(xaxis_title="Rank", yaxis_title="Rolling Avg Points")
                fig_points_curve.update_xaxes(autorange="reversed")
                st.plotly_chart(fig_points_curve, width="stretch")
            else:
                st.info("Not enough ranking data for the points curve.")

        with line_cols[1]:
            if selected_line_countries:
                country_line_df = filtered_rankings[filtered_rankings["country"].isin(selected_line_countries)].copy()
                country_line_df.sort_values(["country", "rank"], inplace=True)
                if country_line_df.empty:
                    st.info("No competitors remain after applying the country focus.")
                else:
                    fig_country_points = px.line(
                        country_line_df,
                        x="rank",
                        y="points",
                        color="country",
                        hover_data=["competitor_name", "movement", "competitions_played"],
                        markers=True,
                        title="Points Trajectory by Country"
                    )
                    fig_country_points.update_layout(xaxis_title="Rank", yaxis_title="Points", legend_title="Country")
                    fig_country_points.update_xaxes(autorange="reversed")
                    st.plotly_chart(fig_country_points, width="stretch")
            else:
                st.info("Select at least one country to render the trajectory lines.")

        st.markdown("---")
        st.markdown("#### Composition & Impact")

        pie_cols = st.columns(2)

        with pie_cols[0]:
            if not filtered_competitions.empty:
                comp_type_mix = (
                    filtered_competitions.groupby(["type"], dropna=False, observed=False)["competition_id"]
                    .nunique()
                    .reset_index(name="competitions")
                    .sort_values("competitions", ascending=False)
                )
                comp_type_mix["type"] = comp_type_mix["type"].fillna("Unspecified")
                if comp_type_mix.empty:
                    st.info("Competition type breakdown is unavailable.")
                else:
                    fig_comp_pie = px.pie(
                        comp_type_mix,
                        names="type",
                        values="competitions",
                        title="Competition Types Share",
                        hole=0.35,
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig_comp_pie, width="stretch")
            else:
                st.info("Competition breakdown unavailable with current filters.")

        with pie_cols[1]:
            if not venues_df.empty:
                venue_country_mix = (
                    venues_df.groupby(["country_name"], dropna=False, observed=False)["venue_id"]
                    .nunique()
                    .reset_index(name="venues")
                    .sort_values("venues", ascending=False)
                    .head(12)
                )
                venue_country_mix["country_name"].fillna("Unassigned", inplace=True)
                if venue_country_mix.empty:
                    st.info("Venue distribution unavailable.")
                else:
                    fig_venue_pie = px.pie(
                        venue_country_mix,
                        names="country_name",
                        values="venues",
                        title="Top Venue Footprints",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_venue_pie, width="stretch")
            else:
                st.info("Venue catalogue is empty.")

        st.markdown("---")

        scatter_df = filtered_rankings.copy()
        if not scatter_df.empty:
            scatter_df = scatter_df.dropna(subset=["competitions_played", "points"])
            if scatter_df.empty:
                st.info("Insufficient data to render the performance scatter plot.")
            else:
                scatter_df["competitions_played"] = scatter_df["competitions_played"].astype(int)
                size_metric = scatter_df["rank"].replace(0, np.nan).pow(-0.5).fillna(0)
                size_metric = size_metric.clip(lower=0)
                scatter_fig = px.scatter(
                    scatter_df,
                    x="competitions_played",
                    y="points",
                    size=size_metric,
                    color="country",
                    hover_data=["competitor_name", "rank", "movement"],
                    title="Performance Density: Points vs Competitions"
                )
                scatter_fig.update_layout(xaxis_title="Competitions Played", yaxis_title="Points", legend_title="Country")
                st.plotly_chart(scatter_fig, width="stretch")
        else:
            st.info("Ranking records required for scatter analytics.")

        st.markdown("---")
        st.markdown("#### Momentum Bubble Playback")

        if not momentum_focus.empty:
            bubble_df = momentum_focus.dropna(subset=["rank", "points"]).copy()
            bubble_df = bubble_df.dropna(subset=["competitions_played"]) if "competitions_played" in bubble_df.columns else bubble_df
            if bubble_df.empty:
                st.info("Not enough ranking fields to animate the momentum bubbles.")
            else:
                bubble_df["competitions_played"] = bubble_df["competitions_played"].fillna(0).clip(lower=0)
                bubble_df["movement_bucket"] = pd.cut(
                    bubble_df["movement"],
                    bins=[-50, -10, -5, 0, 5, 10, 50],
                    labels=["≤-10", "-9 to -5", "-4 to 0", "1 to 5", "6 to 10", "≥11"],
                    include_lowest=True
                )
                bubble_df = bubble_df.dropna(subset=["movement_bucket"])
                if bubble_df.empty:
                    st.info("Movement bands require broader ranking selection.")
                else:
                    bubble_df["movement_bucket"] = bubble_df["movement_bucket"].astype(str)
                    bubble_fig = px.scatter(
                        bubble_df,
                        x="rank",
                        y="points",
                        size="competitions_played",
                        color="movement_bucket",
                        animation_frame="movement_bucket",
                        hover_data=["competitor_name", "country", "movement", "competitions_played"],
                        title="Animated Momentum Bubbles"
                    )
                    bubble_fig.update_layout(
                        xaxis_title="Rank",
                        yaxis_title="Points",
                        legend_title="Movement Band"
                    )
                    bubble_fig.update_xaxes(autorange="reversed")
                    st.plotly_chart(bubble_fig, width="stretch")
        else:
            st.info("Momentum animation requires ranking data.")
    else:
        st.info("Ranking momentum requires competitor data.")


with tab_competitions:
    col_comp_left, col_comp_right = st.columns((3, 2))

    if not filtered_competitions.empty:
        level_summary = (
            filtered_competitions.groupby(["level", "gender"], dropna=False, observed=False)["competition_id"]
            .nunique()
            .reset_index(name="competitions")
        )
        level_summary["level"] = level_summary["level"].fillna("Unspecified")
        fig_levels = px.bar(
            level_summary,
            x="competitions",
            y="level",
            color="gender",
            orientation="h",
            barmode="group",
            title="Competitions by Level and Gender"
        )
        fig_levels.update_layout(xaxis_title="Competitions", yaxis_title="Level")
        col_comp_left.plotly_chart(fig_levels, width="stretch")

        type_summary = (
            filtered_competitions.groupby(["type", "category_name"], dropna=False, observed=False)["competition_id"]
            .nunique()
            .reset_index(name="competitions")
        )
        fig_types = px.sunburst(
            type_summary,
            path=["category_name", "type"],
            values="competitions",
            color="competitions",
            color_continuous_scale="Sunset",
            title="Competition Portfolio"
        )
        col_comp_right.plotly_chart(fig_types, width="stretch")

        st.markdown("---")
        st.markdown("#### Level vs Type Intensity")

        heatmap_df = (
            filtered_competitions.groupby(["level", "type"], dropna=False, observed=False)["competition_id"]
            .nunique()
            .reset_index(name="competitions")
        )
        heatmap_df["level"] = heatmap_df["level"].fillna("Unspecified")
        heatmap_df["type"] = heatmap_df["type"].fillna("Unspecified")
        heatmap_pivot = heatmap_df.pivot(index="level", columns="type", values="competitions").fillna(0)
        if heatmap_pivot.empty:
            st.info("Heatmap requires a wider competition spread.")
        else:
            heatmap_fig = px.imshow(
                heatmap_pivot,
                labels=dict(x="Competition Type", y="Competition Level", color="Competitions"),
                color_continuous_scale="Viridis",
                aspect="auto"
            )
            heatmap_fig.update_xaxes(side="top")
            st.plotly_chart(heatmap_fig, width="stretch")

        stream_df = (
            filtered_competitions.groupby(["category_name", "gender"], dropna=False, observed=False)["competition_id"]
            .nunique()
            .reset_index(name="competitions")
        )
        stream_df["category_name"].fillna("Unassigned", inplace=True)
        stream_df["gender"].fillna("Unspecified", inplace=True)
        if stream_df.empty:
            st.info("Category stream requires broader competition coverage.")
        else:
            category_order = (
                stream_df.groupby("category_name")["competitions"].sum().sort_values(ascending=False).index.tolist()
            )
            stream_df["category_name"] = pd.Categorical(stream_df["category_name"], categories=category_order, ordered=True)
            stream_df.sort_values("category_name", inplace=True)
            stream_fig = px.area(
                stream_df,
                x="category_name",
                y="competitions",
                color="gender",
                title="Category Depth Stream",
                groupnorm=None,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            stream_fig.update_layout(xaxis_title="Category", yaxis_title="Competitions", legend_title="Gender")
            st.plotly_chart(stream_fig, width="stretch")

        st.markdown("### Recently Added Competitions")
        st.dataframe(
            filtered_competitions[[
                "competition_name",
                "category_name",
                "type",
                "gender",
                "level"
            ]].sort_values("competition_name").head(30),
            use_container_width=True
        )
    else:
        st.info("Adjust filters to view competition analytics.")


with tab_competitors:
    col_competitor_left, col_competitor_right = st.columns((3, 2))

    if not filtered_rankings.empty:
        rank_scatter = px.scatter(
            filtered_rankings,
            x="rank",
            y="points",
            color="movement",
            hover_data=["competitor_name", "country", "competitions_played"],
            color_continuous_scale="Turbo",
            title="Points vs. Rank with Momentum"
        )
        rank_scatter.update_layout(xaxis_title="World Rank", yaxis_title="Points")
        col_competitor_left.plotly_chart(rank_scatter, width="stretch")

        country_summary = (
            filtered_rankings.groupby(["country", "country_code"], dropna=False, observed=False)["competitor_id"]
            .nunique()
            .reset_index(name="competitors")
        )
        fig_map = px.choropleth(
            country_summary,
            locations="country_code",
            color="competitors",
            hover_name="country",
            color_continuous_scale="Plasma",
            title="Global Competitor Footprint"
        )
        fig_map.update_geos(showcoastlines=True, projection_type="natural earth")
        col_competitor_right.plotly_chart(fig_map, width="stretch")

        st.markdown("### Leaders Table")
        top_leaders = filtered_rankings.sort_values(["rank", "points"]).head(25)
        st.dataframe(
            top_leaders[[
                "competitor_name",
                "country",
                "rank",
                "points",
                "movement",
                "competitions_played"
            ]],
            use_container_width=True
        )

        st.markdown("---")
        st.markdown("#### Points Distribution Insights")

        violin_focus = filtered_rankings.dropna(subset=["points"]).copy()
        if violin_focus.empty:
            st.info("No points data available for the violin distribution.")
        else:
            top_violin_countries = (
                violin_focus.groupby("country")["competitor_id"].nunique()
                .sort_values(ascending=False)
                .head(6)
                .index
                .tolist()
            )
            violin_focus = violin_focus[violin_focus["country"].isin(top_violin_countries)]
            if violin_focus.empty:
                st.info("Select broader filters to populate the distribution view.")
            else:
                violin_fig = px.violin(
                    violin_focus,
                    x="country",
                    y="points",
                    color="country",
                    box=True,
                    points="all",
                    hover_data=["competitor_name", "rank", "movement"],
                    title="Points Spread by Country"
                )
                violin_fig.update_layout(xaxis_title="Country", yaxis_title="Points", showlegend=False)
                st.plotly_chart(violin_fig, width="stretch")

        st.markdown("---")
        st.markdown("#### Movement Compass")

        movement_focus = filtered_rankings.dropna(subset=["movement", "country"]).copy()
        if movement_focus.empty:
            st.info("Movement data unavailable for the compass view.")
        else:
            movement_summary = (
                movement_focus.groupby("country", observed=False)
                .agg(
                    avg_movement=("movement", "mean"),
                    avg_abs_movement=("movement", lambda series: series.abs().mean())
                )
                .reset_index()
            )
            movement_summary.sort_values("avg_abs_movement", ascending=False, inplace=True)
            polar_selection = movement_summary.head(8)
            if polar_selection.empty:
                st.info("Insufficient variance across countries for the compass chart.")
            else:
                polar_fig = px.bar_polar(
                    polar_selection,
                    r="avg_abs_movement",
                    theta="country",
                    color="avg_movement",
                    color_continuous_scale="IceFire",
                    title="Average Movement Intensity by Country"
                )
                polar_fig.update_layout(legend_title="Mean Movement")
                st.plotly_chart(polar_fig, width="stretch")
    else:
        st.info("No competitor records in scope. Relax the filters to see rankings insights.")


with tab_trends:
    if filtered_rankings.empty:
        st.info("Ranking insights require competitor data. Adjust the filters above.")
    else:
        trend_top_row, trend_metric_row = st.columns((2, 1))

        max_available_ranks = selected_rank_range[1] - selected_rank_range[0]
        if max_available_ranks < 1:
            rank_bin_slider = 1
        else:
            rank_bin_slider = trend_top_row.slider(
                "Number of Rank Buckets",
                min_value=5,
                max_value=min(30, max_available_ranks),
                value=min(12, max_available_ranks),
                help="Controls how rankings are grouped for the comparative trend lines."
            )

        trend_metric = trend_metric_row.selectbox(
            "Metric to Plot",
            options=[
                ("points", "Average Points"),
                ("movement", "Average Movement"),
                ("competitions_played", "Average Competitions Played")
            ],
            format_func=lambda item: item[1]
        )[0]

        lower_bound, upper_bound = selected_rank_range
        if lower_bound == upper_bound:
            st.info("Select a wider ranking range to view trend lines.")
        else:
            bin_edges = np.linspace(lower_bound, upper_bound, rank_bin_slider + 1)
            rank_bucket_series = pd.cut(
                filtered_rankings["rank"],
                bins=bin_edges,
                include_lowest=True,
                right=True
            )

            trend_df = (
                filtered_rankings.assign(rank_bucket=rank_bucket_series)
                .dropna(subset=["rank_bucket"])
                .groupby("rank_bucket", observed=False)
                .agg(
                    avg_metric=(trend_metric, "mean"),
                    competitors=("competitor_id", "nunique")
                )
                .reset_index()
            )

            if trend_df.empty:
                st.info("No data available for the current ranking buckets.")
            else:
                trend_df["rank_midpoint"] = trend_df["rank_bucket"].apply(lambda interval: (interval.left + interval.right) / 2)
                line_fig = px.line(
                    trend_df,
                    x="rank_midpoint",
                    y="avg_metric",
                    markers=True,
                    color_discrete_sequence=["#6C5CE7"],
                    title="Average Metric by Rank Bucket"
                )
                y_axis_label = {
                    "points": "Average Points",
                    "movement": "Average Movement",
                    "competitions_played": "Average Competitions Played"
                }[trend_metric]
                line_fig.update_layout(
                    xaxis_title="Rank (Bucket Midpoint)",
                    yaxis_title=y_axis_label
                )
                st.plotly_chart(line_fig, width="stretch")

                st.caption("Bucket size controls the granularity of the curve – smaller buckets highlight micro-trends, larger buckets smooth the view.")

        st.markdown("### Country Ranking Stack")

        country_unique = filtered_rankings["country"].nunique()
        if country_unique == 0:
            st.info("Country information is unavailable for the current selection.")
        else:
            slider_min = 1 if country_unique == 1 else min(3, country_unique)
            slider_max = min(12, country_unique)
            if slider_min == slider_max:
                top_country_count = slider_max
            else:
                default_selection = min(slider_max, max(slider_min, 6))
                top_country_count = st.slider(
                    "Number of Countries to Highlight",
                    min_value=slider_min,
                    max_value=slider_max,
                    value=default_selection,
                    help="Shows the stacked distribution of leading countries across the ranking spectrum."
                )

            leading_countries = (
                filtered_rankings.groupby("country", observed=False)["competitor_id"].nunique()
                .sort_values(ascending=False)
                .head(top_country_count)
                .index
                .tolist()
            )

            if leading_countries:
                country_focus = filtered_rankings[filtered_rankings["country"].isin(leading_countries)].copy()
                if lower_bound != upper_bound:
                    area_bins = pd.cut(
                        country_focus["rank"],
                        bins=np.linspace(lower_bound, upper_bound, rank_bin_slider + 1),
                        include_lowest=True,
                        right=True
                    )
                    area_df = (
                        country_focus.assign(rank_bucket=area_bins)
                        .dropna(subset=["rank_bucket"])
                        .groupby(["rank_bucket", "country"], observed=False)
                        .size()
                        .reset_index(name="competitors")
                    )

                    if not area_df.empty:
                        area_df["rank_midpoint"] = area_df["rank_bucket"].apply(lambda interval: (interval.left + interval.right) / 2)
                        area_fig = px.area(
                            area_df,
                            x="rank_midpoint",
                            y="competitors",
                            color="country",
                            title="Ranking Distribution of Highlighted Countries",
                            color_discrete_sequence=px.colors.qualitative.Dark24
                        )
                        area_fig.update_layout(
                            xaxis_title="Rank (Bucket Midpoint)",
                            yaxis_title="Competitors",
                            legend_title="Country"
                        )
                        st.plotly_chart(area_fig, width="stretch")
                    else:
                        st.info("No country distribution data for the selected range and buckets.")
                else:
                    st.info("Adjust the ranking range to populate the country stack view.")
            else:
                st.info("Expand your filters to include at least one country for the stack view.")