"""Series-style covers for reels (1080 x 1920), so reels match the carousel grid (30 Oct 2026).

Usage:  python3 engine/reel_cover.py weeks/2026-W45      (overwrites reels/<id>.cover.png)
Called automatically at the end of engine/reels_week.py.

The Instagram profile grid shows a 3:4 crop of the 9:16 cover (y 240 ... 1680), so all content
stays inside that window. Colour follows the pillar: rules -> settle (green), gear -> gear (blue),
market -> number (clay), pros -> pros (yellow). Optional per reel: "cover_q" (question to show
instead of spec.claim + "Fair or fault?").
"""
import asyncio, json, pathlib, sys

ENGINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
import series as S  # noqa: E402
from render import HEAD  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

PILLAR = {"rules": "settle", "gear": "gear", "market": "number", "pros": "pros"}


def cover_html(r):
    key = PILLAR.get(r.get("pillar"), "settle")
    ser = S.SERIES[key]
    yellow = ser["bg"] == S.C["ball"]
    fg = ser["fg"]
    hl = S.C["court"] if yellow else S.C["ball"]
    acc = S.C["night"] if yellow else S.C["ball"]
    sp = r["spec"]
    if r.get("cover_q"):
        main = S.head(S.fmt(r["cover_q"], hl), 124, fg)
    else:
        main = S.head(S.fmt(sp["claim"], hl), 112, fg) + S.head("Fair or fault?", 112, acc, 40, 0.9)
    play = (f'<div style="margin-top:auto;display:flex;align-items:center;gap:28px">'
            f'<div style="width:132px;height:132px;border-radius:50%;background:{acc};display:flex;align-items:center;justify-content:center">'
            f'<svg width="52" height="60" viewBox="0 0 52 60"><path d="M6 4 L48 30 L6 56 Z" fill="{S.C["ball"] if yellow else S.C["night"]}"/></svg></div>'
            f'<div style="font-family:{S.MONO};font-size:44px;font-weight:700;text-transform:uppercase;color:{fg}">Watch &amp; call it</div></div>')
    body = S.tag(ser["name"], fg) + main + play
    return (HEAD.replace(".post{width:1080px;height:1350px;", ".post{width:1080px;height:1920px;")
            + f'<div class="post" style="background:{ser["bg"]};color:{fg};padding:300px 88px 300px">{body}</div></body></html>')


async def render(week_dir):
    wd = pathlib.Path(week_dir)
    reels = json.loads((wd / "reels.json").read_text())["reels"]
    out = wd / "reels"
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        for r in reels:
            tmp = out / f".cover-{r['id']}.html"
            tmp.write_text(cover_html(r))
            await pg.goto(f"file://{tmp.resolve()}")
            await pg.evaluate("document.fonts.ready")
            await pg.evaluate("""() => { const p = document.querySelector('.post');
                for (const el of document.querySelectorAll('.fit')) { let s = parseFloat(getComputedStyle(el).fontSize);
                  while (p.scrollHeight > p.clientHeight && s > 60) { s -= 4; el.style.fontSize = s + 'px'; } } }""")
            await pg.screenshot(path=str(out / f"{r['id']}.cover.png"))
            tmp.unlink()
            print("cover:", out / f"{r['id']}.cover.png")
        await b.close()


if __name__ == "__main__":
    asyncio.run(render(sys.argv[1]))
