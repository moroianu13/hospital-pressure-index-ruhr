from src.features.pressure_index import calculate_hpi, min_max_scale


def test_min_max_scale_basic():
    assert min_max_scale(50, 0, 100) == 50


def test_min_max_scale_clips_low_values():
    assert min_max_scale(-10, 0, 100) == 0


def test_min_max_scale_clips_high_values():
    assert min_max_scale(120, 0, 100) == 100


def test_calculate_hpi_returns_expected_weighted_score():
    result = calculate_hpi(
        patient_load_score=80,
        bed_capacity_score=70,
        occupancy_score=90,
        demographic_score=60,
        socioeconomic_score=50,
    )

    assert result == 73.5
    