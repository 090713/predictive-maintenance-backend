# test_real_failure.py
# ---------------------------------------------------------
# This script:
# 1. Loads the real AI4I dataset.
# 2. Finds a machine that actually has a failure label.
# 3. Takes ONLY the six input fields required by our API.
# 4. Sends those values to our FastAPI backend.
# ---------------------------------------------------------

import pandas as pd
import requests


# ---------------------------------------------------------
# 1. Load the AI4I dataset
# ---------------------------------------------------------

df = pd.read_csv("data/ai4i2020.csv")


# ---------------------------------------------------------
# 2. Find an actual failure record
#
# Machine failure = 1 means this record belongs to a
# machine-failure case in the dataset.
# ---------------------------------------------------------

# ---------------------------------------------------------
# Choose a specific failure mode to test.
#
# Change this value to:
# "HDF" -> Heat Dissipation Failure
# "PWF" -> Power Failure
# "OSF" -> Overstrain Failure
# "TWF" -> Tool Wear Failure
# "RNF" -> Random Failure
# ---------------------------------------------------------

failure_mode_to_test = "TWF"

failure_rows = df[df[failure_mode_to_test] == 1]
print(
    f"Total {failure_mode_to_test} failure records:",
    len(failure_rows)
)

# Take the first failure record
row = failure_rows.iloc[0]


# ---------------------------------------------------------
# 3. Display information about the selected record
#
# These labels are used ONLY for checking the result.
# They are NOT sent to the prediction API.
# ---------------------------------------------------------

print("\nSelected dataset row:")
print(row)


# ---------------------------------------------------------
# 4. Prepare API input
#
# The model expects exactly these six raw fields:
# Product Type
# Air Temperature
# Process Temperature
# Rotational Speed
# Torque
# Tool Wear
# ---------------------------------------------------------

machine_data = {
    "product_type": str(row["Type"]),
    "air_temperature": float(row["Air temperature [K]"]),
    "process_temperature": float(row["Process temperature [K]"]),
    "rotational_speed": float(row["Rotational speed [rpm]"]),
    "torque": float(row["Torque [Nm]"]),
    "tool_wear": float(row["Tool wear [min]"])
}


print("\nData being sent to API:")
print(machine_data)


# ---------------------------------------------------------
# 5. Send the data to our FastAPI backend
# ---------------------------------------------------------

response = requests.post(
    "http://127.0.0.1:8000/v1/predict",
    json=machine_data
)


# ---------------------------------------------------------
# 6. Display API result
# ---------------------------------------------------------

print("\nAPI status code:", response.status_code)

print("\nAPI response:")

print(response.json())