/* Signage, Inverted
   Signs from the street, set in letters a text reader found in my photographs.
   data/signs.json    the signs, sorted by tone (edit this to change the text)
   letters/           letter sheets cut from Found-Letters-Tool readings (made by tools/build_letters.py) */
(async function(){
const [signs,letters,comp,riso,order]=await Promise.all([fetch('data/signs.json').then(r=>r.json()),fetch('letters/letters.json').then(r=>r.json()),fetch('data/composition.json').then(r=>r.ok?r.json():null).catch(()=>null),fetch('letters/riso.json').then(r=>r.ok?r.json():null).catch(()=>null),fetch('data/order.json').then(r=>r.ok?r.json():null).catch(()=>null)]);
/* data/composition.json is the arrangement that was printed (tools/build_signs.py); the page opens on it, and Shuffle leaves it */
const D={G:letters.G,S:signs.flatMap(t=>t.signs.map(g=>[t.level,g])),N:signs.map(t=>t.tone),C:signs.map(t=>t.signs.length)};
/* versions: the digital cut, then one version per riso print once the scans are in (tools/cut_scans.py).
   When prints exist, every letter is taken from one of the prints, chosen at random. */
const ALL=letters.versions,PRINTS=ALL.filter(v=>v.name!=='digital'),V=PRINTS.length?PRINTS:ALL;
const FALL={'–':'-','•':'.','ñ':'n','’':"'"};
/* scanned riso sheets (tools/cut_sign_scans.py): every sign printed on a scanned sheet is shown in its scanned letters,
   in the ink's own colour; a swap there takes the same letter from elsewhere on the scans. RR = every scanned letter, RG = by letter. */
const RS=riso?riso.sheets:[],RR=[],RG={},RSIGN={},RK=[];
RS.forEach((sh,si)=>{const o=RR.length;sh.R.forEach((r,i)=>{RR.push([si,r[1],r[2],r[3],r[4]]);RK.push(sh.K[i]);(RG[sh.K[i]]=RG[sh.K[i]]||[]).push([o+i,sh.P[i]])});
  Object.entries(sh.signs).forEach(([b,ls])=>{RSIGN[b]=ls.map(l=>l.map(w=>w.map(c=>c+o)))})});
/* each scanned letter's own strip on its print: from halfway to the letter before it to halfway to the one after (a margin at a word's ends),
   so a letter taken somewhere else brings none of its old neighbours */
const STRIP=[];Object.values(RSIGN).forEach(ls=>ls.forEach(l=>l.forEach(w=>w.forEach((c,n)=>{const r=RR[c],a=RR[w[n-1]],z=RR[w[n+1]],m=r[4]*.12;
  STRIP[c]=[a?(a[1]+a[3]+r[1])/2:r[1]-m,z?(r[1]+r[3]+z[1])/2:r[1]+r[3]+m]}))));
const dpr=Math.min(3,window.devicePixelRatio||1);
const street=document.getElementById('street');
const lines=[];
const noHover=matchMedia('(hover: none)').matches;
let seed=7;const rnd=()=>{seed=(seed*16807)%2147483647;return (seed-1)/2147483646};
/* data/order.json: the order the signs are shown in, within their tones, so the printed colours run on down the page.
   Each sign keeps its own number (k) for its letters and its scan. */
const ORDER=order&&order.length===D.S.length?order:D.S.map((_,i)=>i);
let k=0,n=0;
D.N.forEach((name,ti)=>{
  const lv=ti+1,sec=document.createElement('section');sec.dataset.l=lv;
  sec.innerHTML=`<div class="tone"><b>${lv} / 6</b><span>${name}</span><span>${D.C[ti]} signs</span></div><div class="signs"></div>`;
  const box=sec.querySelector('.signs');
  for(let i=0;i<D.C[ti];i++,n++){
    k=ORDER[n];const [l,text]=D.S[k];
    const b=document.createElement('div');b.className='sign';b.tabIndex=0;b.setAttribute('role','img');
    b.style.setProperty('--o',(rnd()).toFixed(3));
    b.setAttribute('aria-label',text.join(' / '));
    text.forEach((t,li)=>{const ln=document.createElement('span');ln.className='line';ln.setAttribute('aria-hidden','true');
      const words=t.split(' ').filter(Boolean).map(w=>{const cv=document.createElement('canvas');ln.append(cv);return {cv,w,picks:null}});
      b.append(ln);lines.push({el:ln,sign:b,words,l,k,p:k/(D.S.length-1),riso:RSIGN[k]?RSIGN[k][li]:null,fixed:comp&&comp.signs[k]&&comp.signs[k][li],vis:false,stale:true})});
    const rd=document.createElement('span');rd.className='read';rd.setAttribute('aria-hidden','true');rd.textContent=text.join('\n');b.append(rd);
    /* the original words show while the pointer rests on a sign (style.css); on a touch screen, a tap does it */
    if(noHover)b.addEventListener('click',()=>b.classList.toggle('open'));
    box.append(b);
  }
  street.append(sec);
});
function gkey(ch){const g=D.G;if(g[ch])return ch;const f=FALL[ch];if(f&&g[f])return f;const s=ch.toLowerCase()===ch?ch.toUpperCase():ch.toLowerCase();return g[s]?s:null}
function glyph(ch){const k=gkey(ch);return k?D.G[k]:null}
/* every letter has instances ranked from the least sure noise (0) to the surest word (1); a sign at position p down the page draws from the instances nearest p */
const NEAR=10;
function near(list,p){return list.map(([i,v])=>[i,Math.abs(v-p)]).sort((a,b)=>a[1]-b[1]).slice(0,NEAR)}
/* the last two tones stop following the slope and take only the clearest cuts of sure words */
const TOP={5:6,6:3};
function cands(list,o){if(TOP[o.l])return [...list].sort((a,b)=>b[1]-a[1]).slice(0,TOP[o.l]);return near(list,o.p)}
/* a scanned letter is [crop, -1]; a digital one is [letter, version] */
function rcand(ch,o){const l=RG[gkey(ch)];return l&&l.length?near(l,o.p):null}
function one(ch,o){if(o.riso){const c=rcand(ch,o);if(c)return [c[Math.floor(Math.random()*c.length)][0],-1]}
  const list=glyph(ch);if(!list)return null;const c=cands(list,o);return [c[Math.floor(Math.random()*c.length)][0],Math.floor(Math.random()*V.length)]}
function pickFixed(o){if(o.riso){o.words.forEach((wd,wi)=>{wd.picks=(o.riso[wi]||[]).map(c=>[c,-1])});return}
  o.words.forEach((wd,wi)=>{const ids=o.fixed[wi]||[];wd.picks=ids.map(i=>[i,Math.floor(Math.random()*V.length)])})}
function pick(o){o.words.forEach(wd=>{wd.picks=[...wd.w].filter(ch=>glyph(ch)).map(ch=>one(ch,o)).filter(Boolean)})}
/* like Found-Letters-Tool: each crop is scaled smoothly to its size first, then cut to black and white at one threshold */
let thr=0.5;
function draw(o){
  const h=o.h||(o.h=parseFloat(getComputedStyle(o.sign).getPropertyValue('--h'))||16);
  /* the print holds only words with at least one letter it could cut; a word like "-" has no piece and stays empty */
  if(o.riso){let j=0;o.words.forEach(wd=>{const has=[...wd.w].some(ch=>glyph(ch));
    if(!wd.orig){wd.orig=has?(o.riso[j]||[]):[];wd.cur=wd.orig.slice()}if(has)j++;drawWord(wd.cv,wd.orig,wd.cur,h)});o.stale=false;return}
  if(!o.words[0]||!o.words[0].picks){if(o.fixed)pickFixed(o);else pick(o)}
  const gap=h*.08;
  o.words.forEach(({cv,picks})=>{
    const items=picks.map(([i,v])=>{const r=v<0?RR[i]:V[v].R[i];return {r,img:v<0?RS[r[0]].img:V[v].imgs[r[0]],w:Math.max(1,h*r[3]/r[4])}});
    if(picks.some(p=>p[1]<0))return drawRiso(cv,items,h,gap);
    cv.style.margin='';cv.style.mixBlendMode='';
    let W=0;items.forEach((it,i)=>W+=it.w+(i?gap:0));W=Math.max(1,W);
    cv.width=Math.round(W*dpr);cv.height=Math.round(h*dpr);cv.style.width=W+'px';
    const g=cv.getContext('2d',{willReadFrequently:true});g.imageSmoothingEnabled=true;g.imageSmoothingQuality='high';
    g.fillStyle='#fff';g.fillRect(0,0,cv.width,cv.height);
    let x=0;items.forEach((it,i)=>{if(i)x+=gap;const r=it.r;g.drawImage(it.img,r[1],r[2],r[3],r[4],Math.round(x*dpr),0,Math.max(1,Math.round(it.w*dpr)),cv.height);x+=it.w});
    const im=g.getImageData(0,0,cv.width,cv.height),d=im.data,t=thr*255;
    /* digital letters: black or white at one threshold, like Found-Letters-Tool */
    for(let p=0;p<d.length;p+=4){const v=d[p]<t?0:255;d[p]=d[p+1]=d[p+2]=v}
    g.putImageData(im,0,0);
  });
  o.stale=false;
}
/* scanned letters are cut wider than the letter (PX, PY of its height on each side), so the colour that slipped off register
   and the halftone dots stay whole. The crops overlap their neighbours and print over each other (multiply), like a second drum.
   No threshold: only the paper is taken away, so the dots show. */
const PX=.12,PY=.18;
function drawRiso(cv,items,h,gap){
  const px=h*PX,py=h*PY;
  let W=0;items.forEach((it,i)=>W+=it.w+(i?gap:0));W=Math.max(1,W)+2*px;const H=h+2*py;
  cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);cv.style.width=W+'px';
  cv.style.margin=`${-py}px ${-px}px`;cv.style.mixBlendMode='multiply';
  const g=cv.getContext('2d',{willReadFrequently:true});g.imageSmoothingEnabled=true;g.imageSmoothingQuality='high';
  g.globalCompositeOperation='source-over';g.fillStyle='#fff';g.fillRect(0,0,cv.width,cv.height);g.globalCompositeOperation='multiply';
  let x=px;items.forEach((it,i)=>{if(i)x+=gap;const r=it.r,img=it.img,k=r[4]/h;   /* scan px per css px */
    const sx=Math.max(0,r[1]-px*k),sy=Math.max(0,r[2]-py*k),ex=Math.min(img.naturalWidth,r[1]+r[3]+px*k),ey=Math.min(img.naturalHeight,r[2]+r[4]+py*k);
    const dx=x-(r[1]-sx)/k,dy=py-(r[2]-sy)/k;
    g.drawImage(img,sx,sy,ex-sx,ey-sy,dx*dpr,dy*dpr,(ex-sx)/k*dpr,(ey-sy)/k*dpr);x+=it.w});
  g.globalCompositeOperation='source-over';
  const im=g.getImageData(0,0,cv.width,cv.height),d=im.data,lo=234;   /* paper (whitened in tools/cut_sign_scans.py) fades out between lo and lo+16 */
  for(let p=0;p<d.length;p+=4){const m=Math.min(d[p],d[p+1],d[p+2]);d[p+3]=m<=lo?255:m>=lo+16?0:Math.round(255*(lo+16-m)/16)}
  g.putImageData(im,0,0);
}
/* a printed and scanned sign: every word is cut whole from the scan, PX and PY of the letter height wider on each side,
   so its letters keep their spacing, the colour that slipped off register and the halftone dots.
   Scaled so a letter is h tall; only the paper is taken away. Lines break where the sign breaks, and wrap like the page on a narrow screen. */
function drawWord(cv,orig,cur,h){
  const rs=orig.map(i=>RR[i]);
  if(!rs.length){cv.width=cv.height=0;cv.style.display='none';return}
  const img=RS[rs[0][0]].img,lh=rs[0][4],k=lh/h,px=PX*lh,py=PY*lh;
  const sx=Math.max(0,Math.min(...rs.map(r=>r[1]))-px),top=Math.min(...rs.map(r=>r[2])),sy=Math.max(0,top-py);
  const ex=Math.min(img.naturalWidth,Math.max(...rs.map(r=>r[1]+r[3]))+px),ey=Math.min(img.naturalHeight,Math.max(...rs.map(r=>r[2]+r[4]))+py);
  const W=(ex-sx)/k,H=(ey-sy)/k;
  cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);cv.style.width=W+'px';
  cv.style.margin=`${-(top-sy)/k}px ${-px/k}px ${-(ey-top-lh)/k}px`;cv.style.mixBlendMode='multiply';cv.style.maxWidth='none';
  const g=cv.getContext('2d',{willReadFrequently:true});g.imageSmoothingEnabled=true;g.imageSmoothingQuality='high';
  g.drawImage(img,sx,sy,ex-sx,ey-sy,0,0,cv.width,cv.height);
  /* letters that were swapped: the same letter cut from elsewhere, with its own margin, set over the whole strip that letter owns
     (from halfway to its left neighbour to halfway to its right one, top to bottom), so nothing of the old letter shows around it */
  cur.forEach((c,n)=>{if(c===orig[n])return;const r=rs[n],q=RR[c],qi=RS[q[0]].img;
    const L=n?(rs[n-1][1]+rs[n-1][3]+r[1])/2:sx,R=n<rs.length-1?(r[1]+r[3]+rs[n+1][1])/2:ex;
    const fx=q[3]/r[3],fy=q[4]/r[4];
    let qx0=q[1]-(r[1]-L)*fx,qx1=q[1]+q[3]+(R-r[1]-r[3])*fx,qy0=q[2]-(r[2]-sy)*fy,qy1=q[2]+q[4]+(ey-r[2]-r[4])*fy;
    let dx0=L,dx1=R,dy0=sy,dy1=ey;const st=STRIP[c];
    if(st&&qx0<st[0]){dx0+=(st[0]-qx0)/fx;qx0=st[0]}if(st&&qx1>st[1]){dx1-=(qx1-st[1])/fx;qx1=st[1]}
    if(qx0<0){dx0+=-qx0/fx;qx0=0}if(qy0<0){dy0+=-qy0/fy;qy0=0}
    if(qx1>qi.naturalWidth){dx1-=(qx1-qi.naturalWidth)/fx;qx1=qi.naturalWidth}if(qy1>qi.naturalHeight){dy1-=(qy1-qi.naturalHeight)/fy;qy1=qi.naturalHeight}
    const X=v=>(v-sx)/k*dpr,Y=v=>(v-sy)/k*dpr;
    g.fillStyle='#fff';g.fillRect(X(L),0,X(R)-X(L),cv.height);
    g.drawImage(qi,qx0,qy0,qx1-qx0,qy1-qy0,X(dx0),Y(dy0),X(dx1)-X(dx0),Y(dy1)-Y(dy0))});
  const im=g.getImageData(0,0,cv.width,cv.height),d=im.data,lo=234;
  for(let p=0;p<d.length;p+=4){const m=Math.min(d[p],d[p+1],d[p+2]);d[p+3]=m<=lo?255:m>=lo+16?0:Math.round(255*(lo+16-m)/16)}
  g.putImageData(im,0,0);
}
function redrawAll(){lines.forEach(o=>{if(o.vis)draw(o);else o.stale=true})}
/* now and then, without warning, a letter somewhere on screen is cut again from another place it was read.
   It keeps to the sign's position on the slope, so prohibitions stay noise and personal notes stay clear. */
const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
/* now and then, without warning, a scanned letter is taken again from the closest spots on the same print where that letter was printed.
   A common letter stays its colour; a rare one may come from far away in another colour, so the signs slowly stain:
   the same letter, about the same colour, a different piece of the city. */
/* the stains grow with time: one swap in ten at first, every swap after STAIN_MIN minutes on the page, when the colours are all mixed up */
const NEARBY={},STAIN=.1,STAIN_MIN=5,T0=performance.now();
const stain=()=>Math.min(1,STAIN+(1-STAIN)*(performance.now()-T0)/(STAIN_MIN*60000));
function nearby(c){if(NEARBY[c])return NEARBY[c];const r=RR[c];
  return NEARBY[c]=(RG[RK[c]]||[]).map(([i])=>i).filter(i=>i!==c&&RR[i][0]===r[0]).sort((a,b)=>Math.hypot(RR[a][1]-r[1],RR[a][2]-r[2])-Math.hypot(RR[b][1]-r[1],RR[b][2]-r[2])).slice(0,6)}
function swapNear(){
  const seen=lines.filter(o=>o.vis&&o.riso&&!o.sign.matches(':hover')&&!o.sign.classList.contains('open'));if(!seen.length)return;
  const o=seen[Math.floor(Math.random()*seen.length)],ws=o.words.filter(w=>w.orig&&w.orig.length);if(!ws.length)return;
  const wd=ws[Math.floor(Math.random()*ws.length)],n=Math.floor(Math.random()*wd.orig.length);
  /* a stain: the same letter from anywhere on the three prints, in whatever colour it was printed, and it stays */
  const c=Math.random()<stain()?(RG[RK[wd.orig[n]]]||[]).map(([i])=>i):[wd.orig[n],...nearby(wd.orig[n])];if(!c.length)return;
  wd.cur[n]=c[Math.floor(Math.random()*c.length)];draw(o);
}
function tickNear(){if(!document.hidden){swapNear();if(Math.random()<.4)swapNear()}setTimeout(tickNear,40+Math.random()*Math.random()*500)}
function swapLetter(){
  const seen=lines.filter(o=>o.vis&&o.words.length&&!o.sign.matches(':hover')&&!o.sign.classList.contains('open'));
  if(!seen.length)return;
  const o=seen[Math.floor(Math.random()*seen.length)];
  const wd=o.words[Math.floor(Math.random()*o.words.length)];if(!wd.picks||!wd.picks.length)return;
  const chars=[...wd.w].filter(ch=>glyph(ch));if(chars.length!==wd.picks.length)return;
  const k=Math.floor(Math.random()*chars.length),nw=one(chars[k],o);if(!nw)return;
  wd.picks[k]=nw;
  draw(o);
}
function tick(){if(!document.hidden){swapLetter();if(Math.random()<.3)swapLetter()}setTimeout(tick,40+Math.random()*Math.random()*900)}
const io=new IntersectionObserver(es=>es.forEach(e=>{const o=e.target._o;o.vis=e.isIntersecting;if(o.vis&&o.stale)draw(o)}),{rootMargin:'400px 0px'});
/* controls */
const sh=document.getElementById('shuffle'),th=document.getElementById('th'),thv=document.getElementById('thv');
sh.addEventListener('click',()=>{lines.forEach(o=>{if(!o.riso)pick(o);draw(o)})});
let pend=0;
let ready=false;
function setTh(){thr=+th.value;thv.textContent=thr.toFixed(2);if(!ready)return;cancelAnimationFrame(pend);pend=requestAnimationFrame(redrawAll)}
th.addEventListener('input',setTh);
/* the controls stay hidden; press C to show or hide them */
const ctl=document.getElementById('controls');
document.addEventListener('keydown',e=>{if(e.target.closest&&e.target.closest('input'))return;if((e.key==='c'||e.key==='C')&&!e.metaKey&&!e.ctrlKey&&!e.altKey){ctl.hidden=!ctl.hidden}});
/* the letters live on a few sheets; the page starts once every sheet has arrived */
let left=V.reduce((a,v)=>a+v.files.length,0)+RS.length;
/* ?mix opens the page as it looks after a long time: every scanned letter already taken from anywhere on the three prints */
const MIX=new URLSearchParams(location.search).has('mix');
function mixAll(){lines.forEach(o=>{if(!o.riso)return;let j=0;o.words.forEach(wd=>{const has=[...wd.w].some(ch=>glyph(ch));
  if(!wd.orig){wd.orig=has?(o.riso[j]||[]):[];wd.cur=wd.orig.slice()}if(has)j++;
  wd.cur=wd.orig.map(c=>{const l=RG[RK[c]]||[];return l.length?l[Math.floor(Math.random()*l.length)][0]:c})})})}
const start=()=>{if(--left)return;ready=true;setTh();if(MIX)mixAll();lines.forEach(o=>{draw(o);o.el._o=o;io.observe(o.el)});if(!reduceMotion&&RS.length)setTimeout(tickNear,800)};
const load=f=>{const im=new Image();im.onload=start;im.onerror=start;im.src='letters/'+f;return im};
V.forEach(v=>{v.imgs=v.files.map(load)});RS.forEach(sh=>{sh.img=load(sh.file)});
})();
