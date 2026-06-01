"""
Hospital Pressure Index calculations.

This module contains transparent, rule-based indicators for estimating
hospital system pressure from demand, capacity, demographic, and social factors.
"""

from __future__ import annotations


def min_max_scale(value: float, min_value: float, max_value: float) -> float:
    """
    Scale a value to a 0-100 range.

    If min_value == max_value, returns 0 to avoid division by zero.
    """
    if max_value == min_value:
        return 0.0

    scaled = (value - min_value) / (max_value - min_value) * 100
    return max(0.0, min(100.0, scaled))


def calculate_hpi(
    patient_load_score: float,
    bed_capacity_score: float,
    occupancy_score: float,
    demographic_score: float,
    socioeconomic_score: float,
) -> float:
    """
    Calculate the Hospital Pressure Index.

    All input scores should be between 0 and 100.

    Weights:
    - patient load: 30%
    - bed capacity pressure: 25%
    - occupancy: 20%
    - demographic pressure: 15%
    - socioeconomic pressure: 10%
    """
    hpi = (
        patient_load_score * 0.30
        + bed_capacity_score * 0.25
        + occupancy_score * 0.20
        + demographic_score * 0.15
        + socioeconomic_score * 0.10
    )

    return round(hpi, 2)