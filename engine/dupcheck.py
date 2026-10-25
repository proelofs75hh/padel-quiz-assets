"""Duplicate check for a planned week against register.json.

Usage:  python3 engine/dupcheck.py weeks/2026-W44
Rules (from the Fair or Fault playbook):
  * A topic_key may not repeat within 90 days of its last use.
  * After 90 days it may return, but the claim must be reworded:
    similarity to every earlier claim with that key must stay below 0.6.
  * No topic_key twice in the same week (carousels and reels together).
Reels from weeks/<week>/reels.json are checked and registered like posts (format "reel").
Exit code 1 and a list of problems if any rule is broken.
"""
import datetime as dt, difflib, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK_DAYS = 90
MAX_SIMILARITY = 0.6


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\*\*|\n", " ", t.lower())).strip()


def items(week_dir):
    """Carousel posts and reels of a week as (id, slot, pillar, topic_key, claim, verdict, kind)."""
    wd = pathlib.Path(week_dir)
    out = []
    if (wd / "posts.json").exists():
        for p in json.loads((wd / "posts.json").read_text())["posts"]:
            v = next((s["verdict"] for s in p["slides"] if s["type"] == "verdict"), "")
            out.append((p["id"], p["slot"], p["pillar"], p["topic_key"], p["slides"][0]["claim"], v, "carousel"))
    if (wd / "reels.json").exists():
        for r in json.loads((wd / "reels.json").read_text())["reels"]:
            out.append((r["id"], r["slot"], r["pillar"], r["topic_key"], r["spec"]["claim"], r["spec"]["verdict"], "reel"))
    return out


def main(week_dir):
    register = json.loads((ROOT / "register.json").read_text())["posts"]
    problems, seen = [], set()
    for pid, slot, pillar, key, claim_raw, verdict, kind in items(week_dir):
        post = {"id": pid}
        day = dt.date.fromisoformat(slot[:10])
        claim = norm(claim_raw)
        if key in seen:
            problems.append(f"{post['id']}: topic '{key}' twice in this week")
        seen.add(key)
        for old in (r for r in register if r["topic_key"] == key and r["id"] != pid):
            age = (day - dt.date.fromisoformat(old["date"])).days
            if age < BLOCK_DAYS:
                problems.append(f"{post['id']}: topic '{key}' used {age} days ago ({old['id']})")
            sim = difflib.SequenceMatcher(None, claim, norm(old["claim"])).ratio()
            if sim >= MAX_SIMILARITY:
                problems.append(f"{post['id']}: claim too close to {old['id']} ({sim:.2f}) - reword")
    for p in problems:
        print("PROBLEM:", p)
    print("dupcheck ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def add_to_register(week_dir):
    """Append a published week to register.json (run after Metricool drafts exist)."""
    path = ROOT / "register.json"
    reg = json.loads(path.read_text())
    known = {r["id"] for r in reg["posts"]}
    for pid, slot, pillar, key, claim, verdict, kind in items(week_dir):
        if pid in known:
            continue
        reg["posts"].append({"id": pid, "date": slot[:10], "pillar": pillar, "topic_key": key,
                             "claim": claim, "verdict": verdict, "format": kind})
    path.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
    print(f"register now holds {len(reg['posts'])} posts")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--register":
        add_to_register(sys.argv[1])
    else:
        sys.exit(main(sys.argv[1]))
