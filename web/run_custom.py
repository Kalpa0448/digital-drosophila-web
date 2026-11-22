"""自定义实验 worker：按参数真跑一次模拟
用法: python run_custom.py <freq> <nexc> <nrun> [silence_id]
输出: web/jobs/custom_<时间戳>.json  +  web/jobs/custom_latest.json
"""
import os, sys, json, time
import pandas as pd
sys.path.insert(0, "/srv/flybrain/Drosophila_brain_model")
os.chdir("/srv/flybrain/Drosophila_brain_model")
from model import run_exp, default_params
import utils as utl
from brian2 import Hz

MN9 = 720575940660219265
SUGAR = [720575940624963786,720575940630233916,720575940637568838,720575940638202345,
         720575940617000768,720575940630797113,720575940632889389,720575940621754367,
         720575940621502051,720575940640649691,720575940639332736,720575940616885538,
         720575940639198653,720575940620900446,720575940617937543,720575940632425919,
         720575940633143833,720575940612670570,720575940628853239,720575940629176663,
         720575940611875570]

freq = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
nexc = int(sys.argv[2]) if len(sys.argv) > 2 else 20
nrun = int(sys.argv[3]) if len(sys.argv) > 3 else 1
slnc = [int(sys.argv[4])] if len(sys.argv) > 4 and sys.argv[4].isdigit() else []

RES = "./results/web_run"
WEB = "/srv/flybrain/web/jobs"
os.makedirs(RES, exist_ok=True); os.makedirs(WEB, exist_ok=True)

valid = set(pd.read_csv("./Completeness_783.csv").iloc[:, 0])
neu_exc = [n for n in SUGAR[:max(1, min(nexc, len(SUGAR)))] if n in valid]
slnc = [n for n in slnc if n in valid]

name = f"cust_{int(freq)}_{len(neu_exc)}_{len(slnc)}_{nrun}"
t0 = time.time()
p = dict(default_params); p["n_run"] = nrun; p["r_poi"] = freq * Hz
run_exp(exp_name=name, neu_exc=neu_exc, neu_slnc=slnc, params=p,
        path_res=RES, path_comp="./Completeness_783.csv",
        path_con="./Connectivity_783.parquet", n_proc=1)

df = utl.load_exps([f"{RES}/{name}.parquet"])
rate, _ = utl.get_rate(df, t_run=p["t_run"], n_run=nrun)
s = rate.iloc[:, 0]
out = {
    "ok": True, "freq": freq, "n_exc": len(neu_exc), "n_run": nrun,
    "silenced": slnc, "mn9": float(s.get(MN9, 0)),
    "n_firing": int((s > 0).sum()),
    "top": {str(k): float(v) for k, v in s.sort_values(ascending=False).head(60).items()},
    "sec": round(time.time() - t0, 1), "at": time.strftime("%H:%M:%S"),
}
json.dump(out, open(f"{WEB}/custom_latest.json", "w"), ensure_ascii=False, indent=1)
print("done", out["mn9"], out["sec"], "s")
