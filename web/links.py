"""查一个神经元的上下游连接（不算模拟，只查表）
用法: python links.py <flywire_id>
输出: web/jobs/links_<id>.json
"""
import os, sys, json
import pandas as pd

BASE = "/srv/flybrain/Drosophila_brain_model"
os.chdir(BASE)
WEB = "/srv/flybrain/web/jobs"
os.makedirs(WEB, exist_ok=True)

nid = int(sys.argv[1])
cols = ["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"]
df = pd.read_parquet("Connectivity_783.parquet", columns=cols)

out = df[df.Presynaptic_ID == nid].sort_values("Connectivity", ascending=False).head(12)
inn = df[df.Postsynaptic_ID == nid].sort_values("Connectivity", ascending=False).head(12)

def pack(d, key):
    return [{"id": int(r[key]), "syn": int(r.Connectivity), "exc": int(r.Excitatory)}
            for _, r in d.iterrows()]

res = {
    "ok": True, "id": nid,
    "out_degree": int((df.Presynaptic_ID == nid).sum()),
    "in_degree": int((df.Postsynaptic_ID == nid).sum()),
    "out_syn": int(df[df.Presynaptic_ID == nid].Connectivity.sum()),
    "in_syn": int(df[df.Postsynaptic_ID == nid].Connectivity.sum()),
    "downstream": pack(out, "Postsynaptic_ID"),
    "upstream": pack(inn, "Presynaptic_ID"),
}
json.dump(res, open(f"{WEB}/links_{nid}.json", "w"), ensure_ascii=False)
print("ok", res["out_degree"], res["in_degree"])
