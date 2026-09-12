"""Metrics helpers and evaluation of the already frozen predictions (no refitting)."""
import argparse
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss,
    classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
    precision_recall_curve, auc)
from .common import ROOT, read_json, write_json, stage

def binary_metrics(y, probability, threshold):
    y=np.asarray(y,dtype=int)
    probability=np.asarray(probability,dtype=float)
    if not np.isfinite(probability).all() or ((probability<0)|(probability>1)).any():
        raise ValueError('Probabilities must be finite within [0,1]')
    pred=(probability>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    p,r,_=precision_recall_curve(y,probability)
    both=len(np.unique(y))==2
    return {'n':int(len(y)),'positive_support':int(y.sum()),'threshold':float(threshold),
        'accuracy':float(accuracy_score(y,pred)), 'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
        'precision':float(precision_score(y,pred,zero_division=0)), 'recall':float(recall_score(y,pred,zero_division=0)),
        'specificity':float(tn/(tn+fp)) if tn+fp else None, 'f1':float(f1_score(y,pred,zero_division=0)),
        'roc_auc':float(roc_auc_score(y,probability)) if both else None,
        'pr_auc':float(average_precision_score(y,probability)) if y.sum() else None,
        'pr_auc_definition':'average precision (non-interpolated)',
        'pr_auc_trapezoidal':float(auc(r,p)) if y.sum() else None,
        'brier_score':float(brier_score_loss(y,probability)),
        'confusion_matrix':{'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)},
        'classification_report':classification_report(y,pred,labels=[0,1],target_names=['no_failure','failure'],output_dict=True,zero_division=0)}

def select_threshold(y, probability, cfg):
    p=np.asarray(probability)
    thresholds=np.unique(np.r_[0.,p,1.])
    rows=[]
    for t in thresholds:
        predicted=p>=t
        tp=int(np.sum(predicted & (np.asarray(y)==1)))
        fp=int(np.sum(predicted & (np.asarray(y)==0)))
        fn=int(np.sum(~predicted & (np.asarray(y)==1)))
        recall=tp/max(tp+fn,1)
        precision=tp/max(tp+fp,1)
        rows.append({'threshold':float(t),'cost':cfg['false_negative_cost']*fn+cfg['false_positive_cost']*fp,'recall':recall,'precision':precision,'f1':2*precision*recall/max(precision+recall,1e-15),'fn':fn,'fp':fp})
    table=pd.DataFrame(rows)
    feasible=table[table.recall>=cfg['minimum_validation_recall']]
    selected=feasible.sort_values(['cost','f1','precision','threshold'],ascending=[True,False,False,False]).iloc[0].to_dict()
    return selected,table

def bootstrap_intervals(y,p,t,seed=42,repeats=1000):
    rng=np.random.default_rng(seed)
    y=np.asarray(y);p=np.asarray(p)
    neg=np.flatnonzero(y==0);pos=np.flatnonzero(y==1)
    rows=[]
    for _ in range(repeats):
        ids=np.r_[rng.choice(neg,len(neg),replace=True),rng.choice(pos,len(pos),replace=True)]
        yy=y[ids];pp=p[ids];pred=pp>=t
        rows.append([precision_score(yy,pred,zero_division=0),recall_score(yy,pred,zero_division=0),f1_score(yy,pred,zero_division=0),average_precision_score(yy,pp)])
    bounds=np.quantile(np.asarray(rows),[.025,.975],axis=0)
    return {'method':'1000 stratified row bootstraps; descriptive, does not account for selection or dependence','intervals':{k:{'lower':float(bounds[0,i]),'upper':float(bounds[1,i])} for i,k in enumerate(['precision','recall','f1','pr_auc'])}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions',type=str,default=str(ROOT/'reports/metrics/test_predictions.csv'))
    args=parser.parse_args()
    with stage('recompute_metrics_from_frozen_predictions'):
        df=pd.read_csv(args.predictions)
        metrics=binary_metrics(df.actual_failure,df.failure_probability,read_json(ROOT/'models/threshold.json')['threshold'])
        write_json(ROOT/'reports/metrics/recomputed_test_metrics.json',metrics)
        print(pd.Series({k:v for k,v in metrics.items() if isinstance(v,(int,float))}).to_string())

if __name__=='__main__': main()
