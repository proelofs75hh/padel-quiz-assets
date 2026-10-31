"""Re-render single posts of a week without touching the others (their approvals stay valid).

Usage:  python3 engine/render_one.py weeks/2026-W45 2026-11-03-am [2026-11-04-pm ...]
Carousels come from posts.json, reels (ids in reels.json) are re-rendered with reel.py + reel_cover.py.
Writes the new PNGs / MP4 + cover into the week folder and a contact sheet _redo_sheet.png there.
"""
import json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main(week, ids):
    wd = pathlib.Path(week).resolve()
    posts = json.loads((wd / "posts.json").read_text())["posts"] if (wd / "posts.json").exists() else []
    reels = json.loads((wd / "reels.json").read_text())["reels"] if (wd / "reels.json").exists() else []
    sel_p = [p for p in posts if p["id"] in ids]
    sel_r = [r for r in reels if r["id"] in ids]
    missing = set(ids) - {p["id"] for p in sel_p} - {r["id"] for r in sel_r}
    if missing:
        raise SystemExit(f"unknown ids: {sorted(missing)}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="fof_redo_"))
    if sel_p:
        (tmp / "posts.json").write_text(json.dumps({"posts": sel_p}, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "engine" / "render.py"), str(tmp)], check=True)
        for p in sel_p:
            for old in wd.glob(f"{p['id']}-[0-9]*.*"):
                old.unlink()
            for n in range(1, len(p["slides"]) + 1):
                shutil.copy2(tmp / f"{p['id']}-{n}.png", wd / f"{p['id']}-{n}.png")
        shutil.copy2(tmp / "_sheet.png", wd / "_redo_sheet.png")
    if sel_r:
        rt = tmp / "r"
        rt.mkdir()
        (rt / "reels.json").write_text(json.dumps({"reels": sel_r}, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "engine" / "reels_week.py"), str(rt)], check=True)
        (wd / "reels").mkdir(exist_ok=True)
        for r in sel_r:
            for old in (wd / "reels").glob(f"{r['id']}.*"):
                old.unlink()
            for f in (rt / "reels").glob(f"{r['id']}.*"):
                shutil.copy2(f, wd / "reels" / f.name)
        shutil.copy2(rt / "reels" / "_frames.png", wd / "reels" / "_redo_frames.png")
    print("re-rendered:", [p["id"] for p in sel_p] + [r["id"] for r in sel_r])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
