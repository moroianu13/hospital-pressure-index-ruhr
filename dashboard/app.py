
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.load_city_data import load_prepared_ruhr_city_data
from src.features.pressure_index import min_max_scale

st.set_page_config(
    page_title="Hospital Pressure Index — Ruhrgebiet",
    layout="wide",
)

st.title("Hospital Pressure Index — Ruhrgebiet")
st.caption("Prototype for estimating hospital system pressure in the Ruhr region.")

@st.cache_data
def load_data():
    return load_prepared_ruhr_city_data()


def calculate_hpi(patient_load_score, bed_capacity_score, patients_per_bed_score, occupancy_score, demographic_score, socioeconomic_score):
    """Calculate Hospital Pressure Index as weighted average of components."""
    return (
        patient_load_score * 0.25 +
        bed_capacity_score * 0.20 +
        patients_per_bed_score * 0.20 +
        occupancy_score * 0.20 +
        demographic_score * 0.10 +
        socioeconomic_score * 0.05
    )


df = load_data()

# Basic derived indicators
df["patients_per_bed"] = df["stationary_patients"] / df["beds"]
df["beds_per_1000_population"] = df["beds"] / df["population"] * 1000
df["patients_per_bed_score"] = df["patients_per_bed"].apply(
    lambda x: min_max_scale(
        x,
        df["patients_per_bed"].min(),
        df["patients_per_bed"].max(),
    )
)
df["patients_per_1000_population"] = df["stationary_patients"] / df["population"] * 1000

# Pressure components
df["patient_load_score"] = df["patients_per_1000_population"].apply(
    lambda x: min_max_scale(x, df["patients_per_1000_population"].min(), df["patients_per_1000_population"].max())
)

# Lower beds per population = higher pressure, so we invert it
df["bed_capacity_score"] = df["beds_per_1000_population"].apply(
    lambda x: 100 - min_max_scale(x, df["beds_per_1000_population"].min(), df["beds_per_1000_population"].max())
)

df["occupancy_score"] = df["bed_occupancy_rate"].apply(
    lambda x: min_max_scale(x, df["bed_occupancy_rate"].min(), df["bed_occupancy_rate"].max())
)

df["demographic_score"] = df["population_65_plus_pct"].apply(
    lambda x: min_max_scale(x, df["population_65_plus_pct"].min(), df["population_65_plus_pct"].max())
)

df["socioeconomic_score"] = df["unemployment_rate"].apply(
    lambda x: min_max_scale(x, df["unemployment_rate"].min(), df["unemployment_rate"].max())
)

df["hpi"] = df.apply(
    lambda row: calculate_hpi(
        patient_load_score=row["patient_load_score"],
        bed_capacity_score=row["bed_capacity_score"],
        patients_per_bed_score=row["patients_per_bed_score"],
        occupancy_score=row["occupancy_score"],
        demographic_score=row["demographic_score"],
        socioeconomic_score=row["socioeconomic_score"],
    ),
    axis=1,
)


avg_hpi = round(df["hpi"].mean(), 2)
highest_city = df.sort_values("hpi", ascending=False).iloc[0]
lowest_city = df.sort_values("hpi", ascending=True).iloc[0]

col1, col2, col3 = st.columns(3)

col1.metric("Average Ruhr HPI", f"{avg_hpi}/100")
col2.metric("Highest pressure city", f"{highest_city['city']} ({highest_city['hpi']:.2f}/100)")
col3.metric("Lowest pressure city", f"{lowest_city['city']} ({lowest_city['hpi']:.2f}/100)")

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Hospital Pressure Index by city")
    fig = px.bar(
        df.sort_values("hpi", ascending=False),
        x="city",
        y="hpi",
        text="hpi",
        labels={"hpi": "Hospital Pressure Index", "city": "City"},
    )
    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside")
    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

with right:
    selected_city = st.selectbox("Select city", df["city"].sort_values())
    city_row = df[df["city"] == selected_city].iloc[0]

    st.subheader(selected_city)
    st.metric("HPI", f"{city_row['hpi']:.2f}/100")
    st.metric("Patients per bed", round(city_row["patients_per_bed"], 1))
    st.metric("Beds per 1,000 population", round(city_row["beds_per_1000_population"], 2))
    st.metric("Bed occupancy", f"{city_row['bed_occupancy_rate']:.1f}%")

    component_df = pd.DataFrame(
        {
            "component": [
                "Patient load",
                "Bed capacity",
                "Occupancy",
                "Demographic",
                "Socio-economic",
                "Patients per bed",
            ],
            "score": [
                city_row["patient_load_score"],
                city_row["bed_capacity_score"],
                city_row["occupancy_score"],
                city_row["demographic_score"],
                city_row["socioeconomic_score"],
                city_row["patients_per_bed_score"],
            ]
        }
    )

    component_fig = px.bar(
        component_df,
        x="score",
        y="component",
        orientation="h",
        text="score",
        labels={"score": "Pressure score", "component": "Component"},
        title="Pressure drivers",
    )
    component_fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    component_fig.update_layout(xaxis_range=[0, 100])

    st.plotly_chart(component_fig, use_container_width=True)
st.divider()

st.subheader("City-level dataset")
st.dataframe(
    df[
        [
            "city",
            "population",
            "hospitals",
            "beds",
            "stationary_patients",
            "bed_occupancy_rate",
            "population_65_plus_pct",
            "unemployment_rate",
            "hpi",
        ]
    ].sort_values("hpi", ascending=False),
    use_container_width=True,
)

st.warning(
    "Current data is sample data for prototyping. Next step: replace it with official IT.NRW / Destatis data."
)