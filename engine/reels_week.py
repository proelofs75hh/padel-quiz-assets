"""Render all reels of a week from weeks/<week>/reels.json.

Usage:  python3 engine/reels_week.py weeks/2026-W45
reels.json:
{
 "reels": [
  {"id": "2026-11-02-reel", "slot": "2026-11-02T07:30:00", "pillar": "rules",
   "topic_key": "rule.double-bounce", "fact_source": "FIP ... Regla 13.1.c",
   "caption": "...", "hashtags": ["padel", ...],
   "spec": {"format": "refs_view", "label": "Rules", "claim": "...", "verdict": "FAULT",
            "pill": "...", "line": "...", "diagram": "double-bounce"}}
 ]
}
Writes weeks/<week>/reels/<id>.mp4 and <id>.cover.png, plus weeks/<week>/reels/_frames.png
(three frames per reel: question, middle part, verdict) for the visual check.
"""
import asyncio, json, pathlib, subprocess, sys

ENGINE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
import reel  # noqa: E402


def main(week_dir):
    wd = pathlib.Path(week_dir)
    spec = json.loads((wd / "reels.json").read_text())
    out = wd / "reels"
    out.mkdir(exist_ok=True)
    sheets = []
    for r in spec["reels"]:
        s = dict(r["spec"])
        s.setdefault("format", "refs_view")
        mp4 = out / f"{r['id']}.mp4"
        tl = asyncio.run(reel.render(s, mp4))
        print(f"{r['id']}: {s['format']} {tl['T_END']:.1f} s")
        times = [tl["T_READ"] - 0.1, tl["T_CALL"] - 0.3, tl["T_CALL"] + 1.5]
        frames = []
        for i, t in enumerate(times):
            f = out / f".{r['id']}-{i}.png"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4),
                            "-frames:v", "1", "-vf", "scale=270:480", str(f)], check=True)
            frames.append(f)
        sheets.append(frames)
    from PIL import Image
    W, H, g = 270, 480, 10
    sheet = Image.new("RGB", (3 * W + 4 * g, len(sheets) * (H + g) + g), "#DDDDDD")
    for r, frames in enumerate(sheets):
        for c, f in enumerate(frames):
            sheet.paste(Image.open(f), (g + c * (W + g), g + r * (H + g)))
            f.unlink()
    sheet.save(out / "_frames.png")
    print("check:", out / "_frames.png")


if __name__ == "__main__":
    main(sys.argv[1])
