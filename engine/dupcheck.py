"""Duplicate check for a planned week against register.json.

Usage:  python3 engine/dupcheck.py weeks/2026-W44
Rules (from the Fair or Fault playbook):
  * A topic_key may not repeat within 90 days of its last use.
  * After 90 days it may return, but the claim must be reworded:
    similarity to every earlier claim with that key must stay below 0.6.
  * No topic_key twice in the same week.
Exit code 1 and a list of problems if any rule is broken.
"""
import datetime as dt, difflib, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK_DAYS = 90
MAX_SIMILARITY = 0.6


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\*\*|\n", " ", t.lower())).strip()


def main(week_dir):
    register = json.loads((ROOT / "register.json").read_text())["posts"]
    spec = json.loads((pathlib.Path(week_dir) / "posts.json").read_text())
    problems, seen = [], set()
    for post in spec["posts"]:
        key, day = post["topic_key"], dt.date.fromisoformat(post["slot"][:10])
        claim = norm(post["slides"][0]["claim"])
        if key in seen:
            problems.append(f"{post['id']}: topic '{key}' twice in this week")
        seen.add(key)
        for old in (r for r in register if r["topic_key"] == key):
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
    spec = json.loads((pathlib.Path(week_dir) / "posts.json").read_text())
    known = {r["id"] for r in reg["posts"]}
    for post in spec["posts"]:
        if post["id"] in known:
            continue
        verdict = next((s["verdict"] for s in post["slides"] if s["type"] == "verdict"), "")
        reg["posts"].append({"id": post["id"], "date": post["slot"][:10], "pillar": post["pillar"],
                             "topic_key": post["topic_key"], "claim": post["slides"][0]["claim"],
                             "verdict": verdict})
    path.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
    print(f"register now holds {len(reg['posts'])} posts")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--register":
        add_to_register(sys.argv[1])
    else:
        sys.exit(main(sys.argv[1]))
