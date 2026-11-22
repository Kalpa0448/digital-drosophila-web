#!/bin/bash
# ============================================================
# 数字果蝇 · 日常控制
#   sudo ./ctl.sh status              看两个服务状态与端口
#   sudo ./ctl.sh start|stop|restart  启停
#   sudo ./ctl.sh autostart on|off    开关开机自启
#   sudo ./ctl.sh port                看当前占用端口
# ============================================================
set -e
ROOT="${FLYBRAIN_ROOT:-/srv/flybrain}"
ACT="${1:-status}"

port_of(){
  # 从 systemd 单元的 ExecStart 里读端口
  local f="/etc/systemd/system/$1.service"
  [ -f "$f" ] || { echo "?"; return; }
  grep -oE "http\.server [0-9]+" "$f" 2>/dev/null | awk '{print $2}' | head -1 | grep . || {
    grep -oE "FLYBRAIN_PORT=[0-9]+" "$f" | cut -d= -f2 | head -1 | grep . || echo "?"
  }
}

case "$ACT" in
  status)
    echo "=== 服务状态 ==="
    for s in flyplay flybrain; do
      st=$(systemctl is-active "$s" 2>/dev/null || true)
      en=$(systemctl is-enabled "$s" 2>/dev/null || true)
      p=$(port_of "$s")
      printf "  %-10s %-8s 自启:%-8s 端口:%s\n" "$s" "${st:-未安装}" "${en:-—}" "$p"
    done
    echo
    echo "=== 端口自检 ==="
    for pair in "flyplay:$ROOT/play" "flybrain:$ROOT/web"; do
      s="${pair%%:*}"; p=$(port_of "$s")
      [ "$p" = "?" ] && continue
      code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$p/" 2>/dev/null || echo ERR)
      printf "  %-10s :%-6s %s\n" "$s" "$p" "$code"
    done
    ;;
  start|stop|restart)
    for s in flyplay flybrain; do
      systemctl "$ACT" "$s" 2>/dev/null && echo "  $s: $ACT 完成" || echo "  $s: 未安装，跳过"
    done
    ;;
  autostart)
    case "${2:-}" in
      on)
        systemctl enable flyplay >/dev/null 2>&1 && echo "  flyplay 开机自启: 已开启"
        systemctl enable flybrain >/dev/null 2>&1 && echo "  flybrain 开机自启: 已开启"
        ;;
      off)
        systemctl disable flyplay >/dev/null 2>&1 && echo "  flyplay 开机自启: 已关闭"
        systemctl disable flybrain >/dev/null 2>&1 && echo "  flybrain 开机自启: 已关闭"
        ;;
      *) echo "用法: $0 autostart on|off"; exit 1 ;;
    esac
    ;;
  port)
    echo "  flyplay  : $(port_of flyplay)"
    echo "  flybrain : $(port_of flybrain)"
    ;;
  *)
    echo "用法: $0 {status|start|stop|restart|autostart on|off|port}"; exit 1 ;;
esac
