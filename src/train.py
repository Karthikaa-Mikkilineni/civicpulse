import glob, pandas as pd, numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_curve, f1_score, precision_score, recall_score

FILES = sorted(glob.glob("data/civicpulse_*.csv.gz"))
frames = [pd.read_csv(f, compression="gzip", low_memory=False) for f in FILES]
df = pd.concat(frames, ignore_index=True)
df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")
resolution_h = (df["closed_date"] - df["created_date"]).dt.total_seconds()/3600
# Require 7 days of follow-up inside the study window.
df = df[df["created_date"] < "2025-12-25"].copy()
df["slow7d"] = (df["closed_date"].isna() | (resolution_h.loc[df.index] > 168)).astype("int8")
train = df[df.created_date < "2025-10-01"].sample(n=700000, random_state=42)
val = df[(df.created_date >= "2025-10-01") & (df.created_date < "2025-11-01")]
test = df[df.created_date >= "2025-11-01"]
for d in (train,val,test):
    d["hour"] = d.created_date.dt.hour.astype(str); d["dow"] = d.created_date.dt.dayofweek.astype(str)
    d["month"] = d.created_date.dt.month.astype(str); d["weekend"] = (d.created_date.dt.dayofweek>=5).astype(str)
cat=["agency","complaint_type","descriptor","location_type","incident_zip","borough","community_board","hour","dow","month","weekend"]
num=["latitude","longitude"]
for c in cat:
    for d in (train,val,test): d[c]=d[c].fillna("__MISSING__").astype(str)
pre=ColumnTransformer([("cat",OneHotEncoder(handle_unknown="ignore",min_frequency=200),cat),("num",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),num)])
model=SGDClassifier(loss="log_loss",alpha=1e-5,max_iter=50,tol=1e-3,class_weight="balanced",random_state=42,average=True)
pipe=Pipeline([("pre",pre),("model",model)]).fit(train[cat+num],train.slow7d)
pv=pipe.predict_proba(val[cat+num])[:,1]; pt=pipe.predict_proba(test[cat+num])[:,1]
p,r,t=precision_recall_curve(val.slow7d,pv); f=2*p*r/(p+r+1e-12); threshold=t[np.argmax(f[:-1])]
yhat=pt>=threshold
print({"ROC_AUC":roc_auc_score(test.slow7d,pt),"PR_AUC":average_precision_score(test.slow7d,pt),"F1":f1_score(test.slow7d,yhat),"precision":precision_score(test.slow7d,yhat),"recall":recall_score(test.slow7d,yhat)})
