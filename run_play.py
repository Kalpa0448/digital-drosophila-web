"""跑一段 10 秒脑时间的模拟，供网页回放（单次试验，省时间）"""
import os, sys, json, time
sys.path.insert(0, "/srv/flybrain/Drosophila_brain_model")
os.chdir("/srv/flybrain/Drosophila_brain_model")
from model import run_exp, default_params
import utils as utl
from brian2 import ms

SUGAR = [720575940624963786,720575940630233916,720575940637568838,720575940638202345,
         720575940617000768,720575940630797113,720575940632889389,720575940621754367,
         720575940621502051,720575940640649691,720575940639332736,720575940616885538,
         720575940639198653,720575940620900446,720575940617937543,720575940632425919,
         720575940633143833,720575940612670570,720575940628853239,720575940629176663,
         720575940611875570]
valid = set(__import__("pandas").read_csv("./Completeness_783.csv").iloc[:,0])
SUGAR = [n for n in SUGAR if n in valid]

T = 10 * 1000 * ms
os.makedirs("./results/play", exist_ok=True)
p = dict(default_params); p["n_run"] = 1; p["t_run"] = T

t0 = time.time()
run_exp(exp_name="play10", neu_exc=SUGAR, params=p,
        path_res="./results/play", path_comp="./Completeness_783.csv",
        path_con="./Connectivity_783.parquet", n_proc=1)
print("10 秒脑时间跑完，用时 %.0f 秒" % (time.time() - t0), flush=True)
