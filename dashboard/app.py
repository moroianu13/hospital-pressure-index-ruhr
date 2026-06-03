
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.load_city_data import (
    load_adjusted_ruhr_hospital_pressure_data,
    load_ruhr_hospital_forecast_data,
)


SCENARIO_LABELS = {
    "business_as_usual": "Business as usual",
    "stress": "Stress scenario",
    "recruitment_improvement": "Recruitment improvement",
    "capacity_decline": "Capacity decline",
}

SCENARIO_LABEL_TO_KEY = {
    label: key for key, label in SCENARIO_LABELS.items()
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
}


st.set_page_config(
    page_title="Hospital Pressure Index — Ruhrgebiet",
    layout="wide",
)

st.title("Hospital Pressure Index — Ruhrgebiet")


@st.cache_data
def load_historical_data() -> pd.DataFrame:
    """Load historical hospital pressure data with analysis layers."""
    return load_adjusted_ruhr_hospital_pressure_data()


@st.cache_data
def load_forecast_data() -> pd.DataFrame:
    """Load forecast hospital pressure data."""
    return load_ruhr_hospital_forecast_data()


historical_all = load_historical_data()
forecast_all = load_forecast_data()

mode = st.sidebar.radio(
    "Mode",
    ["Historical", "Forecast"],
)

selected_scenario = None
selected_scenario_label = None

if mode == "Historical":
    analysis_layer = st.sidebar.radio(
        "Analysis layer",
        list(ANALYSIS_LAYERS.keys()),
    )

    layer_config = ANALYSIS_LAYERS[analysis_layer]
    selected_hpi_column = layer_config["hpi_column"]
    complete_flag = layer_config["complete_flag"]

    selected_year = int(historical_all["year"].dropna().max())

    df = historical_all[historical_all["year"] == selected_year].copy()
    df_complete = df[df[complete_flag]].copy()
    df_incomplete = df[~df[complete_flag]].copy()

    df_complete["selected_hpi"] = df_complete[selected_hpi_column]

    st.caption(
        f"Historical mode. Layer: {analysis_layer}. "
        f"Cards/table use latest available year: {selected_year}"
    )

else:
    analysis_layer = st.sidebar.radio(
        "Analysis layer",
        list(ANALYSIS_LAYERS.keys()),
    )

    layer_config = ANALYSIS_LAYERS[analysis_layer]
    selected_hpi_column = layer_config["hpi_column"]
    complete_flag = layer_config["complete_flag"]

    available_scenarios = sorted(forecast_all["scenario"].dropna().unique())
    available_scenario_labels = [
        SCENARIO_LABELS.get(scenario, scenario)
        for scenario in available_scenarios
    ]

    selected_scenario_label = st.sidebar.selectbox(
        "Select scenario",
        available_scenario_labels,
    )

    selected_scenario = SCENARIO_LABEL_TO_KEY.get(
        selected_scenario_label,
        selected_scenario_label,
    )

    selected_year = int(forecast_all["year"].dropna().max())

    df = forecast_all[
        (forecast_all["scenario"] == selected_scenario)
        & (forecast_all["year"] == selected_year)
    ].copy()

    df_complete = df[df[complete_flag]].copy()
    df_complete["selected_hpi"] = df_complete[selected_hpi_column]
    df_incomplete = df[~df[complete_flag]].copy()

    st.caption(
        f"Forecast mode. Scenario: {selected_scenario_label}. "
        f"Layer: {analysis_layer}. "
        f"Cards/table use final forecast year: {selected_year}"
    )

if df_complete.empty:
    st.error(
        f"No complete HPI data available for {selected_year}. "
        "All cities have missing or suppressed official data."
    )
    st.stop()


if mode == "Historical" and not df_incomplete.empty:
    excluded_cities = ", ".join(sorted(df_incomplete["city"].unique()))

    st.warning(
        f"Excluded from {analysis_layer} ranking for {selected_year} due to incomplete "
        f"or suppressed official data: {excluded_cities}."
    )


avg_hpi = round(df_complete["selected_hpi"].mean(), 2)
highest_city = df_complete.sort_values("selected_hpi", ascending=False).iloc[0]
lowest_city = df_complete.sort_values("selected_hpi", ascending=True).iloc[0]

col1, col2, col3 = st.columns(3)

col1.metric("Average Ruhr HPI", f"{avg_hpi:.2f}/100")
col2.metric(
    "Highest pressure city",
    f"{highest_city['city']} ({highest_city['selected_hpi']:.2f}/100)",
)
col3.metric(
    "Lowest pressure city",
    f"{lowest_city['city']} ({lowest_city['selected_hpi']:.2f}/100)",
)

st.divider()

left, right = st.columns([2, 1])

with left:
    if mode == "Historical":
        st.subheader(f"HPI evolution by city — 2015–2024 — {analysis_layer}")

        historical_complete_all = historical_all[
            historical_all[complete_flag]
        ].copy()

        historical_complete_all["selected_hpi"] = historical_complete_all[
            selected_hpi_column
        ]

        central_fig = px.line(
            historical_complete_all,
            x="year",
            y="selected_hpi",
            color="city",
            markers=True,
            labels={
                "year": "Year",
                "selected_hpi": "Hospital Pressure Index",
                "city": "City",
            },
            title=f"Historical HPI evolution by city — {analysis_layer}",
        )

        central_fig.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(central_fig, use_container_width=True)

        st.caption(
            "This chart shows HPI evolution for all included Ruhr cities. "
            "The selected analysis layer changes how pressure is calculated."
        )

    else:
        st.subheader(f"Forecast HPI comparison by city — {selected_scenario_label}")

        scenario_history = forecast_all[
            forecast_all["scenario"] == selected_scenario
        ].copy()

        scenario_history = scenario_history[scenario_history[complete_flag]].copy()
        scenario_history["selected_hpi"] = scenario_history[selected_hpi_column]

        central_fig = px.line(
            scenario_history,
            x="year",
            y="selected_hpi",
            color="city",
            markers=True,
            labels={
                "year": "Year",
                "selected_hpi": "Hospital Pressure Index",
                "city": "City",
            },
            title="Forecast HPI evolution by city, 2025–2030",
        )

        central_fig.update_layout(yaxis_range=[0, 100])
        st.plotly_chart(central_fig, use_container_width=True)

        st.caption(
            "Forecast currently uses the hospital-system layer. "
            "Hospital type corrected forecast can be added after validating the historical layer."
        )


with right:
    selected_city = st.selectbox(
        "Select city",
        df_complete["city"].sort_values(),
    )

    city_row = df_complete[df_complete["city"] == selected_city].iloc[0]

    if mode == "Historical":
        patients_per_bed_col = layer_config["patients_per_bed_column"]
        patients_per_physician_col = layer_config["patients_per_physician_column"]
        beds_col = layer_config["beds_column"]
        physicians_col = layer_config["physicians_column"]

        patients_per_bed_score_col = layer_config["patients_per_bed_score"]
        patients_per_physician_score_col = layer_config["patients_per_physician_score"]
        occupancy_score_col = layer_config["occupancy_score"]
        length_of_stay_score_col = layer_config["length_of_stay_score"]

    else:
        patients_per_bed_col = "patients_per_bed"
        patients_per_physician_col = "patients_per_physician"
        beds_col = "beds"
        physicians_col = "hospital_physicians"

        patients_per_bed_score_col = "patients_per_bed_score"
        patients_per_physician_score_col = "patients_per_physician_score"
        occupancy_score_col = "occupancy_score"
        length_of_stay_score_col = "length_of_stay_score"

    st.subheader(selected_city)
    st.metric("HPI", f"{city_row['selected_hpi']:.2f}/100")
    st.metric("Patients per bed", f"{city_row[patients_per_bed_col]:.1f}")
    st.metric(
        "Patients per physician FTE proxy",
        f"{city_row[patients_per_physician_col]:.1f}",
    )
    st.metric("Bed occupancy", f"{city_row['bed_occupancy_rate']:.1f}%")
    st.metric("Average length of stay", f"{city_row['avg_length_of_stay']:.1f} days")

    if mode == "Historical":
        st.caption(
            f"Beds used: {city_row[beds_col]:.1f} | "
            f"Physician FTE proxy used: {city_row[physicians_col]:.1f}"
        )

        if analysis_layer == "Hospital type corrected":
            st.caption(
                f"Acute relevance factor: {city_row['acute_relevance_factor']:.3f}"
            )
    else:
        st.caption(
            f"Physician FTE proxy forecast: {city_row['hospital_physicians']:.1f}"
        )

    component_df = pd.DataFrame(
        {
            "component": [
                "Patients per bed",
                "Patients per physician FTE proxy",
                "Occupancy",
                "Length of stay",
            ],
            "score": [
                city_row[patients_per_bed_score_col],
                city_row[patients_per_physician_score_col],
                city_row[occupancy_score_col],
                city_row[length_of_stay_score_col],
            ],
            "actual_value": [
                f"{city_row[patients_per_bed_col]:.1f}",
                f"{city_row[patients_per_physician_col]:.1f}",
                f"{city_row['bed_occupancy_rate']:.1f}%",
                f"{city_row['avg_length_of_stay']:.1f} days",
            ],
        }
    )

    component_df["label"] = component_df.apply(
        lambda row: f"{row['score']:.1f} | actual: {row['actual_value']}",
        axis=1,
    )

    component_fig = px.bar(
        component_df,
        x="score",
        y="component",
        orientation="h",
        text="label",
        labels={"score": "Relative pressure score", "component": "Component"},
        title="Relative pressure drivers",
    )

    component_fig.update_traces(
        textposition="outside",
        cliponaxis=False,
    )

    component_fig.update_layout(
        xaxis_range=[0, 120],
        margin=dict(l=20, r=120, t=50, b=20),
    )

    st.plotly_chart(component_fig, use_container_width=True)

    st.caption(
        "Driver scores are relative within the selected year/layer. "
        "A score of 0 means lowest pressure among included cities for that metric, "
        "not a missing or zero real value."
    )


st.divider()

if mode == "Historical":
    city_history = historical_all[
        (historical_all["city"] == selected_city)
        & (historical_all[complete_flag])
    ].sort_values("year").copy()

    city_history["selected_hpi"] = city_history[selected_hpi_column]

    trends_title = f"Historical trends — {selected_city} — {analysis_layer}"

else:
    city_history = forecast_all[
        (forecast_all["city"] == selected_city)
        & (forecast_all["scenario"] == selected_scenario)
    ].sort_values("year").copy()

    city_history = city_history[city_history[complete_flag]].copy()
    city_history["selected_hpi"] = city_history[selected_hpi_column]

    trends_title = f"Forecast trends — {selected_city} — {selected_scenario_label}"


st.subheader(trends_title)

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
    hpi_trend_fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(hpi_trend_fig, use_container_width=True)

with trend_col2:
    beds_fig = px.line(
        city_history,
        x="year",
        y=beds_col,
        markers=True,
        labels={"year": "Year", beds_col: "Hospital beds used"},
        title="Beds trend",
    )
    st.plotly_chart(beds_fig, use_container_width=True)

trend_col3, trend_col4 = st.columns(2)

with trend_col3:
    patients_fig = px.line(
        city_history,
        x="year",
        y="stationary_patients",
        markers=True,
        labels={"year": "Year", "stationary_patients": "Stationary patients"},
        title="Patients trend",
    )
    st.plotly_chart(patients_fig, use_container_width=True)

with trend_col4:
    doctors_fig = px.line(
        city_history,
        x="year",
        y=physicians_col,
        markers=True,
        labels={"year": "Year", physicians_col: "Physician FTE proxy used"},
        title="Physician FTE proxy trend",
    )
    st.plotly_chart(doctors_fig, use_container_width=True)


if mode == "Forecast":
    st.divider()

    st.subheader(f"Scenario comparison for selected city — {selected_city}")

    scenario_city_history = forecast_all[
        forecast_all["city"] == selected_city
    ].copy()

    scenario_city_history = scenario_city_history[
        scenario_city_history[complete_flag]
    ].copy()
    scenario_city_history["selected_hpi"] = scenario_city_history[selected_hpi_column]

    scenario_city_history["scenario_label"] = scenario_city_history["scenario"].map(
        SCENARIO_LABELS
    ).fillna(scenario_city_history["scenario"])

    scenario_comparison_fig = px.line(
        scenario_city_history,
        x="year",
        y="selected_hpi",
        color="scenario_label",
        markers=True,
        labels={
            "year": "Year",
            "selected_hpi": "Hospital Pressure Index",
            "scenario_label": "Scenario",
        },
        title=f"HPI forecast by scenario — {selected_city}",
    )

    scenario_comparison_fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(scenario_comparison_fig, use_container_width=True)

    st.caption(
        "This chart compares all forecast scenarios for the selected city from 2025 to 2030."
    )


st.divider()

if mode == "Historical":
    st.subheader("City-level dataset — selected analysis layer")

    table_columns = [
        "city",
        "year",
        "hospitals",
        "acute_relevance_factor",
        "beds",
        "adjusted_beds",
        "hospital_physicians_headcount",
        "hospital_physicians_fte_proxy",
        "adjusted_hospital_physicians",
        "stationary_patients",
        "bed_occupancy_rate",
        "avg_length_of_stay",
        "patients_per_bed",
        "adjusted_patients_per_bed",
        "patients_per_physician",
        "adjusted_patients_per_physician",
        "hospital_hpi",
        "acute_care_adjusted_hpi",
    ]

    existing_table_columns = [
        column for column in table_columns if column in df_complete.columns
    ]

    st.dataframe(
        df_complete[existing_table_columns].sort_values(
            selected_hpi_column,
            ascending=False,
        ),
        use_container_width=True,
    )

    if not df_incomplete.empty:
        st.subheader("Excluded rows — incomplete official data")

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

        existing_excluded_columns = [
            column for column in excluded_columns if column in df_incomplete.columns
        ]

        st.dataframe(
            df_incomplete[existing_excluded_columns].sort_values("city"),
            use_container_width=True,
        )

else:
    st.subheader("Forecast dataset — selected scenario and final year")

    st.dataframe(
        df_complete[
            [
                "city",
                "year",
                "scenario",
                "forecast_confidence",
                "acute_relevance_factor",
                "beds",
                "adjusted_beds",
                "hospital_physicians",
                "adjusted_hospital_physicians",
                "stationary_patients",
                "bed_occupancy_rate",
                "avg_length_of_stay",
                "patients_per_bed",
                "adjusted_patients_per_bed",
                "patients_per_physician",
                "adjusted_patients_per_physician",
                "hospital_hpi",
                "acute_care_adjusted_hpi",
            ]
        ].sort_values(selected_hpi_column, ascending=False),
        use_container_width=True,
    )


st.info(
    "This dashboard uses official Ruhr/NRW hospital statistics for 2015–2024, "
    "a manually verified hospital registry correction layer, and scenario-based "
    "forecasts for 2025–2030. "
    "The demographic and socio-economic layers are planned but not yet included."
)
