#!/bin/bash
# ============================================================
# 数字果蝇 · 一键更新脚本
# 用法: sudo ./update.sh /path/to/flybrain-full.zip
# 作用: 解压新包 → 覆盖 play/web/模型代码 → 保留数据与虚拟环境 → 重启服务
# ============================================================
set -e

ZIP="$1"
ROOT="${FLYBRAIN_ROOT:-/srv/flybrain}"
STAMP=$(date +%Y%m%d_%H%M%S)
WORK="/tmp/flybrain_update_$STAMP"
BACKUP="/tmp/flybrain_backup_$STAMP"

if [ -z "$ZIP" ] || [ ! -f "$ZIP" ]; then
  echo "用法: $0 <包路径.zip>"
  exit 1
fi

echo "[1/6] 解压 $ZIP"
mkdir -p "$WORK"
unzip -q "$ZIP" -d "$WORK"
SRC="$WORK/flybrain"
if [ ! -d "$SRC" ]; then
  # 兼容 zip 里直接是文件的情况
  if [ -d "$WORK/play" ]; then SRC="$WORK"; else
    echo "× 包里没有找到 flybrain/ 或 play/ 目录"; exit 1; fi
fi

echo "[2/6] 备份当前版本到 $BACKUP"
mkdir -p "$BACKUP"
for d in play web Drosophila_brain_model systemd; do
  [ -d "$ROOT/$d" ] && cp -a "$ROOT/$d" "$BACKUP/" 2>/dev/null || true
done

echo "[3/6] 覆盖 play/（保留 brain_worker 数据不动）"
if [ -d "$SRC/play" ]; then
  cp -a "$SRC/play/." "$ROOT/play/"
fi

echo "[4/6] 覆盖 web/（保留 jobs 里的实验结果）"
if [ -d "$SRC/web" ]; then
  mkdir -p "$ROOT/web/jobs"
  cp -a "$SRC/web/." "$ROOT/web/"
fi

echo "[5/6] 覆盖模型代码（保留 results 与 parquet 数据）"
if [ -d "$SRC/Drosophila_brain_model" ]; then
  mkdir -p "$ROOT/Drosophila_brain_model"
  for f in "$SRC/Drosophila_brain_model"/*; do
    base=$(basename "$f")
    case "$base" in
      results|Connectivity_783.parquet|__pycache__) continue ;;
    esac
    cp -a "$f" "$ROOT/Drosophila_brain_model/"
  done
fi

if [ "${FLYBRAIN_NO_RESTART:-0}" = "1" ]; then
  echo "[6/6] 跳过重启（由调用方负责）"
else
  echo "[6/6] 重启服务（延迟 1 秒）"
  ( sleep 1; systemctl restart flybrain.service >/dev/null 2>&1; systemctl restart flyplay.service >/dev/null 2>&1 ) &
  sleep 0.2
fi

echo
echo "=== 完成（服务将在 1 秒后自动重启）==="
echo "  备份在: $BACKUP"
echo "  回滚: cp -a $BACKUP/* $ROOT/"
