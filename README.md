# 数字果蝇 · 网页模拟项目

一个跑在浏览器里的果蝇生态模拟 + 脑仿真实验台。纯前端（无构建、无 CDN），
后端只在"全脑实验台"里用于跑真模拟任务队列。

## 页面

| 路径 | 页面 | 说明 |
|---|---|---|
| `play/` | 围栏 | 顶栏菜单入口，48 神经元 / 145 条边的紧凑 LIF 回路，连接组数据下载到浏览器本地运算 |
| `play/world/` | 大世界 | 2D 等高线地形生态模拟：果蝇、蜘蛛、青蛙、捕蝇草，可看种群与能量曲线 |
| `play/colony/` | 养果蝇 | 单只/群体果蝇 3D 观察，行为状态与脑活动可视化 |
| `web/` | 全脑实验台 | FlyWire v783 全脑（138,639 神经元）LIF 模拟，含沉默实验与敏感性排行 |

## 本地运行

纯静态页面（围栏 / 大世界 / 养果蝇）：

```bash
cd play
python3 -m http.server 8780
# 浏览器打开 http://127.0.0.1:8780/
```

> 不要直接双击 `index.html`：`file://` 下 Web Worker 与连接组数据加载会失败。

全脑实验台需要 Python 环境与官方数据仓库（见下"数据依赖"）：

```bash
python3 web/server.py          # 8770
```

## 目录

```
.
├── play/
│   ├── index.html            围栏主页面（菜单、致谢）
│   ├── flybrain-net.js       48 神经元紧凑回路
│   ├── brain_worker.js       Web Worker 里跑 LIF
│   ├── brain/                连接组压缩数据（gzip）
│   ├── world/                大世界
│   ├── colony/               养果蝇
│   ├── model/                果蝇身体模型
│   └── vendor/               本地第三方库
└── web/                      全脑实验台（前端 + 队列后端）
```

## 技术要点

- **紧凑回路**：把 16.5 万神经元的连接组按细胞类型降维成 48 个 LIF 神经元，保留分组与参数口径
- **本地运算**：连接组 gzip 约 31 MB 下载到浏览器，Web Worker 内 dt=1 ms 跑 LIF，不依赖服务器
- **无依赖前端**：所有页面单文件 HTML + 本地 vendor，离线可跑

## 数据依赖（不进仓库）

以下目录体积过大，未纳入版本控制，需要时按官方仓库自行获取：

- `Drosophila_brain_model/` — philshiu/Drosophila_brain_model（含 FlyWire v783 数据）
- `nmf/`、`flywire_annotations/`、`bench_js/` — 中间数据与基准脚本

## 致谢与许可

- 本项目代码以 **MIT License** 发布，© 2026
- 降维思路与参数口径参考 [fly-sim](https://github.com/sjy20100819mc-cmyk/fly-sim)（MIT，© 2026 sjy20100819mc-cmyk），
  原文见 `play/LICENSE-fly-sim.html`
- 连接组数据来源：FlyWire FAFB v783（138,639 神经元，**CC BY-NC 4.0**）、
  FlyEM 雄性 CNS v1.0；全脑 LIF 模型参考 philshiu/Drosophila_brain_model

> 数据部分为 CC BY-NC 4.0：仅限非商业的学习与研究用途，需署名。
