#!/bin/bash
# ============================================================
# 数字果蝇 · 一键部署（自动处理依赖 / 端口占用 / 开机自启）
#
#   sudo ./install.sh                       默认 /srv/flybrain，端口 8780 + 8770
#   sudo ./install.sh /opt/flybrain         自定义路径
#   sudo ./install.sh --lite                只装前端（8780），不起实验台
#   sudo ./install.sh --port 9000           指定前端端口
#   sudo ./install.sh --no-autostart        装好但不开机自启
#   sudo ./install.sh --no-deps             跳过 pip 安装
#   sudo ./install.sh --mirror              用清华源装 pip（网络慢时）
# ============================================================
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="/srv/flybrain"
SYSD="${FLYBRAIN_SYSTEMD:-/etc/systemd/system}"
PORT=8780
LABPORT=8770
LITE=0
NO_DEPS=0
AUTOSTART=1
MIRROR=0

while [ $# -gt 0 ]; do
  case "$1" in
    --lite) LITE=1 ;;
    --no-deps) NO_DEPS=1 ;;
    --no-autostart) AUTOSTART=0 ;;
    --mirror) MIRROR=1 ;;
    --port) shift; PORT="$1" ;;
    --lab-port) shift; LABPORT="$1" ;;
    -*) echo "未知参数: $1"; exit 1 ;;
    *) TARGET="$1" ;;
  esac
  shift
done

say(){ printf "      %s\n" "$*"; }
port_busy(){ ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"; }

echo "=== 数字果蝇 部署 ==="
echo "路径: $TARGET   端口: $PORT$([ $LITE -eq 0 ] && echo " / $LABPORT")
echo "模式: $([ $LITE -eq 1 ] && echo '仅前端' || echo '完整（含实验台）')  开机自启: $([ $AUTOSTART -eq 1 ] && echo 开 || echo 关)"
echo

# ---------- 0. 环境与依赖 ----------
[ "$(id -u)" = "0" ] || { echo "× 请用 sudo 运行"; exit 1; }

echo "[0/8] 检查运行环境"
command -v python3 >/dev/null || { echo "× 没找到 python3，请先 sudo apt install python3"; exit 1; }
say "python3 $(python3 -V 2>&1 | awk '{print $2}')"

MISS=""
for c in curl ss unzip; do command -v $c >/dev/null || MISS="$MISS $c"; done
if [ $LITE -eq 0 ] && [ $NO_DEPS -eq 0 ]; then
  python3 -c "import venv" 2>/dev/null || MISS="$MISS python3-venv"
fi
if [ -n "$MISS" ]; then
  say "缺少:$MISS —— 尝试自动安装"
  if command -v apt-get >/dev/null; then
    apt-get update -qq >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $MISS >/dev/null 2>&1 && say "已安装:$MISS" || {
      echo "× 自动安装失败，请手动：sudo apt install$MISS"; exit 1; }
  else
    echo "× 缺少$MISS，且没有 apt，请手动安装"; exit 1;
  fi
else
  say "基础工具齐了"
fi

# 磁盘空间（需要约 400 MB）
AVAIL=$(df -Pm "$(dirname "$TARGET")" 2>/dev/null | awk 'NR==2{print $4}')
if [ -n "$AVAIL" ] && [ "$AVAIL" -lt 400 ]; then
  echo "× 磁盘剩余 ${AVAIL}MB，至少需要 400MB"; exit 1
fi
say "磁盘可用 ${AVAIL:-?} MB"

# ---------- 1. 端口 ----------
echo "[1/8] 检查端口占用"
fix_port(){
  local p=$1 name=$2
  if port_busy "$p"; then
    say "端口 $p 已被占用，往上找一个空闲的"
    local q=$((p+1)); local tries=0
    while port_busy "$q" && [ $tries -lt 40 ]; do q=$((q+1)); tries=$((tries+1)); done
    say "→ 改用 $q"
    echo "$q"
  else
    echo "$p"
  fi
}
PORT=$(fix_port "$PORT")
[ $LITE -eq 0 ] && LABPORT=$(fix_port "$LABPORT")
say "最终端口: $PORT$([ $LITE -eq 0 ] && echo " / $LABPORT")"

# ---------- 2. 复制文件 ----------
echo "[2/8] 复制文件到 $TARGET"
mkdir -p "$TARGET"
for d in play web Drosophila_brain_model systemd; do
  [ -d "$HERE/$d" ] || continue
  mkdir -p "$TARGET/$d"; cp -a "$HERE/$d/." "$TARGET/$d/"
done
for f in README_部署.md update.sh uninstall.sh install.sh ctl.sh; do
  [ -f "$HERE/$f" ] && cp -a "$HERE/$f" "$TARGET/" || true
done
chmod +x "$TARGET"/*.sh 2>/dev/null || true

# ---------- 3. 虚拟环境与依赖 ----------
if [ $LITE -eq 0 ] && [ $NO_DEPS -eq 0 ]; then
  echo "[3/8] 创建虚拟环境并装依赖（几分钟）"
  [ -d "$TARGET/.venv" ] || python3 -m venv "$TARGET/.venv"
  P="$TARGET/.venv/bin/pip"
  IDX=""
  [ $MIRROR -eq 1 ] && IDX="-i https://pypi.tuna.tsinghua.edu.cn/simple"
  "$P" install -q -U pip $IDX || true
  if ! "$P" install -q pandas pyarrow numpy scipy brian2==2.10.1 $IDX 2>/dev/null; then
    say "默认源失败，换清华源重试"
    "$P" install -q -i https://pypi.tuna.tsinghua.edu.cn/simple \
      pandas pyarrow numpy scipy brian2==2.10.1 || {
      echo "× 依赖安装失败，可试： sudo $0 --mirror"; exit 1; }
  fi
  python3 - <<PY
import sys
sys.path.insert(0, "$TARGET/.venv/lib/python%s/site-packages" % "$(python3 -V 2>&1 | awk '{print $2}' | cut -d. -f1,2)")
PY
  say "依赖装好了"
else
  echo "[3/8] 跳过依赖安装"
fi

# ---------- 4. systemd ----------
echo "[4/8] 生成 systemd 服务"
PYBIN="$TARGET/.venv/bin/python"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"
mkdir -p "$SYSD"

cat > "$SYSD/flyplay.service" <<EOF
[Unit]
Description=Digital Fly enclosure (static + world + colony)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$TARGET/play
ExecStart=$PYBIN -m http.server $PORT --bind 0.0.0.0 --directory $TARGET/play
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

if [ $LITE -eq 0 ]; then
  # 实验台端口写进 server.py 的启动处（用环境变量覆盖更稳）
  cat > "$SYSD/flybrain.service" <<EOF
[Unit]
Description=FlyBrain 数字果蝇全脑实验台 (web)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$TARGET/web
Environment=FLYBRAIN_PORT=$LABPORT
ExecStart=$PYBIN $TARGET/web/server.py
Restart=always
RestartSec=5
Nice=5

[Install]
WantedBy=multi-user.target
EOF
fi

# ---------- 5. 启动 ----------
echo "[5/8] 启动服务"
systemctl daemon-reload
systemctl enable --now flyplay.service >/dev/null 2>&1 || systemctl restart flyplay.service
[ $LITE -eq 0 ] && { systemctl enable --now flybrain.service >/dev/null 2>&1 || systemctl restart flybrain.service; }
sleep 2

# ---------- 6. 开机自启 ----------
echo "[6/8] 开机自启：$([ $AUTOSTART -eq 1 ] && echo 开启 || echo 关闭)"
if [ $AUTOSTART -eq 1 ]; then
  systemctl enable flyplay.service >/dev/null 2>&1 || true
  [ $LITE -eq 0 ] && systemctl enable flybrain.service >/dev/null 2>&1 || true
else
  systemctl disable flyplay.service >/dev/null 2>&1 || true
  [ $LITE -eq 0 ] && systemctl disable flybrain.service >/dev/null 2>&1 || true
fi

# ---------- 7. 自检 ----------
echo "[7/8] 自检"
chk(){ printf "      %-46s %s\n" "$1" "$(curl -s -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo ERR)"; }
chk "http://127.0.0.1:$PORT/"
chk "http://127.0.0.1:$PORT/world/"
chk "http://127.0.0.1:$PORT/colony/"
[ $LITE -eq 0 ] && chk "http://127.0.0.1:$LABPORT/"

# ---------- 8. 完成 ----------
IP=$(hostname -I 2>/dev/null | awk '{print $1}'); [ -z "$IP" ] && IP=127.0.0.1
echo "[8/8] 完成"
if command -v ufw >/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow $PORT/tcp >/dev/null 2>&1 || true
  [ $LITE -eq 0 ] && { ufw allow $LABPORT/tcp >/dev/null 2>&1 || true; }
  say "已放行 $PORT$([ $LITE -eq 0 ] && echo "、$LABPORT")"
fi
echo
echo "  打开：http://$IP:$PORT/"
echo "        大世界 /world/    养果蝇 /colony/"
[ $LITE -eq 0 ] && echo "        实验台 http://$IP:$LABPORT/"
echo
echo "  控制：sudo $TARGET/ctl.sh status|start|stop|restart|autostart on|off"
echo "  更新：sudo $TARGET/update.sh 新包.zip"
echo "  卸载：sudo $TARGET/uninstall.sh [--purge]"
