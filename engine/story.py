"""Render Instagram story frames (1080 x 1920) from a JSON spec.

Usage: python3 engine/story.py stories/<name>.json
Frame types: question (label, big, claim), answer (verdict, pill, line, diagram_svg_paths, source),
steps (title, steps[], foot). Output: stories/<name>-<n>.png and stories/<name>-sheet.png
"""
import asyncio, json, pathlib, sys
from playwright.async_api import async_playwright

ENGINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
from render import HEAD, C, fmt, CHECK, CROSS  # noqa: E402
import diagrams  # noqa: E402

CSS = """<style>.post{width:1080px;height:1920px;padding:260px 88px 280px}</style>"""


def question(s, n, t):
    return f'''<div class="post" style="background:{C['court']};color:{C['paper']}">
  <div class="top"><span class="chip">Padel {fmt(s['label'])}</span><span>{n}/{t}</span></div>
  <p class="disp big" style="margin-top:120px;font-size:200px">{fmt(s['big'])}</p>
  <h1 class="disp" style="margin-top:56px;font-size:116px;line-height:.98">{fmt(s['claim'])}</h1>
  <p class="disp" style="margin-top:56px;font-size:140px;line-height:.9;color:{C['ball']}">Fair or fault?</p>
  <div class="tiles"><div class="tile" style="background:{C['ball']}">Fair</div><div class="tile" style="background:{C['paper']}">Fault</div></div>
  <p style="margin:48px 0 0;text-align:right;font-family:'JetBrains Mono',monospace;font-size:44px;font-weight:700;text-transform:uppercase">Tap for the answer →</p>
</div>'''


def answer(s, n, t):
    fair = s["verdict"].upper() == "FAIR"
    pill_bg, pill_fg, icon = (C["ball"], C["night"], CHECK) if fair else (C["fault"], C["paper"], CROSS)
    svg = diagrams.court_svg(s["paths"], 330, 600)
    return f'''<div class="post" style="background:{C['night']};color:{C['paper']}">
  <div class="top"><span>The answer</span><span>{n}/{t}</span></div>
  <div style="margin-top:72px;display:flex;flex-direction:column;align-items:flex-start">
    <span class="pill" style="background:{pill_bg};color:{pill_fg}">{icon}{fmt(s['pill'])}</span>
    <h1 class="disp" style="margin-top:24px;font-size:200px;line-height:.88;letter-spacing:-.04em;color:{C['ball'] if fair else C['paper']}">{'FAIR.' if fair else 'FAULT.'}</h1>
    <p style="margin:32px 0 0;font-size:68px;line-height:1.1;font-weight:700">{fmt(s['line'])}</p>
  </div>
  <div style="margin-top:auto;display:flex;gap:40px;align-items:flex-end">{svg}
    <p style="margin:0;flex:1;font-size:48px;line-height:1.15;font-weight:700;color:{C['glass']}">{fmt(s['note'])}</p></div>
  <div class="foot" style="margin-top:56px"><span style="color:{C['glass']}">{fmt(s['source'])}</span><span>Next →</span></div>
</div>'''


def steps(s, n, t):
    rows = "".join(
        f'''<div style="display:flex;gap:36px;align-items:flex-start">
      <span style="flex:none;width:96px;height:96px;border-radius:999px;background:{C['court']};color:{C['paper']};display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-size:48px;font-weight:700">{i}</span>
      <p style="margin:6px 0 0;font-size:62px;line-height:1.08;font-weight:700">{fmt(st, 'hlc')}</p></div>'''
        for i, st in enumerate(s["steps"], 1))
    return f'''<div class="post" style="background:{C['paper']};color:{C['night']}">
  <style>.hlc{{color:{C['court']}}}</style>
  <div class="top" style="color:{C['muted']}"><span>How it goes on</span><span>{n}/{t}</span></div>
  <h1 class="disp" style="margin-top:72px;font-size:150px;line-height:.92">{fmt(s['title'], 'hlc')}</h1>
  <div style="display:flex;flex-direction:column;gap:48px;margin-top:72px">{rows}</div>
  <p style="margin:auto 0 0;font-family:'JetBrains Mono',monospace;font-size:44px;font-weight:700;text-transform:uppercase;color:{C['muted']}">{fmt(s['foot'])}</p>
</div>'''


B = {"question": question, "answer": answer, "steps": steps}


async def main(path):
    p = pathlib.Path(path)
    spec = json.loads(p.read_text())
    frames, out = spec["frames"], []
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        pg = await br.new_page(viewport={"width": 1080, "height": 1920})
        for i, f in enumerate(frames, 1):
            tmp = p.parent / f".tmp-{i}.html"
            tmp.write_text(HEAD + CSS + B[f["type"]](f, i, len(frames)) + "</body></html>")
            await pg.goto(f"file://{tmp.resolve()}")
            await pg.evaluate("document.fonts.ready")
            over = await pg.evaluate("(()=>{const p=document.querySelector('.post');return p.scrollHeight>p.clientHeight})()")
            if over:
                print(f"PROBLEM: frame {i} overflows")
            o = p.parent / f"{p.stem}-{i}.png"
            await pg.screenshot(path=str(o)); tmp.unlink(); out.append(o)
        await br.close()
    from PIL import Image
    W, H, g = 360, 640, 12
    sh = Image.new("RGB", (len(out) * (W + g) + g, H + 2 * g), "#DDDDDD")
    for k, f in enumerate(out):
        sh.paste(Image.open(f).resize((W, H)), (g + k * (W + g), g))
    sh.save(p.parent / f"{p.stem}-sheet.png")
    print("ok", [str(o) for o in out])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
