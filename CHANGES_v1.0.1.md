# v1.0.1 变更清单（大世界生态模拟）

> 基线：v1.0.0（提交 `2663bbb`）
> 改动文件：**仅 `play/world/index.html`**（+313 / −107 行）
> 其他页面（围栏 / 养果蝇 / 全脑实验台）**无改动**

---

## 0. 速查：新增参数（`P` 对象，共 13 个）

```js
fSatiety → 已废弃（改为 satE 能量制）
satE:140,        // 饱腹能量阈值（≥ 该值不觅食）
riskP:0.4,       // 极度饥饿时每秒冒险概率
traitVar:0.2,    // 个体差异极差（0~0.5）
pheroOn:1,       // 报警信息素开关
pheroT:20,       // 信息素残留秒数
pheroR:0.12,     // 回避半径（地图单位 0~1）
pheroK:1.15,     // 回避强度（aversion 增量）
feedMax:5,       // 一块食物同时进食上限
foodDecay:0.8,   // 食物自然变质（能量/秒）
thFeed:6,        // 取食阈值 MN_feed (Hz)
thEsc:20,        // 逃逸阈值 DN_escape (Hz)
thOvip:8         // 产卵阈值 MN_oviposit (Hz)
```

**被调整的默认值**：`pSoftCap 6→15`、`catchP 1.1→0.8`

---

## 1. 状态机与显示（果蝇）

### 1.1 巡游 / 觅食 同色
- 图例合并为一行「果蝇·巡游/觅食」，颜色 `#7c8cff`
- 绘制：`ff.state==='觅食'` 不再单独配色

### 1.2 逃跑滞回（修「疯狂切换」）
**位置**：`step()` 内威胁判定段

```js
var fleeR = 0.02+0.06*f.aversion;
if(f.fleeLock<=0 && nd<fleeR){ f.fleeLock=1.3; }          // 进入
if(f.fleeLock>0 && nd<fleeR*1.6 && f.fleeLock<0.7){       // 续期（滞回）
  f.fleeLock=0.7;
}
```
修前：逃跑锁到期立刻重锁，中间一帧露出「觅食」→ 状态闪烁（12 秒 5.9 次）
修后：3.8 次 / 12 秒

### 1.3 追踪方向平滑（修「乱跳」）
**位置**：`goal` 分支移动段

```js
// 旧：f.dir = atan2(...) + (Math.random()-0.5)*0.7;   // 每帧折返 ±40°
var tg=Math.atan2(gv,gx);
var dA=((tg-f.dir+Math.PI*3)%(Math.PI*2))-Math.PI;
f.dir += dA*Math.min(1,6*dt) + (Math.random()-0.5)*1.4*dt;
```

### 1.4 进食时不每帧重决策
```js
// 旧：f.intentT=0;（每帧 decide → 状态抖动）
f.intentT=Math.max(f.intentT, 0.9);
```

---

## 2. 青蛙移动改为时间基准

**位置**：`draw()` 内（历史遗留，移动写在渲染层）

```js
// 旧：fm._acc += 1/60;            // 帧率相关，高刷屏快一倍，加速时不动
fm._acc = Math.min(2.0, (fm._acc||0) + frameDt*speedMul);
if(fm._acc < 0.1) return;
var nHop = Math.floor(fm._acc/0.1);   // 一帧最多补 4 次
```
新增全局 `var frameDt=1/60;`，`loop()` 里 `frameDt=dt`。
暂停保护保留：`if(paused){ fm._acc=0; return; }`

---

## 3. 饱腹系统（时间 → 能量）

**删除了 satT 计时机制**，改为纯能量阈值。

### 3.1 分级函数（新增，`index.html` 中部）
```js
function satLevel(e, satT){          // 3 饱腹 / 2 正常 / 1 饥饿 / 0 极度饥饿
  if(e >= (P.satE||140)) return 3;
  if(e >= P.hungry) return 2;
  if(e >= P.hungry*0.5) return 1;
  return 0;
}
function satLabel(e, satT){ return ['极度饥饿','饥饿','正常','饱腹'][satLevel(e,satT)]; }
function satLabelP(e, satT){         // 蜘蛛版：按 pBreedE(135) 分档
  var need=P.pBreedE||135;
  if(e>=need) return '饱腹';
  if(e>=need*0.6) return '正常';
  if(e>=need*0.35) return '饥饿';
  return '极度饥饿';
}
```

### 3.2 觅食渴望分级
**位置**：`decide()` 找食物之前

```js
if(f.energy >= (P.satE||140)*(f.satEK||1)){ f.intent='wander'; return; }  // 饱腹不找
var LV = satLevel(f.energy, f.satT);
var want = LV>=3 ? 0 : (LV===2 ? 0.35 : (LV===1 ? 0.8 : 1));
if(Math.random() > want){ f.intent='wander'; return; }
```

### 3.3 档案面板
新增一行 `饱腹感`（`id="o-sat"`），只显示状态词，能量数值留在「能量」行（不重复）。

---

## 4. 极度饥饿 → 冒险觅食

**位置**：`step()` 每帧判定（不依赖 decide）

```js
if((f.riskT||0)<=0 && f.energy < P.hungry*0.5 && foods.length){
  if(Math.random() < P.riskP*dt){          // 每秒 riskP 概率
    f.riskT = 4 + Math.random()*3;
    f.riskN = (f.riskN||0)+1;
    // 并锁定最近食物
    f.intent='food'; f.aim=最近食物; f.intentT=0.3;
  }
}
```
- 冒险期间：**不触发逃跑**（`var braving=(f.riskT||0)>0`）
- 速度 ×1.3
- 吃到食物后 `f.riskT=min(riskT,1.2)` 收尾
- 状态显示：`f.state + '（冒险觅食）'`

---

## 5. 个体差异（以面板参数为均值）

### 5.1 生成器
```js
function traitK(mult){
  var sp=(P.traitVar===undefined?0.2:P.traitVar)*(mult||1);
  if(sp<=0) return 1;
  return Math.max(0.25, 1 + (Math.random()*2-1)*sp);
}
```

### 5.2 果蝇字段（`addFly`）
```js
metK:traitK(1.0),      // 代谢
eatK:traitK(0.75),     // 进食速度
learnK:traitK(1.25),   // 学习率
forgetK:traitK(1.25),  // 遗忘率
clutchK:traitK(1.5),   // 每窝卵数
spdK:traitK(0.6),      // 移动速度（±12%）
satEK:traitK(0.35)     // 饱腹阈值
```

### 5.3 蜘蛛字段（`addPred`）
```js
metK:traitK(1.0), catchK:traitK(1.25), clutchK:traitK(1.5), spdK:traitK(0.6)
```

### 5.4 使用点
| 位置 | 修改 |
|---|---|
| 果蝇代谢 | `P.met*(f.metK||1)*actK*tempMetK()*dt` |
| 进食 | `P.eat*(f.eatK||1)*feedGate*dt` |
| 学习 | `P.learn*(f.learnK||1)*...` |
| 遗忘 | `P.forget*(f.forgetK||1)*dt` |
| 产卵数 | `(P.fClutch||1)*(f.clutchK||1)` |
| 速度（觅食/巡游/逃跑） | `P.speed*(f.spdK||1)` |
| 饱腹阈值 | `(P.satE||140)*(f.satEK||1)` |
| 蜘蛛代谢/捕食/产卵/速度 | 各自 `*K` |

档案面板新增 `个体特质` 行（`id="o-trait"`）。

---

## 6. 卵错峰孵化（防种群激增）

- 所有 `eggs.push({...})` 增加 `hatchK: traitK(1.4)`
- 孵化判定：
```js
var readyT = (e.spider?P.pEggT:P.eggT) * (e.hatchK||1);
```

---

## 7. 剧烈活动额外耗能

```js
// 果蝇
var actK = (f.state==='逃跑') ? 1.8
         : (f.state==='交配') ? 1.5
         : (f.state==='求偶') ? 1.2
         : ((f.riskT||0)>0 ? 1.3 : 1);
f.energy -= P.met*(f.metK||1)*actK*tempMetK()*dt;

// 蜘蛛（追猎时）
p.energy -= 0.15*(p.metK||1)*(p.chasingNow?2.0:1)*tempMetK()*dt;
```

---

## 8. 报警信息素（新系统）

### 8.1 数据结构
```js
var pheros=[];   // {u, v, ttl, life}
function releaseAlarm(u,v){
  if(!P.pheroOn) return;
  if(pheros.length>150) pheros.shift();
  pheros.push({u,v, ttl:P.pheroT, life:P.pheroT});
}
```

### 8.2 释放点（3 处）
- 蜘蛛捕食：`releaseAlarm(fy.u,fy.v)`
- 青蛙弹舌：`releaseAlarm(tgt.u,tgt.v)`
- 捕蝇草夹住：`releaseAlarm(fl2.u,fl2.v)`

### 8.3 衰减
`step()` 内每帧 `ttl-=dt`，≤0 删除。

### 8.4 行为影响（`decide` 开头）
```js
if(P.pheroOn && pheros.length){
  找到最近信息素 bp;
  if(bpd < pheroR²){
    f.aversion += pheroK*0.10;
    if(!f.aim){                       // 只打断闲逛，不打断进食/求偶
      f.intent='wander'; f.aim=null;
      f.dir = atan2(远离方向);
      return;
    }
  }
}
```
> ⚠️ 注意：**正在吃饭/求偶的果蝇不受影响**。早期版本强制放弃目标，导致果蝇饿死、种群灭绝。

### 8.5 绘制
`draw()` 食物之前，红色扩散圈：
```js
ctx.strokeStyle='rgba(240,90,110,'+(0.45*k)+')';   // k = ttl/life
```
图例新增一行「○ 报警信息素（同伴被害处）」

---

## 9. 同时取食上限

**位置**：进食分支前

```js
var nEat=0;
for(...) if(oe!==f && oe.state==='进食' && oe.aim===goal) nEat++;
if(nEat >= (P.feedMax||5)){
  f.aim=null; f.intent='wander'; f.intentT=1+Math.random();
  f.dir+=1.4+Math.random();
  /* 边界夹取后 continue */
}
```

---

## 10. 食物自然变质

`step()` 内：
```js
if((P.foodDecay||0)>0){
  for(...) { foods[df].energy -= P.foodDecay*dt; if(<=0) 删除; }
}
```

---

## 11. 行为读出阈值（接神经放电）

`readBrainOut()` 已产出 `f.mnFeed / f.mnEsc / f.mnStep`（Hz）。

```js
// 取食：MN_feed 放电调制吃速（0.4~1.8 倍）
var feedGate = (f.mnFeed>0.01) ? Math.max(0.4, Math.min(1.8, f.mnFeed/(P.thFeed||6))) : 1;

// 逃逸：DN_escape 调制逃跑时长（0.6~2.0 倍）
var escK = (f.mnEsc>0.01) ? Math.max(0.6, Math.min(2.0, f.mnEsc/(P.thEsc||20))) : 1;
f.fleeLock = 1.3*escK;

// 产卵：MN_oviposit 超阈值多产一颗
if((f.mnStep||0) > (P.thOvip||8)) nEgg += 1;
```

---

## 12. 参数面板重构

**50 个控件，7 个分组**，全部 `id` 保持不变（`bindP` 依赖）：

```
▍果蝇 · 能量与进食   9 项（代谢/饥饿/饱腹/进食/食物/抢食/变质/供给/冒险）
▍果蝇 · 繁殖与寿命   9 项
▍果蝇 · 学习与嗅觉   9 项（学习/遗忘/信息素4项/行为阈值3项）
▍蜘蛛 · 捕食         3 项
▍蜘蛛 · 繁殖与寿命   9 项
▍天敌 · 青蛙与捕蝇草 5 项
▍环境与策略         6 项（温度/斑块/极差/低密度交配+两阈值）
```

新增滑块 id：`q-sate, q-risk, q-tvar, q-feedmax, q-fdecay, q-phon, q-pht, q-phr, q-phk, q-thfeed, q-thesc, q-thovip`

---

## 13. 蜘蛛种群平衡修正

### 13.1 繁殖死锁
**问题**：软容量 6 < 初始投放 8 → `preds.length >= pSoftCap` 恒真 → 永不繁殖。
```js
// 软容量不得低于初始投放数
var pSoftLim = Math.max(P.pSoftCap||14, P.pInit||0, 4);
var pCrowded = preds.length >= pSoftLim;
```
默认 `pSoftCap: 6 → 15`。

### 13.2 卵孵化加软容量
```js
if(preds.length >= Math.max(P.pSoftCap||14, P.pInit||0, 4)+2 || preds.length >= P.pMax){ 延迟孵化 }
```

### 13.3 捕食概率
`catchP: 1.1 → 0.8`（补偿新增的活动耗能，避免果蝇崩盘）

---

## 14. 调试接口扩展

```js
window.__dbg = {
  ...原有 frogs/traps/preds/hAt/isNearWater/waterEdgeSpot/WATER,
  get flies(), get foods(), get eggs(), get pheros(),
  pick(id),            // 按 id 选中个体（测试用）
  satLabel, satLevel,
  releaseAlarm(u,v)
}
```

---

## 15. 平衡实测（30× 加速，每轮约 2400 秒模拟）

| 指标 | 结果 |
|---|---|
| 果蝇 | 30 ~ 66 |
| 蜘蛛 | 12 ~ 17 |
| 果蝇:蜘蛛 | **2.8 ~ 3.1 : 1** |
| 灭绝 | 多轮（6+6+3）未见 |
| NaN / 越界 / 非法状态 | 0 |
| 未捕获异常 | 0 |
| 全局变量数 | 恒定 246（无泄漏） |

---

## 16. 性能 / 兼容性注意

- `step()` 新增每帧遍历：`pheros`（≤150）、`foods`（≤70），开销可忽略
- 进食时遍历 `flies` 统计同食物进食者：O(n²)，n≈50，实测单帧 <1 ms
- 所有新参数都有 `|| 默认值` 兜底，缺字段的旧存档不会报错
- `f.satT` 字段保留但**不再参与判定**（仅兼容）

---

## 17. 已知遗留 / 可继续做

1. 卵在超软容量时仍是「概率消失」，未改成延迟孵化
2. 捕蝇草只参与档案「最近威胁」显示，行为层仍按老逻辑（吸引 + 夹住）
3. 行为读取阈值依赖 `readBrainOut`，非选中个体降频 3 帧更新，阈值响应有 ~50 ms 延迟
