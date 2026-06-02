
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.load_city_data import (
    load_combined_ruhr_hospital_pressure_data,
    load_ruhr_hospital_forecast_data,
)


st.set_page_config(
    page_title="Hospital Pressure Index — Ruhrgebiet",
    layout="wide",
)

st.title("Hospital Pressure Index — Ruhrgebiet")


@st.cache_data
def load_historical_data() -> pd.DataFrame:
    """Load official hospital data with HPI scores."""
    return load_combined_ruhr_hospital_pressure_data()


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

if mode == "Historical":
    available_years = sorted(historical_all["year"].dropna().unique(), reverse=True)

    selected_year = st.sidebar.selectbox(
        "Select year",
        available_years,
        index=0,
    )

    selected_scenario = None

    df = historical_all[historical_all["year"] == selected_year].copy()
    df_complete = df[df["is_hpi_complete"]].copy()
    df_incomplete = df[~df["is_hpi_complete"]].copy()

    st.caption(
        f"Official hospital-data prototype for the Ruhr region. "
        f"Selected year: {selected_year}"
    )
    
else:
    SCENARIO_LABELS = {
    "business_as_usual": "Business as usual",
    "stress": "Stress scenario",
    "recruitment_improvement": "Recruitment improvement",
    "capacity_decline": "Capacity decline",
}
    available_scenarios = sorted(forecast_all["scenario"].dropna().unique())

    selected_scenario_label = st.sidebar.selectbox(
    "Select scenario",
    [SCENARIO_LABELS.get(s, s) for s in available_scenarios],
)

    selected_scenario = {
    label: scenario for scenario, label in SCENARIO_LABELS.items()
}.get(selected_scenario_label, selected_scenario_label)



    available_years = sorted(forecast_all["year"].dropna().unique())

    selected_year = st.sidebar.selectbox(
        "Select forecast year",
        available_years,
        index=0,
    )

    df = forecast_all[
        (forecast_all["scenario"] == selected_scenario)
        & (forecast_all["year"] == selected_year)
    ].copy()

    df_complete = df.copy()
    df_incomplete = pd.DataFrame()

    st.caption(
        f"Forecast mode for the Ruhr region. "
        f"Scenario: {selected_scenario_label}. Selected year: {selected_year}"
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
        f"Excluded from HPI ranking for {selected_year} due to incomplete or "
        f"suppressed official data: {excluded_cities}."
    )


avg_hpi = round(df_complete["hpi"].mean(), 2)
highest_city = df_complete.sort_values("hpi", ascending=False).iloc[0]
lowest_city = df_complete.sort_values("hpi", ascending=True).iloc[0]

col1, col2, col3 = st.columns(3)

col1.metric("Average Ruhr HPI", f"{avg_hpi:.2f}/100")
col2.metric(
    "Highest pressure city",
    f"{highest_city['city']} ({highest_city['hpi']:.2f}/100)",
)
col3.metric(
    "Lowest pressure city",
    f"{lowest_city['city']} ({lowest_city['hpi']:.2f}/100)",
)

st.divider()

left, right = st.columns([2, 1])

with left:
    chart_title = (
        "Hospital Pressure Index by city"
        if mode == "Historical"
        else f"Forecast HPI by city — {selected_scenario}"
    )

    st.subheader(chart_title)

    ranking_fig = px.bar(
        df_complete.sort_values("hpi", ascending=False),
        x="city",
        y="hpi",
        text="hpi",
        labels={"hpi": "Hospital Pressure Index", "city": "City"},
    )

    ranking_fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
    )
    ranking_fig.update_layout(yaxis_range=[0, 100])

    st.plotly_chart(ranking_fig, use_container_width=True)

with right:
    selected_city = st.selectbox(
        "Select city",
        df_complete["city"].sort_values(),
    )

    city_row = df_complete[df_complete["city"] == selected_city].iloc[0]

    st.subheader(selected_city)
    st.metric("HPI", f"{city_row['hpi']:.2f}/100")
    st.metric("Patients per bed", f"{city_row['patients_per_bed']:.1f}")
    st.metric("Patients per physician", f"{city_row['patients_per_physician']:.1f}")
    st.metric("Bed occupancy", f"{city_row['bed_occupancy_rate']:.1f}%")
    st.metric("Average length of stay", f"{city_row['avg_length_of_stay']:.1f} days")

    component_df = pd.DataFrame(
        {
            "component": [
                "Patients per bed",
                "Patients per physician",
                "Occupancy",
                "Length of stay",
            ],
            "score": [
                city_row["patients_per_bed_score"],
                city_row["patients_per_physician_score"],
                city_row["occupancy_score"],
                city_row["length_of_stay_score"],
            ],
            "actual_value": [
                f"{city_row['patients_per_bed']:.1f}",
                f"{city_row['patients_per_physician']:.1f}",
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
        "Driver scores are relative within the selected year. "
        "A score of 0 means lowest pressure among included cities for that metric, "
        "not a missing or zero real value."
    )

st.divider()

if mode == "Historical":
    city_history = historical_all[
        (historical_all["city"] == selected_city)
        & (historical_all["is_hpi_complete"])
    ].sort_values("year")

    trends_title = f"Historical trends — {selected_city}"
else:
    city_history = forecast_all[
        (forecast_all["city"] == selected_city)
        & (forecast_all["scenario"] == selected_scenario)
    ].sort_values("year")

    trends_title = f"Forecast trends — {selected_city} — {selected_scenario}"

st.subheader(trends_title)

trend_col1, trend_col2 = st.columns(2)

with trend_col1:
    hpi_trend_fig = px.line(
        city_history,
        x="year",
        y="hpi",
        markers=True,
        labels={"year": "Year", "hpi": "Hospital Pressure Index"},
        title="HPI trend",
    )
    hpi_trend_fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(hpi_trend_fig, use_container_width=True)

with trend_col2:
    beds_fig = px.line(
        city_history,
        x="year",
        y="beds",
        markers=True,
        labels={"year": "Year", "beds": "Hospital beds"},
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
        y="hospital_physicians",
        markers=True,
        labels={"year": "Year", "hospital_physicians": "Hospital physicians"},
        title="Doctors trend",
    )
    st.plotly_chart(doctors_fig, use_container_width=True)

st.divider()

if mode == "Historical":
    st.subheader("City-level dataset — complete HPI rows")

    st.dataframe(
        df_complete[
            [
                "city",
                "year",
                "hospitals",
                "hospital_physicians",
                "beds",
                "stationary_patients",
                "bed_occupancy_rate",
                "avg_length_of_stay",
                "patients_per_bed",
                "patients_per_physician",
                "hpi",
            ]
        ].sort_values("hpi", ascending=False),
        use_container_width=True,
    )

    if not df_incomplete.empty:
        st.subheader("Excluded rows — incomplete official data")

        st.dataframe(
            df_incomplete[
                [
                    "city",
                    "year",
                    "hospitals",
                    "hospital_physicians",
                    "beds",
                    "stationary_patients",
                    "bed_occupancy_rate",
                    "avg_length_of_stay",
                    "data_completeness_status",
                ]
            ].sort_values("city"),
            use_container_width=True,
        )

else:
    st.subheader("Forecast dataset — selected scenario and year")

    st.dataframe(
        df_complete[
            [
                "city",
                "year",
                "scenario",
                "hospital_physicians",
                "beds",
                "stationary_patients",
                "bed_occupancy_rate",
                "avg_length_of_stay",
                "patients_per_bed",
                "patients_per_physician",
                "hpi",
            ]
        ].sort_values("hpi", ascending=False),
        use_container_width=True,
    )

st.info(
    "This dashboard uses official Ruhr/NRW hospital statistics for 2015–2024 "
    "and scenario-based forecasts for 2025–2030. "
    "The current HPI is hospital-only and does not yet include demographic or "
    "socio-economic indicators."
)
