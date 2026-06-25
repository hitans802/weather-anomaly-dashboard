# Melbourne Weather Anomaly Monitoring Dashboard

## About the Project

Weather forecasts are useful for understanding upcoming conditions, but they do not indicate whether those conditions are unusual. This project focuses on identifying weather patterns that differ significantly from recent historical behaviour rather than simply displaying daily forecasts.

The application automatically retrieves the latest weather data for Melbourne from the Open-Meteo API whenever the dashboard is opened. The data is then validated, cleaned, transformed into daily weather summaries, analysed for anomalies, and presented through an interactive Streamlit dashboard.

The dashboard combines 60 days of historical weather observations with a 5-day forecast, providing both context and an early indication of potential weather anomalies.

---

## Features

* Automatic retrieval of live weather data
* Data validation and cleaning
* Hourly weather observations aggregated into daily summaries
* Statistical anomaly detection for temperature, wind speed and rainfall
* Interactive Streamlit dashboard
* Historical weather trends
* Historical anomaly monitoring
* Five-day forecast anomaly monitoring
* Human-readable explanations describing why an anomaly was detected
* Automatic pipeline execution whenever the dashboard is launched

---

## How the Dashboard Works

Opening the dashboard automatically triggers the complete data processing pipeline.

The application performs the following steps:

1. Retrieves the latest weather data from the Open-Meteo API.
2. Validates the API response.
3. Cleans and processes the hourly weather observations.
4. Aggregates the hourly data into daily weather summaries.
5. Detects unusual weather events using statistical methods.
6. Stores the latest processed dataset.
7. Displays the updated information through the dashboard.

Because the pipeline runs automatically, the dashboard always displays the most recent available weather data without requiring any manual updates.

---

## Dashboard Overview

The dashboard is organised into several sections to provide a clear overview of current and upcoming weather conditions.

### Summary

The summary section provides a quick overview of:

* Current weather status
* Latest available date
* Number of detected anomalous days
* Most recent anomaly

### Latest Weather Insight

This section highlights the latest available day's weather conditions and explains whether any unusual behaviour has been detected.

Instead of displaying technical statistics alone, anomalies are explained in plain language. For example:

Temperature averaged 29.4°C, which was 6.2°C warmer than the recent 14-day average of 23.2°C.

### Weather Trends

Historical observations and forecast data are visualised using interactive charts showing:

* Average daily temperature
* Average daily wind speed
* Total daily rainfall

Detected anomalies are highlighted directly on the graphs.

### Historical Anomalies

Displays unusual weather events that have already occurred based on observed historical data.

### Forecast Anomalies

Displays potential weather anomalies predicted within the next five days, providing an early indication of unusual upcoming conditions.

---

## Project Architecture

The project is organised into two main components.

### Backend

The backend is responsible for collecting and processing the weather data.

Its responsibilities include:

* Retrieving weather data from the Open-Meteo API
* Validating the API response
* Cleaning the raw data
* Aggregating hourly observations into daily weather summaries
* Detecting anomalies
* Saving the processed dataset

### Dashboard

The dashboard is responsible for presenting the processed data.

Rather than interacting directly with the weather API, it reads the latest processed dataset created by the backend pipeline and visualises the results through interactive charts, summary cards and anomaly tables.

Separating the processing pipeline from the dashboard keeps the application modular, easier to maintain and easier to extend.

---

## Anomaly Detection

Different weather variables exhibit different statistical behaviour, so different detection methods are used.

### Temperature

Temperature anomalies are detected using a rolling 14-day baseline.

Each day's average temperature is compared against recent historical observations using a Z-score. Days with unusually high or low temperatures are flagged as anomalies.

### Wind Speed

Wind speed is analysed using the same rolling baseline approach as temperature. Unusually strong or unusually calm conditions are identified using Z-scores.

### Rainfall

Rainfall behaves differently because many days receive little or no rainfall while occasional days experience heavy precipitation.

Instead of using Z-scores, rainfall anomalies are detected using a rolling 95th percentile threshold, providing a more reliable approach for highly variable rainfall data.

---

## Project Structure

```text
Weather Project
│
├── dashboard/
│   ├── ui_app.py
│   └── ui_renderers.py
│
├── src/
│   ├── config.py
│   ├── repository.py
│   ├── services.py
│   ├── pipeline.py
│   └── main.py
│
├── data/
│   ├── raw/
│   └── processed/
|
├── report/
|
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Technologies Used

* Python
* Streamlit
* Pandas
* NumPy
* Matplotlib
* Requests
* Open-Meteo API

---

## Running the Application

Install the required packages:

```bash
pip install -r requirements.txt
```

Launch the dashboard:

```bash
streamlit run dashboard/ui_app.py
```

When the dashboard is opened, the application automatically retrieves the latest weather data, runs the complete processing pipeline, detects anomalies and updates the dashboard with the newest available information.

---

## Future Improvements

Several enhancements could be added in future versions of the project, including:

* Support for multiple cities
* Interactive weather maps
* Email notifications for severe weather events
* Database integration
* Cloud deployment
* Machine learning-based anomaly detection
* Anomaly severity classification
* User-selectable forecast horizons

---

## Author
Hitan S
