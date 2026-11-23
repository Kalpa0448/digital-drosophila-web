#!/usr/bin/env bash
# 一键构建 APK（ARM64 本机编译）
# 用法: ./build.sh            → debug 包
#       ./build.sh release    → 未签名 release 包
set -euo pipefail

TC=/srv/android-toolchain
ROOT=/srv/flybrain
APK_DIR=$ROOT/apk

export ANDROID_HOME=$TC/sdk
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))

# SDK 路径
echo "sdk.dir=$ANDROID_HOME" > "$APK_DIR/local.properties"

# 同步网页资源
rm -rf "$APK_DIR/app/src/main/assets/www"
mkdir -p "$APK_DIR/app/src/main/assets"
cp -r "$ROOT/play" "$APK_DIR/app/src/main/assets/www"
rm -rf "$APK_DIR/app/src/main/assets/www/.git"
echo "assets: $(du -sh "$APK_DIR/app/src/main/assets/www" | cut -f1)"

cd "$APK_DIR"
TASK=${1:-debug}
if [ "$TASK" = "release" ]; then
  "$TC/gradle-8.7/bin/gradle" --no-daemon assembleRelease
  OUT=app/build/outputs/apk/release/app-release-unsigned.apk
else
  "$TC/gradle-8.7/bin/gradle" --no-daemon assembleDebug
  OUT=app/build/outputs/apk/debug/app-debug.apk
fi

echo ""
echo "✅ 产物: $APK_DIR/$OUT"
ls -lh "$APK_DIR/$OUT" | awk '{print "   大小:", $5}'
