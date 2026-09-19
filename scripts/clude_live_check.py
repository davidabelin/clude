"""Check a deployed clude service by playing a table on it (Phase 8.2d).

Two accounts play a game through the same JSON routes the table screen
uses -- sit, deal, poll, work, answer -- and the replay must open at the
end. A second table can be left mid-game across a redeploy to check that
a cold instance rebuilds it at the same pending decision. Every request
kind is timed. Nothing here needs a browser; `docs/web.md`
("Deploying") has the sequence.

    python scripts/clude_live_check.py URL play NAME_A NAME_B
    python scripts/clude_live_check.py URL start NAME_A NAME_B     -> prints a table id
    ... redeploy ...
    python scripts/clude_live_check.py URL resume NAME_A NAME_B TABLE_ID

The accounts are throwaway ones made with ``users add NAME --uri
gs://...`` beforehand, at the default password, and removed after. This
is a maintainer tool, not part of the app and not imported by it.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time

import requests

PASSWORD = "password"
TIMES: dict = {}


def timed(kind, fn):
    t0 = time.perf_counter()
    out = fn()
    TIMES.setdefault(kind, []).append(time.perf_counter() - t0)
    return out


def login(base: str, name: str) -> requests.Session:
    """A signed-in session; the one-time password offer, if pending, is
    declined so the account's password stays what it was."""
    s = requests.Session()
    page = s.get(f"{base}/login").text
    token = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
    r = s.post(f"{base}/login", data={"name": name, "password": PASSWORD, "csrf": token}, allow_redirects=False)
    assert r.status_code == 302, (r.status_code, r.text[:200])
    r = s.get(f"{base}/", allow_redirects=False)
    if r.status_code == 302 and "/password" in r.headers.get("Location", ""):
        page = s.get(f"{base}/password").text
        token = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
        s.post(f"{base}/password", data={"csrf": token, "action": "keep"}, allow_redirects=False)
    return s


def csrf(s: requests.Session, base: str) -> str:
    page = s.get(f"{base}/").text
    return re.search(r'<meta name="csrf" content="([^"]+)"', page).group(1)


def poll(s, base, tid, since=0):
    r = timed("poll", lambda: s.get(f"{base}/tables/{tid}/poll?since={since}"))
    assert r.status_code == 200, r.text[:200]
    return r.json()


def work(s, base, tid):
    r = timed("work", lambda: s.post(f"{base}/tables/{tid}/work", data={"csrf": csrf(s, base)}))
    assert r.status_code == 200, r.text[:200]
    return r.json()


def answer(s, base, tid, seq, data):
    r = timed(
        "answer",
        lambda: s.post(
            f"{base}/tables/{tid}/answer",
            data={"csrf": csrf(s, base), "seq": str(seq), "data": json.dumps(data)},
        ),
    )
    assert r.status_code == 200, r.text[:300]
    return r.json()


def simple(pending: dict):
    """A legal answer to any decision: the first move, a fixed
    suggestion, no accusation, the first card."""
    kind = pending["kind"]
    if kind == "movement":
        option = pending["options"][0]
        return {"move": option["move"], "to": option["to"]}
    if kind == "suggestion":
        return {"suspect": "Plum", "weapon": "Rope"}
    if kind == "accusation":
        return None
    return {"card": pending["candidates"][0]}


def play_out(base, tid, clients: dict, limit=3000, stop_after=None):
    """Drive a table through the JSON routes until it ends, or until
    `stop_after` answers have been given."""
    first = next(iter(clients.values()))
    payload = poll(first, base, tid)
    answered = 0
    for _ in range(limit):
        if payload["finished"]:
            return payload
        if payload["waiting"] is not None:
            who = payload["waiting"]["seat"]
            label = next(s["label"] for s in payload["seats"] if s["seat"] == who)
            owner = clients[label]
            mine = poll(owner, base, tid)
            assert mine["pending"] is not None, "the owner was not shown the decision"
            payload = answer(owner, base, tid, mine["pending"]["seq"], simple(mine["pending"]))
            answered += 1
            if stop_after and answered >= stop_after:
                return payload
        elif payload["work"]:
            payload = work(first, base, tid)
            if payload.get("did") == "waiting":
                time.sleep(1.6)
        else:
            time.sleep(0.5)
            payload = poll(first, base, tid)
    raise SystemExit("the game did not end")


def new_table(s, base, seats: dict) -> str:
    fields = {"csrf": csrf(s, base), "seed": "7"}
    fields.update({f"seat-{token}": value for token, value in seats.items()})
    r = s.post(f"{base}/tables", data=fields, allow_redirects=False)
    assert r.status_code == 302, r.text[:300]
    return r.headers["Location"].rstrip("/").split("/")[-1]


def seat_and_deal(a, b, base) -> str:
    tid = new_table(a, base, {"Scarlett": "me", "Mustard": "character", "White": "character", "Green": "open"})
    assert "Waiting for players" in a.get(f"{base}/tables/{tid}").text
    r = b.post(f"{base}/tables/{tid}/sit", data={"csrf": csrf(b, base), "token": "Green"}, allow_redirects=False)
    assert r.status_code == 302, r.text[:200]
    r = a.post(f"{base}/tables/{tid}/deal", data={"csrf": csrf(a, base)}, allow_redirects=False)
    assert r.status_code == 302, r.text[:200]
    return tid


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("url", help="The service, e.g. https://clude-....run.app")
    parser.add_argument("phase", choices=("play", "start", "resume"))
    parser.add_argument("name_a")
    parser.add_argument("name_b")
    parser.add_argument("table_id", nargs="?", default="", help="For resume: the table `start` printed.")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")
    a, b = login(base, args.name_a), login(base, args.name_b)
    clients = {args.name_a.lower(): a, args.name_b.lower(): b}

    if args.phase == "play":
        tid = seat_and_deal(a, b, base)
        t0 = time.perf_counter()
        final = play_out(base, tid, clients)
        print(f"table {tid} finished in {time.perf_counter() - t0:.1f}s: turns {final['turns']}, {final['over']}")
        r = a.get(f"{base}{final['over']['replay']}")
        assert r.status_code == 200 and "replay-data" in r.text, "the replay did not open"
        print("replay opens")
        view_b = poll(b, base, tid)
        assert view_b["me"]["seat"] == 3 and view_b["notepad"] is not None
    elif args.phase == "start":
        tid = seat_and_deal(a, b, base)
        payload = play_out(base, tid, clients, stop_after=3)
        print(f"TABLE {tid}: turns {payload['turns']}, seq {payload['seq']}, waiting on {payload['waiting']}")
        print("now redeploy, then run `resume` with that id")
    else:
        if not args.table_id:
            parser.error("resume needs the table id `start` printed")
        t0 = time.perf_counter()
        payload = poll(a, base, args.table_id)
        print(
            f"first poll after the redeploy (the cold rebuild): {time.perf_counter() - t0:.1f}s; "
            f"turns {payload['turns']}, seq {payload['seq']}, waiting on {payload['waiting']}"
        )
        final = play_out(base, args.table_id, clients)
        print(f"table {args.table_id} finished: turns {final['turns']}, {final['over']}")

    for kind, values in TIMES.items():
        print(f"{kind}: n={len(values)}, median {statistics.median(values) * 1000:.0f} ms, max {max(values) * 1000:.0f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
