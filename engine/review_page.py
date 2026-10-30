"""Build the files of the approval page (Claude artifact "Fair or Fault Freigabe").

Usage:  python3 engine/review_page.py weeks/2026-W45 [weeks/2026-W46 ...]

Writes .review_build/ (git-ignored): index.html (from engine/review_template.html),
data/review.json, img/*.jpg (slide thumbnails 540 px), video/*.mp4 and files.json
(the files map for the Artifact publish call). Approvals are stored in the artifact's
db collection "reviews" ({status: approved|redo|pending, note, rev, at}) and synced
into weeks/*/queue.json by engine/sync_reviews.py.
"""
import datetime as dt, json, pathlib, shutil, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / ".review_build"
DAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def thumb(src: pathlib.Path, dst: pathlib.Path, w=540):
    im = Image.open(src).convert("RGB")
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "JPEG", quality=80, optimize=True, progressive=True)


def build(week_dirs):
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True); (OUT / "video").mkdir(); (OUT / "data").mkdir()
    items, weeks = [], []
    for wd in week_dirs:
        wd = pathlib.Path(wd).resolve()
        q = json.loads((wd / "queue.json").read_text())
        weeks.append(q["week"])
        for it in q["items"]:
            d = {k: it.get(k, "") for k in ("id", "kind", "slot", "series", "pillar", "claim", "question",
                                             "verdict", "fact_source", "caption", "rev", "error")}
            d["server_status"] = it.get("status") if it.get("status") in ("published", "failed") else ""
            d["permalink"] = (it.get("published") or {}).get("permalink", "")
            d["server_note"] = it.get("review_note", "")
            if it["kind"] == "carousel":
                d["images"] = []
                for n, img in enumerate(it["images"], 1):
                    name = f"img/{it['id']}-{n}-{it['rev']}.jpg"
                    thumb(ROOT / img, OUT / name)
                    d["images"].append(name)
            else:
                name = f"video/{it['id']}-{it['rev']}.mp4"
                shutil.copy(ROOT / it["video"], OUT / name)
                d["video"] = name
                d["poster"] = f"img/{it['id']}-cover-{it['rev']}.jpg"
                thumb(ROOT / it["cover"], OUT / d["poster"])
            items.append(d)
    items.sort(key=lambda i: i["slot"])
    first, last = dt.date.fromisoformat(items[0]["slot"][:10]), dt.date.fromisoformat(items[-1]["slot"][:10])
    title = f"{', '.join('KW ' + w.split('-W')[1] for w in weeks)} · {first:%d.%m.}–{last:%d.%m.%Y}"
    (OUT / "data" / "review.json").write_text(json.dumps({"title": title, "weeks": weeks, "items": items},
                                                          ensure_ascii=False, indent=1))
    shutil.copy(ROOT / "engine" / "review_template.html", OUT / "index.html")
    files = {str(p.relative_to(OUT)): str(p) for p in sorted(OUT.rglob("*"))
             if p.is_file() and p.name not in ("index.html", "files.json")}
    (OUT / "files.json").write_text(json.dumps(files, indent=1))
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"review page: {len(items)} posts, {len(files)} files, {size/1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    build(sys.argv[1:])
