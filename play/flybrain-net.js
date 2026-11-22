/* ============================================================
   flybrain-net.js — FlyEM 雄性 CNS v1.0 实测连接组降维 LIF 脑
   25 功能群 / 48 神经元 / 145 条边（119 条实测 = 82%）
   LIF: τm=20ms τsyn=5ms 不应期 2ms 适应 0.18
   w = wSyn(0.275)·gain(0.42)·K(5)·实测强度·极性
   用法: newFlyBrain() → fbStep(br, dt) → fbRate(br,'MN_walk')
   ============================================================ */
var CTYPE = [
  ['ORN_food', 'Sensory', 1, 5, '食物气味感受 · 实测 2,115 个 / ACh'],
  ['ORN_ferm', 'Sensory', 1, 1, '发酵气味感受 · 实测 316 个 / ACh'],
  ['ORN_alarm', 'Sensory', 1, 1, '信息素感受 · 实测 204 个 / ACh'],
  ['GRN_sugar', 'Sensory', 1, 1, '糖味觉感受 · 实测 100 个 / ACh'],
  ['mechano', 'Sensory', 1, 3, '机械/听觉(JO) · 实测 672 个 / ACh'],
  ['visual', 'Sensory', -1, 5, '光感受器 · 实测 4,114 个 / 组胺'],
  ['Hugin', 'Drives', -1, 1, '饥饿驱动(Hugin) · 实测 4 个 / 谷氨酸+肽'],
  ['NPF', 'Drives', 1, 1, '取食促进(NPF) · 实测 2 个 / 肽'],
  ['FB_energy', 'Drives', -1, 2, '饱足(扇形体) · 实测 601 个 / GABA'],
  ['LN_al', 'Central', -1, 1, '触角叶局部 · 实测 28 个 / GABA'],
  ['PN', 'Central', 1, 3, '投射神经元 · 实测 808 个 / ACh'],
  ['LHON', 'Central', 1, 5, '侧角输出 · 实测 1,975 个 / ACh'],
  ['KC', 'Central', 1, 5, '蘑菇体Kenyon · 实测 4,064 个 / ACh'],
  ['APL', 'Central', -1, 1, '蘑菇体反馈 · 实测 2 个 / GABA'],
  ['MBON_app', 'Central', 1, 1, 'MBON03 食欲性输出 · 实测 2 个 / 谷氨酸(功能极性按食欲性)'],
  ['MBON_av', 'Central', -1, 1, 'MBON11 厌恶性输出 · 实测 2 个 / 谷氨酸'],
  ['PPL1', 'Central', 0, 1, '惩罚多巴胺 · 实测 16 个 / 多巴胺'],
  ['PAM', 'Central', 0, 1, '奖赏多巴胺 · 实测 316 个 / 多巴胺'],
  ['ring_EB', 'Central', 1, 1, '椭球体ring · 实测 278 个 / ACh'],
  ['PFN', 'Central', 1, 2, '桥神经元 · 实测 456 个 / ACh'],
  ['DN_escape', 'Central', 1, 1, '巨纤维逃逸 · 实测 6 个 / ACh'],
  ['DN_walk', 'Central', 1, 1, '下行行进 · 实测 10 个 / ACh'],
  ['MN_feed', 'Motor', 1, 1, 'MN9 喙伸展 · 实测 2 个 / ACh'],
  ['MN_walk', 'Motor', 1, 2, '腿部运动 · 实测 485 个 / ACh'],
  ['MN_oviposit', 'Motor', 1, 1, '腹部运动 · 实测 214 个 / ACh'],
];;
var CONNECTIONS = [
  ['APL', 'APL', 0.171, null, 'MCNS*'],
  ['APL', 'KC', 2.759, null, 'MCNS'],
  ['APL', 'LHON', 0.040, null, 'MCNS'],
  ['APL', 'MBON_app', 4.085, null, 'MCNS'],
  ['APL', 'MBON_av', 4.780, null, 'MCNS'],
  ['APL', 'PAM', 0.172, null, 'MCNS'],
  ['APL', 'PN', 0.737, null, 'MCNS'],
  ['APL', 'PPL1', 2.555, null, 'MCNS'],
  ['DN_escape', 'DN_escape', 0.021, null, 'MCNS*'],
  ['DN_escape', 'DN_walk', 0.132, null, 'MCNS'],
  ['DN_escape', 'MN_oviposit', 0.083, null, 'MCNS'],
  ['DN_escape', 'MN_walk', 0.526, null, 'MCNS'],
  ['DN_walk', 'DN_escape', 1.057, null, 'MCNS'],
  ['DN_walk', 'MN_oviposit', 0.014, null, 'MCNS'],
  ['DN_walk', 'MN_walk', 0.111, null, 'MCNS'],
  ['FB_energy', 'FB_energy', 0.750, null, 'MCNS*'],
  ['FB_energy', 'LHON', 0.050, null, 'MCNS'],
  ['FB_energy', 'LN_al', 2.526, null, 'MCNS'],
  ['FB_energy', 'PAM', 0.408, null, 'MCNS'],
  ['FB_energy', 'PFN', 3.197, null, 'MCNS'],
  ['FB_energy', 'PPL1', 3.382, null, 'MCNS'],
  ['FB_energy', 'ring_EB', 0.011, null, 'MCNS'],
  ['GRN_sugar', 'GRN_sugar', 0.307, null, 'MCNS*'],
  ['GRN_sugar', 'PN', 0.006, null, 'MCNS'],
  ['KC', 'APL', 5.000, null, 'MCNS'],
  ['KC', 'FB_energy', 0.002, null, 'MCNS'],
  ['KC', 'KC', 0.429, null, 'MCNS*'],
  ['KC', 'LHON', 0.135, null, 'MCNS'],
  ['KC', 'MBON_app', 5.000, 'app', 'MCNS'],
  ['KC', 'MBON_av', 5.000, 'av', 'MCNS'],
  ['KC', 'PAM', 3.041, null, 'MCNS'],
  ['KC', 'PN', 0.008, null, 'MCNS'],
  ['KC', 'PPL1', 5.000, null, 'MCNS'],
  ['LHON', 'APL', 5.000, null, 'MCNS'],
  ['LHON', 'DN_escape', 2.997, null, 'MCNS'],
  ['LHON', 'DN_walk', 0.365, null, 'MCNS'],
  ['LHON', 'FB_energy', 1.622, null, 'MCNS'],
  ['LHON', 'KC', 0.463, null, 'MCNS'],
  ['LHON', 'LHON', 0.675, null, 'MCNS*'],
  ['LHON', 'LN_al', 1.236, null, 'MCNS'],
  ['LHON', 'MBON_app', 1.791, null, 'MCNS'],
  ['LHON', 'PAM', 0.903, null, 'MCNS'],
  ['LHON', 'PN', 3.166, null, 'MCNS'],
  ['LHON', 'PPL1', 4.466, null, 'MCNS'],
  ['LHON', 'ring_EB', 0.414, null, 'MCNS'],
  ['LN_al', 'FB_energy', 0.792, null, 'MCNS'],
  ['LN_al', 'LHON', 0.003, null, 'MCNS'],
  ['LN_al', 'LN_al', 0.643, null, 'MCNS*'],
  ['LN_al', 'MN_oviposit', 0.141, null, 'MCNS'],
  ['LN_al', 'PFN', 2.939, null, 'MCNS'],
  ['LN_al', 'PN', 1.329, null, 'MCNS'],
  ['MBON_app', 'APL', 1.865, null, 'MCNS'],
  ['MBON_app', 'FB_energy', 0.006, null, 'MCNS'],
  ['MBON_app', 'KC', 0.001, null, 'MCNS'],
  ['MBON_app', 'LHON', 0.141, null, 'MCNS'],
  ['MBON_app', 'PAM', 0.094, null, 'MCNS'],
  ['MBON_av', 'APL', 5.000, null, 'MCNS'],
  ['MBON_av', 'FB_energy', 0.038, null, 'MCNS'],
  ['MBON_av', 'KC', 0.002, null, 'MCNS'],
  ['MBON_av', 'LHON', 0.033, null, 'MCNS'],
  ['MBON_av', 'MBON_app', 3.348, null, 'MCNS'],
  ['MBON_av', 'MBON_av', 0.466, null, 'MCNS*'],
  ['MBON_av', 'PAM', 0.174, null, 'MCNS'],
  ['MBON_av', 'PPL1', 2.456, null, 'MCNS'],
  ['MN_feed', 'MN_feed', 0.067, null, 'MCNS*'],
  ['MN_oviposit', 'MN_oviposit', 0.215, null, 'MCNS*'],
  ['MN_walk', 'MN_walk', 0.077, null, 'MCNS*'],
  ['NPF', 'LHON', 0.002, null, 'MCNS'],
  ['ORN_alarm', 'ORN_alarm', 0.150, null, 'MCNS*'],
  ['ORN_alarm', 'PN', 2.591, null, 'MCNS'],
  ['ORN_ferm', 'LN_al', 0.705, null, 'MCNS'],
  ['ORN_ferm', 'ORN_ferm', 0.276, null, 'MCNS*'],
  ['ORN_ferm', 'ORN_food', 0.001, null, 'MCNS'],
  ['ORN_ferm', 'PN', 3.092, null, 'MCNS'],
  ['ORN_food', 'LHON', 0.001, null, 'MCNS'],
  ['ORN_food', 'LN_al', 4.051, null, 'MCNS'],
  ['ORN_food', 'ORN_alarm', 0.004, null, 'MCNS'],
  ['ORN_food', 'ORN_ferm', 0.024, null, 'MCNS'],
  ['ORN_food', 'ORN_food', 0.345, null, 'MCNS*'],
  ['ORN_food', 'PN', 5.000, null, 'MCNS'],
  ['PAM', 'APL', 5.000, null, 'MCNS'],
  ['PAM', 'FB_energy', 0.005, null, 'MCNS'],
  ['PAM', 'KC', 0.559, null, 'MCNS'],
  ['PAM', 'LHON', 0.001, null, 'MCNS'],
  ['PAM', 'MBON_app', 5.000, null, 'MCNS'],
  ['PAM', 'MBON_av', 2.808, null, 'MCNS'],
  ['PAM', 'PAM', 0.062, null, 'MCNS*'],
  ['PAM', 'PPL1', 1.186, null, 'MCNS'],
  ['PFN', 'FB_energy', 1.949, null, 'MCNS'],
  ['PFN', 'LN_al', 5.000, null, 'MCNS'],
  ['PFN', 'PFN', 0.545, null, 'MCNS*'],
  ['PN', 'APL', 5.000, null, 'MCNS'],
  ['PN', 'FB_energy', 0.544, null, 'MCNS'],
  ['PN', 'KC', 3.632, null, 'MCNS'],
  ['PN', 'LHON', 4.536, null, 'MCNS'],
  ['PN', 'LN_al', 3.559, null, 'MCNS'],
  ['PN', 'MBON_app', 0.880, null, 'MCNS'],
  ['PN', 'NPF', 0.783, null, 'MCNS'],
  ['PN', 'ORN_alarm', 0.019, null, 'MCNS'],
  ['PN', 'ORN_ferm', 0.237, null, 'MCNS'],
  ['PN', 'ORN_food', 0.162, null, 'MCNS'],
  ['PN', 'PAM', 0.128, null, 'MCNS'],
  ['PN', 'PN', 0.650, null, 'MCNS*'],
  ['PN', 'PPL1', 2.472, null, 'MCNS'],
  ['PN', 'ring_EB', 0.409, null, 'MCNS'],
  ['PPL1', 'APL', 5.000, null, 'MCNS'],
  ['PPL1', 'FB_energy', 0.282, null, 'MCNS'],
  ['PPL1', 'KC', 0.672, null, 'MCNS'],
  ['PPL1', 'LHON', 0.083, null, 'MCNS'],
  ['PPL1', 'MBON_av', 5.000, null, 'MCNS'],
  ['PPL1', 'PAM', 0.152, null, 'MCNS'],
  ['PPL1', 'PN', 0.001, null, 'MCNS'],
  ['PPL1', 'PPL1', 0.433, null, 'MCNS*'],
  ['mechano', 'DN_escape', 4.837, null, 'MCNS'],
  ['mechano', 'PN', 0.125, null, 'MCNS'],
  ['mechano', 'mechano', 0.066, null, 'MCNS*'],
  ['ring_EB', 'FB_energy', 0.006, null, 'MCNS'],
  ['ring_EB', 'ring_EB', 0.750, null, 'MCNS*'],
  ['visual', 'visual', 0.189, null, 'MCNS*'],
  ['Hugin', 'PN', 30.00, null, 'inf'],
  ['Hugin', 'MN_walk', 40.00, null, 'inf'],
  ['Hugin', 'MBON_av', 30.00, null, 'inf'],
  ['NPF', 'MN_feed', 25.00, null, 'inf'],
  ['NPF', 'MN_oviposit', 40.00, null, 'inf'],
  ['GRN_sugar', 'MN_feed', 45.00, null, 'inf'],
  ['GRN_sugar', 'NPF', 40.00, null, 'inf'],
  ['GRN_sugar', 'PAM', 30.00, null, 'inf'],
  ['FB_energy', 'MN_feed', 40.00, null, 'inf'],
  ['FB_energy', 'Hugin', 35.00, null, 'inf'],
  ['FB_energy', 'MN_oviposit', 30.00, null, 'inf'],
  ['visual', 'DN_escape', 45.00, null, 'inf'],
  ['visual', 'ring_EB', 30.00, null, 'inf'],
  ['ORN_alarm', 'DN_escape', 40.00, null, 'inf'],
  ['ORN_alarm', 'PPL1', 40.00, null, 'inf'],
  ['ORN_alarm', 'MBON_av', 60.00, null, 'inf'],
  ['ring_EB', 'PFN', 40.00, null, 'inf'],
  ['PFN', 'DN_walk', 35.00, null, 'inf'],
  ['PFN', 'MN_walk', 35.00, null, 'inf'],
  ['LHON', 'MN_feed', 8.00, null, 'inf'],
  ['MBON_app', 'DN_walk', 35.00, null, 'inf'],
  ['MBON_av', 'DN_walk', 35.00, null, 'inf'],
  ['MBON_av', 'MN_feed', 300.00, null, 'inf'],
  ['MBON_av', 'NPF', 150.00, null, 'inf'],
  ['mechano', 'MN_walk', 30.00, null, 'inf'],
  ['LHON', 'PFN', 30.00, null, 'inf'],
];

var NET = (function(){
 try{
  var n=0, name={}, start={}, cnt={}, col=[], sign=[], nm=[];
  CTYPE.forEach(function(c){
    var t=c[0]; name[t]=n; start[t]=n; cnt[t]=c[3];
    for(var k=0;k<c[3];k++){ col.push(c[1]); sign.push(c[2]); nm.push(t); }
    n+=c[3];
  });
  var BW=0.275, GAIN=0.42, K=5;
  var srcL=[], dstL=[], w0L=[], plL=[], meas=0;
  CONNECTIONS.forEach(function(c){
    var a=name[c[0]], b=name[c[1]];
    if(a===undefined||b===undefined) return;
    srcL.push(a); dstL.push(b);
    w0L.push(BW*GAIN*K*c[2]*sign[a]);
    plL.push(c[3]==='av'?1:(c[3]==='app'?2:0));
    if(String(c[4]).indexOf('MCNS')===0) meas++;
  });
  var deg=new Array(n).fill(0);
  srcL.forEach(function(s){ deg[s]++; });
  var off=new Array(n+1); off[0]=0;
  for(var i=0;i<n;i++) off[i+1]=off[i]+deg[i];
  var fill=off.slice();
  var oDst=new Array(srcL.length), oW=new Array(srcL.length), oPl=new Array(srcL.length);
  for(var e=0;e<srcL.length;e++){
    var pos=fill[srcL[e]]++;
    oDst[pos]=dstL[e]; oW[pos]=w0L[e]; oPl[pos]=plL[e];
  }
  return {n:n,name:name,start:start,cnt:cnt,col:col,sign:sign,nm:nm,
          E:srcL.length,off:off,oDst:oDst,oW:oW,oPl:oPl,meas:meas};
 }catch(err){ window.__netErr=(err&&err.message)||String(err); throw err; }
})();

var CFG_B={tauM:0.020,tauSyn:0.005,tauR:0.20,tauAdapt:0.10,
           vThr:1.0,vReset:0,vRefrac:0.002,adapt:0.18,
           noise:0.028,lr:0.15,extinct:0.5,daThresh:3.0,wMax:3.2,plasticTau:0.35};

function newFlyBrain(){
  var n=NET.n;
  return {n:n,
    v:new Float32Array(n), I:new Float32Array(n), ext:new Float32Array(n),
    r:new Float32Array(n), refr:new Float32Array(n), a:new Float32Array(n),
    w:NET.oW.slice(0), w0:NET.oW.slice(0),
    kcTrace:new Float32Array(NET.cnt['KC']),
    kcBase:NET.start['KC'], kcN:NET.cnt['KC'], spikes:0};
}
function fbRate(br,typeName){
  var st=NET.start[typeName], num=NET.cnt[typeName], s=0;
  for(var i=0;i<num;i++) s+=br.r[st+i];
  return s/num;
}
function fbStep(br,dt){
  var B=CFG_B, n=br.n, v=br.v, I=br.I, ext=br.ext, r=br.r, refr=br.refr, ad=br.a;
  var decI=Math.exp(-dt/B.tauSyn), decR=Math.exp(-dt/B.tauR), decA=Math.exp(-dt/B.tauAdapt);
  for(var i=0;i<n;i++){ I[i]*=decI; r[i]*=decR; ad[i]*=decA; }
  var kicks=B.noise*n*dt*3, k=Math.floor(kicks)+(Math.random()<(kicks%1)?1:0);
  while(k-->0) I[(Math.random()*n)|0]+=1.25;
  var dtM=dt/B.tauM, rGain=1/B.tauR, cnt=0;
  for(var j=0;j<n;j++){
    if(refr[j]>0){ refr[j]-=dt; v[j]=0; continue; }
    var vj=v[j]+dtM*(-v[j]+I[j]+ext[j]-ad[j]);
    if(vj>=B.vThr){
      v[j]=B.vReset; refr[j]=B.vRefrac; ad[j]+=B.adapt; cnt++;
      r[j]+=rGain;
      if(j>=br.kcBase && j<br.kcBase+br.kcN) br.kcTrace[j-br.kcBase]+=1;
      for(var e=NET.off[j]; e<NET.off[j+1]; e++) I[NET.oDst[e]]+=br.w[e];
    } else v[j]=vj;
  }
  br.spikes=cnt;
  var decK=Math.exp(-dt/B.plasticTau);
  for(var q=0;q<br.kcN;q++) br.kcTrace[q]*=decK;
  var daP=fbRate(br,'PPL1'), daR=fbRate(br,'PAM');
  var dopP=Math.max(0,Math.min(1.5,(daP-B.daThresh)/25));
  var dopR=Math.max(0,Math.min(1.5,(daR-B.daThresh)/25));
  if(dopP>0||dopR>0){
    var kP=B.lr*dopP*dt, kR=B.lr*dopR*dt;
    for(var e2=0;e2<NET.E;e2++){
      var plv=NET.oPl[e2]; if(!plv) continue;
      var tr=Math.min(1.2, br.kcTrace[e2 % br.kcN]/6);
      if(tr<0.03) continue;
      var w00=br.w0[e2];
      if(plv===1 && kP>0) br.w[e2]=Math.max(0,Math.min(w00*B.wMax, br.w[e2]+kP*tr*w00));
      else if(plv===2 && kR>0) br.w[e2]=Math.max(0,Math.min(w00*B.wMax, br.w[e2]+kR*tr*w00));
    }
  } else {
    var kE=B.lr*B.extinct*dt;
    for(var e3=0;e3<NET.E;e3++){
      if(NET.oPl[e3]!==1) continue;
      var tr2=Math.min(1.2, br.kcTrace[e3 % br.kcN]/6);
      if(tr2<0.03) continue;
      var w01=br.w0[e3];
      br.w[e3]=Math.max(w01*0.35, br.w[e3]-kE*tr2*w01);
    }
  }
  for(var e4=0;e4<NET.E;e4++){
    if(!NET.oPl[e4]) continue;
    br.w[e4]+=(br.w0[e4]-br.w[e4])*dt*0.03;
  }
}

