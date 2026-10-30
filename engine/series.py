"""Fair or Fault carousel series (design of 29 Oct 2026).

Four series, one per pillar, each with its own ground colour; the last slide is always
night blue with the logo signature. One statement and at most one picture per slide.

  settle  Settle the Argument  rules   turf green   question+arguing figures / scene / your call / answer
  gear    Gear X-Ray           gear    court blue (plain, no grid)   question+racket / fact drawing / statement+tiles / answer
  pros    Pro Move             pros    ball yellow  question+figure / scene / your call / answer
  number  The Number           market  clay         question+courts / guess bars / reveal / twist (night)

Used by engine/render.py for every post that has a "series" field. Slide types:
  q        {"q": headline, "claim": register claim, optional "figure": pose for pros}
  scene    {"text": one line, "scene": {...}}            (settle, pros)
  fact     {"text": headline, "drawing": "dims"|"holes"|"cord", optional "labels"}  (gear)
  call     {}                                            (settle, pros: "Your answer?" + tiles)
  claim    {"text": statement}                           (gear: statement + "Fair or fault?" + tiles)
  guess    {"bars": ["15,000", "35,000", "58,000"]}      (number)
  reveal   {"big": "58,000+", "text": "...", "source": "..."}  (number, series colour)
  verdict  {"verdict": FAIR|FAULT, "line": "...", "source": "..."}  (night, logo signature)
           number series: {"verdict": "FAIR", "pre": "The FIP even counts", "big": "91,200", "source": "..."}
Text: "\n" = line break, **word** = highlight.
"""
import html, math, re

C = dict(court="#1747B0", night="#0E1630", paper="#F4F1E8", glass="#D6E6F3", ball="#D7F23A",
         fault="#C2361F", muted="#4A5470", chalk="#FFFFFF", turf="#1E6B47", clay="#E2733C")
DISPLAY = "'Bricolage Grotesque','Arial Narrow',sans-serif"
SANS = "'Instrument Sans',system-ui,sans-serif"
MONO = "'JetBrains Mono',ui-monospace,monospace"

SERIES = {
    "settle": dict(name="Settle the argument", bg=C["turf"], fg=C["paper"], acc=C["ball"], line=C["paper"]),
    "gear": dict(name="Gear X-Ray", bg=C["court"], fg=C["paper"], acc=C["ball"], line=C["paper"]),
    "pros": dict(name="Pro move", bg=C["ball"], fg=C["night"], acc=C["night"], line=C["night"]),
    "number": dict(name="The number", bg=C["clay"], fg=C["night"], acc=C["night"], line=C["night"]),
    "lingo": dict(name="Padel lingo", bg="#5B3FD1", fg=C["paper"], acc=C["ball"], line=C["paper"]),
}


def fmt(t, col):
    t = html.escape(t or "")
    t = re.sub(r"\*\*(.+?)\*\*", rf'<span style="color:{col}">\1</span>', t)
    return t.replace("\n", "<br>")


# ---------------------------------------------------------------- building blocks
def wrap(bg, fg, body):
    return (f'<div class="post" style="background:{bg};color:{fg};position:relative">{body}</div>')


def tag(name, fg):
    return (f'<div style="display:flex"><span style="font-family:{MONO};font-size:40px;font-weight:700;letter-spacing:.02em;'
            f'text-transform:uppercase;border:4px solid {fg};border-radius:999px;padding:8px 28px">{html.escape(name)}</span></div>')


def head(text, size, col, mt=56, lh=0.96, extra=""):
    return (f'<h1 class="fit" style="margin:{mt}px 0 0;font-family:{DISPLAY};font-size:{size}px;line-height:{lh};font-weight:800;'
            f'letter-spacing:-.03em;color:{col};{extra}">{text}</h1>')


def para(text, size, col, mt=0):
    return f'<p style="margin:{mt}px 0 0;font-family:{SANS};font-size:{size}px;line-height:1.08;font-weight:700;color:{col}">{text}</p>'


def label(text, col, mt=40, align="left"):
    return (f'<p style="margin:{mt}px 0 0;text-align:{align};font-family:{MONO};font-size:40px;line-height:1.2;font-weight:700;'
            f'text-transform:uppercase;color:{col}">{html.escape(text)}</p>')


def swipe(col, mt=40):
    return label("Swipe →", col, mt, "right")


def tiles(on_yellow=False):
    """Neutral Fair / Fault buttons: both white, same style (no hint at the answer), with an 'OR' disc overlapping both."""
    t = (f"flex:1;padding:44px 0;border-radius:20px;text-align:center;font-family:{DISPLAY};font-size:84px;line-height:1;"
         f"font-weight:800;letter-spacing:-.02em;background:#FFFFFF;color:{C['night']};"
         + (f"border:6px solid {C['night']};" if on_yellow else ""))
    disc_bg, disc_fg = (C["night"], C["ball"]) if on_yellow else (C["ball"], C["night"])
    disc = (f'<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:128px;height:128px;'
            f'border-radius:50%;background:{disc_bg};color:{disc_fg};border:8px solid {C["night"]};box-sizing:border-box;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-family:{MONO};font-size:48px;font-weight:700;letter-spacing:.02em">OR</div>')
    return (f'<div style="position:relative;display:flex;gap:24px;margin-top:auto"><div style="{t}">Fair</div>'
            f'<div style="{t}">Fault</div>{disc}</div>')


def svgbox(w, h, inner, alt):
    return f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{html.escape(alt)}" style="display:block">{inner}</svg>'


def end_block():
    mark = (f'<circle cx="80" cy="80" r="80" fill="{C["court"]}"/>'
            f'<line x1="26" y1="40" x2="134" y2="40" stroke="{C["glass"]}" stroke-width="6"/>'
            f'<line x1="26" y1="120" x2="134" y2="120" stroke="{C["glass"]}" stroke-width="6"/>'
            f'<line x1="80" y1="43" x2="80" y2="117" stroke="{C["chalk"]}" stroke-width="2"/>'
            f'<text x="49" y="102" text-anchor="middle" fill="{C["paper"]}" font-family="Bricolage Grotesque" font-size="56" font-weight="800">F</text>'
            f'<text x="111" y="102" text-anchor="middle" fill="{C["paper"]}" font-family="Bricolage Grotesque" font-size="56" font-weight="800">F</text>'
            f'<circle cx="80" cy="91" r="11" fill="{C["ball"]}"/>')
    return (f'<div style="margin-top:auto;padding-top:48px;border-top:4px solid rgba(244,241,232,.25);display:flex;align-items:center;gap:36px">'
            f'<svg viewBox="0 0 160 160" width="160" height="160" role="img" aria-label="Fair or Fault logo" style="flex:none;display:block">{mark}</svg>'
            f'<div><div style="font-family:{DISPLAY};font-size:72px;line-height:1;font-weight:800;letter-spacing:-.02em;color:{C["paper"]}">Fair or Fault</div>'
            f'<div style="margin-top:12px;font-family:{SANS};font-size:44px;line-height:1.15;font-weight:700;color:{C["ball"]}">Follow for your Daily Padel Quiz</div></div></div>')


# ---------------------------------------------------------------- pictogram figures
POSES = {  # hip at (0,0), y down, facing right
    "point": dict(neck=(4, -150), head=(8, -205), el1=(60, -132), ha1=(130, -140), el2=(-34, -92), ha2=(-8, -52),
                  kn1=(26, 86), ft1=(44, 172), kn2=(-22, 86), ft2=(-40, 172)),
    "shrug": dict(neck=(0, -150), head=(0, -205), el1=(58, -136), ha1=(98, -196), el2=(-58, -136), ha2=(-98, -196),
                  kn1=(30, 86), ft1=(52, 172), kn2=(-30, 86), ft2=(-52, 172)),
    "swing": dict(neck=(14, -148), head=(22, -202), el1=(70, -176), ha1=(112, -222), el2=(-46, -110), ha2=(-86, -84),
                  kn1=(48, 74), ft1=(88, 168), kn2=(-36, 86), ft2=(-62, 172)),
    "smash": dict(neck=(0, -150), head=(-8, -205), el1=(34, -222), ha1=(52, -292), el2=(-52, -172), ha2=(-86, -222),
                  kn1=(30, 80), ft1=(44, 172), kn2=(-22, 66), ft2=(-60, 156)),
    "forehand": dict(neck=(10, -150), head=(16, -205), el1=(70, -110), ha1=(140, -100), el2=(-40, -120), ha2=(-70, -80),
                     kn1=(40, 80), ft1=(70, 170), kn2=(-30, 84), ft2=(-56, 172)),
    "reach": dict(neck=(30, -140), head=(48, -190), el1=(100, -120), ha1=(170, -118), el2=(-20, -100), ha2=(-50, -70),
                  kn1=(50, 76), ft1=(96, 166), kn2=(-30, 84), ft2=(-60, 172)),
    "run": dict(neck=(26, -146), head=(40, -198), el1=(70, -110), ha1=(110, -140), el2=(-30, -100), ha2=(-70, -120),
                kn1=(60, 60), ft1=(40, 150), kn2=(-30, 80), ft2=(-90, 130)),
    "jump": dict(neck=(0, -150), head=(0, -205), el1=(56, -100), ha1=(100, -60), el2=(-50, -130), ha2=(-80, -180),
                 kn1=(34, 70), ft1=(20, 140), kn2=(-26, 74), ft2=(-44, 140)),
}


def racket(x, y, ang, col, hole, s=1.0):
    holes = "".join(f'<circle cx="{cx*s:.1f}" cy="{cy*s:.1f}" r="{4.2*s:.1f}" fill="{hole}"/>'
                    for cx, cy in [(0, -66), (-12, -56), (12, -56), (0, -46), (-12, -36), (12, -36), (0, -26)])
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f})">'
            f'<rect x="{-6*s:.1f}" y="{-6*s:.1f}" width="{12*s:.1f}" height="{30*s:.1f}" rx="{5*s:.1f}" fill="{col}"/>'
            f'<path d="M0 {-96*s:.1f} C {30*s:.1f} {-96*s:.1f}, {40*s:.1f} {-74*s:.1f}, {40*s:.1f} {-50*s:.1f} C {40*s:.1f} {-28*s:.1f}, {24*s:.1f} {-14*s:.1f}, {8*s:.1f} {-8*s:.1f} '
            f'L {-8*s:.1f} {-8*s:.1f} C {-24*s:.1f} {-14*s:.1f}, {-40*s:.1f} {-28*s:.1f}, {-40*s:.1f} {-50*s:.1f} C {-40*s:.1f} {-74*s:.1f}, {-30*s:.1f} {-96*s:.1f}, 0 {-96*s:.1f} Z" fill="{col}"/>'
            f'{holes}</g>')


def figure(x, y, pose, col, sc=1.0, mirror=False, racket_col=None, hole=None):
    P = POSES[pose]

    def pt(k):
        px, py = P[k]
        return (x + (-px if mirror else px) * sc, y + py * sc)

    def poly(a, b, c, w):
        return (f'<polyline points="{a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f} {c[0]:.1f},{c[1]:.1f}" fill="none" stroke="{col}" '
                f'stroke-width="{w*sc:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    hip = (x, y)
    n = pt("neck")
    out = poly(hip, pt("kn1"), pt("ft1"), 30) + poly(hip, pt("kn2"), pt("ft2"), 30)
    out += f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{n[0]:.1f}" y2="{n[1]:.1f}" stroke="{col}" stroke-width="{40*sc:.1f}" stroke-linecap="round"/>'
    out += poly(n, pt("el2"), pt("ha2"), 24) + poly(n, pt("el1"), pt("ha1"), 24)
    hx, hy = pt("head")
    out += f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{36*sc:.1f}" fill="{col}"/>'
    if racket_col:
        ax, ay = pt("ha1")
        ex, ey = pt("el1")
        ang = math.degrees(math.atan2(ay - ey, ax - ex)) + 90
        out += racket(ax, ay, ang, racket_col, hole, sc)
    return out


def bubble(x, y, w, h, text, tail_x, tail_dir, bg, fg, size=64):
    tx, ty = x + tail_x, y + h
    tail = f'<path d="M{tx-22} {ty-2} L{tx + (34 if tail_dir > 0 else -34)} {ty+46} L{tx+22} {ty-2} Z" fill="{bg}"/>'
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="36" fill="{bg}"/>{tail}'
            f'<text x="{x + w/2}" y="{y + h/2 + size*0.35:.0f}" text-anchor="middle" fill="{fg}" font-family="Instrument Sans" font-size="{size}" font-weight="700">{html.escape(text)}</text>')


# ---------------------------------------------------------------- scenes (904 x 720)
def scene_svg(sc, S):
    """Side view ("side") or top view ("top"). Coordinates are in the 904 x 720 box.

    side: ground (y), glass [[x, top]], fence [[x, top, bottom]], net x, figures [{x, y, pose, mirror, scale, color}],
          path [[x,y], ...] or quad ["M..."], ball [x,y], bounce [x]
    top:  court box, net, glass on back walls; path points, ball, marks [[x,y]], box (highlight service box)
    """
    fg, acc = S["line"], (C["ball"] if S["bg"] != C["ball"] else C["night"])
    ball_fill = C["ball"] if S["bg"] != C["ball"] else C["paper"]
    hole = S["bg"]
    o = ""
    if sc.get("view", "side") == "side":
        g = sc.get("ground", 700)
        for x, top in sc.get("glass", []):
            o += f'<rect x="{x}" y="{top}" width="40" height="{g-top}" fill="{C["glass"] if S["bg"] != C["ball"] else C["paper"]}" stroke="{C["night"] if S["bg"] == C["ball"] else "none"}" stroke-width="5"/>'
        for x, top, bot in sc.get("fence", []):
            o += f'<rect x="{x}" y="{top}" width="40" height="{bot-top}" fill="none" stroke="{fg}" stroke-width="5"/>'
            o += "".join(f'<line x1="{x}" y1="{yy}" x2="{x+40}" y2="{yy+20}" stroke="{fg}" stroke-width="3"/>' for yy in range(top, bot - 10, 20))
        o += f'<line x1="0" y1="{g}" x2="904" y2="{g}" stroke="{fg}" stroke-width="8"/>'
        if "net" in sc:
            nx = sc["net"]
            o += f'<rect x="{nx-5}" y="{g-128}" width="10" height="128" fill="{fg if S["bg"] == C["ball"] else C["chalk"]}"/>'
            o += f'<rect x="{nx-45}" y="{g-132}" width="90" height="12" rx="6" fill="{fg if S["bg"] == C["ball"] else C["chalk"]}"/>'
    else:
        x0, y0, w, h = 252, 10, 400, 700
        o += f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="none" stroke="{fg}" stroke-width="6"/>'
        o += f'<line x1="{x0-14}" y1="{y0+h/2}" x2="{x0+w+14}" y2="{y0+h/2}" stroke="{fg}" stroke-width="10"/>'
        sl = h * 6.95 / 20
        for yy in (y0 + h/2 - sl, y0 + h/2 + sl):
            o += f'<line x1="{x0}" y1="{yy:.0f}" x2="{x0+w}" y2="{yy:.0f}" stroke="{fg}" stroke-width="4"/>'
        o += f'<line x1="{x0+w/2}" y1="{y0+h/2-sl:.0f}" x2="{x0+w/2}" y2="{y0+h/2+sl:.0f}" stroke="{fg}" stroke-width="4"/>'
        gl = C["glass"] if S["bg"] != C["ball"] else C["paper"]
        for yy, d in ((y0, 1), (y0 + h, -1)):
            o += f'<path d="M{x0} {yy + d*140} V{yy} H{x0+w} V{yy + d*140}" fill="none" stroke="{gl}" stroke-width="16"/>'
        if sc.get("box"):
            bx, by = sc["box"]
            o += f'<rect x="{bx}" y="{by}" width="{w/2}" height="{sl:.0f}" fill="{acc}" fill-opacity="0.18"/>'
        if sc.get("arrows"):
            for (x1, y1, x2, y2) in sc["arrows"]:
                o += (f'<path d="M{x1} {y1} Q {x1 + (x2-x1)/2 + 120} {(y1+y2)/2}, {x2} {y2}" fill="none" stroke="{acc}" stroke-width="10" stroke-linecap="round"/>'
                      f'<circle cx="{x2}" cy="{y2}" r="14" fill="{acc}"/>')
    for sx in sc.get("shadow", []):
        o += f'<ellipse cx="{sx}" cy="{sc.get("ground", 700) - 4}" rx="90" ry="14" fill="{fg}" fill-opacity="0.25"/>'
    for f in sc.get("figures", []):
        col = {"paper": C["paper"], "ball": C["ball"], "night": C["night"]}[f.get("color", "paper" if S["bg"] != C["ball"] else "night")]
        o += figure(f["x"], f["y"], f["pose"], col, f.get("scale", 0.95), f.get("mirror", False),
                    col if f.get("racket", True) else None, hole)
    if sc.get("path"):
        pts = sc["path"]
        d = "M" + " L".join(f"{x} {y}" for x, y in pts) if isinstance(pts[0], list) else pts[0]
        o += f'<path d="{d}" fill="none" stroke="{acc}" stroke-width="10" stroke-dasharray="24 16" stroke-linecap="round" stroke-linejoin="round"/>'
    for extra in sc.get("paths", []):
        o += f'<path d="{extra}" fill="none" stroke="{acc}" stroke-width="10" stroke-dasharray="24 16" stroke-linecap="round"/>'
    for x, y in sc.get("marks", []):
        o += f'<path d="M{x-16} {y-16} L{x+16} {y+16} M{x+16} {y-16} L{x-16} {y+16}" stroke="{acc}" stroke-width="8" stroke-linecap="round"/>'
    if sc.get("ball"):
        bx, by = sc["ball"]
        o += f'<circle cx="{bx}" cy="{by}" r="24" fill="{ball_fill}" stroke="{C["night"]}" stroke-width="{6 if S["bg"] == C["ball"] else 0}"/>'
    return svgbox(904, 720, o, sc.get("alt", "Padel situation"))


# ---------------------------------------------------------------- gear drawings
def racket_outline(cx, cy, s, ang=0, holes=True, col=C["paper"], w=6):
    hp = ("M0 -260 C 120 -260, 160 -170, 160 -90 C 160 -10, 110 40, 50 62 L 26 110 L -26 110 L -50 62 "
          "C -110 40, -160 -10, -160 -90 C -160 -170, -120 -260, 0 -260 Z")
    hl = ""
    if holes:
        for yy in range(-210, 20, 42):
            for xx in range(-112, 113, 42):
                if (xx / 135) ** 2 + ((yy + 95) / 150) ** 2 < 1:
                    hl += f'<circle cx="{xx}" cy="{yy}" r="9" fill="none" stroke="{col}" stroke-width="{w*0.6:.1f}"/>'
    return (f'<g transform="translate({cx} {cy}) rotate({ang}) scale({s})">'
            f'<path d="{hp}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>'
            f'<path d="M-24 110 L-24 250 Q -24 262 -12 262 L 12 262 Q 24 262 24 250 L 24 110" fill="none" stroke="{col}" stroke-width="{w}"/>'
            f'<path d="M0 30 L 22 70 L -22 70 Z" fill="none" stroke="{col}" stroke-width="{w*0.7:.1f}"/>{hl}</g>')


GRID = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="1350" stroke="{C["paper"]}" stroke-opacity="0.10" stroke-width="2"/>' for x in range(0, 1081, 60)) + \
       "".join(f'<line x1="0" y1="{y}" x2="1080" y2="{y}" stroke="{C["paper"]}" stroke-opacity="0.10" stroke-width="2"/>' for y in range(0, 1351, 60))
BLUEPRINT = f'<svg viewBox="0 0 1080 1350" width="1080" height="1350" aria-hidden="true" style="position:absolute;top:0;left:0">{GRID}</svg>'


def gear_drawing(kind, labels):
    P, B = C["paper"], C["ball"]
    num = lambda x, y, t: f'<div style="position:absolute;left:{x}px;top:{y}px;font-family:{MONO};font-size:60px;line-height:1.05;font-weight:700;color:{B}">{t}</div>'
    if kind == "dims":
        d = (racket_outline(452, 330, 1.05, 0, False) +
             f'<line x1="190" y1="58" x2="190" y2="608" stroke="{B}" stroke-width="6"/>'
             f'<path d="M174 76 L190 58 L206 76 M174 590 L190 608 L206 590" fill="none" stroke="{B}" stroke-width="6"/>'
             f'<line x1="284" y1="20" x2="620" y2="20" stroke="{B}" stroke-width="6"/>'
             f'<path d="M302 4 L284 20 L302 36 M602 4 L620 20 L602 36" fill="none" stroke="{B}" stroke-width="6"/>')
        return (f'<div style="position:relative">{svgbox(904, 640, d, "Racket with length and width dimension lines")}'
                + num(0, 270, labels.get("length", "45.5<br>cm")) + num(650, -20, labels.get("width", "26 cm")) + '</div>')
    if kind == "holes":
        d = (racket_outline(300, 340, 1.0, -10, True) +
             f'<circle cx="300" cy="230" r="70" fill="none" stroke="{B}" stroke-width="8"/>'
             f'<line x1="352" y1="280" x2="560" y2="430" stroke="{B}" stroke-width="8"/>'
             f'<circle cx="700" cy="470" r="190" fill="none" stroke="{B}" stroke-width="10"/>'
             f'<circle cx="640" cy="420" r="52" fill="none" stroke="{P}" stroke-width="8"/>'
             f'<circle cx="770" cy="420" r="52" fill="none" stroke="{P}" stroke-width="8"/>'
             f'<circle cx="705" cy="540" r="52" fill="none" stroke="{P}" stroke-width="8"/>')
        return f'<div style="position:relative">{svgbox(904, 680, d, "Racket with a magnifier on its holes")}</div>'
    if kind == "cord":
        d = (racket_outline(330, 300, 0.95, 0, True) +
             f'<path d="M330 548 C 330 640, 520 680, 600 600 C 680 520, 560 470, 500 520 C 450 560, 420 600, 334 560" fill="none" stroke="{B}" stroke-width="10" stroke-linecap="round"/>')
        return f'<div style="position:relative">{svgbox(904, 680, d, "Racket with its wrist cord")}</div>'
    raise ValueError(kind)


# ---------------------------------------------------------------- cover variants (slide 1)
def _bleed(svg_inner, x, y, w, h, alt):
    """An SVG placed absolutely on the slide; may run off the edge (graphic cover)."""
    return (f'<div style="position:absolute;left:0;top:0;width:1080px;height:1350px;overflow:hidden">'
            f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{html.escape(alt)}" '
            f'style="position:absolute;left:{x}px;top:{y}px;display:block">{svg_inner}</svg></div>')


def cover(post, s, S, q, fg, hl, top, yellow):
    """Optional slide-1 variant via s["cover"]. Returns None for the series default.

    type     giant question, huge "?" running off the right edge          (all series)
    scene    question + the situation drawing from slide 2               (settle, pros)
    versus   question + stacked FAIR / OR / FAULT in outline type          (settle, gear)
    zoom     question + oversized racket head running off the corner      (gear)
    drawing  question + the fact drawing from slide 2                    (gear)
    digits   question + a hidden number "?,???"                           (number)
    """
    kind = s.get("cover")
    if not kind:
        return None
    if kind == "photo":
        return photo_cover(post, s, S, q, fg, top)
    acc = C["ball"] if not yellow else C["night"]
    if kind == "type":
        mark = (f'<text x="0" y="660" font-family="Bricolage Grotesque" font-size="860" font-weight="800" '
                f'fill="{acc}" fill-opacity="{1 if not yellow else 0.16}">?</text>')
        big = _bleed(mark, 700, 560, 760, 760, "Big question mark")
        return big + top + head(q, 150, fg, 72, 0.92, "position:relative") + '<div style="margin-top:auto"></div>' + swipe(fg)
    if kind == "scene":
        sc = next(x for x in post["slides"] if x["type"] == "scene")["scene"]
        svg = scene_svg(sc, S).replace('width="904" height="720"', 'width="904" height="640"')
        return top + head(q, 104, fg) + f'<div style="margin-top:auto">{svg}</div>' + swipe(fg)
    if kind == "versus":
        st = (f"margin:0;font-family:{DISPLAY};font-size:230px;line-height:.86;font-weight:800;letter-spacing:-.04em;")
        words = (f'<p style="{st}color:{fg}">FAIR</p>'
                 f'<p style="margin:6px 0 6px 8px;font-family:{MONO};font-size:56px;font-weight:700;color:{acc}">— OR —</p>'
                 f'<p style="{st}color:{fg}">FAULT</p>')
        return top + head(q, 104, fg) + f'<div style="margin-top:auto">{words}</div>' + swipe(fg)
    if kind == "zoom":
        r = racket_outline(720, 1000, 1.9, -62, True, C["paper"], 5)
        return _bleed(r, 0, 0, 1080, 1350, "Close-up line drawing of a padel racket") + top + \
            head(q, 120, fg, 56, 0.96, "position:relative;max-width:820px") + '<div style="margin-top:auto"></div>' + swipe(fg)
    if kind == "drawing":
        f = next(x for x in post["slides"] if x["type"] == "fact")
        return top + head(q, 104, fg) + f'<div style="margin-top:auto">{gear_drawing(f["drawing"], f.get("labels", {}))}</div>' + swipe(fg)
    if kind == "digits":
        d = s.get("digits", "?,???")
        return (top + head(q, 104, fg) +
                f'<div style="margin-top:auto;font-family:{DISPLAY};font-size:330px;line-height:.84;font-weight:800;'
                f'letter-spacing:-.05em;white-space:nowrap;color:{C["night"]}">{html.escape(d)}</div>' + swipe(fg))
    raise ValueError(f"unknown cover {kind}")


# ---------------------------------------------------------------- photo covers
import pathlib
PHOTOS = pathlib.Path(__file__).resolve().parent.parent / "assets" / "photos"
DUO = {  # shadow, mid, highlight per series
    "settle": ("#04170D", "#2F8A5E", "#E8F6EC"),
    "gear": ("#050F33", "#3767D6", "#E3ECFA"),
    "pros": ("#0E1630", "#7E8F1A", "#F7FDD2"),
    "number": ("#2A0E04", "#B85A2C", "#FCE9DC"),
    "lingo": ("#140A3D", "#5B3FD1", "#ECE6FF"),
}


def _photo_file(pid, series, w, h, focus, zoom):
    """Crop a w x h window (zoom >= 1 = tighter detail) around focus=(fx, fy) and tint it in the series
    duotone. Returns the path of a cached JPEG."""
    from PIL import Image, ImageOps
    out = pathlib.Path("/tmp/fof_photo_cache") / f"{pid}-{series}-{w}x{h}-{focus[0]}-{focus[1]}-{zoom}.jpg"
    if out.exists():
        return out
    out.parent.mkdir(exist_ok=True)
    im = Image.open(PHOTOS / f"{pid}.jpg").convert("RGB")
    sc = max(w / im.width, h / im.height) * zoom
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    x = min(max(0, round(im.width * focus[0] - w / 2)), im.width - w)
    y = min(max(0, round(im.height * focus[1] - h / 2)), im.height - h)
    g = ImageOps.autocontrast(ImageOps.grayscale(im.crop((x, y, x + w, y + h))), cutoff=1)
    d, m, l = DUO[series]
    ImageOps.colorize(g, black=d, white=l, mid=m).save(out, quality=90)
    return out


PLACE = {  # photo block on the slide: left, top, width, height (may run off the edge)
    "right": (180, 600, 980, 830),
    "left": (-80, 600, 960, 830),
    "wide": (0, 600, 1080, 750),
}


def photo_cover(post, s, S, q, fg, top):
    """Photo cover: series-colour band with the question, below it a photo tinted in the series duotone.
    s: photo (id in assets/photos), photo_focus [fx, fy] (crop centre, 0..1), photo_zoom (1 = whole
    photo, 2 = detail), photo_place "right" | "left" | "wide" (block shifted / running off the edge),
    photo_tilt (degrees, e.g. -3)."""
    L, T, W, H = PLACE[s.get("photo_place", "right")]
    f = _photo_file(s["photo"], post["series"], W, H, tuple(s.get("photo_focus", [0.5, 0.5])), s.get("photo_zoom", 1))
    tilt = s.get("photo_tilt", 0)
    img = (f'<div style="position:absolute;left:0;top:0;width:1080px;height:1350px;overflow:hidden">'
           f'<div style="position:absolute;left:{L}px;top:{T}px;width:{W}px;height:{H}px;'
           f'background:url(\'file://{f}\') center/cover;transform:rotate({tilt}deg);transform-origin:50% 0;'
           f'box-shadow:0 24px 60px rgba(14,22,48,.35)"></div></div>')
    sw = swipe(C["paper"])
    return (img + '<div style="position:relative;display:flex;flex-direction:column;flex:1">' + top
            + head(q, 100, fg) + '<div style="margin-top:auto"></div>'
            + f'<div style="text-shadow:0 2px 14px rgba(14,22,48,.9)">{sw}</div></div>')


# ---------------------------------------------------------------- slide builders
def build(post, i):
    S = SERIES[post["series"]]
    s = post["slides"][i]
    last = i == len(post["slides"]) - 1
    t, bg, fg, acc = s["type"], S["bg"], S["fg"], S["acc"]
    yellow = bg == C["ball"]
    blue = ""  # no blueprint grid (removed 30 Oct 2026)
    if last:
        bg, fg = C["night"], C["paper"]
    top = blue + tag(S["name"], fg)
    hl = C["ball"] if not yellow else C["court"]

    if t == "q" and post["series"] == "lingo" and not s.get("cover"):
        # the term itself is the hero: huge, bold, with a yellow "?"; pronunciation/meaning as a dictionary line
        term = html.escape(s["term"])
        say = s.get("say", "")
        size = min(220, int(904 / (0.5 * (len(s["term"]) + 1))))
        pic = ""
        if s.get("scene"):  # the shot drawn small between term and question (slide 1 + 2 merged, 30 Oct)
            pic = ('<div style="margin-top:auto">' + scene_svg(s["scene"], S).replace('width="904" height="720"', 'width="904" height="430"') + '</div>')
        body = (top
                + f'<h1 style="margin:48px 0 0;font-family:{DISPLAY};font-size:{size}px;line-height:.9;'
                  f'font-weight:800;letter-spacing:-.04em;white-space:nowrap;color:{fg}">{term}<span style="color:{C["ball"]}">?</span></h1>'
                + (label(say, C["glass"], 20) if say else "")
                + pic
                + head(fmt(s["q"], hl), 88, fg, 36 if pic else 0, 1.0, "" if pic else "margin-top:auto") + swipe(fg))
        return wrap(bg, fg, body)
    if t == "q":
        q = fmt(s["q"], hl)
        if post["series"] == "settle":
            pic = (bubble(70, 10, 330, 124, "Fair!", 150, 1, C["paper"], C["night"]) +
                   bubble(504, 10, 330, 124, "Fault!", 180, -1, C["paper"], C["night"]) +
                   figure(250, 400, "point", C["paper"], 1.0) + figure(654, 400, "shrug", C["ball"], 1.0, True))
            vis = svgbox(904, 560, pic, "Two faceless players disagree: one says fair, the other says fault")
        elif post["series"] == "gear":
            vis = svgbox(904, 600, racket_outline(452, 310, 1.0, -16), "Blueprint line drawing of a padel racket")
        elif post["series"] == "pros":
            pose = s.get("figure", "smash")
            pic = figure(330, 430, pose, C["night"], 1.0, False, C["night"], C["ball"])
            if pose == "smash":
                pic += (f'<path d="M512 50 Q 700 -10, 904 30" fill="none" stroke="{C["night"]}" stroke-width="10" stroke-dasharray="24 16" stroke-linecap="round"/>'
                        f'<circle cx="482" cy="58" r="26" fill="{C["paper"]}" stroke="{C["night"]}" stroke-width="6"/>')
            pic += f'<line x1="0" y1="{600 if pose != "jump" else 640}" x2="904" y2="{600 if pose != "jump" else 640}" stroke="{C["night"]}" stroke-width="6" stroke-opacity="0.35"/>'
            vis = svgbox(904, 660, pic, "A faceless padel player")
        else:
            pat = [1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0]
            mc = "".join(f'<rect x="{4 + (k % 6) * 152}" y="{4 + (k // 6) * 216}" width="120" height="180" rx="8" fill="{C["night"] if pat[k] else "none"}" stroke="{C["night"]}" stroke-width="6"/>'
                         f'<line x1="{4 + (k % 6) * 152}" y1="{94 + (k // 6) * 216}" x2="{124 + (k % 6) * 152}" y2="{94 + (k // 6) * 216}" stroke="{C["paper"] if pat[k] else C["night"]}" stroke-width="5"/>'
                         for k in range(18))
            mc += f'<circle cx="368" cy="270" r="24" fill="{C["ball"]}" stroke="{C["night"]}" stroke-width="6"/>'
            vis = svgbox(904, 620, mc, "Grid of padel courts seen from above")
        body = top + head(q, 112, fg) + f'<div style="margin-top:auto">{vis}</div>' + swipe(fg)
        body = cover(post, s, S, q, fg, hl, top, yellow) or body
    elif t == "scene":
        body = top + head(fmt(s["text"], hl), 80, fg, 56, 1.0) + f'<div style="margin-top:auto">{scene_svg(s["scene"], S)}</div>' + swipe(fg)
    elif t == "fact":
        body = top + head(fmt(s["text"], hl), 112, fg) + f'<div style="margin-top:auto">{gear_drawing(s["drawing"], s.get("labels", {}))}</div>' + swipe(fg)
    elif t == "call" and s.get("q"):  # call slide that repeats the question (lingo), so nobody forgets it
        body = (top + label("Your answer?", acc if not yellow else C["night"], 0).replace("margin:0px 0 0", "margin:auto 0 0")
                + head(fmt(s["q"], hl), 150, fg, 24, 0.92) + '<div style="height:110px"></div>'
                + tiles(yellow).replace("margin-top:auto", "") + swipe(fg))
    elif t == "call":
        body = top + head("Your answer?", 240, acc if not yellow else C["night"], 0, 0.88, "margin-top:auto") + \
               '<div style="height:120px"></div>' + tiles(yellow).replace("margin-top:auto", "") + swipe(fg)
    elif t == "claim":
        body = (top + head(fmt(s["text"], hl), 112, fg) + head("Fair or fault?", 112, C["ball"], 48, 0.9) +
                tiles(yellow) + swipe(fg))
    elif t == "guess":
        bars = s["bars"]
        vals = [float(re.sub(r"[^0-9.]", "", b)) for b in bars]
        mx = max(vals)
        rows = "".join(f'<div style="margin-top:48px"><div style="font-family:{DISPLAY};font-size:88px;font-weight:800;letter-spacing:-.02em">{html.escape(b)}</div>'
                       f'<div style="margin-top:12px;height:64px;width:{904*v/mx:.0f}px;border-radius:999px;background:{C["night"]}"></div></div>'
                       for b, v in zip(bars, vals))
        body = top + head("Your guess?", 160, fg, 56, 0.9) + f'<div style="margin-top:auto">{rows}</div>' + swipe(fg, 56)
    elif t == "reveal":
        body = (top + head(fmt(s["big"], hl), 230, fg, 0, 0.86, "margin-top:auto;white-space:nowrap") +
                para(fmt(s["text"], hl), 76, fg, 32) + label(s["source"], fg, 40) + '<div style="margin-top:auto"></div>' + swipe(fg, 0))
    elif t == "verdict":
        if post["series"] == "number":
            body = (top + para(fmt(s["pre"], C["ball"]), 76, fg, 0).replace("margin:0px 0 0", "margin:auto 0 0") +
                    head(fmt(s["big"], C["ball"]), 260, C["ball"], 16, 0.86, "white-space:nowrap") +
                    label(s["source"], C["glass"], 40) + end_block())
        else:
            fair = s["verdict"].upper() == "FAIR"
            body = (top + head("FAIR." if fair else "FAULT.", 260, C["ball"] if fair else C["paper"], 0, 0.86, "margin-top:auto") +
                    para(fmt(s["line"], C["ball"]), 76, fg, 48)
                    + (f'<p style="margin:28px 0 0;font-family:{SANS};font-size:46px;line-height:1.2;font-weight:500;color:{C["glass"]}">{fmt(s["desc"], C["paper"])}</p>' if s.get("desc") else "")
                    + label(s["source"], C["glass"], 40) + end_block())
    else:
        raise ValueError(f"unknown slide type {t}")
    return wrap(bg, fg, body)
