# APK 构建（ARM64 本机编译）

## 为什么能编
Google 的 `aapt2` 只有 x86_64 二进制，ARM64 直接跑会报 `cannot execute`。
解法规避：用社区编的 **ARM64 aapt2**（ReVanced/aapt2），在 `gradle.properties` 里覆盖：

```properties
android.aapt2FromMavenOverride=/tmp/andro/aapt2
```

## 环境
```
JDK 21 / Gradle 8.7 / AGP 8.5.2
Android SDK: platform-tools + platforms;android-34 + build-tools;34.0.0
aapt2: ReVanced/aapt2 v1.1.0 (aapt2-arm64-v8a)
```

## 构建
```bash
export ANDROID_HOME=/tmp/andro/sdk
cd /srv/flybrain/apk
# 先把网页复制进 assets
rm -rf app/src/main/assets/www && cp -r /srv/flybrain/play app/src/main/assets/www
/tmp/andro/gradle-8.7/bin/gradle --no-daemon assembleDebug
# 产物 app/build/outputs/apk/debug/app-debug.apk
```

## 已知事项
- **aapt 会把 `*.gz` 自动解压并去掉后缀**，所以 `brain_worker.js` 加了兼容：
  先请求 `.gz`，404 时请求无后缀文件，靠 gzip 魔数判断是否需要解压
- 目前是 debug 签名（可安装，不可上架）；正式发布需要 keystore
- 图标用的是系统默认（Manifest 未指定 icon）
- WebView 以 `file:///android_asset/www/index.html` 加载，已开启
  `allowFileAccessFromFileURLs` / `allowUniversalAccessFromFileURLs`
