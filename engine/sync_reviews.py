"""Apply the approvals from the review page to weeks/*/queue.json.

Usage:  python3 engine/sync_reviews.py <dir with reviews/*.json>

The review page (Claude artifact "Fair or Fault Freigabe") stores one document per post in
its db collection "reviews": {status: approved|redo|pending, note, rev, at}. Claude exports
them with ArtifactData list (out_dir) and runs this script. A review only counts for the
revision (rev) it was given for - after a post is re-made it is "pending" again.

Prints a JSON summary: {"changed": [...], "redo": [{"id","week","note"}], "published": [...],
"failed": [...]} so the calling session knows what to re-make and what to report.
"""
import glob, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_reviews(d):
    out = {}
    for f in glob.glob(str(pathlib.Path(d) / "**" / "*.json"), recursive=True):
        doc = json.loads(pathlib.Path(f).read_text())
        body = doc.get("data", doc)
        out[pathlib.Path(f).stem] = body
    return out


def main(review_dir):
    reviews = load_reviews(review_dir)
    summary = {"changed": [], "redo": [], "published": [], "failed": []}
    for qf in sorted(glob.glob(str(ROOT / "weeks" / "*" / "queue.json"))):
        path = pathlib.Path(qf)
        q = json.loads(path.read_text())
        dirty = False
        for it in q["items"]:
            if it.get("status") == "published":
                summary["published"].append({"id": it["id"], "permalink": (it.get("published") or {}).get("permalink", "")})
                continue
            if it.get("status") == "failed":
                summary["failed"].append({"id": it["id"], "error": it.get("error", "")})
                continue
            r = reviews.get(it["id"])
            want = "pending"
            if r and r.get("rev") == it.get("rev") and r.get("status") in ("approved", "redo"):
                want = r["status"]
            if want != it.get("status") or (want == "redo" and r.get("note", "") != it.get("note", "")):
                it["status"] = want
                it["note"] = r.get("note", "") if want == "redo" else ""
                dirty = True
                summary["changed"].append({"id": it["id"], "status": want})
            if want == "redo":
                summary["redo"].append({"id": it["id"], "week": q["week"], "kind": it["kind"], "note": it["note"]})
        if dirty:
            path.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
