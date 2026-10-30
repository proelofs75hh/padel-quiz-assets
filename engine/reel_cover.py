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
    """White cover (paper) so reels stand apart from the coloured carousels in the grid; the pillar
    colour appears only as a reference: filled series tag, colour bar on the left, coloured
    "Fair or fault?" and play disc. (30 Oct 2026: reels white again, colour only as a hint.)"""
    key = PILLAR.get(r.get("pillar"), "settle")
    ser = S.SERIES[key]
    col = ser["bg"] if ser["bg"] != S.C["ball"] else S.C["night"]  # yellow is unreadable on white
    tagfg = ser["fg"]
    ink = S.C["night"]
    sp = r["spec"]
    tag = (f'<div style="display:flex"><span style="font-family:{S.MONO};font-size:40px;font-weight:700;letter-spacing:.02em;'
           f'text-transform:uppercase;background:{ser["bg"]};color:{tagfg};border-radius:999px;padding:12px 32px">{ser["name"]}</span></div>')
    if r.get("cover_q"):
        main = S.head(S.fmt(r["cover_q"], col), 124, ink)
    else:
        main = S.head(S.fmt(sp["claim"], col), 112, ink) + S.head("Fair or fault?", 112, col, 40, 0.9)
    play = (f'<div style="margin-top:auto;display:flex;align-items:center;gap:28px">'
            f'<div style="width:132px;height:132px;border-radius:50%;background:{ser["bg"]};display:flex;align-items:center;justify-content:center">'
            f'<svg width="52" height="60" viewBox="0 0 52 60"><path d="M6 4 L48 30 L6 56 Z" fill="{tagfg}"/></svg></div>'
            f'<div style="font-family:{S.MONO};font-size:44px;font-weight:700;text-transform:uppercase;color:{ink}">Watch &amp; call it</div></div>')
    bar = f'<div style="position:absolute;left:0;top:240px;width:28px;height:1440px;background:{ser["bg"]}"></div>'
    body = bar + tag + main + play
    return (HEAD.replace(".post{width:1080px;height:1350px;", ".post{width:1080px;height:1920px;")
            + f'<div class="post" style="position:relative;background:{S.C["paper"]};color:{ink};padding:300px 88px 300px">{body}</div></body></html>')


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
