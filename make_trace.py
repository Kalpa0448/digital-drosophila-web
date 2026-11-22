"""把 play10.parquet 的脉冲时刻 → 网页回放用的分组放电率序列
输出: play/trace.json
"""
import os, json, sys
import numpy as np
import pandas as pd

BASE = "/srv/flybrain/Drosophila_brain_model"
os.chdir(BASE)
WEB = "/srv/flybrain/play"

MN9 = 720575940660219265
SUGAR = [720575940624963786,720575940630233916,720575940637568838,720575940638202345,
         720575940617000768,720575940630797113,720575940632889389,720575940621754367,
         720575940621502051,720575940640649691,720575940639332736,720575940616885538,
         720575940639198653,720575940620900446,720575940617937543,720575940632425919,
         720575940633143833,720575940612670570,720575940628853239,720575940629176663,
         720575940611875570]

df = pd.read_parquet("./results/play/play10.parquet")
print("脉冲行数:", len(df), "| 列:", list(df.columns)[:6])
# 兼容列名
t = df["t"].to_numpy(dtype=float)
if "flywire_id" in df.columns:
    flyid = df["flywire_id"].to_numpy()
else:
    ids = pd.read_csv("./Completeness_783.csv", index_col=0).index.to_numpy()
    flyid = ids[df["i"].to_numpy()]

counts = pd.Series(flyid).value_counts()
order = counts.index.to_numpy()

sugar_set = set(SUGAR)
# 运动/输出组：MN9 的最强上游里挑 6 个
con = pd.read_parquet("./Connectivity_783.parquet", columns=["Presynaptic_ID","Postsynaptic_ID","Connectivity"])
up = con[con.Postsynaptic_ID == MN9].sort_values("Connectivity", ascending=False).head(6).Presynaptic_ID.tolist()
motor = set([MN9] + [int(x) for x in up])

central = [int(x) for x in counts.head(200).index if int(x) not in sugar_set and int(x) not in motor]

groups = {
    "sensory": sorted(sugar_set),
    "motor": sorted(motor),
    "central": central,
}

BIN = 0.1  # 100 ms
tmax = float(t.max()) if len(t) else 10.0
nb = int(np.ceil((tmax + 1e-6) / BIN))
bins = np.zeros((nb, 3), dtype=float)   # sensory, central, motor
sets = [set(groups["sensory"]), set(groups["central"]), set(groups["motor"])]
bi = np.clip((t / BIN).astype(int), 0, nb - 1)
for k, s in enumerate(sets):
    m = np.isin(flyid, list(s))
    np.add.at(bins[:, k], bi[m], 1.0)

# 归一化到 0~1（按各组的 95 分位）
norm = np.zeros_like(bins)
for k in range(3):
    q = np.percentile(bins[:, k], 95) or 1.0
    norm[:, k] = np.clip(bins[:, k] / q, 0, 1)

trace = {
    "meta": {"bin": BIN, "seconds": round(tmax, 2), "n_spikes": int(len(t)),
             "n_neurons_firing": int(counts.size),
             "groups": {k: len(v) for k, v in groups.items()}},
    "frames": [{"s": round(float(a), 3), "c": round(float(b), 3), "m": round(float(c), 3)}
               for a, b, c in norm],
}
json.dump(trace, open(f"{WEB}/trace.json", "w"))
print("帧数:", nb, "| 秒数:", trace["meta"]["seconds"], "| 有放电神经元:", counts.size)
print("写出", f"{WEB}/trace.json")
