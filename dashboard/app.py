
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.load_city_data import load_official_ruhr_hospital_pressure_data


st.set_page_config(
    page_title="Hospital Pressure Index — Ruhrgebiet",
    layout="wide",
)

st.title("Hospital Pressure Index — Ruhrgebiet")


@st.cache_data
def load_data():
    return load_official_ruhr_hospital_pressure_data()





df_all = load_data()


available_years = sorted(df_all["year"].dropna().unique(), reverse=True)

selected_year = st.sidebar.selectbox(
    "Select year",
    available_years,
    index=0,
)

st.caption(
    f"Official hospital-data prototype for the Ruhr region. Selected year: {selected_year}"
)


df = df_all[df_all["year"] == selected_year].copy()


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
    st.metric("Patients per physician", round(city_row["patients_per_physician"], 1))
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

st.info(
    "This dashboard uses official Ruhr/NRW hospital statistics for 2015–2023. "
    "Current HPI version is hospital-only and does not yet include demographics or socio-economic indicators."
)