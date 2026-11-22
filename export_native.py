"""把连接组导出成手机端可加载的紧凑格式
- indptr: int32 (N+1)  行指针
- dst:    行内排序后做差分 + varint(LEB128)
- w:      突触数*兴奋性 → int16（除以 WSCALE 量化）
- meta:   常数、刺激神经元索引
"""
import os, gzip, json
import numpy as np
import pandas as pd

BASE = "/srv/flybrain/Drosophila_brain_model"
OUT = "/srv/flybrain/play/brain"
os.makedirs(OUT, exist_ok=True)

df = pd.read_parquet(f"{BASE}/Connectivity_783.parquet",
                     columns=["Presynaptic_Index", "Postsynaptic_Index", "Connectivity", "Excitatory"])
src = df.Presynaptic_Index.to_numpy(np.int64)
dst = df.Postsynaptic_Index.to_numpy(np.int64)
syn = df.Connectivity.to_numpy(np.float32)
exc = df.Excitatory.to_numpy(np.float32)
w = syn * np.where(exc > 0, 1.0, -1.0)

N = int(max(src.max(), dst.max())) + 1
order = np.lexsort((dst, src))          # 先按源，再按目标（行内有序）
src, dst, w = src[order], dst[order], w[order]

indptr = np.zeros(N + 1, np.int64)
np.add.at(indptr, src + 1, 1)
indptr = np.cumsum(indptr).astype(np.int32)
M = len(dst)
print("N", N, "M", M)

# ---- w → int16 量化 ----
WSCALE = 1.0
wq = np.clip(np.round(w / WSCALE), -32000, 32000).astype(np.int16)

# ---- dst → 行内差分 varint ----
starts = indptr[:-1].astype(np.int64)
shifted = np.concatenate(([0], dst[:-1]))     # 前一个元素
delta = dst - shifted
delta[starts] = dst[starts] + 1               # 每行开头相对 -1
# 行首 delta = dst + 1；其余为小差值；统一转无符号
d = delta.astype(np.int64)
assert d.min() >= 0, d.min()

buf = bytearray()
for v in d:
    v = int(v)
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            break
print("varint 字节数 %.1f MB" % (len(buf) / 1e6))

def wgz(name, data):
    p = f"{OUT}/{name}.gz"
    with gzip.open(p, "wb", compresslevel=9) as f:
        f.write(data)
    print(name, "%.1f MB" % (os.path.getsize(p) / 1e6))

wgz("indptr", indptr.tobytes())
wgz("dst", bytes(buf))
wgz("w", wq.tobytes())

# ---- meta ----
SUGAR = [720575940624963786,720575940630233916,720575940637568838,720575940638202345,
         720575940617000768,720575940630797113,720575940632889389,720575940621754367,
         720575940621502051,720575940640649691,720575940639332736,720575940616885538,
         720575940639198653,720575940620900446,720575940617937543,720575940632425919,
         720575940633143833,720575940612670570,720575940628853239,720575940629176663,
         720575940611875570]
ids = pd.read_csv(f"{BASE}/Completeness_783.csv", index_col=0).index.to_numpy()
fly2i = {int(k): i for i, k in enumerate(ids)}
sugar_idx = [fly2i[s] for s in SUGAR if s in fly2i]
mn9 = fly2i.get(720575940660219265)

# 输出组：MN9 上游中最强的几个
con = pd.read_parquet(f"{BASE}/Connectivity_783.parquet",
                      columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
up = con[con.Postsynaptic_ID == 720575940660219265].sort_values(
    "Connectivity", ascending=False).head(6).Presynaptic_ID.tolist()
motor = sorted(set([mn9] + [fly2i[u] for u in up if u in fly2i]))

meta = {"N": N, "M": M, "wscale": WSCALE,
        "sugar": sugar_idx, "motor": [m for m in motor if m is not None],
        "mn9": mn9}
json.dump(meta, open(f"{OUT}/meta.json", "w"))
print("meta", meta["sugar"][:3], "motor", meta["motor"])
print("总下载量约 %.1f MB" % (sum(os.path.getsize(f"{OUT}/{f}") for f in os.listdir(OUT)) / 1e6))
