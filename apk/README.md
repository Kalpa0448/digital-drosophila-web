# APK 构建（ARM64 本机编译）

## 为什么能编
Google 的 `aapt2` 只有 x86_64 二进制，ARM64 直接跑会报 `cannot execute`。
解法规避：用社区编的 **ARM64 aapt2**（ReVanced/aapt2），在 `gradle.properties` 覆盖：

```properties
android.aapt2FromMavenOverride=/srv/android-toolchain/aapt2
```

## 工具链位置（已持久化到 /srv，系统还原不影响）
```
/srv/android-toolchain/
├── gradle-8.7/            Gradle
├── sdk/                   Android SDK（platform-tools / platforms;android-34 / build-tools;34.0.0）
└── aapt2                  ReVanced aapt2 v1.1.0 (arm64-v8a)
```

## 一键构建
```bash
bash /srv/flybrain/apk/build.sh          # debug 包
bash /srv/flybrain/apk/build.sh release  # release（未签名）
```
脚本会自动：写 `local.properties` → 同步 `play/` 到 assets → 调 Gradle 构建。

产物：`apk/app/build/outputs/apk/debug/app-debug.apk`

## 重建工具链（如果 /srv 也丢了）
```bash
mkdir -p /srv/android-toolchain && cd /srv/android-toolchain
curl -sLO https://services.gradle.org/distributions/gradle-8.7-bin.zip
curl -sLO https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
curl -sL -o aapt2 https://github.com/ReVanced/aapt2/releases/download/v1.1.0/aapt2-arm64-v8a
chmod +x aapt2
unzip -q gradle-8.7-bin.zip && unzip -q commandlinetools-linux-11076708_latest.zip
yes | cmdline-tools/bin/sdkmanager --sdk_root=$PWD/sdk --licenses
cmdline-tools/bin/sdkmanager --sdk_root=$PWD/sdk platform-tools "platforms;android-34" "build-tools;34.0.0"
```

## 已知事项
- **aapt 会把 `*.gz` 自动解压并去掉后缀**，`brain_worker.js` 已做兼容（先试 .gz，404 试无后缀，靠 gzip 魔数判断）
- 目前 debug 签名（可安装，不可上架）；正式发布需要 keystore
- 图标用系统默认（Manifest 未指定 icon）
- WebView 加载 `file:///android_asset/www/index.html`
- 手机实机调试走过的坑：`location.origin` 在 file:// 下为空 → 页面跳转要用相对路径 + 带 index.html
