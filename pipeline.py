"""果蝇全脑模型：批量跑实验，产出网页用的结果
- 基线（刺激 20 个糖神经元）
- 沉默实验（逐个关掉高放电的中间神经元）
- 刺激方案对比（20 个糖神经元 150Hz / 100Hz；只刺激 10 个）
"""
import os, sys, json, time
import pandas as pd
sys.path.insert(0, "/srv/flybrain/Drosophila_brain_model")
os.chdir("/srv/flybrain/Drosophila_brain_model")
from model import run_exp, default_params
import utils as utl
from brian2 import Hz

OUT = "/srv/flybrain/Drosophila_brain_model/results/web"
os.makedirs(OUT, exist_ok=True)
RES = "/srv/flybrain/Drosophila_brain_model/results/web_run"
os.makedirs(RES, exist_ok=True)

MN9 = 720575940660219265
SUGAR = [720575940624963786,720575940630233916,720575940637568838,720575940638202345,
         720575940617000768,720575940630797113,720575940632889389,720575940621754367,
         720575940621502051,720575940640649691,720575940639332736,720575940616885538,
         720575940639198653,720575940620900446,720575940617937543,720575940632425919,
         720575940633143833,720575940612670570,720575940628853239,720575940629176663,
         720575940611875570]
valid = set(pd.read_csv("./Completeness_783.csv").iloc[:,0])
SUGAR = [n for n in SUGAR if n in valid]

CFG = dict(path_res=RES, path_comp="./Completeness_783.csv",
           path_con="./Connectivity_783.parquet", n_proc=1)
N = 5   # 每次实验的试验次数

def log(*a):
    print(*a, flush=True)

def rate_of(name):
    df = utl.load_exps([f"{RES}/{name}.parquet"])
    rate, _ = utl.get_rate(df, t_run=default_params["t_run"], n_run=N)
    return rate.iloc[:,0]

def params(n=5, r_poi=None):
    p = dict(default_params); p["n_run"] = n
    if r_poi is not None: p["r_poi"] = r_poi * Hz
    return p

summary = {"meta": {"n_trials": N, "mn9": MN9, "sugar": SUGAR}, "baseline": {}, "silences": [], "variants": []}

t0 = time.time()
# ---------- 1. 基线 ----------
if not os.path.exists(f"{RES}/base.parquet"):
    log(">>> 基线实验")
    run_exp(exp_name="base", neu_exc=SUGAR, params=params(N), **CFG)
base = rate_of("base")
summary["baseline"] = {
    "mn9": float(base.get(MN9, 0)),
    "n_firing": int((base > 0).sum()),
    "top": {str(k): float(v) for k, v in base.sort_values(ascending=False).head(400).items()},
}
log("基线 MN9 =", summary["baseline"]["mn9"], "| 有放电", summary["baseline"]["n_firing"], "| 用时", int(time.time()-t0))

# ---------- 2. 沉默实验 ----------
sugar_set = set(SUGAR)
cand = [int(i) for i in base.sort_values(ascending=False).index if int(i) not in sugar_set]
cand = [c for c in cand if base[c] > 30][:8]
log("沉默候选:", cand)

for cid in cand:
    name = f"sl_{cid}"
    if not os.path.exists(f"{RES}/{name}.parquet"):
        log(">>> 沉默", cid)
        run_exp(exp_name=name, neu_exc=SUGAR, neu_slnc=[cid], params=params(N), **CFG)
    r = rate_of(name)
    row = {"id": cid, "own_rate": float(base.get(cid, 0)),
           "mn9": float(r.get(MN9, 0)),
           "delta": float(r.get(MN9, 0) - summary["baseline"]["mn9"]),
           "n_firing": int((r > 0).sum())}
    summary["silences"].append(row)
    log("   结果:", row, "| 累计 %.0f min" % ((time.time()-t0)/60))

# ---------- 3. 刺激方案对比 ----------
variants = [("v_100hz", SUGAR, 100), ("v_sugar10", SUGAR[:10], None), ("v_sugar30", (SUGAR + [c for c in cand])[:30], None)]
for name, group, freq in variants:
    if not os.path.exists(f"{RES}/{name}.parquet"):
        log(">>> 对比", name, len(group), "个刺激神经元", freq or 150, "Hz")
        run_exp(exp_name=name, neu_exc=[g for g in group if g in valid], params=params(N, freq), **CFG)
    r = rate_of(name)
    summary["variants"].append({"name": name, "n_exc": len([g for g in group if g in valid]),
                                "freq": freq or 150,
                                "mn9": float(r.get(MN9, 0)),
                                "n_firing": int((r > 0).sum()),
                                "top": {str(k): float(v) for k, v in r.sort_values(ascending=False).head(200).items()}})
    log("   结果:", summary["variants"][-1]["name"], summary["variants"][-1]["mn9"], "Hz")

json.dump(summary, open(f"{OUT}/summary.json", "w"), ensure_ascii=False, indent=1)
log("完成，总用时 %.1f 分钟" % ((time.time()-t0)/60))
