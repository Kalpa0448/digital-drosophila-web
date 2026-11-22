/* 手机端本机运算：LIF 全脑模型（13.9 万神经元 / 1500 万连接） */

let N = 0, M = 0, WSCALE = 8;
let indptr, dst, wq, meta;
let v, g, rfc, sugar, motor, motorSet, isSugar, isMotor;

const V0 = -52, VRST = -52, VTH = -45, TMBR = 20, TAU = 5, TRFC = 2.2, WSYN = 0.275;
const DT = 1.0;                 // ms（1 ms 步长，精度略降、快 10 倍）
const BIN = 100;                // 每 100 ms 脑时间回报一次
const SUGAR_HZ = 150;

let stepsPerBin = Math.round(BIN / DT);
let running = false;

/* ---- 可塑性：两条通路的增益（感觉→中枢、中枢→输出） ----
   简化 R-STDP：按三组放电率的相关性调整通路增益，不是逐条突触改权重 */
let train = false;

/* ---- 投喂 ---- */
let feedUntil = 0;            // 脑时间(ms)之前，糖神经元用高频刺激
let brainMs = 0;              // 已模拟的脑时间(ms)

/* ---- 条件化训练协议 ----
   每轮 8 秒：线索 3s → 奖励 2s（线索+糖）→ 休息 3s
   学习：奖励期里"线索活跃 & 输出活跃"→ 线索→输出 通路增强（R-STDP） */
let condOn = false;
let cueSet = [];              // 作为"气味线索"的神经元索引
let cueHz = 200, proxHz = 0;
let round = 0, phase = 'idle', phaseT = 0;
let wCue = 0.0;               // 学到的"线索→输出"强度
let cueTrace = 0, motTrace = 0;
let cueRate = 0, cueMotorRate = 0;
let learnHist = [];           // 每轮：线索期输出放电率
const ROUND_MS = 8000, CUE_MS = 3000, REWARD_MS = 2000;
const COND_LR = 0.06, COND_DECAY = 0.005;
let gainSC = 1.0, gainCM = 1.0;      // 初始增益
let rateSC = 0, rateCM = 0;          // 平滑后的相关量
let mn9Rate = 0, mn9Hist = [];
const LR = 0.02, DECAY = 0.02;

async function gunzip(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('加载失败 ' + url);
  if (!res.body || typeof DecompressionStream === 'undefined') {
    // 浏览器不支持流式解压时，退化成后端给明文（不应该发生）
    return new Uint8Array(await res.arrayBuffer());
  }
  const ds = new DecompressionStream('gzip');
  const stream = res.body.pipeThrough(ds);
  const chunks = [];
  const reader = stream.getReader();
  let total = 0;
  for (; ;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); total += value.length;
    self.postMessage({ type: 'progress', loaded: total });
  }
  const out = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) { out.set(c, off); off += c.length; }
  return out;
}

function decodeVarint(bytes, M) {
  const out = new Int32Array(M);
  let p = 0, i = 0;
  while (i < M) {
    let v0 = 0, shift = 0, b;
    do { b = bytes[p++]; v0 |= (b & 0x7f) << shift; shift += 7; } while (b & 0x80);
    out[i++] = v0;
  }
  return out;
}

async function init() {
  meta = await (await fetch('brain/meta.json')).json();
  N = meta.N; M = meta.M; WSCALE = meta.wscale;
  self.postMessage({ type: 'status', text: '下载连接组 3.8 MB…' });

  const ipRaw = await gunzip('brain/indptr.gz');
  indptr = new Int32Array(ipRaw.buffer, 0, N + 1);

  const dstRaw = await gunzip('brain/dst.gz');
  self.postMessage({ type: 'status', text: '解码连接表…' });
  const deltas = decodeVarint(dstRaw, M);
  dst = new Int32Array(M);
  for (let i = 0; i < N; i++) {
    const s = indptr[i], e = indptr[i + 1];
    let prev = -1;
    for (let j = s; j < e; j++) { prev = prev + deltas[j]; dst[j] = prev; }
  }

  const wRaw = await gunzip('brain/w.gz');
  wq = new Int16Array(wRaw.buffer, 0, M);

  v = new Float32Array(N).fill(V0);
  g = new Float32Array(N);
  rfc = new Float32Array(N);
  sugar = meta.sugar;
  motor = meta.motor;
  motorSet = new Set(motor);
  isSugar = new Uint8Array(N); isMotor = new Uint8Array(N);
  for (const x of sugar) isSugar[x] = 1;
  for (const x of motor) isMotor[x] = 1;
  // 挑 12 个"非糖、非输出"的神经元当嗅觉线索
  cueSet = [];
  for (let i = 0; i < N && cueSet.length < 12; i++) {
    if (!isSugar[i] && !isMotor[i]) cueSet.push(i);
  }

  self.postMessage({ type: 'ready', N: N, M: M });
  loop();
}

const fired = new Int32Array(2048);
let nFired = 0;
let binSpikes = { s: 0, c: 0, m: 0 };
let stepAcc = 0;
let tBrain = 0;          // ms 脑时间
let tWall = 0;           // ms 真实时间
let lastReport = performance.now();
let stepsDone = 0;
let accReal = 0;

function loop() {
  if (!running) return;
  try { loopBody(); } catch (err) { self.postMessage({ type: 'error', text: 'loop: ' + err.message }); running = false; }
  if (running) setTimeout(loop, 0);
}
function loopBody() {
  const t0 = performance.now();
  // 一次跑一个 bin（100 步，约 150 ms）
  for (let s = 0; s < stepsPerBin; s++) {
    nFired = 0;
    for (let i = 0; i < N; i++) {
      let gi = g[i] - DT * g[i] / TAU;
      let vi = v[i];
      if (rfc[i] > 0) { rfc[i] -= DT; }
      else {
        vi = vi + DT * ((V0 - vi + gi) / TMBR);
        if (vi > VTH) {
          vi = VRST; gi = 0; rfc[i] = TRFC;
          if (nFired < fired.length) fired[nFired++] = i;
        }
      }
      g[i] = gi; v[i] = vi;
    }
    // ---- 条件化协议推进 ----
    if (condOn) {
      if (phase === 'idle') { phase = 'cue'; phaseT = 0; round++; }
      phaseT += DT;
      if (phase === 'cue' && phaseT >= CUE_MS) { phase = 'reward'; phaseT = 0; }
      if (phase === 'reward' && phaseT >= REWARD_MS) { phase = 'rest'; phaseT = 0; }
      if (phase === 'rest' && phaseT >= (ROUND_MS - CUE_MS - REWARD_MS)) {
        // 一轮结束：记录线索期输出放电率
        learnHist.push(+cueMotorRate.toFixed(1));
        if (learnHist.length > 60) learnHist.shift();
        phase = 'cue'; phaseT = 0; round++;
        cueMotorRate = 0;
      }
    }
    // 线索神经元输入（线索期 200Hz，奖励期 100Hz）
    if (condOn) {
      const hint = (phase === 'cue') ? cueHz : (phase === 'reward' ? cueHz * 0.5 : 0);
      if (hint > 0) {
        const pc = hint * DT / 1000;
        for (let k = 0; k < cueSet.length; k++) if (Math.random() < pc) fired[nFired++] = cueSet[k];
      }
    }
    // 外部味觉输入（泊松）
    const p = (brainMs < feedUntil ? 320 : SUGAR_HZ) * DT / 1000;
    for (let k = 0; k < sugar.length; k++) if (Math.random() < p) fired[nFired++] = sugar[k];

    // 传播
    for (let k = 0; k < nFired; k++) {
      const src = fired[k], e = indptr[src + 1];
      var gain = 1;
      if (train) { gain = isSugar[src] ? gainSC : (isMotor[src] ? 1 : gainCM); }
      for (let j = indptr[src]; j < e; j++) g[dst[j]] += wq[j] * WSCALE * WSYN * gain;
      if (condOn && phase === 'cue' && isMotor[src]) cueMotorRate += 1;
      if (isSugar[src]) binSpikes.s++;
      else if (isMotor[src]) binSpikes.m++;
      else binSpikes.c++;
    }
    tBrain += DT; stepsDone++;
  }

  const real = performance.now() - t0;
  tWall += real;

  // 归一化到 0~1（经验标定）
  const sz = 0.1 * sugar.length, cz = 0.1 * (N - sugar.length - motor.length), mz = 0.1 * motor.length;
  const sHz = binSpikes.s / sz, cHz = binSpikes.c / cz, mHz = binSpikes.m / mz;
  // 显示用的经验标定：每 100 ms 里"满格"对应多少脉冲
  const REF = { s: 450, c: 1500, m: 40 };
  const sNorm = Math.min(1, binSpikes.s / REF.s);
  const cNorm = Math.min(1, binSpikes.c / REF.c);
  const mNorm = Math.min(1, binSpikes.m / REF.m);

  // ---- 条件化学习（R-STDP：奖励期线索与输出同时活跃 → 增强） ----
  if (condOn) {
    const cueSpk = 0; // 线索脉冲已在上面计入 cueMotor 统计，这里用平滑率近似
    cueTrace = 0.95 * cueTrace + 0.05 * (phase === 'cue' ? 1 : 0);
    motTrace = 0.95 * motTrace + 0.05 * (binSpikes.m > 0 ? 1 : 0);
    if (phase === 'reward') {
      wCue += COND_LR * (cueTrace * motTrace - COND_DECAY * wCue);
      wCue = Math.min(1.5, Math.max(0, wCue));
    }
  }
  brainMs += BIN;

  // ---- 可塑性更新（相关性驱动） ----
  if (train) {
    const sH = binSpikes.s / sz / 0.1;      // 感觉组 Hz
    const cH = binSpikes.c / cz / 0.1;      // 中枢组 Hz
    const mH = binSpikes.m / mz / 0.1;      // 运动输出 Hz
    mn9Rate = 0.8 * mn9Rate + 0.2 * mH;
    mn9Hist.push(+mn9Rate.toFixed(1)); if (mn9Hist.length > 60) mn9Hist.shift();
    // Hebbian：前级越活跃 & 后级越活跃 → 通路变强
    rateSC = 0.9 * rateSC + 0.1 * (sH * cH);
    rateCM = 0.9 * rateCM + 0.1 * (cH * mH);
    gainSC += LR * (rateSC / 1e4 - DECAY * gainSC);
    gainCM += LR * (rateCM / 1e4 - DECAY * gainCM);
    gainSC = Math.min(3, Math.max(0.2, gainSC));
    gainCM = Math.min(3, Math.max(0.2, gainCM));
  }

  self.postMessage({
    type: 'frame', s: sNorm, c: cNorm, m: mNorm,
    spikes: binSpikes.s + binSpikes.c + binSpikes.m,
    hz: { s: binSpikes.s / sz, c: binSpikes.c / cz, m: binSpikes.m / mz },
    speed: (BIN / real).toFixed(2),       // 每真实秒推进多少"脑秒"
    brainSec: (tBrain / 1000).toFixed(1),
    hz2: { s: +sHz.toFixed(1), c: +cHz.toFixed(2), m: +mHz.toFixed(1) },
    cond: { on: condOn, round: round, phase: phase, wCue: +wCue.toFixed(3),
            cueMotor: +cueMotorRate.toFixed(1), hist: learnHist.slice(-40) },
    train: train, gainSC: +gainSC.toFixed(3), gainCM: +gainCM.toFixed(3),
    mn9: +mn9Rate.toFixed(1), hist: mn9Hist.slice(-40)
  });
  binSpikes = { s: 0, c: 0, m: 0 };
}

self.onmessage = (e) => {
  if (e.data === 'start') { running = true; if (!v) init().catch(err => self.postMessage({ type: 'error', text: String(err) })); else loop(); }
  if (e.data === 'stop') { running = false; }
  if (e.data === 'train-on') { train = true; }
  if (e.data === 'train-off') { train = false; }
  if (e.data === 'feed') { feedUntil = brainMs + 5000; }   // 投喂：5 秒高频糖刺激
  if (e.data === 'cond-on') { condOn = true; phase = 'idle'; phaseT = 0; round = 0; learnHist = []; wCue = 0; }
  if (e.data === 'cond-off') { condOn = false; phase = 'idle'; }
  if (e.data === 'cond-reset') { round = 0; learnHist = []; wCue = 0; cueMotorRate = 0; phase = 'idle'; }
  if (e.data === 'train-reset') { gainSC = 1.0; gainCM = 1.0; rateSC = 0; rateCM = 0; mn9Rate = 0; mn9Hist = []; }
};
