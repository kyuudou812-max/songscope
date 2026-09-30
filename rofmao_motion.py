"""モーショングラフィックス版「ROF-MAOって？」40秒（非公式ファンメイド）。

キャラクターの絵は使わず、メンバーカラー・文字・図形・動きで見せる。
映像は HTML/CSS/SVG をコードで組み立て、Chromium で1コマずつ撮影して動画にする。
効果音・BGM もすべてプログラムで合成する（外部素材なし）。

使い方:
    python3 rofmao_motion.py                          # rofmao_motion.mp4 を書き出す
    python3 rofmao_motion.py --stills <dir> [秒 ...]  # 確認用の静止画だけ書き出す
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from playwright.sync_api import sync_playwright

import rofmao_video as sfx  # 効果音の合成関数を使い回す

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
W, H, FPS, DURATION = 1920, 1080, 30, 40.0
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 映像（HTML + JS）
PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:#000}
#stage{position:relative;width:1920px;height:1080px;overflow:hidden;
  font-family:"Noto Sans CJK JP",sans-serif;font-weight:700;color:#fff}
.a{position:absolute;left:0;top:0;white-space:nowrap;will-change:transform}
.c{transform-origin:50% 50%}
</style></head><body><div id="stage"></div>
<script>
const W=1920,H=1080;
const M=[
 {name:"加賀美ハヤト",en:"KAGAMI HAYATO",role:"社長",col:"#F2F2F7",ink:"#1b1726"},
 {name:"剣持刀也",en:"KENMOCHI TOYA",role:"高校生",col:"#8A4FFF",ink:"#ffffff"},
 {name:"不破湊",en:"FUWA MINATO",role:"ホスト",col:"#E2419F",ink:"#ffffff"},
 {name:"甲斐田晴",en:"KAIDA HARU",role:"研究者",col:"#2FB0F0",ink:"#ffffff"},
];
const COLS=M.map(m=>m.col);
const DARK="#16121f", YEL="#FFE14A", RED="#FF3B5C";

// ---- 小道具
const cl=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const P=(t,a,b)=>cl((t-a)/(b-a));
const eo=x=>1-Math.pow(1-x,3);
const eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
const back=x=>{const c=1.9;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const pop=(t,a,d=.28)=>t<a?0:back(P(t,a,a+d));
function rnd(seed){return function(){seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);
  t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}

// 中心を (x,y) に置く
function at(x,y,html,{s=1,r=0,o=1,z=0,extra=""}={}){
  if(s<=0.001||o<=0.001)return"";
  return `<div class="a" style="transform:translate(${x}px,${y}px) translate(-50%,-50%) rotate(${r}deg) scale(${s});opacity:${o};z-index:${z};${extra}">${html}</div>`;
}
// 縁取り文字（後ろに太い縁の文字、前に塗りの文字を重ねる）
function txt(s,size,{fill="#fff",stroke=null,sw=0,stroke2=null,sw2=0,ls=0,weight=900,shadow=""}={}){
  const base=`font-size:${size}px;letter-spacing:${ls}px;line-height:1.1;font-weight:${weight};`;
  let h=`<div style="position:relative;${base}">`;
  if(stroke2)h+=`<div style="position:absolute;left:0;top:0;-webkit-text-stroke:${sw2*2}px ${stroke2};color:${stroke2}">${s}</div>`;
  if(stroke)h+=`<div style="position:absolute;left:0;top:0;-webkit-text-stroke:${sw*2}px ${stroke};color:${stroke}">${s}</div>`;
  h+=`<div style="position:relative;color:${fill};${shadow?"text-shadow:"+shadow:""}">${s}</div></div>`;
  return h;
}
function rect(x,y,w,h,col,{r=0,rot=0,o=1,extra=""}={}){
  return `<div class="a" style="transform:translate(${x}px,${y}px) rotate(${rot}deg);width:${w}px;height:${h}px;background:${col};border-radius:${r}px;opacity:${o};${extra}"></div>`;
}
function bg(col){return `<div class="a" style="width:${W}px;height:${H}px;background:${col}"></div>`;}
function svg(inner){return `<svg class="a" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${inner}</svg>`;}

// コーナー名（左上）と番組ロゴ（右上）
function ui(label){
  let h=`<div class="a" style="transform:translate(40px,36px);padding:10px 30px;background:${RED};border:5px solid #fff;
    border-radius:18px;font-size:44px;font-weight:900;box-shadow:8px 8px 0 rgba(0,0,0,.35)">${label}</div>`;
  let dots=COLS.map(c=>`<span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:${c};border:2px solid #1b1726;margin-right:6px"></span>`).join("");
  h+=`<div class="a" style="transform:translate(${W-500}px,36px);width:450px;padding:14px 0;background:#fff;border:5px solid #1b1726;
    border-radius:48px;text-align:center;color:#6b3fd8;font-size:38px;font-weight:900">${dots}ROF-MAOって？</div>`;
  return h;
}
// 集中線
function speed(t,col="rgba(255,255,255,.9)",n=90,cx=W/2,cy=H/2,r0=430){
  const R=rnd(Math.floor(t*14)+7);let s="";
  for(let i=0;i<n;i++){const a=R()*Math.PI*2,r=r0+R()*260,w=2+R()*7;
    const x1=cx+Math.cos(a)*r,y1=cy+Math.sin(a)*r*.62,x2=cx+Math.cos(a)*1500,y2=cy+Math.sin(a)*1500*.62;
    s+=`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${col}" stroke-width="${w}"/>`;}
  return svg(s);
}
// 回転する放射
function rays(t,c1,c2,n=24,cx=W/2,cy=H/2){
  let s=`<rect width="${W}" height="${H}" fill="${c1}"/>`;
  for(let i=0;i<n;i+=2){const a0=i/n*Math.PI*2+t*.25,a1=(i+1)/n*Math.PI*2+t*.25,R=2400;
    s+=`<polygon points="${cx},${cy} ${cx+Math.cos(a0)*R},${cy+Math.sin(a0)*R} ${cx+Math.cos(a1)*R},${cy+Math.sin(a1)*R}" fill="${c2}"/>`;}
  return svg(s);
}
function confetti(t,seed=3,n=140){
  const R=rnd(seed);let s="";
  for(let i=0;i<n;i++){const x=(R()*W+Math.sin(t*2+i)*40+W)%W, sp=160+R()*260;
    const y=((R()*-H+t*sp)%(H+60)+H+60)%(H+60)-30, a=t*(120+R()*300)+i*37;
    const c=[...COLS,YEL,RED][i%6];
    s+=`<rect x="${-12}" y="${-6}" width="24" height="12" fill="${c}" transform="translate(${x},${y}) rotate(${a}) scale(1,${Math.cos(t*4+i)})"/>`;}
  return svg(s);
}
// ふきだし
function bubble(x,y,text,col,tail,s){
  const tx=tail[0],ty=tail[1];
  return at(x,y,`<div style="position:relative;padding:22px 40px;background:#fff;border:7px solid ${col};border-radius:40px;
    font-size:54px;font-weight:900;color:#1b1726;box-shadow:10px 10px 0 rgba(0,0,0,.25)">${text}
    <div style="position:absolute;left:${tx}px;top:${ty}px;width:0;height:0;border-left:22px solid transparent;border-right:22px solid transparent;
    border-top:40px solid ${col}"></div></div>`,{s});
}

// ================================================================ 場面
// 0-4 オープニング
function sOpening(t){
  let h=bg(DARK);
  // 4本の帯が上から落ちてくる
  COLS.forEach((c,i)=>{const k=eo(P(t,i*.12,i*.12+.5));const w=W/4;
    const shrink=eio(P(t,1.0,1.5));const ww=w*(1-shrink)+46*shrink, x=(i*w)*(1-shrink)+(W/2-2*46+i*46)*shrink;
    h+=rect(x,-H+H*k,ww,H,c,{o:1-P(t,3.3,3.6)*.0});});
  // 中央の帯の上にタイトル
  if(t>1.2){
    const s=pop(t,1.2,.35);
    h+=at(W/2,420,txt("ROF-MAO",250,{fill:"#fff",stroke:DARK,sw:14,ls:6,
      shadow:`10px 10px 0 ${COLS[1]},20px 20px 0 ${COLS[2]},30px 30px 0 ${COLS[3]}`}),{s,r:-3*(1-P(t,1.2,1.6))});
  }
  if(t>1.8)h+=at(W/2,640,txt("って？",170,{fill:YEL,stroke:DARK,sw:16}),{s:pop(t,1.8,.3),r:4});
  if(t>2.5)h+=at(W/2,830,`<div style="padding:14px 44px;background:#fff;color:${DARK};font-size:52px;border-radius:12px">
    にじさんじの4人組ユニットを、40秒でご紹介！</div>`,{s:pop(t,2.5,.3)});
  return h;
}

// 4-10 メンバー紹介
function memberCard(t,i){
  const m=M[i];let h=bg(m.col);
  // 背景に大きく流れる英字
  const off=-t*260;
  h+=at(W/2+off+300,540,`<div style="font-size:330px;font-weight:900;color:transparent;-webkit-text-stroke:4px ${m.ink};opacity:.18;letter-spacing:10px">${m.en} ${m.en}</div>`);
  // 丸いモチーフ
  const k=eo(P(t,0,.4));
  h+=`<div class="a" style="transform:translate(${1380-200*k}px,${140}px);width:${720}px;height:${720}px;border-radius:50%;
     border:28px solid ${m.ink};opacity:.14"></div>`;
  // 番号
  h+=at(250,230,txt(`0${i+1}<span style="font-size:60px;opacity:.6"> / 04</span>`,140,{fill:m.ink}),{o:k});
  // 役割タグ
  h+=at(430+(1-k)*-200,470,`<div style="padding:12px 40px;background:${DARK};color:#fff;font-size:72px;border-radius:14px;transform:skewX(-8deg)">${m.role}</div>`,{s:pop(t,.12,.25)});
  // 名前
  h+=at(760+(1-eo(P(t,.05,.45)))*400,650,txt(m.name,190,{fill:m.ink,stroke:i==0?"#d9d6e6":"rgba(0,0,0,.25)",sw:i==0?0:0}),{o:P(t,.05,.2)});
  h+=at(760+(1-eo(P(t,.15,.5)))*500,800,`<div style="font-size:64px;letter-spacing:18px;color:${m.ink};opacity:.75">${m.en}</div>`,{o:P(t,.15,.3)});
  return h;
}
function sMembers(t){
  if(t<5.0){
    const i=Math.min(3,Math.floor(t/1.25)), lt=t-i*1.25;
    let h=memberCard(lt,i);
    // 次のカードへのスライド
    if(i<3&&lt>1.05){const k=eio(P(lt,1.05,1.25));h+=rect(W-W*k-200,0,W+400,H,M[i+1].col,{rot:0,extra:`clip-path:polygon(200px 0,100% 0,100% 100%,0 100%)`});}
    return h;
  }
  // 4分割で「設定、バラバラ。」
  const u=t-5.0;let h=bg(DARK);
  M.forEach((m,i)=>{const k=eo(P(u,i*.06,i*.06+.3));
    h+=rect(i*W/4,H*(1-k)*(i%2?1:-1),W/4,H,m.col);
    h+=at(i*W/4+W/8,300,txt(m.role,96,{fill:m.ink}),{o:k});
    h+=at(i*W/4+W/8,420,`<div style="font-size:40px;color:${m.ink}">${m.name}</div>`,{o:k});});
  if(u>.35){h+=rect(0,620,W,220,DARK,{o:.92});
    h+=at(W/2,730,txt("設定、バラバラ。",150,{fill:YEL}),{s:pop(u,.35,.3)});}
  return h;
}

// 10-16 VTuberといえば？ → ロケに行く
const CHAT=["こんばんは！","初見です","草","888888","かわいい","神回","きたー！","おつかれ〜","うますぎ","それな"];
function sVtuber(t){
  let h="";
  if(t<3.0){
    h+=bg("#1e1a2e");
    // 配信画面
    const k=eo(P(t,0,.5));
    h+=`<div class="a" style="transform:translate(${140}px,${250+(1-k)*80}px);width:1120px;height:630px;border-radius:26px;overflow:hidden;
      background:linear-gradient(135deg,#3b2f7a,#b0508a);opacity:${k};box-shadow:0 30px 60px rgba(0,0,0,.5)">
      <div style="position:absolute;left:40px;top:34px;padding:6px 20px;background:${RED};border-radius:8px;font-size:34px">● LIVE</div>
      <div style="position:absolute;right:40px;top:40px;font-size:32px;opacity:.85">👁 ${Math.floor(1200+t*2400).toLocaleString()}</div>
      <div style="position:absolute;left:0;right:0;bottom:0;height:120px;background:rgba(0,0,0,.45)"></div>
      <div style="position:absolute;left:50%;top:48%;transform:translate(-50%,-50%);width:300px;height:300px;border-radius:50%;
        background:rgba(255,255,255,.18);border:6px dashed rgba(255,255,255,.5)"></div>
      <div style="position:absolute;left:44px;bottom:36px;font-size:40px">雑談・ゲーム実況・歌枠 …</div></div>`;
    // コメント欄
    h+=`<div class="a" style="transform:translate(1300px,${250+(1-k)*80}px);width:480px;height:630px;border-radius:26px;background:#2a2540;opacity:${k};overflow:hidden">`;
    for(let j=0;j<12;j++){const y=600-((t*260+j*70)%840);const c=COLS[j%4];
      h+=`<div style="position:absolute;left:24px;top:${y}px;font-size:34px"><span style="color:${c}">●</span> ${CHAT[(j+Math.floor(t*3.7))%CHAT.length]}</div>`;}
    h+=`</div>`;
    h+=at(W/2,170,txt("VTuberといえば…",90,{fill:"#fff",stroke:DARK,sw:12}),{s:pop(t,.4,.3)});
    if(t>1.3)h+=at(700,965,txt("配信！",200,{fill:YEL,stroke:DARK,sw:18}),{s:pop(t,1.3,.3),r:-4});
    // グリッチ
    if(t>2.55){const R=rnd(Math.floor(t*30));let g="";
      for(let j=0;j<14;j++){const y=R()*H,hh=10+R()*80;g+=rect((R()-.5)*300,y,W,hh,[RED,"#00e5ff","#fff",...COLS][j%7],{o:.8});}
      h+=g;}
    return h;
  }
  const u=t-3.0;
  if(u<.12)return bg("#ffffff");
  h+=rays(u,"#48b8ff","#7fd0ff");
  // 地図のピンが降ってくる
  const pins=[[260,760],[1660,720],[420,300],[1520,300]];
  pins.forEach((p,i)=>{const a=1.0+i*.15;if(u<a)return;const k=eo(P(u,a,a+.35));
    h+=at(p[0],p[1]-300*(1-k),`<svg width="150" height="200" viewBox="0 0 150 200"><path d="M75 195 C75 195 5 115 5 72 A70 70 0 1 1 145 72 C145 115 75 195 75 195Z"
      fill="${COLS[i]}" stroke="${DARK}" stroke-width="8"/><circle cx="75" cy="72" r="28" fill="#fff" stroke="${DARK}" stroke-width="6"/></svg>`,{r:Math.sin(u*6+i)*6});});
  h+=at(W/2,330,txt("ROF-MAOは、",120,{fill:"#fff",stroke:DARK,sw:14}),{s:pop(u,.2,.3)});
  if(u>.8)h+=at(W/2,640,txt("ロケに行く。",260,{fill:YEL,stroke:DARK,sw:22,stroke2:"#fff",sw2:34}),{s:pop(u,.8,.35),r:-3+Math.sin(u*5)*1.2});
  return h;
}

// 16-23 本気の挑戦
function sChallenge(t){
  let h=bg("#ff7a1a");
  h+=`<div class="a" style="width:${W}px;height:${H}px;background:radial-gradient(circle at 50% 55%,#ffb347 0,#ff7a1a 55%,#e8430f 100%)"></div>`;
  // 背景の流れる文字
  for(let j=0;j<3;j++)h+=at(W/2+((t*(j%2?-300:300))%1400)-(j%2?-700:700),200+j*340,
    `<div style="font-size:260px;font-weight:900;color:transparent;-webkit-text-stroke:5px rgba(255,255,255,.25)">CHALLENGE CHALLENGE</div>`);
  if(t>4.4)h+=speed(t);
  // お題
  h+=at(W/2,220,`<div style="padding:18px 60px;background:#fff;border:10px solid ${DARK};border-radius:24px;color:${DARK};font-size:76px;
     box-shadow:12px 12px 0 ${DARK}">お題：<span style="color:${RED}">ガチの料理対決</span></div>`,{s:pop(t,.3,.3)*(1-.25*eio(P(t,4.2,4.5))),o:1-P(t,4.3,4.5)});
  // 本気度ゲージ
  const gx=[480,800,1120,1440];
  M.forEach((m,i)=>{const a=1.1+i*.35;if(t<a)return;
    const k=eo(P(t,a,a+1.2)), v=Math.round(k*100);
    const top=860-460*k;
    h+=rect(gx[i]-90,400,180,460,"rgba(0,0,0,.25)",{r:24});
    h+=rect(gx[i]-90,top,180,860-top,m.col,{r:24,extra:`border:6px solid ${DARK};box-sizing:border-box`});
    h+=at(gx[i],930,`<div style="font-size:48px;color:#fff;text-shadow:0 4px 0 ${DARK}">${m.role}</div>`);
    h+=at(gx[i],top-60,txt(`${v}%`,70,{fill:"#fff",stroke:DARK,sw:9}),{s:v==100?1+.12*Math.sin(t*14):1});
  });
  if(t>1.0&&t<4.4)h+=at(W/2,1010,`<div style="font-size:54px;color:#fff;text-shadow:0 4px 0 ${DARK}">本気度メーター</div>`,{o:P(t,1,1.2)});
  if(t>4.5){const sh=t<5.0?Math.sin(t*90)*14:0;
    h+=rect(0,380,W,340,DARK,{o:.85});
    h+=at(W/2+sh,550,txt("全員、本気。",230,{fill:"#fff",stroke:RED,sw:18}),{s:pop(t,4.5,.3)});}
  return h;
}

// 23-29 まさかの結果
function sResult(t){
  let h=bg("#0d0b14");
  if(t<1.8){
    // スポットライト
    for(let j=0;j<3;j++){const x=W/2+Math.sin(t*2.2+j*2.1)*600;
      h+=`<div class="a" style="width:${W}px;height:${H}px;background:radial-gradient(ellipse 260px 420px at ${x}px 620px,rgba(255,240,200,.28),transparent)"></div>`;}
    const dots=".".repeat(1+Math.floor(t*4)%3);
    h+=at(W/2,540,txt("結果は"+`<span style="display:inline-block;width:170px;text-align:left">${dots.replace(/\./g,"・")}</span>`,150,{fill:"#fff"}),{s:pop(t,.2,.3)});
    return h;
  }
  if(t<2.0)return bg("#000");
  const u=t-2.0;
  const shake=u<.5?Math.sin(u*80)*26*(1-u/.5):0;
  const grey=P(u,.9,1.4);
  h=bg(`rgb(${Math.round(60-30*grey)},${Math.round(12+10*grey)},${Math.round(30+30*grey)})`);
  // ヒビ
  let s="";const R=rnd(9);
  for(let i=0;i<16;i++){let x=W/2,y=500,a=i/16*Math.PI*2+R()*.3,pts=`${x},${y}`;
    for(let r=0;r<1300;){r+=80+R()*160;const aa=a+(R()-.5)*.3;pts+=` ${W/2+Math.cos(aa)*r},${500+Math.sin(aa)*r}`;}
    s+=`<polyline points="${pts}" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="5"/>`;}
  h+=svg(s);
  h+=at(W/2+shake,480,txt("大失敗",330,{fill:RED,stroke:"#fff",sw:16,stroke2:DARK,sw2:30}),{s:pop(u,0,.25)*(1-.08*grey)});
  // メンバーカラーの丸が落ちてしょんぼり
  if(u>.9){M.forEach((m,i)=>{const k=P(u,.9+i*.05,1.5+i*.05);const y=600+Math.min(1,k)*180+Math.abs(Math.sin(k*9))*(1-k)*-40;
    h+=`<div class="a" style="transform:translate(${560+i*260}px,${y}px) translate(-50%,-50%);width:120px;height:120px;border-radius:50%;
      background:${m.col};border:6px solid #fff;filter:grayscale(${grey})"></div>`;});
    h+=at(W/2,300-80,`<div style="font-size:60px;color:#9fb4ff">〜 チーン 〜</div>`,{o:P(u,1.0,1.3)});}
  if(u>1.6)h+=at(W/2,980,txt("まさかの結果",120,{fill:"#9fc3ff",stroke:DARK,sw:14}),{s:pop(u,1.6,.3)});
  return h;
}

// 29-34 ツッコミが止まらない
const LINES=[[.2,1,"火力、強すぎでしょ！",520,300,[60,95]],[.7,0,"いや、レシピ通りです！",1260,250,[300,95]],
 [1.2,3,"どのレシピ見たの？",1320,520,[200,95]],[1.7,2,"逆にすごくない？",560,560,[80,95]],
 [2.2,1,"もう一回やらせて！",960,760,[160,95]],[2.6,0,"スタッフさん笑ってる！",700,420,[260,95]]];
function sTsukkomi(t){
  let h=`<div class="a" style="width:${W}px;height:${H}px;background:${YEL};
    background-image:radial-gradient(rgba(255,120,0,.35) 18%,transparent 19%);background-size:48px 48px;background-position:${t*40}px ${t*20}px"></div>`;
  LINES.forEach(([a,who,text,x,y,tail])=>{if(t<a)return;const jig=Math.sin(t*9+a*7)*4;
    h+=bubble(x,y+jig,text,COLS[who]==COLS[0]?"#b9b6c9":COLS[who],tail,pop(t,a,.22));});
  // （笑）スタンプ
  const ST=[[150,740,-12],[1770,380,10],[1750,700,-8],[1560,900,14],[330,920,8]];
  ST.forEach(([x,y,r],j)=>{const a=1.0+j*.4;if(t<a)return;
    h+=at(x,y,txt("（笑）",78,{fill:RED,stroke:"#fff",sw:8}),{s:pop(t,a,.2),r});});
  if(t>3.2){h+=rect(0,860,W,200,DARK,{o:.9});
    h+=at(W/2,960,txt("ツッコミが止まらない",140,{fill:YEL,stroke:RED,sw:10}),{s:pop(t,3.2,.3)});}
  return h;
}

// 34-40 エンディング
function sEnding(t){
  let h=rays(t,"#2a1f4a","#352763");
  h+=confetti(t);
  // 斜めの4色の帯
  COLS.forEach((c,i)=>{const k=eo(P(t,i*.08,i*.08+.5));
    h+=rect(-400+(1-k)*-2600,300+i*56,W+800,56,c,{rot:-6});});
  h+=`<div class="a" style="transform:translate(${W/2-820}px,${340}px) rotate(-6deg) scale(${pop(t,.5,.35)});width:1640px;height:260px;
     background:#fff;border:12px solid ${DARK};border-radius:30px;box-shadow:18px 18px 0 ${DARK}"></div>`;
  if(t>.7)h+=at(W/2-10,470,txt("VTuberの、<span style='color:"+RED+"'>バラエティ番組。</span>",108,{fill:DARK}),{s:pop(t,.7,.35),r:-6});
  if(t>1.8){const names=M.map(m=>`<span style="color:${m.col==M[0].col?"#fff":m.col}">${m.name}</span>`).join("　");
    h+=at(W/2,800,`<div style="font-size:52px;text-shadow:0 4px 0 ${DARK}">${names}</div>`,{o:P(t,1.8,2.3)});
    h+=at(W/2,900,txt("ROF-MAO",90,{fill:"#fff",ls:14,shadow:`6px 6px 0 ${COLS[1]},12px 12px 0 ${COLS[2]},18px 18px 0 ${COLS[3]}`}),{o:P(t,2.1,2.6)});}
  if(t>5.3)h+=rect(0,0,W,H,"#000",{o:P(t,5.3,6.0)});
  return h;
}

// 場面の切り替え（4色の帯が横切る）
function bands(p){
  let h="";const bw=560,sk=380,cols=[YEL,...COLS];const total=bw*cols.length;
  const x0=-total-sk+p*(W+total+sk*2);
  cols.forEach((c,i)=>{const x=x0+i*bw;
    h+=`<div class="a" style="width:${W}px;height:${H}px;background:${c};clip-path:polygon(${x+sk}px 0,${x+sk+bw+2}px 0,${x+bw+2}px 100%,${x}px 100%)"></div>`;});
  return h;
}

const SCENES=[[0,4,sOpening,null],[4,10,sMembers,"メンバー紹介"],[10,16,sVtuber,"VTuberといえば？"],
  [16,23,sChallenge,"本気の挑戦"],[23,29,sResult,"まさかの結果"],[29,34,sTsukkomi,"反省会"],[34,40,sEnding,null]];
const TR=.28;
function render(t){
  let h="";
  for(const [a,b,f,label] of SCENES){
    if(t>=a&&(t<b||b==40)){h+=f(t-a);if(label&&!(f==sResult&&t-a<2.0&&t-a>=1.8))h+=ui(label);break;}
  }
  for(const [a] of SCENES.slice(1)){if(Math.abs(t-a)<TR)h+=bands((t-a+TR)/(2*TR));}
  document.getElementById("stage").innerHTML=h;
}
</script></body></html>"""

# ---------------------------------------------------------------- 音（120BPM・拍に合わせる）
SR = sfx.SR


def bgm(total, bpm=120):
    beat = 60 / bpm
    out = np.zeros(int(SR * total), np.float32)
    prog = [("C3", ["C4", "E4", "G4"]), ("G2", ["B3", "D4", "G4"]),
            ("A2", ["C4", "E4", "A4"]), ("F2", ["A3", "C4", "F4"])]
    for b in range(int(total / beat)):
        root, chord = prog[(b // 4) % 4]
        t = b * beat

        def put(tt, snd):
            i = int(tt * SR)
            out[i:i + len(snd)] += snd[: max(0, len(out) - i)]

        put(t, sfx.pluck(sfx.note(root), beat * 0.9, 0.17))
        put(t, sfx.sine(60, 0.18, 0.35, decay=20, sweep=40) if b % 2 == 0 else np.zeros(1, np.float32))  # キック
        put(t + beat / 2, sfx.mix(*[sfx.pluck(sfx.note(n), beat * 0.4, 0.035) for n in chord]))
        if b % 2 == 1:
            put(t, sfx.noise(0.12, 0.12, decay=30, smooth=2, seed=b))  # スネア
        for hh in (0, 0.5):
            x = sfx.noise(0.03, 0.05, decay=120, seed=b * 2 + int(hh * 2))
            put(t + hh * beat, x - np.convolve(x, np.ones(4) / 4, mode="same"))
    return out


def build_audio(path):
    buf = np.zeros(int(SR * DURATION) + SR * 3, np.float32)

    def add(t, snd, vol=1.0):
        i = int(t * SR)
        j = min(len(buf), i + len(snd))
        buf[i:j] += snd[: j - i] * vol

    music = bgm(DURATION)
    gate = np.ones(len(music), np.float32)
    s0, s1, fade = int(22.9 * SR), int(27.0 * SR), int(0.25 * SR)
    gate[s0 - fade:s0] = np.linspace(1, 0, fade)
    gate[s0:s1] = 0
    gate[s1:s1 + fade] = np.linspace(0, 1, fade)
    gate[int(34.4 * SR):] *= 0.45
    buf[:len(music)] += music * gate

    for s in (4, 10, 16, 23, 29, 34):
        add(s - 0.3, sfx.se_whoosh())
    # オープニング
    for i in range(4):
        add(i * 0.12, sfx.se_pon(), 0.6)
    add(1.2, sfx.se_don())
    add(1.2, sfx.se_jan(), 0.8)
    add(1.8, sfx.se_pon())
    add(2.5, sfx.se_pon())
    # メンバー紹介
    for i in range(4):
        add(4.0 + i * 1.25 + 0.12, sfx.se_pon())
    add(9.0, sfx.se_don(), 0.7)
    add(9.35, sfx.se_jan(), 0.8)
    # VTuberといえば？
    add(10.4, sfx.se_pon())
    add(11.3, sfx.se_don(), 0.7)
    add(12.55, sfx.se_gashan())
    add(13.2, sfx.se_pon())
    add(13.8, sfx.se_don())
    add(13.8, sfx.se_jan(), 0.8)
    for i in range(4):
        add(14.0 + i * 0.15, sfx.se_pon(), 0.5)
    # 本気の挑戦
    add(16.3, sfx.se_jan())
    for i in range(4):
        add(17.1 + i * 0.35, sfx.sine(300, 1.2, 0.08, decay=1.0, sweep=900))  # ゲージが上がる音
        add(18.3 + i * 0.35, sfx.se_pinpon()[: int(SR * 0.3)], 0.5)
    add(20.5, sfx.se_don())
    add(20.5, sfx.se_jan())
    # まさかの結果
    add(23.2, sfx.se_drumroll(1.6))
    add(25.0, sfx.se_don())
    add(25.0, sfx.se_gashan(), 0.5)
    add(26.0, sfx.se_chin())
    add(26.6, sfx.se_pon())
    # 反省会
    for a in (0.2, 0.7, 1.2, 1.7, 2.2, 2.6):
        add(29.0 + a, sfx.se_pon())
    add(32.2, sfx.se_jan())
    # エンディング
    add(34.5, sfx.se_pinpon())
    add(34.7, sfx.se_jingle())
    buf = buf[: int(SR * DURATION)]
    fo = int(0.8 * SR)
    buf[-fo:] *= np.linspace(1, 0, fo)
    peak = np.max(np.abs(buf))
    if peak > 0.95:
        buf *= 0.95 / peak
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((buf * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- 書き出し
def open_page(p):
    b = p.chromium.launch(executable_path=CHROME)
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pg.set_content(PAGE)
    pg.evaluate("document.fonts.ready")
    return b, pg


def shot(pg, t, **kw):
    pg.evaluate(f"render({t:.4f})")
    return pg.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}, **kw)


def main():
    with sync_playwright() as p:
        b, pg = open_page(p)
        if "--stills" in sys.argv:
            i = sys.argv.index("--stills")
            out = sys.argv[i + 1]
            os.makedirs(out, exist_ok=True)
            times = [float(x) for x in sys.argv[i + 2:]] or \
                [1.0, 3.0, 4.6, 7.2, 9.8, 11.5, 12.7, 14.6, 16.8, 19.0, 21.5, 24.2, 26.8, 30.8, 33.0, 36.5]
            for t in times:
                shot(pg, t, path=os.path.join(out, f"still_{t:05.2f}.png"))
            b.close()
            return
        wav = os.path.join(OUT_DIR, "_rofmao_motion.wav")
        mp4 = os.path.join(OUT_DIR, "rofmao_motion.mp4")
        build_audio(wav)
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
               "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(DURATION * FPS)):
            ff.stdin.write(shot(pg, f / FPS, type="png"))
        ff.stdin.close()
        ff.wait()
        b.close()
    os.remove(wav)
    print("wrote", mp4)


if __name__ == "__main__":
    main()
