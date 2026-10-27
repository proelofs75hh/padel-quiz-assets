"""Render a Fair or Fault quiz reel (1080 x 1920, silent H.264 MP4) plus a cover PNG.

Usage:  python3 engine/reel.py <reel.json> <out.mp4>

Common fields:
  format   "refs_view" | "three_second_call" | "guess_number"
  label    Rules | Gear | Market            (rendered as "Padel <label>")
  claim    the statement (same language rules as the carousels, < 10 words)
  verdict  FAIR | FAULT
  pill     2-3 words on the verdict pill
  line     reason, "\\n" = line break, **word** = highlight
Format-specific:
  refs_view          diagram: key of engine/diagrams.py LIB
  three_second_call  -
  checklist          rows: [[label, value, ok], ...] -> rows appear slowly with ✓ (ok) / ✕
  compare            cols: [a, b], rows: [[label, value_a, value_b], ...] (side-by-side table)
  spec_sheet         rows: [[label, value], ...] (value "?" = the open question), racket outline
  guess_number       number (float), marker (the claim's value), decimals (int, default 0),
                     unit (text under the number), marker_label (default "the claim")

Shared timeline: intro "Fair or Fault / Your Daily Padel Quiz" (2.5 s) -> statement word by word (0.32 s per word) -> 0.7 s gap -> "Fair or fault?" ->
1.6 s reading pause -> question moves up, the middle part fades in ->
middle part (ball path / 3-2-1 ball timer / counting number) -> verdict, reason,
comment prompt -> 0.4 s fade to the empty opening frame (seamless loop).
Key text stays clear of Instagram's overlays (top 250 px, bottom 420 px).
"""
import asyncio, html, json, pathlib, re, subprocess, sys, tempfile

from playwright.async_api import async_playwright

ENGINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
import diagrams  # noqa: E402

FONTS = ENGINE / "fonts"
FPS = 30
C = diagrams.C
# Theme palettes. "light" (white video, default since 27.10.) and "dark" (blue/night, original).
THEMES = {
    "light": dict(bg=C["paper"], bg2=C["paper"], fg=C["night"], acc=C["court"], muted=C["muted"],
                  line="rgba(14,22,48,.18)", fair_word=C["court"], fault_word=C["fault"], intro_f=C["court"]),
    "dark": dict(bg=C["court"], bg2=C["night"], fg=C["paper"], acc=C["ball"], muted=C["glass"],
                 line="rgba(244,241,232,.3)", fair_word=C["ball"], fault_word=C["paper"], intro_f=C["ball"]),
}
T = THEMES["light"]
INTRO, WORD, CALL_LEN, FADE, ASK_GAP = 2.5, 0.32, 3.4, 0.4, 0.7
COVER_BADGE = True  # play badge on the white cover
TRANS = 0.5  # extra pause question -> proof and proof -> answer
MID_LEN = {"refs_view": 2.6, "three_second_call": 3.2, "guess_number": 3.0, "spec_sheet": 3.4, "compare": 3.6}
CHECK_STEP = 1.3  # checklist: seconds between rows


def mid_len(spec):
    if spec["format"] in ("checklist", "compare"):
        return 0.4 + len(spec["rows"]) * CHECK_STEP + 0.4
    return MID_LEN[spec["format"]]


def fmt(t, cls="hl"):
    t = html.escape(t or "")
    t = re.sub(r"\*\*(.+?)\*\*", rf'<span class="{cls}">\1</span>', t)
    return t.replace("\n", "<br>")


def words(t):
    return " ".join(f'<span class="w">{html.escape(w)}</span>' for w in t.split())


def timeline(spec):
    nw = len(spec["claim"].split())
    # "Fair or fault?" starts ASK_GAP after the last word is fully visible
    t_ask = INTRO + 0.3 + (nw - 1) * WORD + 0.25 + ASK_GAP
    t_read = t_ask + 0.35 + 1.6
    t_mid = t_read + 0.4 + TRANS
    t_call = t_mid + mid_len(spec) + TRANS
    return dict(T_ASK=t_ask, T_READ=t_read, T_MID=t_mid, T_CALL=t_call,
                T_END=t_call + CALL_LEN + FADE)


# ---------------------------------------------------------------- middle parts
def mid_refs_view(spec):
    d = diagrams.LIB[spec["diagram"]]
    vcol = C["ball"] if spec["verdict"].upper() == "FAIR" else C["fault"]
    if spec.get("ring") == "neutral":  # decisive point shows the correct play, not the fault
        vcol = C["ball"]
    players = "".join(f'<circle cx="{x}" cy="{y}" r="12" fill="{C["night"]}" stroke="#FFF" stroke-width="3"/>'
                      for x, y in d.get("players", []))
    inner = f'''{players}
  <polyline id="trail" fill="none" stroke="{C['ball']}" stroke-width="6" stroke-dasharray="12 8" points=""/>
  <g id="bncs"></g>
  <circle id="hit" r="0" fill="none" stroke="{vcol}" stroke-width="6"/>
  <circle id="ball" r="11" fill="{C['ball']}" stroke="{C['night']}" stroke-width="3"/>'''
    svg = diagrams.court_svg(inner, 520, 946, floor="#1E56C8", el_id="mid")
    js = f"""
const P={json.dumps(d['points'])}, BOUNCES={json.dumps(d['bounces'])}, DEC={d['decisive']};
const L=[0]; for(let i=1;i<P.length;i++) L.push(L[i-1]+Math.hypot(P[i][0]-P[i-1][0],P[i][1]-P[i-1][1]));
const TOT=L[L.length-1];
function at(k){{ const d=k*TOT; let i=1; while(i<L.length-1&&L[i]<d) i++;
  const f=(d-L[i-1])/(L[i]-L[i-1]||1); return [lerp(P[i-1][0],P[i][0],f), lerp(P[i-1][1],P[i][1],f), i]; }}
function mid(t){{
  const k=ease(clamp((t-T_MID)/1.8)); const [x,y,i]=at(k);
  $('ball').setAttribute('cx',x); $('ball').setAttribute('cy',y);
  const tr=P.slice(0,i).concat([[x,y]]); $('trail').setAttribute('points', k>0? tr.map(p=>p.join(',')).join(' '):'');
  $('bncs').innerHTML = BOUNCES.filter(b=>i>b || k>=1).map(b=>`<circle cx="${{P[b][0]}}" cy="${{P[b][1]}}" r="16" fill="none" stroke="{C['ball']}" stroke-width="5"/>`).join('');
  const r = t>T_MID+1.8 ? 16+26*clamp((t-T_MID-1.8)/0.4) : 0;
  $('hit').setAttribute('cx',P[DEC][0]); $('hit').setAttribute('cy',P[DEC][1]); $('hit').setAttribute('r',r);
  const dt=t-T_MID, n= dt<0?0: dt<0.8?3: dt<1.6?2: dt<2.4?1:0;
  $('count').textContent=n||''; $('count').style.opacity = n? 1:0;
}}"""
    css = "#mid{position:absolute;left:50%;transform:translateX(-50%)}"
    return svg, css, js


def mid_three_second_call(spec):
    R = 230
    circ = 2 * 3.14159 * (R + 34)
    svg = f'''<svg id="mid" viewBox="-300 -300 600 600" width="600" height="600">
  <circle r="{R+34}" fill="none" stroke="{T['line']}" stroke-width="22"/>
  <circle id="arc" r="{R+34}" fill="none" stroke="{T['acc']}" stroke-width="22" stroke-linecap="round"
          transform="rotate(-90)" stroke-dasharray="{circ:.1f}" stroke-dashoffset="0"/>
  <circle r="{R}" fill="{C['ball']}"/>
  <path d="M{-R*0.92:.0f} {-R*0.38:.0f} C {-R*0.35:.0f} {-R*0.05:.0f}, {-R*0.35:.0f} {R*0.05:.0f}, {-R*0.92:.0f} {R*0.38:.0f}" fill="none" stroke="{C['paper']}" stroke-width="12"/>
  <path d="M{R*0.92:.0f} {-R*0.38:.0f} C {R*0.35:.0f} {-R*0.05:.0f}, {R*0.35:.0f} {R*0.05:.0f}, {R*0.92:.0f} {R*0.38:.0f}" fill="none" stroke="{C['paper']}" stroke-width="12"/>
  <text id="tnum" x="0" y="80" text-anchor="middle" font-family="Bricolage Grotesque" font-weight="800" font-size="230" fill="{C['night']}"></text>
</svg>'''
    js = f"""
const CIRC={circ:.1f};
function mid(t){{
  const dt=t-T_MID, k=clamp(dt/3.0);
  $('arc').setAttribute('stroke-dashoffset', (CIRC*k).toFixed(1));
  const n= dt<1?3: dt<2?2: dt<3?1:0;
  $('tnum').textContent = n? n : '';
  const pulse = (dt>0 && dt<3) ? 1+0.04*Math.sin((dt%1)*Math.PI) : 1;
  $('mid').style.transform=`translateX(-50%) scale(${{pulse}})`;
}}"""
    css = "#mid{position:absolute;left:50%;transform:translateX(-50%)}"
    return svg, css, js


def mid_guess_number(spec):
    num, mark = float(spec["number"]), float(spec["marker"])
    dec = int(spec.get("decimals", 0))
    scale = max(num, mark) * 1.15
    unit = fmt(spec.get("unit", ""))
    mlabel = fmt(spec.get("marker_label", "the claim"))
    mark_txt = f"{mark:,.{dec}f}"
    html_ = f'''<div id="mid">
  <div id="gnum" class="disp">0</div>
  <div id="gunit">{unit}</div>
  <div id="bar"><div id="fill"></div>
    <div id="mk" style="left:{mark/scale*100:.1f}%"><span class="mono">{mlabel}: {mark_txt}</span></div></div>
</div>'''
    css = f"""#mid{{position:absolute;left:88px;right:88px}}
#gnum{{font-size:230px;line-height:1;color:{T['acc']};white-space:nowrap}}
#gunit{{font-size:56px;font-weight:700;margin-top:10px}}
#bar{{position:relative;height:56px;margin-top:150px;background:{T['line']};border-radius:999px}}
#fill{{position:absolute;left:0;top:0;bottom:0;width:0;background:{T['acc']};border-radius:999px}}
#mk{{position:absolute;top:-30px;bottom:-30px;width:8px;margin-left:-4px;background:{T['fg']}}}
#mk span{{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:34px;padding-bottom:10px}}"""
    js = f"""
const NUM={num}, SCALE={scale}, DEC={dec};
function mid(t){{
  const k=1-Math.pow(1-clamp((t-T_MID)/2.4),3);
  const v=NUM*k;
  $('gnum').textContent=v.toLocaleString('en-US',{{minimumFractionDigits:DEC,maximumFractionDigits:DEC}});
  $('fill').style.width=(v/SCALE*100).toFixed(2)+'%';
}}"""
    return html_, css, js


def mid_spec_sheet(spec):
    rows = spec["rows"]
    racket = f'''<svg id="rk" viewBox="0 0 260 520" width="250" height="500">
  <path d="M130 8 C 225 8 252 80 252 170 C 252 255 205 300 165 318 L 158 360 L 102 360 L 95 318 C 55 300 8 255 8 170 C 8 80 35 8 130 8 Z"
        fill="none" stroke="{T['acc']}" stroke-width="10"/>
  {"".join(f'<circle cx="{x}" cy="{y}" r="7" fill="{T['acc']}" opacity=".7"/>' for x in range(60, 210, 30) for y in range(70, 260, 34) if (x-130)**2/110**2 + (y-165)**2/120**2 < 1)}
  <rect x="104" y="360" width="52" height="150" rx="14" fill="{T['fg']}"/>
</svg>'''
    items = "".join(
        f'<div class="sr" id="sr{i}"><span class="sl mono">{fmt(l)}</span>'
        f'<span class="sv disp{" q" if v == "?" else ""}">{fmt(v)}</span></div>' for i, (l, v) in enumerate(rows))
    html_ = f'<div id="mid">{racket}<div id="rows">{items}</div></div>'
    css = f"""#mid{{position:absolute;left:88px;right:88px;display:flex;gap:56px;align-items:center}}
#rows{{flex:1;display:flex;flex-direction:column;gap:34px}}
.sr{{opacity:0;border-bottom:3px solid {T['line']};padding-bottom:18px}}
.sl{{display:block;font-size:34px;color:{T['muted']}}}
.sv{{display:block;font-size:92px;line-height:1;margin-top:6px}}
.sv.q{{color:{T['acc']};font-size:150px}}"""
    js = f"""
const NR={len(rows)};
function mid(t){{
  const dt=t-T_MID;
  for(let i=0;i<NR;i++){{ const e=$('sr'+i); const k=clamp((dt-i*0.6)/0.3);
    e.style.opacity=k; e.style.transform=`translateX(${{(1-k)*40}}px)`; }}
  const q=document.querySelector('.sv.q');
  if(q){{ const qt=dt-(NR-1)*0.6-0.3; q.style.transform = qt>0? `scale(${{1+0.08*Math.abs(Math.sin(qt*Math.PI*1.5))}})`:'none'; q.style.transformOrigin='left center'; }}
}}"""
    return html_, css, js


def mid_compare(spec):
    """Side-by-side table; optional 4th value per row (True/False) adds a ✓/✕ badge.
    Rows appear slowly one after another (CHECK_STEP)."""
    ca, cb = spec["cols"]
    badges = any(len(r) > 3 for r in spec["rows"])
    cols = "230px 1fr 1fr" + (" 96px" if badges else "")
    head = (f'<div class="cr ch"><span></span><span class="mono">{fmt(ca)}</span>'
            f'<span class="mono">{fmt(cb)}</span>{"<span></span>" if badges else ""}</div>')
    def badge(r):
        if len(r) < 4:
            return ""
        ok = r[3]
        return (f'<span class="cb" style="background:{C["ball"] if ok else C["fault"]};'
                f'color:{C["night"] if ok else C["paper"]}">{"✓" if ok else "✕"}</span>')
    body = "".join(
        f'<div class="cr" id="cr{i}"><span class="mono cl">{fmt(r[0])}</span>'
        f'<span class="disp cv">{fmt(r[1])}</span><span class="disp cv">{fmt(r[2])}</span>{badge(r)}</div>'
        for i, r in enumerate(spec["rows"]))
    html_ = f'<div id="mid">{head}{body}</div>'
    css = f"""#mid{{position:absolute;left:88px;right:88px}}
.cr{{display:grid;grid-template-columns:{cols};gap:18px;align-items:center;padding:30px 0;border-bottom:3px solid {T['line']}}}
.ch{{padding-top:0;border-bottom:5px solid {T['acc']}}}
.ch span{{font-size:46px;color:{T['acc']}}}
.cl{{font-size:34px;line-height:1.15;color:{T['muted']};white-space:nowrap}}
.cv{{font-size:58px;line-height:1;white-space:nowrap}}
.cb{{width:88px;height:88px;border-radius:999px;display:flex;align-items:center;justify-content:center;font-size:52px;font-weight:700;transform:scale(0)}}
.cr:not(.ch){{opacity:0}}"""
    js = f"""
const NC={len(spec['rows'])}, STEP={CHECK_STEP};
function mid(t){{
  const dt=t-T_MID;
  for(let i=0;i<NC;i++){{ const e=$('cr'+i); const k=clamp((dt-0.2-i*STEP)/0.5);
    e.style.opacity=k; e.style.transform=`translateY(${{(1-k)*30}}px)`;
    const bb=e.querySelector('.cb'); if(bb){{ const b=clamp((dt-0.2-i*STEP-0.6)/0.35); bb.style.transform=`scale(${{b}})`; }} }}
}}"""
    return html_, css, js

def mid_checklist(spec):
    """Rows appear one after another, each with a check (true) or cross (false) badge."""
    items = "".join(
        f'<div class="ck" id="ck{i}"><span class="cb" style="background:{C["ball"] if ok else C["fault"]};'
        f'color:{C["night"] if ok else C["paper"]}">{"✓" if ok else "✕"}</span>'
        f'<span><span class="ckl mono">{fmt(l)}</span><span class="ckv disp">{fmt(v)}</span></span></div>'
        for i, (l, v, ok) in enumerate(spec["rows"]))
    html_ = f'<div id="mid">{items}</div>'
    css = f"""#mid{{position:absolute;left:88px;right:88px;display:flex;flex-direction:column;gap:44px}}
.ck{{display:flex;gap:36px;align-items:center;opacity:0}}
.cb{{flex:none;width:110px;height:110px;border-radius:999px;display:flex;align-items:center;justify-content:center;font-size:64px;font-weight:700;transform:scale(0)}}
.ckl{{display:block;font-size:36px;color:{T['muted']}}}
.ckv{{display:block;font-size:80px;line-height:1;margin-top:6px}}"""
    js = f"""
const NK={len(spec['rows'])}, STEP={CHECK_STEP};
function mid(t){{
  const dt=t-T_MID;
  for(let i=0;i<NK;i++){{ const e=$('ck'+i); const k=clamp((dt-0.2-i*STEP)/0.5);
    e.style.opacity=k; e.style.transform=`translateY(${{(1-k)*30}}px)`;
    const b=clamp((dt-0.2-i*STEP-0.45)/0.35); const bb=e.querySelector('.cb');
    bb.style.transform=`scale(${{b<1? b*1.15 : 1}})`; }}
}}"""
    return html_, css, js


MIDS = {"refs_view": mid_refs_view, "three_second_call": mid_three_second_call, "guess_number": mid_guess_number, "spec_sheet": mid_spec_sheet, "compare": mid_compare, "checklist": mid_checklist}
MID_TOP = {"refs_view": (760, 610), "three_second_call": (900, 760), "guess_number": (980, 820), "spec_sheet": (900, 700), "compare": (900, 720), "checklist": (900, 760)}


def call_rows(spec):
    """Optional answer graphic: rows [label, ok] -> check / cross list under the reason."""
    rows = spec.get("call_rows")
    if not rows:
        return ""
    items = "".join(
        f'<span style="display:flex;align-items:center;gap:28px;margin-top:22px;font-size:58px">'
        f'<span style="width:76px;height:76px;border-radius:999px;display:inline-flex;align-items:center;justify-content:center;'
        f'font-size:44px;background:{C["ball"] if ok is True else (C["fault"] if ok is False else C["glass"])};color:{C["paper"] if ok is False else C["night"]}">{"✓" if ok is True else ("✕" if ok is False else ok)}</span>'
        f'{fmt(label)}</span>' for label, ok in rows)
    return f'<span style="display:block;margin-top:36px">{items}</span>'


def page(spec):
    global T
    T = THEMES[spec.get("theme", "light")]
    fair = spec["verdict"].upper() == "FAIR"
    vcol = C["ball"] if fair else C["fault"]
    pill_fg = C["night"] if fair else C["paper"]
    tl = timeline(spec)
    mid_html, mid_css, mid_js = MIDS[spec["format"]](spec)
    top0, top1 = MID_TOP[spec["format"]]
    consts = "".join(f"const {k}={v:.3f};" for k, v in tl.items())
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:"Bricolage Grotesque";src:url("file://{FONTS}/Bricolage.ttf");font-weight:200 800}}
@font-face{{font-family:"Instrument Sans";src:url("file://{FONTS}/InstrumentSans.ttf");font-weight:400 700}}
@font-face{{font-family:"JetBrains Mono";src:url("file://{FONTS}/JetBrainsMono.ttf");font-weight:100 800}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1920px;overflow:hidden;font-family:'Instrument Sans';color:{T['fg']}}}
#bg{{position:absolute;inset:0;background:{T['bg']}}}
#night{{position:absolute;inset:0;background:{T['bg2']};opacity:0}}
.disp{{font-family:'Bricolage Grotesque';font-weight:800;letter-spacing:-.03em}}
.mono{{font-family:'JetBrains Mono';font-weight:700;text-transform:uppercase}}
#top{{position:absolute;left:88px;right:88px;top:250px;display:flex;justify-content:space-between;align-items:center;font-size:40px}}
.chip{{border:4px solid currentColor;border-radius:999px;padding:8px 28px}}
#q{{position:absolute;left:88px;right:88px;top:360px;transform-origin:left top}}
#claim{{font-size:96px;line-height:.98}}
.w{{opacity:0}}
#ask{{font-size:120px;line-height:.9;color:{T['acc']};margin-top:28px;opacity:0}}
#count{{position:absolute;right:88px;top:1040px;font-size:260px;color:{T['acc']};opacity:0}}
#call{{position:absolute;left:88px;right:88px;top:560px;opacity:0;transform-origin:left top}}
.pill{{display:inline-flex;align-items:center;gap:20px;border-radius:999px;padding:18px 40px;font-size:52px;background:{vcol};color:{pill_fg}}}
#verdict{{font-size:300px;line-height:.88;margin-top:40px;color:{T['fair_word'] if fair else T['fault_word']}}}
#why{{font-size:76px;line-height:1.1;font-weight:700;margin-top:60px;opacity:0}}
#cta{{font-size:44px;margin-top:70px;color:{T['acc']};opacity:0}}
.hl{{color:{T['acc']}}}
#intro{{position:absolute;left:0;right:0;top:700px;text-align:center}}
#intro .t{{font-size:170px;line-height:.9}}
#intro .t .f{{color:{T['intro_f']}}}
#intro .s{{font-size:44px;margin-top:40px;letter-spacing:.06em}}
{mid_css}
</style></head><body>
<div id="bg"></div><div id="night"></div>
<div id="intro"><div class="t disp"><span class="f">Fair</span> or<br>Fault</div><div class="s mono">Your Daily Padel Quiz</div></div>
<div id="top" class="mono"><span class="chip">Padel {fmt(spec['label'])}</span><span>@fairorfault</span></div>
<div id="q"><h1 id="claim" class="disp">{words(spec['claim'])}</h1><p id="ask" class="disp">Fair or fault?</p></div>
{mid_html}
<div id="count" class="disp"></div>
<div id="call"><span class="pill mono">{'✓' if fair else '✕'} {fmt(spec['pill'])}</span>
  <h1 id="verdict" class="disp">{'FAIR.' if fair else 'FAULT.'}</h1>
  <p id="why">{fmt(spec['line'])}{call_rows(spec)}</p>
  <p id="cta" class="mono">Got it right? Comment ✓</p></div>
<script>
{consts}
const $=id=>document.getElementById(id);
const PAPER='{C['paper']}',NIGHT='{C['night']}',COURT='{C['court']}',BALL='{C['ball']}';
// Cover for the Instagram grid: white tile, dark text, so reels stand out from the blue carousels.
function coverMode(badge){{
  setT(T_READ-0.05);
  $('bg').style.background=PAPER; $('intro').style.opacity=0;
  document.body.style.color=NIGHT;
  $('top').style.color=NIGHT; $('claim').style.color=NIGHT; $('ask').style.color=COURT;
  // keep everything inside the 4:5 grid crop (y 285-1635)
  $('top').style.top='380px'; $('q').style.top='500px'; $('q').style.transform='none';
  $('claim').style.fontSize='118px'; $('ask').style.fontSize='140px'; $('ask').style.marginTop='44px';
  if(badge){{ const b=document.createElement('div'); b.id='badge';
    b.innerHTML='<span style="display:inline-flex;width:84px;height:84px;border-radius:999px;background:'+COURT+';align-items:center;justify-content:center"><svg width="34" height="38" viewBox="0 0 34 38"><path d="M4 3 L31 19 L4 35 Z" fill="'+BALL+'"/></svg></span><span>Watch &amp; make the call</span>';
    b.style.cssText='position:absolute;left:88px;top:1470px;display:flex;align-items:center;gap:28px;font-family:JetBrains Mono;font-weight:700;text-transform:uppercase;font-size:42px;color:'+NIGHT;
    document.body.appendChild(b); }}
}}

const lerp=(a,b,k)=>a+(b-a)*k, clamp=(x)=>Math.max(0,Math.min(1,x));
const ease=(k)=>k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
const WS=[...document.querySelectorAll('.w')];
{mid_js}
function setT(t){{
  const it=clamp(t/0.4)*(1-clamp((t-{INTRO}+0.45)/0.4));
  $('intro').style.opacity=it; $('intro').style.transform=`scale(${{lerp(0.94,1,clamp(t/0.8))}})`;
  $('top').style.opacity=clamp((t-{INTRO}+0.1)/0.3);
  WS.forEach((w,i)=>w.style.opacity=clamp((t-{INTRO}-0.3-i*{WORD})/0.25));
  $('ask').style.opacity=clamp((t-T_ASK)/0.35);
  const g=ease(clamp((t-T_READ)/0.4));
  $('q').style.transform=`scale(${{lerp(1,0.62,g)}})`;
  $('mid').style.top=lerp({top0},{top1},g)+'px';
  mid(t);
  const c=clamp((t-T_CALL)/0.35);
  $('night').style.opacity=c; $('call').style.opacity=c;
  $('call').style.transform=`scale(${{lerp(1.08,1,c)}})`;
  $('q').style.opacity=1-c; $('mid').style.opacity=Math.min(g,1-c);
  $('why').style.opacity=clamp((t-T_CALL-0.6)/0.3); $('cta').style.opacity=clamp((t-T_CALL-1.0)/0.3);
  const o=clamp((t-(T_END-{FADE}))/0.3);
  if(o>0){{ $('call').style.opacity=1-o; $('night').style.opacity=1-o; }}
}}
</script></body></html>"""


async def render_cover(spec, out, badge=COVER_BADGE):
    """Only the cover PNG (fast preview without rendering the video)."""
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "reel.html"; f.write_text(page(spec))
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 1080, "height": 1920})
            await pg.goto(f"file://{f}"); await pg.evaluate("document.fonts.ready")
            await pg.evaluate(f"coverMode({'true' if badge else 'false'})")
            await pg.screenshot(path=str(out)); await b.close()


async def render(spec, out):
    tl = timeline(spec)
    out = pathlib.Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / "reel.html").write_text(page(spec))
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 1080, "height": 1920})
            await pg.goto(f"file://{tmp/'reel.html'}")
            await pg.evaluate("document.fonts.ready")
            frames = int(round(FPS * tl["T_END"]))
            for f in range(frames):
                await pg.evaluate(f"setT({f/FPS})")
                await pg.screenshot(path=str(tmp / f"f{f:04d}.png"))
            await pg.evaluate(f"coverMode({'true' if COVER_BADGE else 'false'})")  # white grid cover, full question
            await pg.screenshot(path=str(out.with_suffix(".cover.png")))
            await b.close()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(out)], check=True)
    return tl


if __name__ == "__main__":
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    spec.setdefault("format", "refs_view")
    tl = asyncio.run(render(spec, sys.argv[2]))
    print(f"reel -> {sys.argv[2]} ({tl['T_END']:.1f} s)")
