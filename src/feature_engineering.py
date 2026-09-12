"""Train-only imputation, strict predictor allowlist, and shared feature derivation."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

FEATURES = ['product_type', 'air_temperature', 'process_temperature', 'rotational_speed', 'torque', 'tool_wear']
NUMERIC = FEATURES[1:]
DERIVED = ['temperature_difference', 'mechanical_power_w', 'overstrain_measure']
TARGETS = ['Machine failure', 'TWF', 'HDF', 'PWF', 'OSF', 'RNF']
MODES = TARGETS[1:]
FORBIDDEN = {'UDI', 'UID', 'Product ID', *TARGETS, 'machine_id', 'event_timestamp', 'production_state'}
RENAME = dict(zip(['Type','Air temperature [K]','Process temperature [K]','Rotational speed [rpm]','Torque [Nm]','Tool wear [min]'], FEATURES))
UNITS = {'product_type':'L/M/H', 'air_temperature':'K','process_temperature':'K','rotational_speed':'rpm','torque':'Nm','tool_wear':'min','temperature_difference':'K','mechanical_power_w':'W','overstrain_measure':'min*Nm'}

def assert_predictors(X):
    if not isinstance(X, pd.DataFrame):
        raise TypeError('Predictors must be a named pandas DataFrame')
    if not X.columns.is_unique:
        raise ValueError('Duplicate predictor columns are forbidden')
    unexpected = set(X.columns) - set(FEATURES)
    missing = set(FEATURES) - set(X.columns)
    if unexpected or missing:
        raise ValueError(f'Predictor allowlist violation; forbidden/unexpected={sorted(unexpected)}, missing={sorted(missing)}')

def derive_values(row):
    return {'temperature_difference': float(row['process_temperature']-row['air_temperature']),
            'mechanical_power_w': float(row['torque']*row['rotational_speed']*2*np.pi/60),
            'overstrain_measure': float(row['tool_wear']*row['torque'])}

class FeatureBuilder(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        assert_predictors(X)
        self.feature_names_in_ = np.asarray(FEATURES, dtype=object)
        self.n_features_in_ = len(FEATURES)
        self.numeric_imputer_ = SimpleImputer(strategy='median', keep_empty_features=True).fit(X[NUMERIC])
        self.type_imputer_ = SimpleImputer(strategy='most_frequent', keep_empty_features=True).fit(X[['product_type']])
        return self

    def transform(self, X):
        check_is_fitted(self, 'numeric_imputer_')
        assert_predictors(X)
        result = pd.DataFrame(self.numeric_imputer_.transform(X[NUMERIC]), columns=NUMERIC, index=X.index)
        result['product_type'] = self.type_imputer_.transform(X[['product_type']]).ravel()
        result['temperature_difference'] = result.process_temperature-result.air_temperature
        result['mechanical_power_w'] = result.torque*result.rotational_speed*2*np.pi/60
        result['overstrain_measure'] = result.tool_wear*result.torque
        return result[FEATURES+DERIVED]

    def get_feature_names_out(self, input_features=None):
        return np.asarray(FEATURES+DERIVED, dtype=object)

def make_preprocessor(scale=False):
    encoder = ColumnTransformer([
        ('type', OneHotEncoder(categories=[['L','M','H']], handle_unknown='ignore', sparse_output=False), ['product_type']),
        ('numeric', StandardScaler() if scale else 'passthrough', NUMERIC+DERIVED)
    ], remainder='drop', verbose_feature_names_out=False)
    return Pipeline([('features', FeatureBuilder()), ('encode', encoder)])

def make_pipeline(model, scale=False):
    return Pipeline([('preprocess', make_preprocessor(scale)), ('model', model)])
