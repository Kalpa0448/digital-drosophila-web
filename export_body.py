"""把 NeuroMechFly 的 SDF 转成网页能用的 JSON（每个 link 一个网格 + 位姿）"""
import json, os, re, shutil
import xml.etree.ElementTree as ET

SRC = "/srv/flybrain/nmf/data/design"
OUT = "/srv/flybrain/play/model"

tree = ET.parse(f"{SRC}/sdf/neuromechfly_noLimits.sdf")
root = tree.getroot()
model = root.find("model")

links = []
for link in model.findall("link"):
    name = link.get("name")
    pose = [float(x) for x in (link.findtext("pose") or "0 0 0 0 0 0").split()]
    vis = link.find("visual")
    if vis is None:
        continue
    mesh = vis.find("geometry/mesh")
    if mesh is None:
        continue
    uri = mesh.findtext("uri").strip()
    scale = float((mesh.findtext("scale") or "1 1 1").split()[0])
    stl = os.path.basename(uri)
    links.append({"name": name, "pose": [round(p, 5) for p in pose], "mesh": stl, "scale": scale})

os.makedirs(f"{OUT}/stl", exist_ok=True)
used = set()
for l in links:
    src = f"{SRC}/meshes/stl/{l['mesh']}"
    if os.path.exists(src) and l["mesh"] not in used:
        shutil.copy2(src, f"{OUT}/stl/{l['mesh']}")
        used.add(l["mesh"])

xs = [l["pose"][0] for l in links]
ys = [l["pose"][1] for l in links]
zs = [l["pose"][2] for l in links]
meta = {"links": links,
        "bounds": {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]}}
json.dump(meta, open(f"{OUT}/body.json", "w"))
print("links:", len(links), "| 复制网格:", len(used))
print("包围盒 x", meta["bounds"]["x"], "z", meta["bounds"]["z"])
print("名字样例:", [l["name"] for l in links][:12])
