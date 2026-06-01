from pathlib import Path 
import pandas as pd




PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = PROJECT_ROOT/"data"/"processed"/"ruhr_cities_sample.csv"


def load_ruhr_city_sample_data() -> pd.DataFrame:
    """Load the sample data for Ruhr cities."""
    return pd.read_csv(SAMPLE_DATA_PATH)



def add_capacity_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived indicators related to hospital capacity."""
    df=df.copy()
    
    df["patients_per_bed"] = df["stationary_patients"] / df["beds"]
    df["beds_per_1000_population"] = df["beds"] / df["population"] * 1000
    df["patients_per_1000_population"] = df["stationary_patients"] / df["population"] * 1000
    return df