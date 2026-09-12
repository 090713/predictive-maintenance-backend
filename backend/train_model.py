import pandas as pd


# ---------------------------------------------------------
# STEP 1: Load the AI4I 2020 dataset
# ---------------------------------------------------------
# The CSV file is stored in the project's "data" folder.
# Pandas reads the CSV file and stores it as a DataFrame.
# ---------------------------------------------------------

df = pd.read_csv("data/ai4i2020.csv")


# ---------------------------------------------------------
# STEP 2: Create derived features
# ---------------------------------------------------------
# The original dataset gives us the raw machine readings.
#
# We can also calculate additional values that are useful
# for understanding the machine's operating condition.
#
# These formulas come from our project definition:
#
# Temperature Difference = Process Temperature - Air Temperature
#
# Mechanical Power =
# Torque × Rotational Speed × 2π / 60
#
# Overstrain Measure = Tool Wear × Torque
# ---------------------------------------------------------

df["Temperature Difference"] = (
    df["Process temperature [K]"] - df["Air temperature [K]"]
)

df["Mechanical Power [W]"] = (
    df["Torque [Nm]"]
    * df["Rotational speed [rpm]"]
    * 2
    * 3.14159265359
    / 60
)

df["Overstrain Measure"] = (
    df["Tool wear [min]"] * df["Torque [Nm]"]
)


# ---------------------------------------------------------
# STEP 3: Select the features for our ML model
# ---------------------------------------------------------
# These are the pieces of information the model is allowed
# to use when predicting whether a machine will fail.
#
# Notice that we are NOT including:
# - UDI
# - Product ID
# - Machine failure
# - TWF
# - HDF
# - PWF
# - OSF
# - RNF
#
# The failure columns are historical labels/targets, not
# prediction-time sensor inputs.
# ---------------------------------------------------------

features = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Temperature Difference",
    "Mechanical Power [W]",
    "Overstrain Measure"
]


# ---------------------------------------------------------
# STEP 4: Create X and y
# ---------------------------------------------------------
# X = input features given to the ML model.
#
# y = target that the ML model needs to learn to predict.
#
# Our target is "Machine failure":
# 0 = No machine failure
# 1 = Machine failure
# ---------------------------------------------------------

X = df[features].copy()
y = df["Machine failure"]


# ---------------------------------------------------------
# STEP 5: Check what we have prepared
# ---------------------------------------------------------

print("\n--- Features Used by the Model ---")
print(X.columns.tolist())

print("\n--- Number of Input Rows ---")
print(len(X))

print("\n--- Target Distribution ---")
print(y.value_counts())


from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder


# ---------------------------------------------------------
# STEP 6: Separate numerical and categorical features
# ---------------------------------------------------------
# "Type" is categorical because it contains L, M, and H.
#
# The remaining features are numerical measurements.
#
# We handle these two types of data differently.
# ---------------------------------------------------------

categorical_features = ["Type"]

numerical_features = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Temperature Difference",
    "Mechanical Power [W]",
    "Overstrain Measure"
]


# ---------------------------------------------------------
# STEP 7: Create the preprocessing pipeline
# ---------------------------------------------------------
# OneHotEncoder converts Type (L/M/H) into numerical
# columns that the ML model can understand.
#
# handle_unknown="ignore" means that if a new/unexpected
# category appears later, the prediction pipeline will not
# crash because of that category.
# ---------------------------------------------------------

preprocessor = ColumnTransformer(
    transformers=[
        (
            "type_encoder",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        )
    ],
    remainder="passthrough"
)


# ---------------------------------------------------------
# STEP 8: Split the dataset into training and testing data
# ---------------------------------------------------------
# Training data is used to teach the model.
#
# Testing data is kept separate so that we can evaluate
# how well the model performs on data it did not see
# during training.
#
# stratify=y is important here because machine failure is
# highly imbalanced:
#
# 96.61% = no failure
# 3.39%  = failure
#
# Stratification keeps approximately the same proportion
# of failures in both training and testing sets.
# ---------------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# ---------------------------------------------------------
# STEP 9: Fit the preprocessing using training data
# ---------------------------------------------------------
# IMPORTANT:
# We fit preprocessing only on the training data.
#
# This prevents information from the test set from
# accidentally influencing the training process.
# ---------------------------------------------------------

X_train_processed = preprocessor.fit_transform(X_train)

X_test_processed = preprocessor.transform(X_test)


# ---------------------------------------------------------
# STEP 10: Display the resulting dataset sizes
# ---------------------------------------------------------

print("\n--- Training Data ---")
print("Rows:", X_train.shape[0])

print("\n--- Testing Data ---")
print("Rows:", X_test.shape[0])

print("\n--- Processed Training Shape ---")
print(X_train_processed.shape)

print("\n--- Processed Testing Shape ---")
print(X_test_processed.shape)


from sklearn.ensemble import RandomForestClassifier


# ---------------------------------------------------------
# STEP 11: Create the Random Forest model
# ---------------------------------------------------------
# Random Forest is an ensemble of decision trees.
#
# Instead of relying on a single decision tree, Random
# Forest combines predictions from many trees.
#
# class_weight="balanced" is important for our dataset
# because machine failures are much less common than
# normal machine operation.
#
# This tells the model to give more importance to the
# minority failure class during training.
# ---------------------------------------------------------

model = RandomForestClassifier(
    n_estimators=200,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)


# ---------------------------------------------------------
# STEP 12: Train the model
# ---------------------------------------------------------
# The model learns the relationship between:
#
# X_train_processed → machine condition
# y_train           → whether failure occurred
#
# After this step, the model has learned patterns from
# the training data.
# ---------------------------------------------------------

model.fit(X_train_processed, y_train)

print("\n--- Model Training ---")
print("Random Forest model trained successfully.")


from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


# ---------------------------------------------------------
# STEP 13: Make predictions on the test data
# ---------------------------------------------------------
# The test data was NOT used to train the model.
#
# This allows us to see how the model performs on
# previously unseen machine records.
# ---------------------------------------------------------

y_pred = model.predict(X_test_processed)


# ---------------------------------------------------------
# STEP 14: Calculate evaluation metrics
# ---------------------------------------------------------
# Accuracy  → overall percentage of correct predictions.
#
# Precision → when the model predicts failure, how often
#             is it actually a failure?
#
# Recall    → of all the actual failures, how many did
#             the model successfully detect?
#
# F1-score  → combines precision and recall into one
#             balanced metric.
# ---------------------------------------------------------

accuracy = accuracy_score(y_test, y_pred)

precision = precision_score(
    y_test,
    y_pred,
    zero_division=0
)

recall = recall_score(
    y_test,
    y_pred,
    zero_division=0
)

f1 = f1_score(
    y_test,
    y_pred,
    zero_division=0
)


# ---------------------------------------------------------
# STEP 15: Display the results
# ---------------------------------------------------------

print("\n--- Model Evaluation ---")

print(f"Accuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print(f"F1 Score : {f1:.4f}")


# ---------------------------------------------------------
# STEP 16: Display the confusion matrix
# ---------------------------------------------------------
# The confusion matrix shows:
#
#                 Predicted
#                 0       1
#
# Actual  0      TN      FP
#         1      FN      TP
#
# For predictive maintenance, False Negatives are
# particularly important because they represent failures
# that the model failed to detect.
# ---------------------------------------------------------

cm = confusion_matrix(y_test, y_pred)

print("\n--- Confusion Matrix ---")
print(cm)


# ---------------------------------------------------------
# STEP 17: Display the complete classification report
# ---------------------------------------------------------
# This gives us precision, recall and F1-score separately
# for both classes (normal and failure).
# ---------------------------------------------------------

print("\n--- Classification Report ---")
print(
    classification_report(
        y_test,
        y_pred,
        target_names=["Normal", "Failure"],
        zero_division=0
    )
)