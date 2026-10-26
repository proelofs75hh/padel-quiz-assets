"""Court diagram library for Fair or Fault (shared by carousel explainers and reels).

Court seen from above, 200 x 400 units:
  x 0..200 = width (10 m), y 0..400 = length (20 m), net at y = 200.
  Top half (y < 200) = opponents, bottom half (y > 200) = "you".
  Service lines at y = 61 and y = 339, centre line x = 100 between them.
  Glass: back walls (y = -6 / 406) and the first 80 units of each side wall;
  wire fence (mesh): side walls between y = 80 and y = 320.

Each entry:
  points   ball positions in order (first = where the ball is hit)
  bounces  indices of floor bounces (drawn as yellow rings)
  decisive index of the point that decides the call (ring in verdict colour)
  ok       True if the situation is legal (FAIR), False if it is a fault
  players  optional player positions (dark dots)
  rule     FIP Reglamento de Juego reference the drawing was checked against
Only add a diagram after checking the situation against the FIP rules.
"""
C = dict(court="#1747B0", night="#0E1630", paper="#F4F1E8", glass="#9FC3E3",
         ball="#D7F23A", fault="#C2361F", muted="#4A5470")

LIB = {
    "serve-side-mesh": dict(  # serve bounces in the box, then hits the side fence
        points=[[150, 376], [60, 150], [-2, 104]], bounces=[1], decisive=2, ok=False,
        rule="Regla 7.1.e"),
    "serve-then-glass": dict(  # serve bounces in the box, then hits the back glass
        points=[[150, 376], [60, 150], [35, -2]], bounces=[1], decisive=2, ok=True,
        rule="Regla 7.1.e, 12.3"),
    "serve-wrong-box": dict(  # serve lands in the wrong (straight) box
        points=[[150, 376], [150, 140]], bounces=[1], decisive=1, ok=False,
        rule="Regla 6.6, 7.1.c"),
    "serve-net-cord": dict(  # serve clips the net, then lands in the correct box
        points=[[150, 376], [110, 200], [60, 150]], bounces=[2], decisive=1, ok=True,
        rule="Regla 9.1.a"),
    "volley-return": dict(  # receiver hits the serve before it bounces
        points=[[150, 376], [64, 136]], bounces=[], decisive=1, ok=False,
        players=[[150, 392], [52, 122]], rule="Regla 8.1, Caso 3"),
    "own-back-glass": dict(  # you play the ball into your own back glass, it goes over
        points=[[130, 330], [110, 404], [80, 110]], bounces=[2], decisive=1, ok=True,
        rule="Regla 14.1.b"),
    "direct-back-glass": dict(  # your shot hits their back glass before bouncing
        points=[[120, 300], [90, -2]], bounces=[], decisive=1, ok=False,
        rule="Regla 13.1.g"),
    "bounce-then-glass": dict(  # rally ball bounces on their side, then hits their glass
        points=[[120, 300], [110, 60], [100, -2]], bounces=[1], decisive=2, ok=True,
        rule="Regla 12.3, 14.1.c"),
    "bounce-then-fence": dict(  # rally ball bounces on their side, then hits the side fence
        points=[[120, 300], [40, 130], [-2, 96]], bounces=[1], decisive=2, ok=True,
        rule="Regla 14.1.c"),
    "double-bounce": dict(  # ball bounces twice on your side before you hit it
        points=[[100, 60], [80, 280], [68, 340]], bounces=[1, 2], decisive=2, ok=False,
        rule="Regla 13.1.c"),
    "tiebreak-first-serve": dict(  # tie-break point 1: served from the server's right side, diagonally
        points=[[150, 376], [60, 150]], bounces=[], decisive=0, ok=True,
        rule="Regla 1 (tie-break, punto 3)"),
}


def court_svg(paths="", width=420, height=764, floor=None, el_id=""):
    floor = floor or C["court"]
    idattr = f' id="{el_id}"' if el_id else ""
    return f'''<svg{idattr} viewBox="-22 -22 244 444" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="200" height="400" fill="{floor}"/>
  <rect x="0" y="0" width="200" height="400" fill="none" stroke="#FFF" stroke-width="2.5"/>
  <line x1="0" y1="61" x2="200" y2="61" stroke="#FFF" stroke-width="2.5"/>
  <line x1="0" y1="339" x2="200" y2="339" stroke="#FFF" stroke-width="2.5"/>
  <line x1="100" y1="61" x2="100" y2="339" stroke="#FFF" stroke-width="2.5"/>
  <line x1="-10" y1="200" x2="210" y2="200" stroke="#FFF" stroke-width="5"/>
  <path d="M-6 80 V-6 H206 V80" fill="none" stroke="{C['glass']}" stroke-width="10"/>
  <path d="M-6 320 V406 H206 V320" fill="none" stroke="{C['glass']}" stroke-width="10"/>
  <line x1="-6" y1="80" x2="-6" y2="320" stroke="{C['muted']}" stroke-width="4" stroke-dasharray="3 6"/>
  <line x1="206" y1="80" x2="206" y2="320" stroke="{C['muted']}" stroke-width="4" stroke-dasharray="3 6"/>
  {paths}
</svg>'''


def _mark(x, y, n, col):
    return (f'<circle cx="{x}" cy="{y}" r="17" fill="{col}"/>'
            f'<text x="{x}" y="{y+8}" text-anchor="middle" fill="{C["paper"]}" '
            f'font-family="JetBrains Mono" font-size="22" font-weight="700">{n}</text>')


def static_svg(name, width=420, height=764):
    """Finished diagram for the carousel explainer slide.
    Numbered marks: 1 = first bounce (or the first turning point), 2 = decisive point."""
    d = LIB[name]
    pts = d["points"]
    col = C["ball"] if d["ok"] else C["fault"]
    path = "M" + " L".join(f"{x} {y}" for x, y in pts)
    parts = [f'<path d="{path}" fill="none" stroke="{col}" stroke-width="6" stroke-dasharray="12 8"/>']
    for px, py in d.get("players", []):
        parts.append(f'<circle cx="{px}" cy="{py}" r="12" fill="{C["night"]}" stroke="#FFF" stroke-width="3"/>')
    parts.append(f'<circle cx="{pts[0][0]}" cy="{pts[0][1]}" r="9" fill="{C["night"]}"/>')
    first = d["bounces"][0] if d["bounces"] else (1 if len(pts) > 2 else None)
    marks = {}
    if first is not None and first != d["decisive"]:
        marks[first] = C["night"]
    marks[d["decisive"]] = C["night"] if d["ok"] else C["fault"]
    end = pts[-1]
    last = len(pts) - 1
    if last not in marks:
        parts.append(f'<circle cx="{end[0]}" cy="{end[1]}" r="10" fill="{C["ball"]}" stroke="{C["night"]}" stroke-width="3"/>')
    for n, idx in enumerate(sorted(marks), 1):
        mx, my = pts[idx]
        if idx == last:  # ball ends here: yellow ring around the number
            parts.append(f'<circle cx="{mx}" cy="{my}" r="22" fill="{C["ball"]}"/>')
        parts.append(_mark(mx, my, n, marks[idx]))
    return court_svg("\n  ".join(parts), width, height)


if __name__ == "__main__":
    # contact sheet of all diagrams for checking: python3 engine/diagrams.py out.html
    import sys, pathlib
    cells = "".join(
        f'<div style="display:inline-block;margin:16px;text-align:center;font:600 18px sans-serif">'
        f'{static_svg(k, 210, 382)}<br>{k}<br><span style="color:{"#2a7" if v["ok"] else "#c33"}">'
        f'{"FAIR" if v["ok"] else "FAULT"}</span> · {v["rule"]}</div>' for k, v in LIB.items())
    pathlib.Path(sys.argv[1]).write_text(f"<html><body style='background:#F4F1E8;width:1300px'>{cells}</body></html>")
