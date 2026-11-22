#!/usr/bin/env python3
"""果蝇全脑模型 · 网页实验台 后端"""
import base64, json, os, subprocess, threading, time, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = "/srv/flybrain/web"
SUMMARY = "/srv/flybrain/Drosophila_brain_model/results/web/summary.json"
JOBS = os.path.join(ROOT, "jobs")
PY = "/srv/flybrain/.venv/bin/python"
WORKER = os.path.join(ROOT, "run_silence.py")
LOCK = threading.Lock()
UP_FILE = "/srv/flybrain/web/jobs/_update_state.json"
UP = {"path": None, "size": 0, "state": "idle", "log": "", "started": 0}

def up_save():
    try:
        os.makedirs(os.path.dirname(UP_FILE), exist_ok=True)
        with open(UP_FILE, "w", encoding="utf-8") as f:
            json.dump({"state": UP["state"], "bytes": UP["size"], "log": UP["log"],
                       "sec": round(time.time()-UP["started"], 1) if UP["started"] else 0}, f)
    except Exception:
        pass
CURRENT = {"id": None, "proc": None, "started": 0, "n": 1}
LINKS = {}
LINKS_PY = os.path.join(ROOT, "links.py")
CUSTOM_PY = os.path.join(ROOT, "run_custom.py")
CUSTOM = {"proc": None, "started": 0}


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def job_status(nid):
    p = os.path.join(JOBS, f"{nid}.json")
    if os.path.exists(p):
        return {"state": "done", "result": read_json(p, {})}
    if CURRENT["id"] == nid and CURRENT["proc"] and CURRENT["proc"].poll() is None:
        return {"state": "running", "sec": int(time.time() - CURRENT["started"]),
                "n": CURRENT["n"]}
    if CURRENT["id"] == nid:
        return {"state": "failed"}
    return {"state": "missing"}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, body, ctype="application/json; charset=utf-8", code=200):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(json.dumps(obj, ensure_ascii=False), code=code)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        p, q = u.path, urllib.parse.parse_qs(u.query)

        if p in ("/", "/index.html"):
            fp = os.path.join(ROOT, "index.html")
            if not os.path.exists(fp):
                return self._json({"error": "no index"}, 500)
            return self._send(open(fp, "rb").read(), "text/html; charset=utf-8")

        if p == "/api/summary":
            s = read_json(SUMMARY, {})
            # 已跑完的按需实验也并进去
            extra = []
            if os.path.isdir(JOBS):
                for fn in os.listdir(JOBS):
                    if fn.endswith(".json") and fn.startswith("sl_"):
                        d = read_json(os.path.join(JOBS, fn), {})
                        if d.get("ok"):
                            extra.append({"id": d["id"], "mn9": d["mn9"],
                                          "n_trials": d.get("n_trials", 1),
                                          "n_firing": d.get("n_firing", 0),
                                          "on_demand": True})
            s["extra"] = extra
            s["busy"] = {"id": CURRENT["id"], "n": CURRENT["n"]} if CURRENT["id"] else None
            return self._json(s)

        if p == "/api/job":
            nid = (q.get("id") or [""])[0]
            if not nid.isdigit():
                return self._json({"error": "bad id"}, 400)
            return self._json(job_status(nid))

        if p == "/api/custom":
            fp = os.path.join(JOBS, "custom_latest.json")
            running = CUSTOM["proc"] is not None and CUSTOM["proc"].poll() is None
            data = read_json(fp, {})
            data["running"] = running
            data["elapsed"] = int(time.time() - CUSTOM["started"]) if running else None
            return self._json(data)

        if p == "/api/links":
            nid = (q.get("id") or [""])[0]
            if not nid.isdigit():
                return self._json({"error": "bad id"}, 400)
            fp = os.path.join(JOBS, f"links_{nid}.json")
            if os.path.exists(fp):
                return self._json(read_json(fp, {}))
            if LINKS.get(nid) == "running":
                return self._json({"state": "running"})
            LINKS[nid] = "running"

            def work():
                try:
                    subprocess.run([PY, LINKS_PY, nid], cwd="/srv/flybrain",
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
                    LINKS[nid] = "done"
                except Exception:
                    LINKS[nid] = "failed"

            threading.Thread(target=work, daemon=True).start()
            return self._json({"state": "running"})

        if p == "/api/health":
            return self._json({"ok": True, "busy": CURRENT["id"]})
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urllib.parse.urlsplit(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}

        # ============ 网页上传更新（分片） ============
        if u.path == "/api/up_chunk":
            i = int(body.get("i") or 0)
            if i == 0 or not UP.get("path"):
                UP["path"] = "/tmp/flybrain_upload_%d.zip" % int(time.time())
                UP["state"] = "uploading"; UP["size"] = 0; UP["log"] = ""
                open(UP["path"], "wb").close()
            try:
                raw = base64.b64decode(body.get("data") or "")
            except Exception:
                return self._json({"ok": False, "error": "分片解码失败"}, 400)
            with open(UP["path"], "ab") as f:
                f.write(raw)
            UP["size"] += len(raw)
            up_save()
            return self._json({"ok": True, "i": i, "recv": UP["size"]})

        if u.path == "/api/up_finish":
            if not UP.get("path") or not os.path.exists(UP["path"]):
                return self._json({"ok": False, "error": "没有收到上传"}, 400)
            UP["state"] = "applying"; UP["started"] = time.time(); up_save()

            def _apply():
                try:
                    env2 = dict(os.environ, FLYBRAIN_NO_RESTART="1")
                    r = subprocess.run(["/bin/bash", "/srv/flybrain/update.sh", UP["path"]],
                                       capture_output=True, text=True, timeout=600, env=env2)
                    UP["log"] = ((r.stdout or "")[-3000:] + (r.stderr or "")[-1500:]).strip()
                    UP["state"] = "done" if r.returncode == 0 else "failed"
                    up_save()
                    # 状态已落盘，再脱离当前进程重启（否则重启会杀掉本线程）
                    subprocess.Popen(["/bin/bash", "-c",
                                      "sleep 2; systemctl restart flybrain.service; systemctl restart flyplay.service"],
                                     start_new_session=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    UP["log"] = "执行异常: %s" % e
                    UP["state"] = "failed"
                finally:
                    try: os.remove(UP["path"])
                    except Exception: pass
                    UP["path"] = None

            threading.Thread(target=_apply, daemon=True).start()
            return self._json({"ok": True, "state": "applying"})

        if u.path == "/api/up_status":
            if UP["state"] == "idle" and os.path.exists(UP_FILE):
                try:
                    with open(UP_FILE, encoding="utf-8") as f:
                        d = json.load(f)
                    if d.get("state") in ("done", "failed"):
                        return self._json(d)
                except Exception:
                    pass
            return self._json({"state": UP["state"], "bytes": UP["size"], "log": UP["log"],
                               "sec": round(time.time()-UP["started"], 1) if UP["started"] else 0})

        if u.path == "/api/custom":
            if CUSTOM["proc"] is not None and CUSTOM["proc"].poll() is None:
                return self._json({"error": "busy"}, 429)
            freq = str(int(float(body.get("freq") or 150)))
            nexc = str(int(body.get("nexc") or 20))
            nrun = str(max(1, min(int(body.get("nrun") or 1), 5)))
            slnc = str(int(body.get("silence"))) if str(body.get("silence") or "").isdigit() else "0"
            try:
                os.remove(os.path.join(JOBS, "custom_latest.json"))
            except Exception:
                pass
            CUSTOM["proc"] = subprocess.Popen([PY, CUSTOM_PY, freq, nexc, nrun, slnc],
                                              cwd="/srv/flybrain",
                                              stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL)
            CUSTOM["started"] = time.time()
            return self._json({"ok": True, "freq": freq, "nexc": nexc, "nrun": nrun, "silence": slnc})

        if u.path == "/api/run":
            nid = str(body.get("id") or "")
            ntr = max(1, min(int(body.get("n") or 1), 5))
            if not nid.isdigit():
                return self._json({"error": "bad id"}, 400)
            with LOCK:
                if CURRENT["id"] and CURRENT["proc"] and CURRENT["proc"].poll() is None:
                    return self._json({"error": "busy", "id": CURRENT["id"]}, 429)
                os.makedirs(JOBS, exist_ok=True)
                jf = os.path.join(JOBS, f"{nid}.json")
                if os.path.exists(jf):
                    os.remove(jf)
                proc = subprocess.Popen([PY, WORKER, nid, str(ntr)],
                                        cwd="/srv/flybrain",
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
                CURRENT.update({"id": nid, "proc": proc, "started": time.time(), "n": ntr})
            return self._json({"ok": True, "id": nid, "n": ntr})
        return self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    os.makedirs(JOBS, exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", 8770), H).serve_forever()
