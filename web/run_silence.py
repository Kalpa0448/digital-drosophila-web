"""网页后台：单次沉默实验 worker
用法: python run_silence.py <neuron_id> <n_trials>
输出: results/web/job_<id>.json
"""
import os, sys, json, time
import pandas as pd
sys.path.insert(0, "/srv/flybrain/Drosophila_brain_model")
os.chdir("/srv/flybrain/Drosophila_brain_model")
from model import run_exp, default_params
import utils as utl

MN9 = 720575940660219265
SUGAR = [720575940624963786,720575940630233916,720575940637568838,720575940638202345,
         720575940617000768,720575940630797113,720575940632889389,720575940621754367,
         720575940621502051,720575940640649691,720575940639332736,720575940616885538,
         720575940639198653,720575940620900446,720575940617937543,720575940632425919,
         720575940633143833,720575940612670570,720575940628853239,720575940629176663,
         720575940611875570]
RES = "./results/web_run"
WEB = "/srv/flybrain/web/jobs"
os.makedirs(RES, exist_ok=True); os.makedirs(WEB, exist_ok=True)

nid = int(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
valid = set(pd.read_csv("./Completeness_783.csv").iloc[:,0])
if nid not in valid:
    json.dump({"ok": False, "error": "ID 不在 v783 清单里"}, open(f"{WEB}/{nid}.json", "w"))
    sys.exit(1)

name = f"sl_{nid}"
t0 = time.time()
if not os.path.exists(f"{RES}/{name}.parquet"):
    p = dict(default_params); p["n_run"] = n
    run_exp(exp_name=name, neu_exc=[s for s in SUGAR if s in valid], neu_slnc=[nid],
            params=p, path_res=RES, path_comp="./Completeness_783.csv",
            path_con="./Connectivity_783.parquet", n_proc=1)

df = utl.load_exps([f"{RES}/{name}.parquet"])
rate, _ = utl.get_rate(df, t_run=default_params["t_run"], n_run=n)
s = rate.iloc[:,0]
out = {"ok": True, "id": nid, "n_trials": n, "mn9": float(s.get(MN9, 0)),
       "n_firing": int((s > 0).sum()), "own_rate": float(s.get(nid, 0)),
       "top": {str(k): float(v) for k, v in s.sort_values(ascending=False).head(120).items()},
       "sec": round(time.time()-t0, 1)}
json.dump(out, open(f"{WEB}/{nid}.json", "w"), ensure_ascii=False, indent=1)
print("done", out["mn9"], out["sec"], "s")
