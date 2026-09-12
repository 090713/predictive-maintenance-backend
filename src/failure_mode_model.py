"""Independent binary models plus honest evidence-only handling for rare/random modes."""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from .feature_engineering import MODES, make_pipeline
from .condition_engine import NAMES
from .evaluate import binary_metrics, select_threshold

class FailureModeComponent:
    def __init__(self, seed=42, min_positives=50):
        self.seed=seed
        self.min_positives=min_positives

    def fit(self, X, Y, X_validation, Y_validation, cfg):
        self.models_={};self.thresholds_={};self.support_={};self.prevalence_={};self.validation_metrics_={}
        for mode in MODES:
            count=int(Y[mode].sum())
            self.support_[mode]=count
            self.prevalence_[mode]=float(Y[mode].mean())
            if mode=='RNF' or count<self.min_positives:
                continue
            pipeline=make_pipeline(RandomForestClassifier(n_estimators=200,min_samples_leaf=2,max_features=1.,class_weight='balanced_subsample',random_state=self.seed,n_jobs=2))
            pipeline.fit(X,Y[mode])
            p=pipeline.predict_proba(X_validation)[:,1]
            selected,_=select_threshold(Y_validation[mode],p,cfg)
            self.thresholds_[mode]=selected['threshold']
            self.models_[mode]=pipeline
            self.validation_metrics_[mode]=binary_metrics(Y_validation[mode],p,selected['threshold'])
        return self

    def probabilities(self, X):
        return {m:model.predict_proba(X)[:,1] for m,model in self.models_.items()}

    def rank(self, X, evidence):
        conditions={e['mode']:e for e in evidence}
        result=[]
        for mode in MODES:
            triggered=conditions[mode]['triggered']
            if mode in self.models_:
                p=float(self.models_[mode].predict_proba(X)[0,1])
                result.append({'mode':mode,'name':NAMES[mode],'probability':p,'score':p,'score_kind':'uncalibrated_binary_model_probability','predicted_active':p>=self.thresholds_[mode], 'supporting_condition':triggered,'limitation':f'Only {self.support_[mode]} training positives; probability not factory validated and not separately calibrated.'})
            elif mode=='RNF':
                result.append({'mode':mode,'name':NAMES[mode],'probability':None,'score':self.prevalence_[mode],'score_kind':'training_base_rate_not_individual_probability','predicted_active':False,'supporting_condition':False,'limitation':'Random event with no deterministic sensor cause. Base rate is descriptive only.'})
            else:
                result.append({'mode':mode,'name':NAMES[mode],'probability':None,'score':1. if triggered else 0.,'score_kind':'condition_context_indicator_not_probability','predicted_active':False,'supporting_condition':triggered,'limitation':f'{self.support_[mode]} training positives below minimum {self.min_positives}; no dependable standalone model. Wear-interval context does not confirm failure.'})
        # Binary evidence indicators and probabilities are not on a common calibrated scale.
        # Evidence-supported items first, followed by model score; expose the semantics in each item.
        return sorted(result,key=lambda item:(item['supporting_condition'],item['score']),reverse=True)
