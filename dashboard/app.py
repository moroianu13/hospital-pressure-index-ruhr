
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.load_city_data import load_combined_ruhr_hospital_data
from src.features.pressure_index import calculate_hospital_only_hpi, min_max_scale

st.set_page_config(
    page_title="Hospital Pressure Index — Ruhrgebiet",
    layout="wide",
)

st.title("Hospital Pressure Index — Ruhrgebiet")


@st.cache_data
def load_data():
    return load_combined_ruhr_hospital_data()





df_all = load_data()

available_years = sorted(df_all["year"].dropna().unique(), reverse=True)

selected_year = st.sidebar.selectbox(
    "Select year",
    available_years,
    index=0,
)

df = df_all[df_all["year"] == selected_year].copy()



required_raw_columns = [
    "stationary_patients",
    "beds",
    "hospital_physicians",
    "bed_occupancy_rate",
    "avg_length_of_stay",
    "patients_per_bed",
    "patients_per_physician",
]

df_complete = df[
    df[required_raw_columns].notna().all(axis=1)
    & (df["stationary_patients"] > 0)
    & (df["beds"] > 0)
    & (df["hospital_physicians"] > 0)
    & (df["bed_occupancy_rate"] > 0)
    & (df["avg_length_of_stay"] > 0)
].copy()

df_incomplete = df[~df.index.isin(df_complete.index)].copy()


def add_score_column(frame, source_column, score_column):
    min_value = frame[source_column].min()
    max_value = frame[source_column].max()

    frame[score_column] = frame[source_column].apply(
        lambda x: min_max_scale(x, min_value, max_value)
    )

    return frame


df_complete = add_score_column(
    df_complete,
    "patients_per_bed",
    "patients_per_bed_score",
)

df_complete = add_score_column(
    df_complete,
    "patients_per_physician",
    "patients_per_physician_score",
)

df_complete = add_score_column(
    df_complete,
    "bed_occupancy_rate",
    "occupancy_score",
)

df_complete = add_score_column(
    df_complete,
    "avg_length_of_stay",
    "length_of_stay_score",
)

df_complete["hpi"] = df_complete.apply(
    lambda row: calculate_hospital_only_hpi(
        patients_per_bed_score=row["patients_per_bed_score"],
        patients_per_physician_score=row["patients_per_physician_score"],
        occupancy_score=row["occupancy_score"],
        length_of_stay_score=row["length_of_stay_score"],
    ),
    axis=1,
)





if not df_incomplete.empty:
    missing_cities = ", ".join(sorted(df_incomplete["city"].unique()))

    st.warning(
        f"The following cities are excluded from the HPI ranking for {selected_year} "
        f"because official hospital data is incomplete or suppressed: {missing_cities}."
    )

st.caption(
    f"Official hospital-data prototype for the Ruhr region. Selected year: {selected_year}"
)

avg_hpi = round(df_complete["hpi"].mean(), 2)
highest_city = df_complete.sort_values("hpi", ascending=False).iloc[0]
lowest_city = df_complete.sort_values("hpi", ascending=True).iloc[0]

col1, col2, col3 = st.columns(3)

col1.metric("Average Ruhr HPI", f"{avg_hpi}/100")
col2.metric("Highest pressure city", f"{highest_city['city']} ({highest_city['hpi']:.2f}/100)")
col3.metric("Lowest pressure city", f"{lowest_city['city']} ({lowest_city['hpi']:.2f}/100)")

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Hospital Pressure Index by city")
    fig = px.bar(
        df_complete.sort_values("hpi", ascending=False),
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
    selected_city = st.selectbox("Select city", df_complete["city"].sort_values())
    city_row = df_complete[df_complete["city"] == selected_city].iloc[0]
    
    
    
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

   

   

st.subheader("City-level dataset")

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

st.info(
    "This dashboard uses official Ruhr/NRW hospital statistics for 2015–2024. " 
    "Current HPI version is hospital-only and does not yet include demographics or socio-economic indicators."
)


if not df_incomplete.empty:
    excluded_cities = ", ".join(sorted(df_incomplete["city"].unique()))

    st.warning(
        f"Excluded from HPI ranking for {selected_year} due to incomplete or "
        f"suppressed official data: {excluded_cities}."
    )