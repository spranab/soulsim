#!/usr/bin/env python3
"""The translator-ladder dashboard: one page, live or static.

    python3 ladder_dashboard.py [ladder/results.json] [ladder/dashboard.html]   # static snapshot
    python3 ladder_server.py                                                    # live, polls every 3 s

The page inlines the results it was built with, then keeps polling
`results.json` (and the runner's `log`) from wherever it is served; when the
`updated` stamp changes it redraws in place, keeping your chapter and writer
selections. On a static host the polls fail quietly and the inlined snapshot
stands. No library, no network beyond the page's own origin.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

TEMPLATE = r"""<title>The Translator Ladder</title>
<style>
:root { color-scheme: light;
  --bg:#f3f2f6; --s1:#fbfbfd; --s2:#edecf2; --border:#e0dfe8; --bstrong:#cfced9;
  --ink:#12111a; --sec:#565467; --muted:#86849a; --muted2:#a3a1b5;
  --accent:#d1541f; --good:#0a7d3e; --warn:#b3780a; --bad:#c03a38;
  --grid:rgba(18,17,26,0.08);
  --english:#2a78d6; --compact:#eb6834;
  --sup:#2a78d6; --tex:#9ec5f4; --uns:#ec835a; --con:#d03b3b;
  --disp:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,ui-serif,serif;
  --body:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  color-scheme: dark;
  --bg:#0d0d14; --s1:#16161f; --s2:#1d1d28; --border:#2a2a37; --bstrong:#3a3a49;
  --ink:#f4f3fa; --sec:#b6b4c6; --muted:#7d7b90; --muted2:#6a6880;
  --accent:#f0793a; --good:#3fae6c; --warn:#e0a63a; --bad:#e66767;
  --grid:rgba(255,255,255,0.08);
  --english:#3987e5; --compact:#d95926;
  --sup:#3987e5; --tex:#6da7ec; --uns:#ec835a; --con:#d03b3b; } }
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg:#0d0d14; --s1:#16161f; --s2:#1d1d28; --border:#2a2a37; --bstrong:#3a3a49;
  --ink:#f4f3fa; --sec:#b6b4c6; --muted:#7d7b90; --muted2:#6a6880;
  --accent:#f0793a; --good:#3fae6c; --warn:#e0a63a; --bad:#e66767;
  --grid:rgba(255,255,255,0.08);
  --english:#3987e5; --compact:#d95926;
  --sup:#3987e5; --tex:#6da7ec; --uns:#ec835a; --con:#d03b3b; }
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1100px;margin:0 auto;padding-block:40px 80px;padding-inline:20px}
header{border-bottom:1px solid var(--border);padding-bottom:22px;margin-bottom:26px}
.kicker{font-family:var(--mono);font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin:0 0 10px}
h1{font-family:var(--disp);font-weight:600;font-size:clamp(2rem,4.6vw,2.9rem);margin:0;line-height:1.05;text-wrap:balance}
.thesis{color:var(--sec);max-width:64ch;margin:14px 0 0;font-size:1.02rem;text-wrap:pretty}
.facts{display:flex;flex-wrap:wrap;gap:8px 18px;margin:18px 0 0;font-family:var(--mono);font-size:.76rem;color:var(--muted);align-items:center}
.facts b{color:var(--sec);font-weight:500}
.status{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:.74rem;letter-spacing:.06em;text-transform:uppercase;padding:4px 11px;border-radius:999px;border:1px solid var(--bstrong);color:var(--sec)}
.status .dot{width:8px;height:8px;border-radius:50%;background:var(--muted2)}
.status.running .dot{background:var(--warn);animation:pulse 1.6s ease-in-out infinite}
.status.done .dot{background:var(--good)}
.status.live{border-color:var(--good);color:var(--good)}
@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
@media(prefers-reduced-motion:reduce){.status.running .dot{animation:none}}
h2{font-family:var(--disp);font-weight:600;font-size:1.35rem;margin:38px 0 6px}
p.sub{color:var(--sec);margin:0 0 14px;max-width:70ch}
.card{background:var(--s1);border:1px solid var(--border);border-radius:12px;padding:16px 18px}
.row3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:820px){.row3{grid-template-columns:1fr}}
.card h3{font-family:var(--body);font-weight:600;font-size:.92rem;margin:0 0 2px}
.card .note{color:var(--muted);font-size:.78rem;margin:0 0 10px}
svg.chart{display:block;width:100%;height:auto}
svg.chart text{font-family:var(--mono);font-size:10.5px;fill:var(--muted)}
svg.chart .ax{stroke:var(--grid);stroke-width:1}
svg.chart .lbl{fill:var(--sec)}
svg.chart .lbl.strong{fill:var(--ink);font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:10px 0 0;font-family:var(--mono);font-size:.74rem;color:var(--sec)}
.legend .sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:6px}
.legend .sw.line{height:3px;border-radius:2px;vertical-align:2px}
table{border-collapse:collapse;width:100%;font-size:.84rem;font-variant-numeric:tabular-nums}
.tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px;background:var(--s1)}
th,td{padding:9px 11px;border-bottom:1px solid var(--border);text-align:right;white-space:nowrap}
th{font-family:var(--mono);font-weight:500;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);background:var(--s2)}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
tr:last-child td{border-bottom:none}
td.dim{color:var(--muted)}
.pill{display:inline-block;font-family:var(--mono);font-size:.66rem;letter-spacing:.07em;text-transform:uppercase;padding:2px 9px;border-radius:999px;border:1px solid var(--bstrong);color:var(--sec)}
.pill.go{color:var(--good);border-color:var(--good)}
.pill.nogo{color:var(--bad);border-color:var(--bad)}
.pill.ref{color:var(--accent);border-color:var(--accent)}
.pill.running{color:var(--warn);border-color:var(--warn)}
.swatch{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:7px;vertical-align:0}
.read{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.read{grid-template-columns:1fr}}
.read .card{font-family:var(--disp);font-size:1rem;line-height:1.6}
.read .card .who{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.read .card .who b{color:var(--sec);font-weight:500}
.read mark{background:transparent;border-bottom:2px solid var(--uns);color:inherit;padding:0}
.read mark.con{border-bottom-color:var(--con)}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 12px;align-items:center;font-size:.84rem;color:var(--sec)}
select{font:inherit;font-size:.84rem;color:var(--ink);background:var(--s1);border:1px solid var(--bstrong);border-radius:8px;padding:5px 9px;max-width:100%}
select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
details{border:1px solid var(--border);border-radius:12px;background:var(--s1);padding:0 16px;margin:0 0 10px}
summary{cursor:pointer;padding:12px 0;font-weight:600;font-size:.92rem}
summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
details table{margin:0 0 14px}
.empty{color:var(--muted);font-family:var(--mono);font-size:.8rem;padding:24px;text-align:center}
pre.log{margin:0;background:var(--s2);border:1px solid var(--border);border-radius:12px;padding:12px 14px;font-family:var(--mono);font-size:.74rem;line-height:1.5;color:var(--sec);max-height:220px;overflow:auto;white-space:pre-wrap}
footer{margin-top:44px;color:var(--muted);font-size:.74rem;font-family:var(--mono)}
</style>
<div class="wrap">
<header>
  <p class="kicker">soulsim · the translator ladder</p>
  <h1>How small can a writer be when the world supplies the facts?</h1>
  <p class="thesis">The same chapters, the same fact-sheets, the same judge. Only the writer shrinks. Every sentence is graded against a world with a complete record, so the score needs no human. The bet: the model's job is style, and style is cheap.</p>
  <div class="facts" id="facts"></div>
</header>

<h2>Grounded quality by model size</h2>
<p class="sub">Quality = share of sentences the judge found supported or texture × must-say facts kept × lint pass rate. A rung passes if it holds within five points of the largest writer on the same notation.</p>
<div class="card"><svg class="chart" id="hero" viewBox="0 0 900 340" role="img" aria-label="grounded quality against model size, English and compact notation"></svg>
<div class="legend"><span><span class="sw line" style="background:var(--english)"></span>English fact-sheets</span><span><span class="sw line" style="background:var(--compact)"></span>Compact notation</span><span><span class="sw line" style="background:var(--muted2)"></span>go/no-go floor</span></div></div>

<div class="row3" style="margin-top:14px">
  <div class="card"><h3>Seconds per chapter</h3><p class="note">Wall time for the writer's calls, retries included.</p><svg class="chart" id="secs" viewBox="0 0 320 250"></svg></div>
  <div class="card"><h3>Prompt tokens per chapter</h3><p class="note">What the writer had to read on its first attempt (retries count as cost, not here).</p><svg class="chart" id="toks" viewBox="0 0 320 250"></svg></div>
  <div class="card"><h3>What the judge saw</h3><p class="note">Every sentence, before any repair.</p><svg class="chart" id="verd" viewBox="0 0 320 250"></svg>
  <div class="legend"><span><span class="sw" style="background:var(--sup)"></span>supported</span><span><span class="sw" style="background:var(--tex)"></span>texture</span><span><span class="sw" style="background:var(--uns)"></span>unsupported</span><span><span class="sw" style="background:var(--con)"></span>contradicted</span></div></div>
</div>

<h2>The rungs</h2>
<p class="sub">Efficiency = quality ÷ (seconds per chapter × gigabytes). The reference rung is the largest writer on English fact-sheets.</p>
<div class="tablewrap"><table id="rungs"></table></div>

<h2>The runner, right now</h2>
<pre class="log" id="log">no log yet</pre>

<h2>Read the difference</h2>
<p class="sub">The same chapter from two writers. Underlined sentences are what the judge flagged: orange unsupported, red contradicted.</p>
<div class="controls">
  <label for="chapsel">Chapter</label><select id="chapsel"></select>
  <label for="leftsel">Left</label><select id="leftsel"></select>
  <label for="rightsel">Right</label><select id="rightsel"></select>
</div>
<div class="read" id="read"></div>

<h2>Every chapter, every rung</h2>
<div id="detail"></div>

<footer id="foot"></footer>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const LIVE = __LIVE__;
const NS='http://www.w3.org/2000/svg';
const fmt = (x, d=2) => (x==null||isNaN(x)) ? '—' : Number(x).toFixed(d);
const pct = x => (x==null||isNaN(x)) ? '—' : (100*x).toFixed(0)+'%';
const short = w => w.replace('qwen','q').replace(':','·');
function el(t,a,txt){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e;}
function title(e,t){e.appendChild(el('title',{},t));return e;}
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function clear(id){const n=document.getElementById(id); while(n.firstChild) n.removeChild(n.firstChild); return n;}

function render(D){
  const rungs = D.rungs || [];
  const done = rungs.filter(r => r.status==='done' && r.summary && r.summary.sentences>0);
  const withData = rungs.filter(r => r.summary && (r.chapters_done||0)>0);
  const topOf = itf => done.filter(r=>r.interface===itf).sort((a,b)=>b.size_gb-a.size_gb)[0] || null;
  const ref = topOf('english');
  const floorOf = itf => { const t=topOf(itf); return t ? t.summary.quality-0.05 : null; };
  function verdict(r){ if(!r.summary||!(r.chapters_done>0)) return '<span class="pill">queued</span>';
    if(r.status!=='done') return '<span class="pill running">running</span>';
    const top=topOf(r.interface); if(top&&top.id===r.id) return '<span class="pill ref">reference</span>';
    const f=floorOf(r.interface); if(f==null) return '<span class="pill">—</span>';
    return r.summary.quality>=f ? '<span class="pill go">go</span>' : '<span class="pill nogo">no-go</span>'; }

  // facts
  { const b=D.benchmark||{}; const running=rungs.find(r=>r.status==='running'); const nDone=rungs.filter(r=>r.status==='done').length;
    const chDone=rungs.reduce((s,r)=>s+(r.chapters_done||0),0), chAll=rungs.length*(b.chapters||0);
    const st = running ? 'running' : (nDone===rungs.length&&rungs.length? 'done':'queued');
    document.getElementById('facts').innerHTML =
     `<span class="status ${st}"><span class="dot"></span>${st==='running'?('rung '+(nDone+1)+' of '+rungs.length+' · '+chDone+' of '+chAll+' chapters'):(st==='done'?'all '+rungs.length+' rungs done':'queued · '+rungs.length+' rungs')}</span>`+
     (LIVE?'<span class="status live"><span class="dot" style="background:var(--good)"></span>live · polls every 3 s</span>':'')+
     `<span><b>seed</b> ${b.seed} · ${b.years} years</span><span><b>chapters</b> ${b.chapters} from ${(b.genres||[]).join(', ')}</span><span><b>judge</b> ${b.judge||'—'}</span><span><b>machine</b> ${b.machine||'—'}</span><span><b>updated</b> ${(D.updated||'').replace('T',' ').slice(0,16)}</span>`;
    document.getElementById('foot').textContent = 'ladder.py · '+(LIVE?'served live by ladder_server.py':'results.json inlined; regenerate with ladder_dashboard.py')+' · every chapter graded by the judge against the Annals of seed '+b.seed; }

  // hero
  { const svg=clear('hero'); const W=900,H=340,L=56,R=30,T=18,B=48;
    if(!withData.length){svg.appendChild(el('text',{x:W/2,y:H/2,'text-anchor':'middle',class:'lbl'},'no chapters rendered yet — the first rung starts with the largest writer'));}
    else {
    const sizes=rungs.map(r=>r.size_gb).filter(Boolean); const xmin=Math.log10(Math.min(...sizes)/1.6), xmax=Math.log10(Math.max(...sizes)*1.6);
    const X=g=>L+(Math.log10(g)-xmin)/(xmax-xmin)*(W-L-R); const Y=q=>T+(1-q)*(H-T-B);
    for(const q of [0,0.25,0.5,0.75,1]){svg.appendChild(el('line',{x1:L,y1:Y(q),x2:W-R,y2:Y(q),class:'ax'}));svg.appendChild(el('text',{x:L-8,y:Y(q)+3.5,'text-anchor':'end'},q.toFixed(2)));}
    const byWriter={}; rungs.forEach(r=>{if(r.size_gb)byWriter[r.writer]=r.size_gb;});
    Object.entries(byWriter).forEach(([w,g])=>{svg.appendChild(el('text',{x:X(g),y:H-B+18,'text-anchor':'middle',class:'lbl'},short(w)));svg.appendChild(el('text',{x:X(g),y:H-B+32,'text-anchor':'middle'},g+' GB'));});
    svg.appendChild(el('text',{x:L,y:H-4,class:'lbl'},'model size, log scale →'));
    svg.appendChild(el('text',{x:14,y:T+10,class:'lbl'},'quality'));
    for(const itf of ['english','compact']){ const f=floorOf(itf); if(f!=null){svg.appendChild(el('line',{x1:L,y1:Y(f),x2:W-R,y2:Y(f),stroke:'var(--muted2)','stroke-width':1}));svg.appendChild(el('text',{x:W-R,y:Y(f)-5,'text-anchor':'end'},'floor · '+itf+' · '+f.toFixed(2)));}}
    for(const itf of ['english','compact']){ const pts=withData.filter(r=>r.interface===itf).sort((a,b)=>a.size_gb-b.size_gb); if(!pts.length)continue;
      const col=`var(--${itf})`;
      if(pts.length>1) svg.appendChild(el('path',{d:pts.map((r,i)=>(i?'L':'M')+X(r.size_gb)+' '+Y(r.summary.quality)).join(' '),fill:'none',stroke:col,'stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'}));
      pts.forEach(r=>{ const partial=r.status!=='done'; const c=el('circle',{cx:X(r.size_gb),cy:Y(r.summary.quality),r:5.5,fill:partial?'var(--s1)':col,stroke:partial?col:'var(--s1)','stroke-width':2});
        title(c,`${r.writer} · ${itf}${partial?' (partial, '+r.chapters_done+' ch)':''}\nquality ${fmt(r.summary.quality)} · grounded ${pct(r.summary.grounded_rate)} · ${fmt(r.summary.seconds_per_chapter,0)} s/ch`); svg.appendChild(c);});
      const last=pts[pts.length-1]; svg.appendChild(el('text',{x:X(last.size_gb)+10,y:Y(last.summary.quality)+4,class:'lbl strong'},itf==='english'?'English':'compact'));
    } } }

  // small bars
  function barsBy(svgId, key, digits, unit){ const svg=clear(svgId); const W=320,H=250,L=8,R=40,T=8;
    const rs=withData.slice().sort((a,b)=>b.size_gb-a.size_gb||a.interface.localeCompare(b.interface)); if(!rs.length){svg.appendChild(el('text',{x:W/2,y:H/2,'text-anchor':'middle'},'waiting for the first rung'));return;}
    const max=Math.max(...rs.map(r=>r.summary[key]||0))||1; const band=Math.min(26,(H-T-8)/rs.length); const bh=Math.min(16,band-6);
    rs.forEach((r,i)=>{ const y=T+i*band; const w=(r.summary[key]||0)/max*(W-L-R-118);
      svg.appendChild(el('text',{x:L,y:y+bh-3,class:'lbl'},short(r.writer)+' '+(r.interface==='english'?'en':'cp')));
      const b=el('rect',{x:L+112,y:y,width:Math.max(w,2),height:bh,rx:4,fill:`var(--${r.interface})`}); title(b,`${r.writer} · ${r.interface}: ${fmt(r.summary[key],digits)} ${unit}`); svg.appendChild(b);
      svg.appendChild(el('text',{x:L+112+Math.max(w,2)+6,y:y+bh-3},fmt(r.summary[key],digits))); }); }
  barsBy('secs','seconds_per_chapter',0,'s');
  barsBy('toks', withData.some(r=>r.summary.prompt_tokens_first_per_chapter!=null) ? 'prompt_tokens_first_per_chapter' : 'prompt_tokens_per_chapter', 0, 'tokens');
  { const svg=clear('verd'); const W=320,H=250,L=8,T=8;
    const rs=withData.slice().sort((a,b)=>b.size_gb-a.size_gb||a.interface.localeCompare(b.interface)); if(!rs.length){svg.appendChild(el('text',{x:W/2,y:H/2,'text-anchor':'middle'},'waiting for the first rung'));}
    else { const band=Math.min(26,(H-T-8)/rs.length); const bh=Math.min(16,band-6); const x0=L+112, span=W-x0-8;
    rs.forEach((r,i)=>{ const y=T+i*band; const s=r.summary; const n=s.sentences||1; let x=x0;
      svg.appendChild(el('text',{x:L,y:y+bh-3,class:'lbl'},short(r.writer)+' '+(r.interface==='english'?'en':'cp')));
      [['supported','sup'],['texture','tex'],['unsupported','uns'],['contradicted','con']].forEach(([k,v])=>{ const w=(s[k]||0)/n*span; if(w<=0)return; const seg=el('rect',{x:x,y:y,width:Math.max(w-2,0.5),height:bh,fill:`var(--${v})`}); title(seg,`${r.writer} · ${r.interface}: ${k} ${s[k]} of ${n} (${pct((s[k]||0)/n)})`); svg.appendChild(seg); x+=w; }); }); } }

  // rung table
  { const t=document.getElementById('rungs'); const cols=['writer','notation','size GB','status','ch','s / ch','read tok','cost tok','gen tok','tok/s','lint first','grounded','kept','quality','efficiency','verdict'];
    let h='<thead><tr>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>';
    rungs.forEach(r=>{ const s=r.summary||{}; h+=`<tr><td><span class="swatch" style="background:var(--${r.interface})"></span>${r.writer}</td><td class="dim">${r.interface}</td><td>${r.size_gb??'—'}</td><td class="dim">${r.status}</td><td>${r.chapters_done||0}</td><td>${fmt(s.seconds_per_chapter,0)}</td><td>${fmt(s.prompt_tokens_first_per_chapter??s.prompt_tokens_per_chapter,0)}</td><td>${fmt(s.prompt_tokens_per_chapter,0)}</td><td>${fmt(s.gen_tokens_per_chapter,0)}</td><td>${fmt(s.gen_tps,0)}</td><td>${pct(s.lint_first_pass_rate)}</td><td>${pct(s.grounded_rate)}</td><td>${pct(s.coverage)}</td><td><b>${fmt(s.quality)}</b></td><td>${fmt(s.efficiency,4)}</td><td>${verdict(r)}</td></tr>`; });
    t.innerHTML = rungs.length ? h+'</tbody>' : '<tr><td class="empty">no rungs planned</td></tr>'; }

  // read the difference (keep selections across redraws)
  { const chap=document.getElementById('chapsel'), ls=document.getElementById('leftsel'), rs=document.getElementById('rightsel'), out=document.getElementById('read');
    const prev={c:chap.value,l:ls.value,r:rs.value};
    if(!withData.length){out.innerHTML='<div class="card empty">nothing rendered yet</div>';}
    else {
    const heads=[]; withData.forEach(r=>r.per_chapter.forEach(c=>{if(!heads.includes(c.heading))heads.push(c.heading);}));
    chap.innerHTML=heads.map(h=>`<option>${esc(h)}</option>`).join('');
    const opts=withData.map(r=>`<option value="${r.id}">${r.writer} · ${r.interface}</option>`).join(''); ls.innerHTML=opts; rs.innerHTML=opts;
    const ids=withData.map(r=>r.id);
    chap.value = heads.includes(prev.c) ? prev.c : heads[0];
    ls.value = ids.includes(prev.l) ? prev.l : (ref||withData[0]).id;
    const smallest=withData.slice().sort((a,b)=>a.size_gb-b.size_gb)[0]; rs.value = ids.includes(prev.r) ? prev.r : smallest.id;
    const draw=()=>{ out.innerHTML=[ls.value,rs.value].map(id=>{ const r=withData.find(x=>x.id===id); const c=r&&r.per_chapter.find(x=>x.heading===chap.value);
        if(!c) return `<div class="card"><p class="who"><b>${r?r.writer:'?'}</b> · ${r?r.interface:''}</p><p class="empty">not rendered yet</p></div>`;
        let text=esc(c.text||''); (c.flags||[]).forEach(f=>{ const s=esc(f.sentence||''); if(s&&text.includes(s)) text=text.replace(s,`<mark class="${f.verdict==='CONTRADICTED'?'con':''}" title="${esc(f.why||'')}">${s}</mark>`); });
        return `<div class="card"><p class="who"><b>${r.writer}</b> · ${r.interface} · ${fmt(c.seconds,0)} s · ${c.words} words · ${(c.unsupported||0)+(c.contradicted||0)} flagged of ${c.sentences} · lint ${c.lint_ok?'pass':'fail'}</p>${text.split(/\n\n+/).map(p=>'<p>'+p.replace(/\n/g,'<br>')+'</p>').join('')}</div>`; }).join(''); };
    if(!chap._wired){[chap,ls,rs].forEach(s=>s.addEventListener('change',draw)); chap._wired=true; chap._draw=draw;}
    chap._draw=draw; draw(); } }

  // detail
  { const d=document.getElementById('detail'); const open=new Set([...d.querySelectorAll('details[open]')].map(x=>x.dataset.id));
    if(!withData.length){d.innerHTML='<div class="empty">no chapters yet</div>';}
    else d.innerHTML=withData.map(r=>`<details data-id="${r.id}"${open.has(r.id)?' open':''}><summary>${r.writer} · ${r.interface} · ${r.chapters_done} chapters${r.status==='done'?'':' (running)'}</summary><div class="tablewrap" style="border:none"><table><thead><tr><th>genre</th><th>chapter</th><th>s</th><th>tries</th><th>prompt</th><th>gen</th><th>lint</th><th>kept</th><th>sent.</th><th>uns.</th><th>con.</th><th>flags</th></tr></thead><tbody>${r.per_chapter.map(c=>`<tr><td class="dim">${c.genre}</td><td>${esc(c.heading)}</td><td>${fmt(c.seconds,0)}</td><td>${c.attempts}</td><td>${c.prompt_tokens}</td><td>${c.gen_tokens}</td><td>${c.lint_ok?'pass':'fail'}</td><td>${pct(c.coverage)}</td><td>${c.sentences}</td><td>${c.unsupported}</td><td>${c.contradicted}</td><td style="white-space:normal;text-align:left;max-width:360px;color:var(--muted)">${(c.flags||[]).slice(0,3).map(f=>esc(f.why||'')).join(' · ')}</td></tr>`).join('')}</tbody></table></div></details>`).join(''); }
}

// boot: inlined snapshot first, then keep polling wherever the page is served from
let current = JSON.parse(document.getElementById('data').textContent);
render(current);
async function poll(){
  try { const r = await fetch('results.json?t='+Date.now(), {cache:'no-store'}); if(r.ok){ const d = await r.json(); if(d && d.updated !== current.updated){ current = d; render(current); } } } catch(e) {}
  try { const r = await fetch('log?t='+Date.now(), {cache:'no-store'}); if(r.ok){ const t = await r.text(); const box=document.getElementById('log'); if(box.textContent!==t){ box.textContent=t||'no log yet'; box.scrollTop=box.scrollHeight; } } } catch(e) {}
}
if(LIVE){ poll(); setInterval(poll, 3000); }
</script>
"""


def build_html(data: dict, live: bool = False) -> str:
    return (TEMPLATE.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
            .replace("__LIVE__", "true" if live else "false"))


def plan_only(writers: str, interfaces: str) -> dict:
    return {"benchmark": {"seed": 11, "years": 500, "genres": ["epic", "novel", "tales"],
                          "chapters": 12, "judge": "qwen3.6:35b", "machine": "Apple M4 Pro, 48 GB"},
            "rungs": [{"id": f"{w}|{i}", "writer": w, "interface": i, "size_gb": None,
                       "status": "queued", "chapters_done": 0, "per_chapter": [], "summary": None}
                      for i in interfaces.split(",") for w in writers.split(",")],
            "updated": dt.datetime.now().isoformat(timespec="minutes")}


def load_results(path: str, writers: str, interfaces: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except ValueError:
            pass   # mid-write; the caller keeps its last good copy
    return plan_only(writers, interfaces)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", default="ladder/results.json")
    ap.add_argument("out", nargs="?", default="ladder/dashboard.html")
    ap.add_argument("--writers", default="qwen3.6:35b,qwen3.5:9b,qwen3.5:4b,qwen2.5:1.5b")
    ap.add_argument("--interfaces", default="english,compact")
    args = ap.parse_args()
    data = load_results(args.results, args.writers, args.interfaces)
    html = build_html(data, live=False)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(html)
    n = sum(r.get("chapters_done", 0) for r in data.get("rungs", []))
    print(f"wrote {args.out}: {len(data.get('rungs', []))} rungs, {n} chapters, {len(html) // 1024} KB")


if __name__ == "__main__":
    main()
