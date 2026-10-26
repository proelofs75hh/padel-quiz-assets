"""Render a week of Fair or Fault posts from weeks/<week>/posts.json.

Usage:  python3 engine/render.py weeks/2026-W44
Output: weeks/<week>/<post-id>-<n>.png (1080 x 1350) and a contact sheet
        weeks/<week>/_sheet.png for visual checking.

Templates reproduce the Claude Design "Fair or Fault" design system
(court / night / paper, Bricolage Grotesque, Instrument Sans, JetBrains Mono).
Text fields accept plain text; "\n" = line break, **word** = highlight colour.
"""
import asyncio, html, json, pathlib, re, sys

from playwright.async_api import async_playwright

ENGINE = pathlib.Path(__file__).resolve().parent
FONTS = ENGINE / "fonts"

C = dict(court="#1747B0", night="#0E1630", paper="#F4F1E8", glass="#D6E6F3",
         ball="#D7F23A", fault="#C2361F", muted="#4A5470", chalk="#FFFFFF")

HEAD = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
@font-face{{font-family:"Bricolage Grotesque";src:url("file://{FONTS}/Bricolage.ttf");font-weight:200 800}}
@font-face{{font-family:"Instrument Sans";src:url("file://{FONTS}/InstrumentSans.ttf");font-weight:400 700}}
@font-face{{font-family:"JetBrains Mono";src:url("file://{FONTS}/JetBrainsMono.ttf");font-weight:100 800}}
body{{margin:0}}
.post{{width:1080px;height:1350px;box-sizing:border-box;padding:80px 88px;font-family:'Instrument Sans',system-ui,sans-serif;display:flex;flex-direction:column;overflow:hidden}}
.top{{display:flex;justify-content:space-between;align-items:center;font-family:'JetBrains Mono',monospace;font-size:40px;font-weight:700;letter-spacing:.02em;text-transform:uppercase}}
.chip{{border:4px solid currentColor;border-radius:999px;padding:8px 28px}}
.disp{{font-family:'Bricolage Grotesque','Arial Narrow',sans-serif;font-weight:800;letter-spacing:-.03em;margin:0}}
.big{{font-size:260px;line-height:.85;letter-spacing:-.04em;color:{C['ball']};white-space:nowrap}}
.tiles{{display:flex;gap:24px;margin-top:auto;padding-top:72px}}
.tile{{flex:1;padding:40px 0;border-radius:20px;color:{C['night']};text-align:center;font-size:72px;line-height:1;font-weight:700}}
.foot{{display:flex;justify-content:space-between;align-items:center;margin-top:auto;font-family:'JetBrains Mono',monospace;font-size:40px;font-weight:700;text-transform:uppercase}}
.pill{{display:inline-flex;align-items:center;gap:20px;border-radius:999px;padding:18px 40px;font-family:'JetBrains Mono',monospace;font-size:48px;font-weight:700;text-transform:uppercase}}
.hl{{color:{C['ball']}}}
</style></head><body>"""

CHECK = f'<svg width="36" height="36" viewBox="0 0 22 22"><path d="M3 12 L9 18 L19 4" stroke="{C["night"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>'
CROSS = f'<svg width="36" height="36" viewBox="0 0 22 22"><path d="M4 4 L18 18 M18 4 L4 18" stroke="{C["paper"]}" stroke-width="4" stroke-linecap="round" fill="none"/></svg>'


def fmt(text, hl_class="hl"):
    t = html.escape(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", rf'<span class="{hl_class}">\1</span>', t)
    return t.replace("\n", "<br>")


def question(s, n, total):
    has_big = bool(s.get("big"))
    big = f'<p class="disp big" style="margin-top:64px">{fmt(s["big"])}</p>' if has_big else ""
    claim_mt, ask_size = ("32px", 104) if has_big else ("72px", 128)
    return f'''<div class="post" style="background:{C['court']};color:{C['paper']}">
  <div class="top"><span class="chip">Padel {fmt(s['label'])}</span><span>{n}/{total}</span></div>
  {big}
  <h1 class="disp fit" style="margin-top:{claim_mt};font-size:104px;line-height:.98">{fmt(s['claim'])}</h1>
  <p class="disp" style="margin-top:36px;font-size:{ask_size}px;line-height:.9;color:{C['ball']}">Fair or fault?</p>
  <div class="tiles"><div class="tile" style="background:{C['ball']}">Fair</div><div class="tile" style="background:{C['paper']}">Fault</div></div>
  <p style="margin:40px 0 0;text-align:right;font-family:'JetBrains Mono',monospace;font-size:40px;font-weight:700;text-transform:uppercase">Swipe for the answer →</p>
</div>'''


def verdict(s, n, total):
    fair = s["verdict"].upper() == "FAIR"
    pill_bg, pill_fg, icon = (C["ball"], C["night"], CHECK) if fair else (C["fault"], C["paper"], CROSS)
    word_col = C["ball"] if fair else C["paper"]
    figure = ""
    if s.get("figure"):
        figure = f'<p class="disp" style="margin-top:48px;font-size:150px;line-height:.9;color:{C["ball"]};white-space:nowrap">{fmt(s["figure"])}</p>'
        line_style = "margin:24px 0 0;font-size:64px;line-height:1.1;font-weight:700"
    else:
        line_style = "margin:56px 0 0;font-size:72px;line-height:1.1;font-weight:700"
    right = "Why? →" if n < total else "@fairorfault"
    return f'''<div class="post" style="background:{C['night']};color:{C['paper']}">
  <div class="top"><span>The answer</span><span>{n}/{total}</span></div>
  <div style="margin-top:auto;display:flex;flex-direction:column;align-items:flex-start">
    <span class="pill" style="background:{pill_bg};color:{pill_fg}">{icon}{fmt(s['pill'])}</span>
    <h1 class="disp" style="margin-top:40px;font-size:240px;line-height:.88;letter-spacing:-.04em;color:{word_col}">{'FAIR.' if fair else 'FAULT.'}</h1>
    {figure}
    <p class="fit" style="{line_style}">{fmt(s['line'])}</p>
  </div>
  <div class="foot"><span style="color:{C['glass']}">{fmt(s['source'])}</span><span>{right}</span></div>
</div>'''


# ---- explainer diagrams: shared library in engine/diagrams.py -------------
import diagrams as _diagrams

DIAGRAMS = {k: (lambda k=k: _diagrams.static_svg(k)) for k in _diagrams.LIB}


def explainer(s, n, total):
    steps = "".join(
        f'''<div style="display:flex;flex-direction:column;gap:16px">
      <span style="width:80px;height:80px;border-radius:999px;background:{C['fault'] if st.get('bad') else C['night']};color:{C['paper']};display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-size:44px;font-weight:700">{i}</span>
      <p style="margin:0;font-size:60px;line-height:1.05;font-weight:700">{fmt(st['text'], 'hlf')}</p></div>'''
        for i, st in enumerate(s["steps"], 1))
    return f'''<div class="post" style="background:{C['paper']};color:{C['night']}">
  <style>.hlf{{color:{C['fault']}}} .hlc{{color:{C['court']}}}</style>
  <div class="top" style="color:{C['muted']}"><span>Why</span><span>{n}/{total}</span></div>
  <h1 class="disp" style="margin-top:40px;font-size:120px;line-height:.95"><span class="hlc">{fmt(s['title_good'])}</span>{('<br><span class="hlf">' + fmt(s['title_bad']) + '</span>') if s.get('title_bad') else ''}</h1>
  <div style="display:flex;gap:48px;align-items:center;margin-top:auto">{DIAGRAMS[s['diagram']]()}
    <div style="display:flex;flex-direction:column;gap:64px;flex:1">{steps}</div></div>
  <p style="margin:48px 0 0;font-family:'JetBrains Mono',monospace;font-size:40px;font-weight:700;text-transform:uppercase;color:{C['muted']}">Got it right? Comment ✓</p>
</div>'''


BUILDERS = {"question": question, "verdict": verdict, "explainer": explainer}

# Shrink any .fit element until the slide no longer overflows (min 56px).
FIT_JS = """() => {
  const post = document.querySelector('.post');
  const over = () => [...post.children].some(c => c.getBoundingClientRect().bottom > 1350 - 79);
  let guard = 0;
  for (const el of document.querySelectorAll('.fit')) {
    let size = parseFloat(getComputedStyle(el).fontSize);
    while ((over() || post.scrollHeight > post.clientHeight) && size > 56 && guard++ < 200) {
      size -= 4; el.style.fontSize = size + 'px';
    }
  }
  return post.scrollHeight > post.clientHeight || over();
}"""


async def render_week(week_dir: pathlib.Path):
    spec = json.loads((week_dir / "posts.json").read_text())
    problems, files = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        for post in spec["posts"]:
            total = len(post["slides"])
            for i, s in enumerate(post["slides"], 1):
                body = BUILDERS[s["type"]](s, i, total)
                tmp = week_dir / f".tmp-{post['id']}-{i}.html"
                tmp.write_text(HEAD + body + "</body></html>")
                await page.goto(f"file://{tmp.resolve()}")
                await page.evaluate("document.fonts.ready")
                if await page.evaluate(FIT_JS):
                    problems.append(f"{post['id']} slide {i}: text overflows even at minimum size")
                out = week_dir / f"{post['id']}-{i}.png"
                await page.screenshot(path=str(out))
                tmp.unlink()
                files.append(out)
        await browser.close()
    return files, problems


def contact_sheet(week_dir, files):
    from PIL import Image
    W, H, g = 270, 338, 12
    cols = 6
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W + (cols + 1) * g, rows * H + (rows + 1) * g), "#DDDDDD")
    for k, f in enumerate(files):
        im = Image.open(f).resize((W, H), Image.LANCZOS)
        sheet.paste(im, (g + (k % cols) * (W + g), g + (k // cols) * (H + g)))
    sheet.save(week_dir / "_sheet.png")


if __name__ == "__main__":
    wd = pathlib.Path(sys.argv[1])
    files, problems = asyncio.run(render_week(wd))
    contact_sheet(wd, files)
    print(f"rendered {len(files)} slides -> {wd}/_sheet.png")
    for pr in problems:
        print("PROBLEM:", pr)
    sys.exit(1 if problems else 0)
