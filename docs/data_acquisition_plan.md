# Data Acquisition Plan

## Project

Hospital Pressure Index — Ruhrgebiet

## Goal

Build a city-level and later hospital-level dataset for estimating hospital system pressure in the Ruhr region.

The dataset should combine:

- hospital capacity
- patient volume
- bed occupancy
- demographics
- socio-economic indicators
- optional workforce indicators

## Geographic scope

Initial city-level scope:

- Essen
- Dortmund
- Duisburg
- Bochum
- Gelsenkirchen
- Oberhausen
- Mülheim an der Ruhr
- Herne
- Hagen
- Bottrop

Later optional expansion:

- Recklinghausen
- Unna
- Wesel
- Ennepe-Ruhr-Kreis
- Hamm

## Required data fields

### Hospital capacity

Required:

- city
- year
- number_of_hospitals
- number_of_beds
- stationary_patients
- bed_occupancy_rate
- average_length_of_stay

Optional:

- occupied_bed_days
- cases_per_bed
- hospital ownership type
- emergency care participation

### Workforce

Required if available:

- hospital_physicians
- nursing_staff
- total_hospital_staff

Preferred:

- full-time equivalents instead of headcount

### Demographics

Required:

- city
- year
- population_total
- population_65_plus
- population_65_plus_pct

Optional:

- population_80_plus
- population_change_rate

### Socio-economic indicators

Required:

- unemployment_rate

Optional:

- Bürgergeld recipients
- poverty risk proxy
- median income if available

## Target data sources

### IT.NRW

Primary source for NRW and regional/city-level data.

Target datasets:

- hospitals by Kreis / kreisfreie Stadt
- beds by Kreis / kreisfreie Stadt
- stationary patients by Kreis / kreisfreie Stadt
- bed occupancy
- average length of stay
- population by age group
- unemployment or socio-economic indicators where available

### Destatis

Secondary source for national and Bundesland-level validation.

Target datasets:

- Germany hospital statistics
- NRW hospital statistics
- hospital beds
- hospital cases
- hospital personnel
- emergency outpatient cases if available

### Bundesagentur für Arbeit

Source for labour market indicators.

Target datasets:

- unemployment rate by city / Kreis
- Bürgergeld or social benefit indicators if available

### Hospital quality reports

Optional source for hospital-level data.

Target fields:

- hospital name
- address
- beds
- departments
- selected treatment volumes
- quality indicators

## Data storage plan

Raw files should go into:

data/raw/

Cleaned project-ready files should go into:

data/processed/

Expected processed files:

- ruhr_city_hospital_capacity.csv
- ruhr_city_demographics.csv
- ruhr_city_socioeconomics.csv
- ruhr_city_pressure_dataset.csv

## Data quality checks

For every dataset:

- no negative values for beds, hospitals, patients or population
- year must be valid
- city names must be standardized
- missing values must be documented
- source must be documented
- sample data must be clearly marked as sample data

## Methodological notes

The first version of the project will use city-level data.

Hospital-level analysis will be added only when reliable public data is available.

Department-level analysis is optional and should be limited to critical departments such as:

- ICU
- Stroke Unit
- Geriatrics
- Internal Medicine
- Emergency Care

The Hospital Pressure Index is a transparent analytical indicator, not a clinical safety verdict.

## Next steps

1. Identify official IT.NRW datasets for hospital capacity by city/Kreis.
2. Download or manually export first dataset.
3. Store raw file in data/raw/.
4. Create cleaning script in src/data/.
5. Replace sample dashboard dataset with official processed dataset.

## First official dataset candidate

### Open.NRW hospital statistics dataset

Dataset title:

Krankenhausstatistik: Anzahl der Krankenhäuser, aufgestellte Betten, Fallzahl, Berechnungs- und Belegungstage, Verweildauer und Bettennutzung

Why this dataset is relevant:

This dataset contains the core variables required for the first official version of the Hospital Pressure Index:

- number of hospitals
- hospital beds
- inpatient cases
- calculation / occupancy days
- average length of stay
- bed utilization

Geographic level:

- kreisfreie Städte
- Kreise

This matches the planned city-level Ruhrgebiet layer.

Planned usage:

1. Download dataset from Open.NRW.
2. Store original file in data/raw/.
3. Create cleaning script in src/data/.
4. Filter Ruhrgebiet cities.
5. Create data/processed/ruhr_city_hospital_capacity_official.csv.
6. Replace sample hospital capacity values in the dashboard.

## First official dataset candidate

### Open.NRW / Landesdatenbank NRW hospital statistics

Dataset title:

Krankenhausstatistik: Anzahl der Krankenhäuser, aufgestellte Betten, Fallzahl, Berechnungs- und Belegungstage, Verweildauer und Bettennutzung - kreisfreie Städte und Kreise - Stichtag (ab 2002)

Why this dataset matters:

This is the first official dataset candidate for replacing the current sample data. It contains the core variables needed for the city-level Hospital Pressure Index:

- number of hospitals
- hospital beds
- inpatient cases
- calculation / occupancy days
- average length of stay
- bed utilization

Geographic level:

- kreisfreie Städte
- Kreise

This matches the planned Ruhrgebiet city-level layer.

Planned output file:

data/processed/ruhr_city_hospital_capacity_official.csv

Source page:

Open.NRW dataset page for hospital statistics by kreisfreie Städte and Kreise.
