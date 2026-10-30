"""Build the Instagram publishing queue for a week.

Usage:  python3 engine/build_queue.py weeks/2026-W45

Reads weeks/<week>/posts.json (carousels) and reels.json (reels), converts every
slide and reel cover to JPEG (the Instagram API only takes JPEG images) and writes
weeks/<week>/queue.json. Existing review/publish state in queue.json is kept, so the
script can be re-run after a post was re-made.

queue.json
{
 "week": "2026-W45",
 "items": [
  {"id": "2026-11-02-am", "kind": "carousel", "slot": "2026-11-02T08:00:00",
   "series": "settle", "claim": "...", "verdict": "FAULT",
   "images": ["weeks/2026-W45/2026-11-02-am-1.jpg", ...],
   "caption": "full text incl. photo credit and hashtags",
   "status": "pending" | "approved" | "redo" | "published" | "failed",
   "note": "", "published": null | {"media_id": "...", "permalink": "...", "at": "..."},
   "error": ""}
  {"id": "2026-11-02-reel", "kind": "reel", "video": "weeks/.../reels/x.mp4",
   "cover": "weeks/.../reels/x.cover.jpg", ...}
 ]
}
Only items with status "approved" are published (engine/ig_publish.py).
"""
import hashlib, json, pathlib, sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
CREDITS = ROOT / "assets" / "photos" / "credits.json"


def jpeg(png: pathlib.Path) -> pathlib.Path:
    """PNG -> JPEG next to it (quality 92, RGB). Re-converts when the PNG is newer."""
    out = png.with_suffix(".jpg")
    if not out.exists() or out.stat().st_mtime < png.stat().st_mtime:
        Image.open(png).convert("RGB").save(out, "JPEG", quality=92, optimize=True, progressive=True)
    return out


def rel(p: pathlib.Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def caption(text, hashtags, photo_author=None):
    parts = [text.strip()]
    if photo_author and "Photo:" not in text:  # some captions already carry the credit
        parts.append(f"Photo: {photo_author} / Unsplash")
    if hashtags:
        parts.append(" ".join("#" + h.lstrip("#") for h in hashtags))
    return "\n\n".join(parts)


def verdict_of(post):
    return next((s.get("verdict", "") for s in post["slides"] if s.get("type") == "verdict"), "")


def build(week_dir):
    wd = pathlib.Path(week_dir).resolve()
    credits = json.loads(CREDITS.read_text()) if CREDITS.exists() else {}
    qpath = wd / "queue.json"
    old = {i["id"]: i for i in json.loads(qpath.read_text())["items"]} if qpath.exists() else {}
    items = []

    if (wd / "posts.json").exists():
        for p in json.loads((wd / "posts.json").read_text())["posts"]:
            n = len(p["slides"])
            pngs = [wd / f"{p['id']}-{i}.png" for i in range(1, n + 1)]
            missing = [x.name for x in pngs if not x.exists()]
            if missing:
                raise SystemExit(f"{p['id']}: slides missing {missing} - run engine/render.py first")
            s0 = p["slides"][0]
            author = credits.get(s0.get("photo"), {}).get("author") if s0.get("cover") == "photo" else None
            items.append(dict(
                id=p["id"], kind="carousel", slot=p["slot"], series=p.get("series", ""),
                pillar=p.get("pillar", ""), difficulty=p.get("difficulty", ""),
                claim=s0.get("claim") or s0.get("q", ""), question=s0.get("q", ""),
                verdict=verdict_of(p), fact_source=p.get("fact_source", ""),
                images=[rel(jpeg(x)) for x in pngs],
                caption=caption(p["caption"], p.get("hashtags", []), author)))

    if (wd / "reels.json").exists():
        for r in json.loads((wd / "reels.json").read_text())["reels"]:
            mp4 = wd / "reels" / f"{r['id']}.mp4"
            cov = wd / "reels" / f"{r['id']}.cover.png"
            if not mp4.exists() or not cov.exists():
                raise SystemExit(f"{r['id']}: video or cover missing - run engine/reels_week.py first")
            items.append(dict(
                id=r["id"], kind="reel", slot=r["slot"], series=r.get("series", r.get("pillar", "")),
                pillar=r.get("pillar", ""), claim=r["spec"].get("claim", ""), question=r.get("cover_q", ""),
                verdict=r["spec"].get("verdict", ""), fact_source=r.get("fact_source", ""),
                video=rel(mp4), cover=rel(jpeg(cov)),
                caption=caption(r["caption"], r.get("hashtags", []))))

    for it in items:  # content revision: changes whenever media or caption change (approvals are per revision)
        h = hashlib.sha1(it["caption"].encode())
        for f in it.get("images", []) + [it.get("video", ""), it.get("cover", "")]:
            if f:
                h.update((ROOT / f).read_bytes())
        it["rev"] = h.hexdigest()[:10]
    for it in items:  # keep review / publish state
        o = old.get(it["id"], {})
        same = o.get("rev") == it["rev"]
        it["status"] = o.get("status", "pending") if same or o.get("published") else "pending"
        it["note"] = o.get("note", "")
        it["published"] = o.get("published")
        it["error"] = o.get("error", "")
    items.sort(key=lambda i: i["slot"])
    qpath.write_text(json.dumps({"week": wd.name, "items": items}, indent=1, ensure_ascii=False) + "\n")
    print(f"queue: {len(items)} items -> {rel(qpath)}")
    return items


if __name__ == "__main__":
    build(sys.argv[1])
