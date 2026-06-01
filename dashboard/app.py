import streamlit as st

from src.features.pressure_index import calculate_hpi

st.set_page_config(
    page_title="Hospital Pressure Index — Ruhrgebiet",
    layout="wide",
)

st.title("Hospital Pressure Index — Ruhrgebiet")
st.caption("Early prototype for estimating hospital system pressure in the Ruhr region.")

st.sidebar.header("Pressure Components")

patient_load = st.sidebar.slider("Patient load pressure", 0, 100, 70)
bed_capacity = st.sidebar.slider("Bed capacity pressure", 0, 100, 65)
occupancy = st.sidebar.slider("Bed occupancy pressure", 0, 100, 80)
demographic = st.sidebar.slider("Demographic pressure", 0, 100, 60)
socioeconomic = st.sidebar.slider("Socio-economic pressure", 0, 100, 55)

hpi = calculate_hpi(
    patient_load_score=patient_load,
    bed_capacity_score=bed_capacity,
    occupancy_score=occupancy,
    demographic_score=demographic,
    socioeconomic_score=socioeconomic,
)

st.metric("Hospital Pressure Index", f"{hpi}/100")

if hpi < 40:
    st.success("Low estimated pressure")
elif hpi < 70:
    st.warning("Moderate estimated pressure")
else:
    st.error("High estimated pressure")

st.markdown(
    """
    ### Current prototype logic

    The index combines:

    - patient load pressure
    - bed capacity pressure
    - bed occupancy pressure
    - demographic pressure
    - socio-economic pressure

    This is not yet based on real Ruhrgebiet data.  
    Next step: connect official NRW / IT.NRW / Destatis datasets.
    """
)