# Predictive Maintenance Agent - Backend

This is the backend for our Predictive Maintenance project.

## Technologies

- Python
- FastAPI
- Machine Learning
- Pandas
- Scikit-learn

## What it does

- Predicts machine failure
- Detects anomalies
- Identifies possible failure modes
- Gives maintenance recommendations

## Run the Backend

```bash
uvicorn backend.main:app --reload

Dataset

AI4I 2020 Predictive Maintenance Dataset

API
Health Check

GET /health

Prediction

POST /v1/predict