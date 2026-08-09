/* SongScope alignment worker — D1 Diagnostic
 * Diagnostic-only music alignment. Does not modify playback offset automatically.
 * Input feature: STFT pitch-class chroma from mixed karaoke audio.
 * Mapping convention used by matcher: reference(A) time = target(B) time + offsetSec.
 */
'use strict';

const FEATURE_VERSION = 'stft-chroma-log-l2-smooth-v1';
const MATCH_VERSION = 'global-offset-coarse-refine-v1';
const CFG_DEFAULT = {
  analysisSampleRate: 11025,
  fftSize: 4096,
  hopSec: 0.20,
  minHz: 55,
  maxHz: 5000,
  smoothFrames: 5,
  coarseStride: 5,
  refineRadiusSec: 1.2,
  driftRadiusSec: 2.0,
  blockSec: 5.0
};

function FFT(n) {
  this.n=n; this.levels=Math.log2(n)|0;
  if ((1<<this.levels)!==n) throw new Error('FFT size must be power of two');
  this.cos=new Float32Array(n/2); this.sin=new Float32Array(n/2);
  for(let i=0;i<n/2;i++){ this.cos[i]=Math.cos(2*Math.PI*i/n); this.sin[i]=Math.sin(2*Math.PI*i/n); }
  this.rev=new Uint32Array(n);
  for(let i=0;i<n;i++){ let x=i,r=0; for(let j=0;j<this.levels;j++){ r=(r<<1)|(x&1); x>>=1; } this.rev[i]=r; }
}
FFT.prototype.forward=function(re,im){
  const n=this.n, rev=this.rev;
  for(let i=0;i<n;i++){ const j=rev[i]; if(j>i){ let t=re[i];re[i]=re[j];re[j]=t;t=im[i];im[i]=im[j];im[j]=t; } }
  for(let size=2;size<=n;size<<=1){ const half=size>>1, step=n/size;
    for(let i=0;i<n;i+=size){ for(let j=i,k=0;j<i+half;j++,k+=step){ const l=j+half;
      const tre=re[l]*this.cos[k]+im[l]*this.sin[k];
      const tim=-re[l]*this.sin[k]+im[l]*this.cos[k];
      re[l]=re[j]-tre; im[l]=im[j]-tim; re[j]+=tre; im[j]+=tim;
    }}
  }
};

function resample(input, srcRate, dstRate){
  if(Math.abs(srcRate-dstRate)<1) return {data:input, rate:srcRate};
  const ratio=srcRate/dstRate, outLen=Math.floor(input.length/ratio), out=new Float32Array(outLen);
  if(ratio>1){
    const w=Math.max(1,Math.round(ratio));
    for(let i=0;i<outLen;i++){ const c=i*ratio,s=Math.max(0,(c-w/2)|0),e=Math.min(input.length,s+w); let sum=0; for(let j=s;j<e;j++)sum+=input[j]; out[i]=sum/Math.max(1,e-s); }
  } else {
    for(let i=0;i<outLen;i++){ const c=i*ratio,i0=c|0,f=c-i0; out[i]=input[i0]*(1-f)+(input[Math.min(input.length-1,i0+1)]||0)*f; }
  }
  return {data:out, rate:dstRate};
}
function l2norm12(arr, off){ let s=0; for(let p=0;p<12;p++){const v=arr[off+p];s+=v*v;} return Math.sqrt(s); }
function normalize12(arr, off){ const n=l2norm12(arr,off); if(!(n>1e-12)) return false; for(let p=0;p<12;p++)arr[off+p]/=n; return true; }
function percentile(values,p){ if(!values.length)return null; const a=values.slice().sort((x,y)=>x-y); const x=(a.length-1)*p,lo=Math.floor(x),hi=Math.ceil(x); return lo===hi?a[lo]:a[lo]*(hi-x)+a[hi]*(x-lo); }

function extractFeature(pcmIn, srcRate, cfgIn){
  const cfg=Object.assign({},CFG_DEFAULT,cfgIn||{});
  const rs=resample(pcmIn,srcRate,cfg.analysisSampleRate); const pcm=rs.data,sr=rs.rate;
  const N=cfg.fftSize, hop=Math.max(1,Math.round(cfg.hopSec*sr));
  if(pcm.length<N) throw new Error('音声が短すぎてalignment特徴を作れません');
  const frames=1+Math.floor((pcm.length-N)/hop);
  const chroma=new Float32Array(frames*12), rmsDb=new Float32Array(frames), valid=new Uint8Array(frames);
  const hann=new Float32Array(N); for(let i=0;i<N;i++)hann[i]=0.5-0.5*Math.cos(2*Math.PI*i/(N-1));
  const re=new Float32Array(N), im=new Float32Array(N), fft=new FFT(N);
  const k0=Math.max(1,Math.ceil(cfg.minHz*N/sr)), k1=Math.min(N/2-1,Math.floor(cfg.maxHz*N/sr));
  for(let fi=0;fi<frames;fi++){
    const st=fi*hop; let sumsq=0; re.fill(0);im.fill(0);
    for(let i=0;i<N;i++){ const x=pcm[st+i]||0; sumsq+=x*x; re[i]=x*hann[i]; }
    const rms=Math.sqrt(sumsq/N); rmsDb[fi]=rms>1e-12?20*Math.log10(rms):-120;
    fft.forward(re,im); const off=fi*12;
    for(let k=k0;k<=k1;k++){
      const f=k*sr/N; const midi=69+12*Math.log2(f/440); const semi=Math.round(midi); let pc=((semi%12)+12)%12;
      const delta=midi-semi; const weight=Math.exp(-0.5*(delta/0.35)*(delta/0.35));
      const mag=Math.sqrt(re[k]*re[k]+im[k]*im[k])/N;
      const compressed=Math.log1p(200*mag)*weight;
      chroma[off+pc]+=compressed;
    }
    if(rmsDb[fi]>-78 && normalize12(chroma,off)) valid[fi]=1;
    if(fi%40===0) self.postMessage({type:'progress',stage:'extract',pct:Math.round(5+70*fi/Math.max(1,frames-1))});
  }
  // Temporal smoothing over local frames; preserve invalid/silent frames as zero.
  const sm=new Float32Array(chroma.length), rad=Math.max(0,Math.floor(cfg.smoothFrames/2));
  for(let fi=0;fi<frames;fi++){
    const off=fi*12; let cnt=0;
    for(let j=Math.max(0,fi-rad);j<=Math.min(frames-1,fi+rad);j++){
      if(!valid[j])continue; cnt++; const jo=j*12; for(let p=0;p<12;p++)sm[off+p]+=chroma[jo+p];
    }
    if(cnt){ for(let p=0;p<12;p++)sm[off+p]/=cnt; normalize12(sm,off); } else valid[fi]=0;
  }
  const durationSec=pcm.length/sr;
  return { featureAlgorithmVersion:FEATURE_VERSION, config:cfg, sampleRate:sr, fftSize:N, hopSec:hop/sr, frameCount:frames, durationSec, chroma:sm, rmsDb, valid };
}

function frameDot(A,ai,B,bi,rot){
  if(!A.valid[ai]||!B.valid[bi])return NaN;
  const ao=ai*12, bo=bi*12; let s=0;
  // rot is semitones applied to target B before comparison: rotatedB[p] = B[p-rot].
  for(let p=0;p<12;p++){ const src=((p-rot)%12+12)%12; s+=A.chroma[ao+p]*B.chroma[bo+src]; }
  return s;
}
function coarseFeature(F,stride){
  const n=Math.ceil(F.frameCount/stride), ch=new Float32Array(n*12), va=new Uint8Array(n);
  for(let i=0;i<n;i++){ const s=i*stride,e=Math.min(F.frameCount,s+stride),off=i*12;let c=0;
    for(let j=s;j<e;j++){ if(!F.valid[j])continue;c++;const jo=j*12;for(let p=0;p<12;p++)ch[off+p]+=F.chroma[jo+p]; }
    if(c){for(let p=0;p<12;p++)ch[off+p]/=c; if(normalize12(ch,off))va[i]=1;}
  }
  return {frameCount:n,chroma:ch,valid:va,hopSec:F.hopSec*stride,durationSec:F.durationSec};
}
function signedRotation(r){ r=((r%12)+12)%12; return r>6?r-12:r; }
function evalOffset(A,B,d,rot,blockSec){
  const b0=Math.max(0,-d), b1=Math.min(B.frameCount,A.frameCount-d), overlap=Math.max(0,b1-b0);
  if(!overlap)return null; let sum=0,n=0; const blockFrames=Math.max(1,Math.round(blockSec/A.hopSec)); let blockSum=0,blockN=0,blockPos=0; const blocks=[];
  for(let bi=b0;bi<b1;bi++){
    const ai=bi+d, v=frameDot(A,ai,B,bi,rot); blockPos++;
    if(Number.isFinite(v)){sum+=v;n++;blockSum+=v;blockN++;}
    if(blockPos>=blockFrames || bi===b1-1){ if(blockN)blocks.push(blockSum/blockN); blockSum=0;blockN=0;blockPos=0; }
  }
  if(!n)return null;
  const overlapSec=overlap*A.hopSec, targetCoverage=overlap/Math.max(1,B.frameCount), refCoverage=overlap/Math.max(1,A.frameCount), shorterCoverage=overlap/Math.max(1,Math.min(A.frameCount,B.frameCount));
  const mean=sum/n, blockMedian=percentile(blocks,0.5), blockP10=percentile(blocks,0.1);
  const rankingScore=mean*(0.65+0.35*Math.min(1,shorterCoverage));
  return {d,offsetSec:d*A.hopSec,rotation:signedRotation(rot),meanSimilarity:mean,rankingScore,overlapSec,targetCoverageRatio:targetCoverage,referenceCoverageRatio:refCoverage,shorterCoverageRatio:shorterCoverage,supportFrameCount:n,overlapFrameCount:overlap,blockSimilarityMedian:blockMedian,blockSimilarityP10:blockP10,bStart:b0,bEnd:b1};
}
function minOverlapSecFor(A,B){ return Math.min(30,Math.max(8,Math.min(A.durationSec,B.durationSec)*0.25)); }
function topUnique(items,k){
  const s=items.filter(Boolean).sort((a,b)=>b.rankingScore-a.rankingScore), out=[];
  for(const c of s){
    if(out.some(x=>x.rotation===c.rotation && Math.abs(x.offsetSec-c.offsetSec)<1.5))continue;
    out.push(c); if(out.length>=k)break;
  }
  return out;
}
function matchDirection(A0,B0,cfgIn,progressBase=0,progressSpan=100){
  const cfg=Object.assign({},CFG_DEFAULT,cfgIn||{}), stride=cfg.coarseStride;
  const A=coarseFeature(A0,stride), B=coarseFeature(B0,stride), minSec=minOverlapSecFor(A0,B0), minCoarse=Math.max(1,Math.ceil(minSec/A.hopSec));
  const coarse=[]; let total=0,done=0;
  for(let r=0;r<12;r++){ const minD=-(B.frameCount-minCoarse),maxD=A.frameCount-minCoarse; total+=Math.max(0,maxD-minD+1); }
  for(let r=0;r<12;r++){
    const minD=-(B.frameCount-minCoarse),maxD=A.frameCount-minCoarse;
    for(let d=minD;d<=maxD;d++){
      const m=evalOffset(A,B,d,r,cfg.blockSec); if(m && m.overlapSec>=minSec)coarse.push(m); done++;
    }
    self.postMessage({type:'progress',stage:'match',pct:Math.round(progressBase+progressSpan*0.45*done/Math.max(1,total))});
  }
  const coarseTop=topUnique(coarse,30), refined=[]; const rad=Math.max(1,Math.round(cfg.refineRadiusSec/A0.hopSec));
  for(let ci=0;ci<coarseTop.length;ci++){
    const c=coarseTop[ci], center=Math.round(c.offsetSec/A0.hopSec), r=((c.rotation%12)+12)%12;
    for(let d=center-rad;d<=center+rad;d++){
      const m=evalOffset(A0,B0,d,r,cfg.blockSec); if(m && m.overlapSec>=minSec)refined.push(m);
    }
    self.postMessage({type:'progress',stage:'match',pct:Math.round(progressBase+progressSpan*(0.45+0.45*(ci+1)/Math.max(1,coarseTop.length)))});
  }
  const top=topUnique(refined,5);
  return {top,minOverlapSec:minSec};
}
function driftProbe(A,B,best,cfgIn){
  if(!best)return {segments:[]}; const cfg=Object.assign({},CFG_DEFAULT,cfgIn||{}), rot=((best.rotation%12)+12)%12;
  const base=Math.round(best.offsetSec/A.hopSec), rad=Math.max(1,Math.round(cfg.driftRadiusSec/A.hopSec));
  const b0=Math.max(0,-base), b1=Math.min(B.frameCount,A.frameCount-base), len=b1-b0; if(len<9)return {segments:[]};
  const segs=[]; const labels=['early','middle','late'];
  for(let s=0;s<3;s++){
    const sb0=Math.floor(b0+len*s/3), sb1=Math.floor(b0+len*(s+1)/3); let bestLocal=null;
    for(let d=base-rad;d<=base+rad;d++){
      let sum=0,n=0;
      for(let bi=sb0;bi<sb1;bi++){ const ai=bi+d; if(ai<0||ai>=A.frameCount)continue; const v=frameDot(A,ai,B,bi,rot); if(Number.isFinite(v)){sum+=v;n++;} }
      if(!n)continue; const mean=sum/n; if(!bestLocal||mean>bestLocal.meanSimilarity)bestLocal={label:labels[s],offsetSec:d*A.hopSec,meanSimilarity:mean,supportFrameCount:n};
    }
    if(bestLocal)segs.push(bestLocal);
  }
  const offs=segs.map(x=>x.offsetSec); return {segments:segs,offsetRangeSec:offs.length?Math.max(...offs)-Math.min(...offs):null};
}
function diag(A,B,cfg){
  const fwd=matchDirection(A,B,cfg,5,42), best=fwd.top[0]||null, drift=driftProbe(A,B,best,cfg);
  const rev=matchDirection(B,A,cfg,52,42), bestRev=rev.top[0]||null;
  const inverseResidualSec=(best&&bestRev)?best.offsetSec+bestRev.offsetSec:null;
  self.postMessage({type:'progress',stage:'match',pct:98});
  return {
    matchingAlgorithmVersion:MATCH_VERSION,
    featureAlgorithmVersion:FEATURE_VERSION,
    mappingConvention:'reference_time_sec = target_time_sec + offset_sec',
    decision:{status:'diagnostic_only'},
    candidates:fwd.top.map((x,i)=>({rank:i+1,offsetSec:+x.offsetSec.toFixed(3),chromaRotationSemitones:x.rotation,meanSimilarity:+x.meanSimilarity.toFixed(6),rankingScore:+x.rankingScore.toFixed(6),overlapSec:+x.overlapSec.toFixed(3),targetCoverageRatio:+x.targetCoverageRatio.toFixed(6),referenceCoverageRatio:+x.referenceCoverageRatio.toFixed(6),shorterCoverageRatio:+x.shorterCoverageRatio.toFixed(6),supportFrameCount:x.supportFrameCount,overlapFrameCount:x.overlapFrameCount,blockSimilarityMedian:x.blockSimilarityMedian===null?null:+x.blockSimilarityMedian.toFixed(6),blockSimilarityP10:x.blockSimilarityP10===null?null:+x.blockSimilarityP10.toFixed(6)})),
    reverseCheck: bestRev?{bestOffsetSec:+bestRev.offsetSec.toFixed(3),chromaRotationSemitones:bestRev.rotation,meanSimilarity:+bestRev.meanSimilarity.toFixed(6),inverseOffsetResidualSec:inverseResidualSec===null?null:+inverseResidualSec.toFixed(3)}:null,
    driftProbe:{segments:drift.segments.map(x=>({label:x.label,offsetSec:+x.offsetSec.toFixed(3),meanSimilarity:+x.meanSimilarity.toFixed(6),supportFrameCount:x.supportFrameCount})),offsetRangeSec:drift.offsetRangeSec===null?null:+drift.offsetRangeSec.toFixed(3)},
    settings:{...Object.assign({},CFG_DEFAULT,cfg||{}),minimumOverlapSec:+fwd.minOverlapSec.toFixed(3)}
  };
}

self.onmessage=function(ev){
  try{
    const m=ev.data||{};
    if(m.type==='extract'){
      const pcm=m.pcm instanceof Float32Array?m.pcm:new Float32Array(m.pcm);
      const feature=extractFeature(pcm,m.sampleRate,m.config);
      self.postMessage({type:'progress',stage:'extract',pct:95});
      self.postMessage({type:'feature',feature},[feature.chroma.buffer,feature.rmsDb.buffer,feature.valid.buffer]);
    } else if(m.type==='match'){
      const result=diag(m.reference,m.target,m.config);
      self.postMessage({type:'done',result});
    }
  }catch(e){ self.postMessage({type:'error',message:(e&&e.message)||String(e),stack:(e&&e.stack)||''}); }
};
