from __future__ import annotations

import copy
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.load_city_data import (
    load_demographic_socioeconomic_pressure_data,
    load_ruhr_hospital_forecast_data,
)


SCENARIO_LABELS = {
    "business_as_usual": "Business as usual",
    "stress": "Stress scenario",
    "recruitment_improvement": "Recruitment improvement",
    "capacity_decline": "Capacity decline",
}

SCENARIO_LABEL_TO_KEY = {label: key for key, label in SCENARIO_LABELS.items()}

CITY_COORDINATES = {
    "Bochum": {"lat": 51.4818, "lon": 7.2162},
    "Bottrop": {"lat": 51.5291, "lon": 6.9447},
    "Dortmund": {"lat": 51.5136, "lon": 7.4653},
    "Duisburg": {"lat": 51.4344, "lon": 6.7623},
    "Essen": {"lat": 51.4556, "lon": 7.0116},
    "Gelsenkirchen": {"lat": 51.5177, "lon": 7.0857},
    "Hagen": {"lat": 51.3671, "lon": 7.4633},
    "Herne": {"lat": 51.5369, "lon": 7.2009},
    "Mülheim an der Ruhr": {"lat": 51.4186, "lon": 6.8845},
    "Oberhausen": {"lat": 51.4963, "lon": 6.8638},
}

ANALYSIS_LAYERS = {
    "Hospital system only": {
        "hpi_column": "hospital_hpi",
        "complete_flag": "is_hpi_complete",
        "patients_per_bed_column": "patients_per_bed",
        "patients_per_physician_column": "patients_per_physician",
        "beds_column": "beds",
        "physicians_column": "hospital_physicians",
        "patients_per_bed_score": "patients_per_bed_score",
        "patients_per_physician_score": "patients_per_physician_score",
        "occupancy_score": "occupancy_score",
        "length_of_stay_score": "length_of_stay_score",
    },
    "Hospital type corrected": {
        "hpi_column": "acute_care_adjusted_hpi",
        "complete_flag": "is_acute_adjusted_hpi_complete",
        "patients_per_bed_column": "adjusted_patients_per_bed",
        "patients_per_physician_column": "adjusted_patients_per_physician",
        "beds_column": "adjusted_beds",
        "physicians_column": "adjusted_hospital_physicians",
        "patients_per_bed_score": "adjusted_patients_per_bed_score",
        "patients_per_physician_score": "adjusted_patients_per_physician_score",
        "occupancy_score": "adjusted_occupancy_score",
        "length_of_stay_score": "adjusted_length_of_stay_score",
    },
    "Demographic + socioeconomic adjusted": {
        "hpi_column": "demographic_socioeconomic_hpi",
        "complete_flag": "is_acute_adjusted_hpi_complete",
        "patients_per_bed_column": "adjusted_patients_per_bed",
        "patients_per_physician_column": "adjusted_patients_per_physician",
        "beds_column": "adjusted_beds",
        "physicians_column": "adjusted_hospital_physicians",
        "patients_per_bed_score": "adjusted_patients_per_bed_score",
        "patients_per_physician_score": "adjusted_patients_per_physician_score",
        "occupancy_score": "adjusted_occupancy_score",
        "length_of_stay_score": "adjusted_length_of_stay_score",
    },
}

HISTORICAL_ANALYSIS_LAYER_NAMES = [
    "Hospital system only",
    "Hospital type corrected",
    "Demographic + socioeconomic adjusted",
]

FORECAST_ANALYSIS_LAYER_NAMES = [
    "Hospital system only",
    "Hospital type corrected",
    "Demographic + socioeconomic adjusted",
]

DISPLAY_LAYER_TO_INTERNAL = {
    "All hospitals": "Hospital system only",
    "Only acute hospitals": "Hospital type corrected",
    "Demographics": "Demographic + socioeconomic adjusted",
}

DISPLAY_LAYER_TO_HPI_COLUMN = {
    "All hospitals": "hospital_hpi",
    "Only acute hospitals": "acute_care_adjusted_hpi",
    "Demographics": "demographic_socioeconomic_hpi",
}

DISPLAY_LAYER_TO_COMPLETE_FLAG = {
    "All hospitals": "is_hpi_complete",
    "Only acute hospitals": "is_acute_adjusted_hpi_complete",
    "Demographics": "is_acute_adjusted_hpi_complete",
}

INTERNAL_LAYER_TO_DISPLAY = {
    internal: display for display, internal in DISPLAY_LAYER_TO_INTERNAL.items()
}

DEFAULT_DISPLAY_LAYER = "All hospitals"


st.set_page_config(
    page_title="Hospital Pressure Index - Ruhrgebiet",
    layout="wide",
)


@st.cache_data
def load_historical_data() -> pd.DataFrame:
    """Load historical hospital pressure data with all analysis layers."""
    return load_demographic_socioeconomic_pressure_data()


@st.cache_data
def load_forecast_data() -> pd.DataFrame:
    """Load forecast hospital pressure data."""
    return load_ruhr_hospital_forecast_data()


def get_available_layers(mode: str) -> list[str]:
    """Return analysis layers supported by the selected mode."""
    if mode == "Historical":
        layer_names = HISTORICAL_ANALYSIS_LAYER_NAMES
        data = historical_all
    else:
        layer_names = FORECAST_ANALYSIS_LAYER_NAMES
        data = forecast_all

    available_layers = []

    for layer_name in layer_names:
        config = ANALYSIS_LAYERS[layer_name]
        required_columns = [config["hpi_column"], config["complete_flag"]]

        if all(column in data.columns for column in required_columns):
            available_layers.append(layer_name)

    return available_layers


def get_available_display_layers(mode: str) -> list[str]:
    """Return user-facing layer labels supported by the selected mode."""
    if mode == "Historical":
        layer_names = ["All hospitals", "Only acute hospitals", "Demographics"]
        data = historical_all
    else:
        layer_names = ["All hospitals", "Only acute hospitals", "Demographics"]
        data = forecast_all

    available_layers = []

    for layer_name in layer_names:
        hpi_column = DISPLAY_LAYER_TO_HPI_COLUMN[layer_name]
        complete_flag = DISPLAY_LAYER_TO_COMPLETE_FLAG[layer_name]

        if hpi_column in data.columns and complete_flag in data.columns:
            available_layers.append(layer_name)

    return available_layers


def get_layer_view(mode: str) -> str:
    """Read the sidebar layer view selection."""
    available_layers = get_available_display_layers(mode)

    if not available_layers:
        return DEFAULT_DISPLAY_LAYER

    default_index = 0

    if DEFAULT_DISPLAY_LAYER in available_layers:
        default_index = available_layers.index(DEFAULT_DISPLAY_LAYER)

    return st.sidebar.radio(
        "Layer view",
        available_layers,
        index=default_index,
    )


def sync_selected_city_from_sidebar() -> None:
    """Keep the canonical selected city aligned with the sidebar selector."""
    selected_city = st.session_state.get("selected_city_selector")

    if selected_city:
        st.session_state["selected_city"] = selected_city
        st.session_state["ignore_map_selection_once"] = True


def get_layer_config(mode: str, selected_layer: str) -> dict[str, str]:
    """Return the configuration for a mode-supported analysis layer."""
    available_layers = get_available_layers(mode)

    if selected_layer not in available_layers:
        selected_layer = available_layers[0]

    return ANALYSIS_LAYERS[selected_layer]


def add_selected_hpi(df: pd.DataFrame, hpi_column: str) -> pd.DataFrame:
    """Add a standard selected_hpi column used by charts and tables."""
    output = df.copy()

    if hpi_column in output.columns:
        output["selected_hpi"] = pd.to_numeric(output[hpi_column], errors="coerce")
    else:
        output["selected_hpi"] = pd.NA

    return output


def add_active_selected_hpi(
    df: pd.DataFrame,
    hpi_column: str,
    complete_flag: str,
) -> pd.DataFrame:
    """Filter complete rows and add selected_hpi from the resolved active layer."""
    output = df.copy()

    if hpi_column not in output.columns or complete_flag not in output.columns:
        output["selected_hpi"] = pd.NA
        return output.iloc[0:0].copy()

    output["selected_hpi"] = pd.to_numeric(output[hpi_column], errors="coerce")
    complete_mask = output[complete_flag].fillna(False).astype(bool)

    return output[complete_mask & output["selected_hpi"].notna()].copy()


def get_complete_df(df: pd.DataFrame, complete_flag: str) -> pd.DataFrame:
    """Filter to complete rows without raising if a completion flag is absent."""
    if complete_flag not in df.columns:
        return df.iloc[0:0].copy()

    return df[df[complete_flag].fillna(False)].copy()


def hpi_yaxis_range(df: pd.DataFrame, column: str = "selected_hpi") -> list[float]:
    """Use a 0-100 HPI axis, but do not clip forecast values above 100."""
    if column not in df.columns:
        return [0, 100]

    max_hpi = pd.to_numeric(df[column], errors="coerce").max()

    if pd.isna(max_hpi):
        return [0, 100]

    return [0, max(100, float(max_hpi) * 1.05)]


def existing_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Return columns that are present in the dataframe."""
    return [column for column in columns if column in df.columns]


def format_number(value: Any, decimals: int = 1, suffix: str = "") -> str:
    """Format numeric values for Streamlit metrics and hover text."""
    numeric_value = pd.to_numeric(value, errors="coerce")

    if pd.isna(numeric_value):
        return "n/a"

    return f"{numeric_value:,.{decimals}f}{suffix}"


def build_region_map(
    df_complete: pd.DataFrame,
    selected_hpi_column: str,
):
    """Build a Plotly map of Ruhr city HPI values."""
    map_df = df_complete.copy()

    if "selected_hpi" not in map_df.columns:
        map_df = add_selected_hpi(map_df, selected_hpi_column)

    coord_df = pd.DataFrame(
        [
            {"city": city, "lat": coords["lat"], "lon": coords["lon"]}
            for city, coords in CITY_COORDINATES.items()
        ]
    )

    map_df = map_df.merge(coord_df, on="city", how="left")
    map_df = map_df.dropna(subset=["lat", "lon", "selected_hpi"]).copy()

    if map_df.empty:
        return None

    if "population_total" in map_df.columns and map_df["population_total"].notna().any():
        size_column = "population_total"
    else:
        map_df["marker_size"] = map_df["selected_hpi"].clip(lower=1)
        size_column = "marker_size"

    hover_columns = {
        "selected_hpi": ":.2f",
        "lat": False,
        "lon": False,
    }

    if "population_total" in map_df.columns:
        hover_columns["population_total"] = ":,.0f"

    if "acute_relevance_factor" in map_df.columns:
        hover_columns["acute_relevance_factor"] = ":.3f"

    fig = px.scatter_map(
        map_df,
        lat="lat",
        lon="lon",
        color="selected_hpi",
        size=size_column,
        hover_name="city",
        hover_data=hover_columns,
        custom_data=["city"],
        color_continuous_scale="RdYlGn_r",
        range_color=[0, 100],
        size_max=34,
        zoom=8,
        center={"lat": 51.48, "lon": 7.12},
        map_style="carto-darkmatter",
        labels={
            "selected_hpi": "HPI",
            "population_total": "Population",
            "acute_relevance_factor": "Acute relevance factor",
        },
    )

    for trace in fig.data:
        trace.marker.opacity = 1.0
        trace.marker.allowoverlap = True

    if fig.data:
        marker_halo = copy.deepcopy(fig.data[0])
        marker_halo.name = "City marker halo"
        marker_halo.hoverinfo = "skip"
        marker_halo.showlegend = False
        marker_halo.marker.color = "rgba(255,255,255,0.86)"
        marker_halo.marker.coloraxis = None
        marker_halo.marker.opacity = 0.86
        marker_halo.marker.showscale = False
        marker_halo.marker.allowoverlap = True

        if marker_halo.marker.sizeref:
            marker_halo.marker.sizeref = marker_halo.marker.sizeref * 0.58
        marker_halo.marker.sizemin = 14

        fig.add_trace(marker_halo)
        fig.data = (fig.data[-1], *fig.data[:-1])

    fig.update_layout(
        height=520,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar={
            "title": "HPI",
            "bgcolor": "rgba(20,20,20,0.72)",
            "bordercolor": "rgba(255,255,255,0.35)",
            "borderwidth": 1,
        },
    )

    return fig


def get_selected_city_from_map_event(event: Any, fallback_city: str) -> str:
    """Extract a clicked city from a Streamlit Plotly selection event."""
    selection = getattr(event, "selection", None)

    if selection is None and isinstance(event, dict):
        selection = event.get("selection")

    points = getattr(selection, "points", None)

    if points is None and isinstance(selection, dict):
        points = selection.get("points")

    if not points:
        return fallback_city

    point = points[0]
    custom_data = getattr(point, "customdata", None)

    if custom_data is None and isinstance(point, dict):
        custom_data = point.get("customdata")

    if custom_data:
        return str(custom_data[0])

    return fallback_city


def build_pressure_drivers(
    city_row: pd.Series,
    layer_config: dict[str, str],
) -> pd.DataFrame:
    """Build pressure driver rows for the selected city and layer."""
    driver_specs = [
        (
            "Patients per bed",
            layer_config["patients_per_bed_score"],
            layer_config["patients_per_bed_column"],
            "",
        ),
        (
            "Patients per physician FTE proxy",
            layer_config["patients_per_physician_score"],
            layer_config["patients_per_physician_column"],
            "",
        ),
        (
            "Occupancy",
            layer_config["occupancy_score"],
            "bed_occupancy_rate",
            "%",
        ),
        (
            "Length of stay",
            layer_config["length_of_stay_score"],
            "avg_length_of_stay",
            " days",
        ),
    ]

    rows = []

    for label, score_column, value_column, suffix in driver_specs:
        if score_column not in city_row.index or value_column not in city_row.index:
            continue

        score = pd.to_numeric(city_row[score_column], errors="coerce")

        if pd.isna(score):
            continue

        rows.append(
            {
                "component": label,
                "score": score,
                "actual_value": format_number(city_row[value_column], suffix=suffix),
            }
        )

    driver_df = pd.DataFrame(rows)

    if not driver_df.empty:
        driver_df["label"] = driver_df.apply(
            lambda row: f"{row['score']:.1f} | actual: {row['actual_value']}",
            axis=1,
        )

    return driver_df


def build_layer_comparison(
    data: pd.DataFrame,
    city: str,
    layer_names: list[str],
    scenario: str | None = None,
) -> pd.DataFrame:
    """Build a long dataframe comparing HPI layers for one city."""
    layer_frames = []

    for layer_name in layer_names:
        config = ANALYSIS_LAYERS[layer_name]
        hpi_column = config["hpi_column"]
        complete_flag = config["complete_flag"]

        if hpi_column not in data.columns or complete_flag not in data.columns:
            continue

        mask = (data["city"] == city) & data[complete_flag].fillna(False)

        if scenario is not None and "scenario" in data.columns:
            mask = mask & (data["scenario"] == scenario)

        temp = data.loc[mask, ["year", hpi_column]].copy()
        temp = temp.rename(columns={hpi_column: "hpi"})
        temp["layer"] = INTERNAL_LAYER_TO_DISPLAY.get(layer_name, layer_name)

        layer_frames.append(temp)

    if not layer_frames:
        return pd.DataFrame(columns=["year", "hpi", "layer"])

    return pd.concat(layer_frames, ignore_index=True)


def build_scenario_comparison(
    forecast_df: pd.DataFrame,
    city: str,
    hpi_column: str,
    complete_flag: str,
) -> pd.DataFrame:
    """Build a long dataframe comparing forecast scenarios for one city."""
    required_columns = ["city", "year", "scenario"]

    if any(column not in forecast_df.columns for column in required_columns):
        return pd.DataFrame(columns=["year", "hpi", "scenario_label"])

    scenario_df = forecast_df[forecast_df["city"] == city].copy()
    scenario_df = add_active_selected_hpi(
        scenario_df,
        hpi_column=hpi_column,
        complete_flag=complete_flag,
    )

    if scenario_df.empty:
        return pd.DataFrame(columns=["year", "hpi", "scenario_label"])

    scenario_df = scenario_df[["year", "scenario", "selected_hpi"]].rename(
        columns={"selected_hpi": "hpi"}
    )
    scenario_df["scenario_label"] = scenario_df["scenario"].map(SCENARIO_LABELS).fillna(
        scenario_df["scenario"]
    )

    return scenario_df


def build_layer_timeline(
    source_df: pd.DataFrame,
    mode: str,
    selected_scenario: str | None,
    active_layer: str,
    hpi_column: str,
    complete_flag: str,
    scenario_label: str | None = None,
):
    """Build a regional timeline with one active-layer HPI line per city."""
    if "city" not in source_df.columns or "year" not in source_df.columns:
        return None

    timeline_df = source_df.copy()

    if mode == "Forecast":
        if "scenario" not in timeline_df.columns:
            return None

        timeline_df = timeline_df[timeline_df["scenario"] == selected_scenario]

    timeline_df = add_active_selected_hpi(
        timeline_df,
        hpi_column=hpi_column,
        complete_flag=complete_flag,
    )

    if mode == "Historical":
        timeline_df = timeline_df[timeline_df["year"].between(2015, 2024)]
        title = f"HPI evolution by city — 2015–2024 — {active_layer}"
    else:
        scenario_text = scenario_label or selected_scenario or "selected scenario"
        timeline_df = timeline_df[timeline_df["year"].between(2025, 2030)]
        title = f"Forecast HPI evolution by city — {scenario_text} — {active_layer}"

    timeline_df = timeline_df.dropna(subset=["city", "year", "selected_hpi"])

    if timeline_df.empty:
        return None

    fig = px.line(
        timeline_df.sort_values(["city", "year"]),
        x="year",
        y="selected_hpi",
        color="city",
        markers=True,
        labels={
            "year": "Year",
            "selected_hpi": "Hospital Pressure Index",
            "city": "City",
        },
        title=title,
    )

    fig.update_layout(
        yaxis_range=hpi_yaxis_range(timeline_df),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


historical_all = load_historical_data()
forecast_all = load_forecast_data()

st.title("Hospital Pressure Index - Ruhrgebiet")

mode = st.sidebar.radio("Mode", ["Historical", "Forecast"])

if st.sidebar.button("Refresh data cache"):
    st.cache_data.clear()
    st.rerun()


def get_available_display_layers(mode: str) -> list[str]:
    """Return user-facing layer labels supported by the selected mode and data columns."""
    data = historical_all if mode == "Historical" else forecast_all

    layer_names = [
        "All hospitals",
        "Only acute hospitals",
    ]

    if "demographic_socioeconomic_hpi" in data.columns:
        layer_names.append("Demographics")

    available_layers = []

    for layer_name in layer_names:
        hpi_column = DISPLAY_LAYER_TO_HPI_COLUMN[layer_name]
        complete_flag = DISPLAY_LAYER_TO_COMPLETE_FLAG[layer_name]

        if hpi_column in data.columns and complete_flag in data.columns:
            available_layers.append(layer_name)

    return available_layers


available_layers = get_available_display_layers(mode)

if not available_layers:
    st.error(f"No analysis layers are available for {mode} mode.")
    st.stop()

layer_view = get_layer_view(mode)


selected_hpi_column = DISPLAY_LAYER_TO_HPI_COLUMN.get(
    layer_view,
    DISPLAY_LAYER_TO_HPI_COLUMN[DEFAULT_DISPLAY_LAYER],
)
selected_complete_flag = DISPLAY_LAYER_TO_COMPLETE_FLAG.get(
    layer_view,
    DISPLAY_LAYER_TO_COMPLETE_FLAG[DEFAULT_DISPLAY_LAYER],
)

if selected_hpi_column not in (forecast_all.columns if mode == "Forecast" else historical_all.columns):
    layer_view = DEFAULT_DISPLAY_LAYER
    selected_hpi_column = DISPLAY_LAYER_TO_HPI_COLUMN[layer_view]
    selected_complete_flag = DISPLAY_LAYER_TO_COMPLETE_FLAG[layer_view]

analysis_layer = DISPLAY_LAYER_TO_INTERNAL[layer_view]
layer_config = get_layer_config(mode, analysis_layer)

selected_scenario = None
selected_scenario_label = None

if mode == "Historical":
    selected_year = int(historical_all["year"].dropna().max())
    mode_df = historical_all[historical_all["year"] == selected_year].copy()
    caption = (
        f"Historical mode. Layer view: {layer_view}. "
        f"Cards, map, and ranking use latest available year: {selected_year}."
    )
else:
    available_scenarios = sorted(forecast_all["scenario"].dropna().unique())
    scenario_labels = [
        SCENARIO_LABELS.get(scenario, scenario)
        for scenario in available_scenarios
    ]

    selected_scenario_label = st.sidebar.selectbox("Forecast scenario", scenario_labels)
    selected_scenario = SCENARIO_LABEL_TO_KEY.get(
        selected_scenario_label,
        selected_scenario_label,
    )
    selected_year = int(forecast_all["year"].dropna().max())
    mode_df = forecast_all[
        (forecast_all["scenario"] == selected_scenario)
        & (forecast_all["year"] == selected_year)
    ].copy()
    caption = (
        f"Forecast mode. Scenario: {selected_scenario_label}. "
        f"Layer view: {layer_view}. "
        f"Cards, map, and ranking use final forecast year: {selected_year}."
    )

df_complete = add_active_selected_hpi(
    mode_df,
    hpi_column=selected_hpi_column,
    complete_flag=selected_complete_flag,
)

if df_complete.empty:
    st.error(
        f"No complete HPI data available for {selected_year}. "
        "All cities have missing or suppressed official data."
    )
    st.stop()

valid_cities = sorted(df_complete["city"].dropna().unique().tolist())

if (
    "selected_city" not in st.session_state
    or st.session_state["selected_city"] not in valid_cities
):
    st.session_state["selected_city"] = valid_cities[0]

if st.session_state.get("selected_city_selector") != st.session_state["selected_city"]:
    st.session_state["selected_city_selector"] = st.session_state["selected_city"]

st.sidebar.selectbox(
    "Selected city",
    valid_cities,
    key="selected_city_selector",
    on_change=sync_selected_city_from_sidebar,
)

st.caption(caption)
st.caption("Map, timeline, KPI cards, and ranking use the selected Layer view.")

if mode == "Forecast":
    st.caption(
        "Forecast demographic and socio-economic indicators are projected from "
        "historical city trends and should be interpreted as scenario assumptions, "
        "not official future statistics."
    )

overview_tab, city_tab = st.tabs(["Region overview", "City deep dive"])

with overview_tab:
    avg_hpi = df_complete["selected_hpi"].mean()
    highest_city = df_complete.sort_values("selected_hpi", ascending=False).iloc[0]
    lowest_city = df_complete.sort_values("selected_hpi", ascending=True).iloc[0]

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    kpi_col1.metric("Average Ruhr HPI", f"{avg_hpi:.2f}/100")
    kpi_col2.metric(
        "Highest pressure city",
        f"{highest_city['city']} ({highest_city['selected_hpi']:.2f}/100)",
    )
    kpi_col3.metric(
        "Lowest pressure city",
        f"{lowest_city['city']} ({lowest_city['selected_hpi']:.2f}/100)",
    )

    st.subheader("Ruhr city pressure map")

    region_map = build_region_map(df_complete, selected_hpi_column)

    if region_map is None:
        st.warning("No city coordinates are available for the current dataset.")
    else:
        try:
            event = st.plotly_chart(
                region_map,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
            )
            selected_from_map = get_selected_city_from_map_event(
                event,
                st.session_state["selected_city"],
            )

            ignore_map_selection = st.session_state.pop(
                "ignore_map_selection_once",
                False,
            )

            if not ignore_map_selection and selected_from_map in valid_cities:
                st.session_state["selected_city"] = selected_from_map
        except TypeError:
            st.plotly_chart(region_map, use_container_width=True)

    st.caption("Map, timeline, KPI cards, and ranking use the selected Layer view.")
    st.caption("Click a city point on the map to update the city deep dive.")

    st.subheader("Regional HPI timeline")
    timeline_source_df = historical_all if mode == "Historical" else forecast_all
    timeline_fig = build_layer_timeline(
        timeline_source_df,
        mode,
        selected_scenario,
        layer_view,
        selected_hpi_column,
        selected_complete_flag,
        selected_scenario_label,
    )

    if timeline_fig is None:
        st.warning("No timeline data is available for the selected layer view.")
    else:
        st.plotly_chart(timeline_fig, use_container_width=True)

        st.caption(f"This chart shows city-level HPI evolution for {layer_view}.")

    ranking_columns = [
        "city",
        "selected_hpi",
        "hospital_hpi",
        "acute_care_adjusted_hpi",
        "demographic_socioeconomic_hpi",
        "acute_relevance_factor",
        "population_total",
        "population_65_plus_pct",
        "unemployment_rate_proxy",
        "beds",
        "adjusted_beds",
        "hospital_physicians",
        "hospital_physicians_fte_proxy",
        "adjusted_hospital_physicians",
    ]

    st.subheader("City ranking")
    st.dataframe(
        df_complete.sort_values("selected_hpi", ascending=False)[
            existing_columns(df_complete, ranking_columns)
        ],
        use_container_width=True,
    )

    if mode == "Historical":
        incomplete_df = mode_df[~mode_df.index.isin(df_complete.index)].copy()

        if not incomplete_df.empty:
            st.subheader("Excluded rows - incomplete official data")
            excluded_columns = [
                "city",
                "year",
                "hospitals",
                "beds",
                "hospital_physicians_headcount",
                "hospital_physicians_fte_proxy",
                "stationary_patients",
                "bed_occupancy_rate",
                "avg_length_of_stay",
                "data_completeness_status",
            ]
            st.dataframe(
                incomplete_df[existing_columns(incomplete_df, excluded_columns)]
                .sort_values("city"),
                use_container_width=True,
            )

with city_tab:
    selected_city = st.session_state["selected_city"]
    city_row = df_complete[df_complete["city"] == selected_city].iloc[0]

    patients_per_bed_col = layer_config["patients_per_bed_column"]
    patients_per_physician_col = layer_config["patients_per_physician_column"]
    beds_col = layer_config["beds_column"]
    physicians_col = layer_config["physicians_column"]

    st.subheader(f"{selected_city} deep dive")

    metric_cols = st.columns(5)
    metric_cols[0].metric("HPI", f"{city_row['selected_hpi']:.2f}/100")
    metric_cols[1].metric(
        "Patients per bed",
        format_number(city_row.get(patients_per_bed_col)),
    )
    metric_cols[2].metric(
        "Patients per physician FTE proxy",
        format_number(city_row.get(patients_per_physician_col)),
    )
    metric_cols[3].metric(
        "Bed occupancy",
        format_number(city_row.get("bed_occupancy_rate"), suffix="%"),
    )
    metric_cols[4].metric(
        "Average length of stay",
        format_number(city_row.get("avg_length_of_stay"), suffix=" days"),
    )

    if layer_view == "Demographics":
        extra_metrics = [
            ("Population", "population_total", 0, ""),
            ("65+", "population_65_plus_pct", 1, "%"),
            ("80+", "population_80_plus_pct", 1, "%"),
            ("Unemployment proxy", "unemployment_rate_proxy", 1, "%"),
            ("Long-term unemployment", "long_term_unemployment_rate", 1, "%"),
        ]
        available_extra_metrics = [
            spec for spec in extra_metrics if spec[1] in city_row.index
        ]

        if available_extra_metrics:
            extra_cols = st.columns(len(available_extra_metrics))

            for col, (label, column, decimals, suffix) in zip(
                extra_cols,
                available_extra_metrics,
            ):
                col.metric(label, format_number(city_row[column], decimals, suffix))

    if analysis_layer in [
        "Hospital type corrected",
        "Demographic + socioeconomic adjusted",
    ] and "acute_relevance_factor" in city_row.index:
        st.caption(
            f"Acute relevance factor: "
            f"{format_number(city_row['acute_relevance_factor'], 3)}"
        )

    st.caption(
        f"Beds used: {format_number(city_row.get(beds_col))} | "
        f"Physician FTE proxy used: {format_number(city_row.get(physicians_col))}"
    )

    st.subheader("Pressure drivers")
    pressure_drivers = build_pressure_drivers(city_row, layer_config)

    if pressure_drivers.empty:
        st.warning("No pressure driver scores are available for this city and layer.")
    else:
        driver_fig = px.bar(
            pressure_drivers,
            x="score",
            y="component",
            orientation="h",
            text="label",
            labels={"score": "Relative pressure score", "component": "Component"},
            title="Relative pressure drivers",
        )
        driver_fig.update_traces(textposition="outside", cliponaxis=False)
        driver_fig.update_layout(
            xaxis_range=[0, 120],
            margin={"l": 20, "r": 130, "t": 50, "b": 20},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(driver_fig, use_container_width=True)

    if mode == "Historical":
        city_history_source = historical_all[
            historical_all["city"] == selected_city
        ].copy()
    else:
        city_history_source = forecast_all[
            (forecast_all["city"] == selected_city)
            & (forecast_all["scenario"] == selected_scenario)
        ].copy()

    city_history = add_active_selected_hpi(
        city_history_source,
        hpi_column=selected_hpi_column,
        complete_flag=selected_complete_flag,
    ).sort_values("year")

    st.subheader("Trends")
    trend_col1, trend_col2 = st.columns(2)

    with trend_col1:
        hpi_trend_fig = px.line(
            city_history,
            x="year",
            y="selected_hpi",
            markers=True,
            labels={"year": "Year", "selected_hpi": "Hospital Pressure Index"},
            title="HPI trend",
        )
        hpi_trend_fig.update_layout(yaxis_range=hpi_yaxis_range(city_history))
        st.plotly_chart(hpi_trend_fig, use_container_width=True)

    with trend_col2:
        if beds_col in city_history.columns:
            beds_fig = px.line(
                city_history,
                x="year",
                y=beds_col,
                markers=True,
                labels={"year": "Year", beds_col: "Hospital beds used"},
                title="Beds trend",
            )
            st.plotly_chart(beds_fig, use_container_width=True)
        else:
            st.warning("No beds trend is available for this layer.")

    trend_col3, trend_col4 = st.columns(2)

    with trend_col3:
        if "stationary_patients" in city_history.columns:
            patients_fig = px.line(
                city_history,
                x="year",
                y="stationary_patients",
                markers=True,
                labels={"year": "Year", "stationary_patients": "Stationary patients"},
                title="Patients trend",
            )
            st.plotly_chart(patients_fig, use_container_width=True)
        else:
            st.warning("No patient trend is available.")

    with trend_col4:
        if physicians_col in city_history.columns:
            doctors_fig = px.line(
                city_history,
                x="year",
                y=physicians_col,
                markers=True,
                labels={"year": "Year", physicians_col: "Physician FTE proxy used"},
                title="Physician FTE proxy trend",
            )
            st.plotly_chart(doctors_fig, use_container_width=True)
        else:
            st.warning("No physician trend is available for this layer.")

    st.subheader(f"Layer comparison — {selected_city}")
    comparison_layer_options = get_available_display_layers(mode)
    comparison_internal_layers = [
        DISPLAY_LAYER_TO_INTERNAL[layer_name]
        for layer_name in comparison_layer_options
        if layer_name in DISPLAY_LAYER_TO_INTERNAL
    ]
    comparison_source = historical_all if mode == "Historical" else forecast_all
    layer_comparison_df = build_layer_comparison(
        comparison_source,
        selected_city,
        comparison_internal_layers,
        scenario=selected_scenario if mode == "Forecast" else None,
    )

    st.caption("Layer comparison is shown only for the selected city to avoid clutter.")

    if not layer_comparison_df.empty:
        layer_comparison_fig = px.line(
            layer_comparison_df,
            x="year",
            y="hpi",
            color="layer",
            markers=True,
            labels={
                "year": "Year",
                "hpi": "Hospital Pressure Index",
                "layer": "Layer",
            },
            title=f"Layer comparison — {selected_city}",
        )
        layer_comparison_fig.update_layout(
            yaxis_range=hpi_yaxis_range(layer_comparison_df, "hpi")
        )
        st.plotly_chart(layer_comparison_fig, use_container_width=True)
    else:
        st.warning("No layer comparison data is available for this city.")

    if mode == "Forecast":
        st.subheader("Forecast scenario comparison")
        scenario_comparison_df = build_scenario_comparison(
            forecast_all,
            selected_city,
            hpi_column=selected_hpi_column,
            complete_flag=selected_complete_flag,
        )

        if not scenario_comparison_df.empty:
            scenario_fig = px.line(
                scenario_comparison_df,
                x="year",
                y="hpi",
                color="scenario_label",
                markers=True,
                labels={
                    "year": "Year",
                    "hpi": "Hospital Pressure Index",
                    "scenario_label": "Scenario",
                },
                title=f"HPI forecast by scenario - {selected_city}",
            )
            scenario_fig.update_layout(
                yaxis_range=hpi_yaxis_range(scenario_comparison_df, "hpi")
            )
            st.plotly_chart(scenario_fig, use_container_width=True)

st.info(
    "This dashboard uses official Ruhr/NRW hospital statistics for 2015–2024, "
    "a manually verified hospital registry correction layer, demographic indicators, "
    "socio-economic unemployment indicators, and scenario-based forecasts for 2025–2030. "
    "Forecast demographic and socio-economic indicators are projected from historical "
    "city trends and should be interpreted as scenario assumptions, not official future "
    "statistics."
)
