#!/bin/bash
# ============================================================
# 数字果蝇 · 卸载脚本
#   sudo ./uninstall.sh           停服务、删 systemd，保留目录与数据
#   sudo ./uninstall.sh --purge   连整个目录一起删（含实验结果，慎用）
# ============================================================
set -e

ROOT="${FLYBRAIN_ROOT:-/srv/flybrain}"
SYSD="${FLYBRAIN_SYSTEMD:-/etc/systemd/system}"
PURGE=0
for a in "$@"; do
  case "$a" in
    --purge) PURGE=1 ;;
    *) ROOT="$a" ;;
  esac
done

if [ "$(id -u)" != "0" ]; then
  echo "× 请用 sudo 运行"; exit 1
fi

echo "=== 数字果蝇 卸载 ==="
echo "目标: $ROOT"

echo "[1/3] 停止并禁用服务"
for s in flyplay.service flybrain.service; do
  systemctl stop "$s" >/dev/null 2>&1 || true
  systemctl disable "$s" >/dev/null 2>&1 || true
  rm -f "$SYSD/$s"
  echo "      已移除 $s"
done
systemctl daemon-reload >/dev/null 2>&1 || true

echo "[2/3] 清理缓存"
rm -rf "$ROOT/play/brain_worker_cache" 2>/dev/null || true

if [ $PURGE -eq 1 ]; then
  echo "[3/3] 删除整个目录 $ROOT"
  python3 - "$ROOT" <<'PY'
import shutil, sys, os
p=sys.argv[1]
if os.path.isdir(p): shutil.rmtree(p, ignore_errors=True)
print("      已删除" if not os.path.exists(p) else "      × 删除失败，请手动 rm -rf")
PY
else
  echo "[3/3] 保留目录（数据都在里面）"
  echo "      想彻底删除：sudo rm -rf $ROOT"
fi

echo
echo "=== 完成 ==="
echo "  端口 8780 / 8770 已释放"
