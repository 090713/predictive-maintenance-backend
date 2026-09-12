import pandas as pd


# ---------------------------------------------------------
# STEP 1: Load the AI4I 2020 Predictive Maintenance dataset
# ---------------------------------------------------------
# Our CSV file is stored inside the project's "data" folder.
# Pandas allows us to read the CSV and store it as a DataFrame.
#
# A DataFrame is basically a table in Python, similar to
# an Excel spreadsheet.
# ---------------------------------------------------------

df = pd.read_csv("data/ai4i2020.csv")


# ---------------------------------------------------------
# STEP 2: Display the number of rows and columns
# ---------------------------------------------------------
# This helps us verify that the correct dataset was loaded.
# The expected dataset contains 10,000 rows and 14 columns.
# ---------------------------------------------------------

print("\n--- Dataset Shape ---")
print(df.shape)


# ---------------------------------------------------------
# STEP 3: Display all column names
# ---------------------------------------------------------
# We need to know exactly what information is available
# before deciding which columns our ML model should use.
# ---------------------------------------------------------

print("\n--- Column Names ---")
print(df.columns.tolist())


# ---------------------------------------------------------
# STEP 4: Display the first 5 rows
# ---------------------------------------------------------
# This lets us see what the actual machine data looks like.
# ---------------------------------------------------------

print("\n--- First 5 Rows ---")
print(df.head())


# ---------------------------------------------------------
# STEP 5: Display information about every column
# ---------------------------------------------------------
# This tells us:
# - column names
# - data types
# - number of non-empty values
#
# This is useful for finding missing data and understanding
# which columns contain numbers and which contain text.
# ---------------------------------------------------------

print("\n--- Dataset Information ---")
df.info()


# ---------------------------------------------------------
# STEP 6: Check the overall machine failure distribution
# ---------------------------------------------------------
# "Machine failure" is our main target.
#
# 0 = Machine did not fail
# 1 = Machine failed
#
# We want to know how many examples belong to each class.
# This is important because an ML model can behave very
# differently when failures are rare.
# ---------------------------------------------------------

print("\n--- Machine Failure Distribution ---")
print(df["Machine failure"].value_counts())

print("\n--- Machine Failure Percentage ---")
print(df["Machine failure"].value_counts(normalize=True) * 100)


# ---------------------------------------------------------
# STEP 7: Check the distribution of individual failure modes
# ---------------------------------------------------------
# The AI4I dataset contains five failure-mode labels:
#
# TWF -> Tool Wear Failure
# HDF -> Heat Dissipation Failure
# PWF -> Power Failure
# OSF -> Overstrain Failure
# RNF -> Random Failure
#
# These columns contain historical labels.
# We will use them later for training/evaluating our
# failure-mode prediction logic.
# ---------------------------------------------------------

failure_modes = ["TWF", "HDF", "PWF", "OSF", "RNF"]

print("\n--- Failure Mode Distribution ---")

for mode in failure_modes:
    count = df[mode].sum()
    percentage = (count / len(df)) * 100

    print(f"{mode}: {count} ({percentage:.2f}%)")


    # ---------------------------------------------------------
# STEP 8: Inspect product type distribution
# ---------------------------------------------------------
# The dataset contains three product types:
# L = Low
# M = Medium
# H = High
#
# Type is important because some AI4I failure conditions
# use different thresholds depending on the product type.
# ---------------------------------------------------------

print("\n--- Product Type Distribution ---")
print(df["Type"].value_counts())

print("\n--- Product Type Percentage ---")
print(df["Type"].value_counts(normalize=True) * 100)


# ---------------------------------------------------------
# STEP 9: Inspect the numerical machine parameters
# ---------------------------------------------------------
# describe() gives us useful statistics such as:
# - count
# - mean
# - minimum
# - maximum
# - standard deviation
#
# This helps us understand the normal ranges of the
# machine parameters before building the ML model.
# ---------------------------------------------------------

sensor_columns = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]"
]

print("\n--- Sensor Parameter Statistics ---")
print(df[sensor_columns].describe())