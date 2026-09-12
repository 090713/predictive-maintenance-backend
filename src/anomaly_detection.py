import numpy as np
from sklearn.ensemble import IsolationForest
from .feature_engineering import make_pipeline

class AnomalyComponent:
    def __init__(self, seed=42, contamination=.02):
        self.seed=seed;self.contamination=contamination

    def fit(self, X_normal):
        self.pipeline_=make_pipeline(IsolationForest(n_estimators=250,contamination=self.contamination,random_state=self.seed,n_jobs=2))
        self.pipeline_.fit(X_normal)
        self.reference_scores_=np.sort(-self.pipeline_.score_samples(X_normal))
        self.n_normal_training_=len(X_normal)
        return self

    def score(self, X):
        raw=-self.pipeline_.score_samples(X)
        percentile=np.searchsorted(self.reference_scores_,raw,side='right')/len(self.reference_scores_)
        is_anomaly=self.pipeline_.predict(X)==-1
        return raw,np.clip(percentile,0,1),is_anomaly
