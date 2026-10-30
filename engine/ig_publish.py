"""Publish due, approved posts from weeks/*/queue.json to Instagram (Instagram API with Instagram Login).

Runs in GitHub Actions every 10 minutes (.github/workflows/publish.yml).
Env: IG_ACCESS_TOKEN, IG_USER_ID, MEDIA_BASE (public base URL of the repo at the
current commit, e.g. https://cdn.jsdelivr.net/gh/proelofs75hh/padel-quiz-assets@<sha>/).

  python3 engine/ig_publish.py            publish everything that is due
  python3 engine/ig_publish.py --check    no posting: account, token and publishing limit
  python3 engine/ig_publish.py --only ID  publish this approved item now, even before its slot (test)

Rules
* Only status "approved". Due = slot (Europe/Berlin) <= now. Items more than
  MAX_LATE hours overdue are not posted any more (status "failed", error "too late").
* At most MAX_PER_RUN posts per run, oldest first.
* After each attempt the queue file is written, so a crash never re-posts.
Exit code 1 if any post failed (GitHub then sends a failure e-mail).
"""
import datetime as dt, glob, json, os, pathlib, sys, time, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://graph.instagram.com/" + os.environ.get("IG_API_VERSION", "v23.0")
TZ = ZoneInfo("Europe/Berlin")
MAX_LATE = 6        # hours
MAX_PER_RUN = 3
MAX_ATTEMPTS = 3   # a post that fails 3 runs in a row is marked failed
POLL_SECONDS, POLL_TRIES = 10, 36   # up to 6 minutes for video processing


class IGError(Exception):
    pass


def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            err = json.loads(body).get("error", {})
            msg = f"{err.get('code')}/{err.get('error_subcode')}: {err.get('message')}"
        except Exception:
            msg = body[:300]
        raise IGError(f"{method} {path} -> HTTP {e.code} {msg}") from None


def wait_finished(container):
    for _ in range(POLL_TRIES):
        st = call("GET", container, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise IGError(f"container {container} status {st}")
        time.sleep(POLL_SECONDS)
    raise IGError(f"container {container} not ready after {POLL_SECONDS * POLL_TRIES}s")


def url(base, path):
    return base.rstrip("/") + "/" + urllib.parse.quote(path)


def publish_item(it, base):
    uid = os.environ["IG_USER_ID"]
    if it["kind"] == "carousel":
        children = []
        for img in it["images"]:
            c = call("POST", f"{uid}/media", image_url=url(base, img), is_carousel_item="true")
            children.append(c["id"])
        for c in children:
            wait_finished(c)
        parent = call("POST", f"{uid}/media", media_type="CAROUSEL",
                      children=",".join(children), caption=it["caption"])["id"]
    elif it["kind"] == "reel":
        parent = call("POST", f"{uid}/media", media_type="REELS", video_url=url(base, it["video"]),
                      cover_url=url(base, it["cover"]), caption=it["caption"], share_to_feed="true")["id"]
    else:
        raise IGError(f"unknown kind {it['kind']}")
    wait_finished(parent)
    media_id = call("POST", f"{uid}/media_publish", creation_id=parent)["id"]
    info = call("GET", media_id, fields="permalink,timestamp")
    return {"media_id": media_id, "permalink": info.get("permalink", ""),
            "at": dt.datetime.now(TZ).isoformat(timespec="seconds")}


def check():
    me = call("GET", "me", fields="user_id,username,account_type,media_count")
    lim = call("GET", f"{os.environ['IG_USER_ID']}/content_publishing_limit", fields="config,quota_usage")
    out = {"username": me.get("username"), "account_type": me.get("account_type"),
           "media_count": me.get("media_count"), "user_id_matches": str(me.get("user_id")) == os.environ["IG_USER_ID"],
           "publishing_limit": lim.get("data", [{}])[0],
           "checked_at": dt.datetime.now(TZ).isoformat(timespec="seconds")}
    p = ROOT / "ops" / "check-result.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def main(only=None):
    base = os.environ["MEDIA_BASE"]
    now = dt.datetime.now(TZ)
    due = []
    for qf in sorted(glob.glob(str(ROOT / "weeks" / "*" / "queue.json"))):
        q = json.loads(pathlib.Path(qf).read_text())
        for it in q["items"]:
            if it.get("status") != "approved" or it.get("published"):
                continue
            slot = dt.datetime.fromisoformat(it["slot"]).replace(tzinfo=TZ)
            if only:
                if it["id"] == only:
                    due.append((slot, qf, it["id"]))
            elif slot <= now:
                due.append((slot, qf, it["id"]))
    due.sort()
    failed = 0
    for slot, qf, iid in due[:MAX_PER_RUN] if not only else due:
        path = pathlib.Path(qf)
        q = json.loads(path.read_text())
        it = next(i for i in q["items"] if i["id"] == iid)
        if not only and (now - slot).total_seconds() > MAX_LATE * 3600:
            it["status"], it["error"] = "failed", f"too late: slot {it['slot']}, now {now:%Y-%m-%d %H:%M}"
            failed += 1
        else:
            try:
                it["published"] = publish_item(it, base)
                it["status"], it["error"] = "published", ""
                print(f"published {iid}: {it['published']['permalink']}")
            except IGError as e:
                it["attempts"] = it.get("attempts", 0) + 1
                it["error"] = str(e)[:500]
                if it["attempts"] >= MAX_ATTEMPTS:   # give up, otherwise retry in the next run
                    it["status"] = "failed"
                    failed += 1
                print(f"FAILED {iid} (attempt {it['attempts']}): {e}")
        path.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
    if not due:
        print("nothing due")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--only" in sys.argv:
        main(only=sys.argv[sys.argv.index("--only") + 1])
    else:
        main()
