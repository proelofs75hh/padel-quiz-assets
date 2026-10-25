"""Render a "Ref's View" quiz reel (1080 x 1920, silent MP4) for Fair or Fault.

Usage:  python3 engine/reel.py <reel.json> <out.mp4>

reel.json:
{
  "label": "Rules",
  "claim": "Your serve hits the fence after the bounce.",
  "verdict": "FAULT",            # or FAIR
  "pill": "Second serve",
  "line": "Glass is fine.\nThe fence is not.",
  "source": "FIP rules · Serve",
  "diagram": "serve-side-mesh"   # key of REEL_DIAGRAMS below
}

Timeline (8 s, 30 fps, loops cleanly):
  0.0-1.5  claim + "Fair or fault?" over a static court
  1.5-4.5  ball path animates, countdown 3-2-1, freeze before the call
  4.5-6.0  verdict flips in (FAIR ball-yellow / FAULT red)
  6.0-7.6  one-line reason + comment prompt
  7.6-8.0  fade back to the opening frame for a seamless loop
Everything important stays inside the Instagram safe zone
(top 250 px and bottom 420 px are kept free of key text).
"""
import asyncio, json, pathlib, subprocess, sys, tempfile, html, re

from playwright.async_api import async_playwright

ENGINE = pathlib.Path(__file__).resolve().parent
FONTS = ENGINE / "fonts"
FPS, DURATION = 30, 8.0
C = dict(court="#1747B0", night="#0E1630", paper="#F4F1E8", glass="#9FC3E3",
         ball="#D7F23A", fault="#C2361F", muted="#4A5470")

# Ball paths on the 200 x 400 court (same coordinates as render.py explainers).
# points: ball positions; marks: (index into points, number) shown as numbered dots.
REEL_DIAGRAMS = {
    "serve-side-mesh": {"points": [[150, 376], [60, 150], [-2, 104]], "bad_point": 2},
    "own-back-glass": {"points": [[130, 330], [110, 404], [80, 110]], "bad_point": None},
    "direct-back-glass": {"points": [[120, 300], [90, -2]], "bad_point": 1},
}


def fmt(t, cls="hl"):
    t = html.escape(t or "")
    t = re.sub(r"\*\*(.+?)\*\*", rf'<span class="{cls}">\1</span>', t)
    return t.replace("\n", "<br>")


def page(spec):
    fair = spec["verdict"].upper() == "FAIR"
    d = REEL_DIAGRAMS[spec["diagram"]]
    pts = json.dumps(d["points"])
    bad = json.dumps(d["bad_point"])
    vcol = C["ball"] if fair else C["fault"]
    pill_fg = C["night"] if fair else C["paper"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:"Bricolage Grotesque";src:url("file://{FONTS}/Bricolage.ttf");font-weight:200 800}}
@font-face{{font-family:"Instrument Sans";src:url("file://{FONTS}/InstrumentSans.ttf");font-weight:400 700}}
@font-face{{font-family:"JetBrains Mono";src:url("file://{FONTS}/JetBrainsMono.ttf");font-weight:100 800}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1920px;overflow:hidden;font-family:'Instrument Sans';color:{C['paper']}}}
#bg{{position:absolute;inset:0;background:{C['court']}}}
#night{{position:absolute;inset:0;background:{C['night']};opacity:0}}
.disp{{font-family:'Bricolage Grotesque';font-weight:800;letter-spacing:-.03em}}
.mono{{font-family:'JetBrains Mono';font-weight:700;text-transform:uppercase}}
#top{{position:absolute;left:88px;right:88px;top:250px;display:flex;justify-content:space-between;align-items:center;font-size:40px}}
.chip{{border:4px solid currentColor;border-radius:999px;padding:8px 28px}}
#q{{position:absolute;left:88px;right:88px;top:360px}}
#claim{{font-size:96px;line-height:.98}}
#ask{{font-size:120px;line-height:.9;color:{C['ball']};margin-top:28px}}
#court{{position:absolute;left:50%;top:940px;transform:translateX(-50%)}}
#count{{position:absolute;right:88px;top:1040px;font-size:260px;color:{C['ball']};opacity:0}}
#call{{position:absolute;left:88px;right:88px;top:560px;opacity:0}}
.pill{{display:inline-flex;align-items:center;gap:20px;border-radius:999px;padding:18px 40px;font-size:52px;background:{vcol};color:{pill_fg}}}
#verdict{{font-size:300px;line-height:.88;margin-top:40px;color:{C['ball'] if fair else C['paper']}}}
#why{{font-size:76px;line-height:1.1;font-weight:700;margin-top:60px;opacity:0}}
#cta{{font-size:44px;margin-top:70px;color:{C['ball']};opacity:0}}
.hl{{color:{C['ball']}}}
</style></head><body>
<div id="bg"></div><div id="night"></div>
<div id="top" class="mono"><span class="chip">Padel {fmt(spec['label'])}</span><span>@fairorfault</span></div>
<div id="q"><h1 id="claim" class="disp">{fmt(spec['claim'])}</h1><p id="ask" class="disp">Fair or fault?</p></div>
<svg id="court" viewBox="-22 -22 244 444" width="470" height="855">
  <rect x="0" y="0" width="200" height="400" fill="#1E56C8"/>
  <rect x="0" y="0" width="200" height="400" fill="none" stroke="#FFF" stroke-width="2.5"/>
  <line x1="0" y1="61" x2="200" y2="61" stroke="#FFF" stroke-width="2.5"/>
  <line x1="0" y1="339" x2="200" y2="339" stroke="#FFF" stroke-width="2.5"/>
  <line x1="100" y1="61" x2="100" y2="339" stroke="#FFF" stroke-width="2.5"/>
  <line x1="-10" y1="200" x2="210" y2="200" stroke="#FFF" stroke-width="5"/>
  <path d="M-6 80 V-6 H206 V80" fill="none" stroke="{C['glass']}" stroke-width="10"/>
  <path d="M-6 320 V406 H206 V320" fill="none" stroke="{C['glass']}" stroke-width="10"/>
  <line x1="-6" y1="80" x2="-6" y2="320" stroke="#B9C4DA" stroke-width="4" stroke-dasharray="3 6"/>
  <line x1="206" y1="80" x2="206" y2="320" stroke="#B9C4DA" stroke-width="4" stroke-dasharray="3 6"/>
  <polyline id="trail" fill="none" stroke="{C['ball']}" stroke-width="6" stroke-dasharray="12 8" points=""/>
  <circle id="bnc" r="0" fill="none" stroke="{C['ball']}" stroke-width="5"/>
  <circle id="hit" r="0" fill="none" stroke="{vcol}" stroke-width="6"/>
  <circle id="ball" r="11" fill="{C['ball']}" stroke="{C['night']}" stroke-width="3"/>
</svg>
<div id="count" class="disp"></div>
<div id="call"><span class="pill mono">{'✓' if fair else '✕'} {fmt(spec['pill'])}</span>
  <h1 id="verdict" class="disp">{'FAIR.' if fair else 'FAULT.'}</h1>
  <p id="why">{fmt(spec['line'])}</p>
  <p id="cta" class="mono">Got it right? Comment ✓</p></div>
<script>
const P={pts}, BAD={bad};
const lerp=(a,b,k)=>a+(b-a)*k, clamp=(x)=>Math.max(0,Math.min(1,x));
const ease=(k)=>k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
function seg(){{ // cumulative lengths for constant-speed travel
  const L=[0]; for(let i=1;i<P.length;i++) L.push(L[i-1]+Math.hypot(P[i][0]-P[i-1][0],P[i][1]-P[i-1][1])); return L; }}
const L=seg(), TOT=L[L.length-1];
function at(k){{ const d=k*TOT; let i=1; while(i<L.length-1&&L[i]<d) i++;
  const f=(d-L[i-1])/(L[i]-L[i-1]||1); return [lerp(P[i-1][0],P[i][0],f), lerp(P[i-1][1],P[i][1],f), i]; }}
function setT(t){{
  const $=id=>document.getElementById(id);
  // 1.2-1.5s: question shrinks to the top, court grows
  const g=ease(clamp((t-1.2)/0.3));
  $('q').style.transformOrigin='left top'; $('q').style.transform=`scale(${{lerp(1,0.62,g)}})`;
  $('court').style.top=lerp(940,610,g)+'px'; $('court').setAttribute('width',lerp(470,520,g)); $('court').setAttribute('height',lerp(855,946,g));
  // ball travel 1.5-3.6s, freeze, countdown 1.5-4.5
  const k=ease(clamp((t-1.5)/2.1)); const [x,y,i]=at(k);
  $('ball').setAttribute('cx',x); $('ball').setAttribute('cy',y);
  const tr=P.slice(0,i).concat([[x,y]]); $('trail').setAttribute('points', k>0? tr.map(p=>p.join(',')).join(' '):'');
  // bounce ring once the ball has passed the first turning point
  if(P.length>2 && i>=2){{ $('bnc').setAttribute('cx',P[1][0]); $('bnc').setAttribute('cy',P[1][1]); $('bnc').setAttribute('r',16); }} else $('bnc').setAttribute('r',0);
  const n=t<1.5?0:t<2.5?3:t<3.5?2:t<4.5?1:0;
  $('count').textContent=n||''; $('count').style.opacity = n? 1:0;
  const target = BAD!==null? P[BAD] : P[P.length-1];
  const r = t>3.6 ? 16+26*clamp((t-3.6)/0.4) : 0;
  $('hit').setAttribute('cx',target[0]); $('hit').setAttribute('cy',target[1]); $('hit').setAttribute('r',r);
  // call 4.5-7.6s: night background, court hidden
  const c=clamp((t-4.5)/0.35);
  $('night').style.opacity=c; $('call').style.opacity=c; $('top').style.opacity=1;
  $('call').style.transform=`scale(${{lerp(1.08,1,c)}})`; $('call').style.transformOrigin='left top';
  $('q').style.opacity=1-c; $('court').style.opacity=1-c;
  $('why').style.opacity=clamp((t-6.0)/0.3); $('cta').style.opacity=clamp((t-6.4)/0.3);
  // loop: 7.6-7.8 fade out, 7.8-8.0 fade in the opening frame
  if(t>=7.6){{
    const o=clamp((t-7.6)/0.2), f=clamp((t-7.8)/0.2);
    $('call').style.opacity=1-o; $('night').style.opacity=1-o;
    $('q').style.transform='scale(1)'; $('q').style.opacity=f;
    $('court').style.top='940px'; $('court').setAttribute('width',470); $('court').setAttribute('height',855); $('court').style.opacity=f;
    $('ball').setAttribute('cx',P[0][0]); $('ball').setAttribute('cy',P[0][1]);
    $('trail').setAttribute('points',''); $('hit').setAttribute('r',0); $('bnc').setAttribute('r',0); }}
}}
</script></body></html>"""


async def render(spec, out):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / "reel.html").write_text(page(spec))
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 1080, "height": 1920})
            await pg.goto(f"file://{tmp/'reel.html'}")
            await pg.evaluate("document.fonts.ready")
            frames = int(FPS * DURATION)
            for f in range(frames):
                await pg.evaluate(f"setT({f/FPS})")
                await pg.screenshot(path=str(tmp / f"f{f:04d}.png"))
            await pg.evaluate("setT(1.0)")
            await pg.screenshot(path=str(pathlib.Path(out).with_suffix('.cover.png')))
            await b.close()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(out)], check=True)


if __name__ == "__main__":
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    asyncio.run(render(spec, sys.argv[2]))
    print("reel ->", sys.argv[2])
