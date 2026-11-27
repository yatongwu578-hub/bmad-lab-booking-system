"""Offline correlation of approved W01 browser, guard, snapshot and ACL evidence."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path


def need(value, text):
    if not value:
        raise SystemExit("STORY25_W01_FINISH_FAILED " + text)


def read(file):
    return json.loads(file.read_text(encoding="utf-8-sig"))


def lines(file):
    return [json.loads(line) for line in file.read_text(encoding="utf-8-sig").splitlines()]


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def evidence_key(obj):
    return tuple(obj[key] for key in ("method","path","query_sha256","status"))


def acl_key(obj):
    cols = sorted(obj["history_columns"], key=lambda x: x["column"])
    acl = sorted((x["column"], int(x["grantee"]), int(x["grantor"]), x["privilege"], x["grantable"])
                 for x in obj["history_explicit"])
    return (obj["identity"], obj["history_table"], cols, acl, obj["existing_rights"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "after", "server", "anonymous", "student", "teacher", "admin", "result"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--automated", action="store_true")
    parser.add_argument("--tool-fixture", action="store_true")
    args = parser.parse_args()
    before, after = read(args.before), read(args.after)
    db, pg_port = ("test_lab_booking", 55435) if args.tool_fixture else ("lab_booking", 5433)
    for x in (before,after):
        need(x["acl_result"] == "EXACT_COLUMNS_PRESENT" and x["missing"] == []
             and x["identity"]["role"] == x["identity"]["login"] == "lab_booking_app"
             and x["identity"]["database"] == db and x["identity"]["port"] == pg_port
             and x["identity"]["host"] == "127.0.0.1" and x["identity"]["version"] == "170012"
             and x["identity"]["read_only"] == "on", "exact runtime ACL not present")
    need(not args.tool_fixture or before["desired_port"] == 49173, "unexpected tool fixture browser endpoint")
    need(acl_key(before) == acl_key(after), "ACL drift during formal browser verification")
    facts = ("reservations","equipment","history_projected","account_security")
    need(all(before["business_snapshot"][x] == after["business_snapshot"][x] for x in facts),
         "business snapshot drift")
    server = lines(args.server)
    need(server[0]["event"] == "ready" and server[-1]["event"] == "stop"
         and server[0]["inspection_sha256"] == sha_bytes(args.before.read_bytes())
         and server[0]["port"] == before["desired_port"], "guard process or input mismatch")
    observed = [x for x in server if x["event"] == "document"]
    need(not any(x["guard_blocked"] or int(x["status"]) >= 500 for x in observed), "a guard or server failure occurred")
    need(all(not x["allowed_tech_writes"] or (
        x["method"] == "POST" and x["path"] in ("/login/","/logout/")
        and set(x["allowed_tech_writes"]) <= ({"session","last_login"} if x["path"]=="/login/" else {"session"})
    ) for x in observed), "non-technical writes were observed")
    if args.automated:
        need(all(x.get("business_sql_categories") == [] for x in observed
                 if x["path"].startswith("/reservations/manage/") and x["status"] in (302, 403)),
             "denied reservation request performed business SQL or did not archive its SQL category")

    scopes = []
    route = "/reservations/manage/"
    sample = before["samples"]
    if sample["full_unsafe_pending"] == 0:
        scopes.append(("full", route, False))
    filters = sample["filter"]
    if filters:
        scopes.append(("filter", route, True))
    detail = sample["detail"]
    if detail:
        scopes.append(("detail",f"{route}{detail['id']}/",False))
    if filters and filters["detail_id"] is not None:
        scopes.append(("filtered-detail",f"{route}{filters['detail_id']}/",True))
    need(scopes, "there are no safe existing reservation paths to exercise")

    browsers = []
    coverage = {}
    origin = "http://127.0.0.1:" + str(before["desired_port"])
    for role in ("anonymous","student","teacher","admin"):
        stream = lines(getattr(args,role))
        head, tail = stream[0], stream[-1]
        need(head["event"] == "capture-ready" and head["origin"] == origin and tail["event"] == "capture-stop"
             and not tail["body_errors"] and not tail["aborted"] and not tail["pending"]
             and all(x["role"] == role for x in stream), f"{role} browser receipt incomplete")
        docs = [x for x in stream if x["event"] == "document"]
        if args.automated and role != "anonymous":
            wanted = ["authenticated identity and role-specific management link"]
            if role == "admin":
                wanted += ["complete list, search and no future mutation controls",
                           "detail summary and persisted history", "affected scope or existing-device empty result"]
                if filters and filters["detail_id"] is not None:
                    wanted.append("filtered detail summary")
            else:
                wanted += ["denial page contains no reservation projection"] * 3
            need([x["label"] for x in stream if x["event"] == "dom-assertion" and x["passed"] is True] == wanted,
                 f"{role} missing automated DOM checks")
        reserved = [x for x in docs if x["path"].startswith(route)]
        need(reserved and all(not x["served_from_cache"] and (
            x["body_sha256"] or 300 <= x["status"] < 400
        ) for x in reserved), f"{role} missing response body digest or cached reservation document")
        if role != "anonymous":
            need(any(x["method"] == "POST" and x["path"] == "/login/" and x["status"] == 302 for x in docs)
                 and any(x["path"] == "/identity/" and x["status"] == 200 for x in docs),
                 f"{role} missing native login and identity page")
            if args.automated:
                need(any(x["method"] == "POST" and x["path"] == "/logout/" and x["status"] == 302 for x in docs),
                     f"{role} missing native logout")
        expected = {"anonymous":302,"admin":200}.get(role,403)
        need(all(x["method"] == "GET" and x["status"] == expected for x in reserved),
             f"{role} unexpected extra reservation status or method")
        matched = []
        for name, path, filtered in scopes:
            if role != "admin" and name == "filtered-detail":
                continue
            # The guard admits only the inspected device number in filtered paths.
            # Match the exact raw query hash across browser and server below, but allow equivalent encodings.
            hits = [x for x in reserved if x["method"] == "GET" and x["path"] == path and
                    (x["query_sha256"] is not None) == filtered
                    and x["status"] == expected]
            need(hits, f"{role} missing {name} status {expected}")
            if role == "anonymous":
                need(all((x["redirect"] or {}).get("path") == "/login/" for x in hits), "anonymous redirect mismatch")
            if role == "admin":
                need(all("no-store" in (x["cache_control"] or "") for x in hits), "administrator page cache mismatch")
            matched.append(name)
        coverage[role] = matched
        browsers.extend(docs)
    need(Counter(map(evidence_key,browsers)) == Counter(map(evidence_key,observed)),
         "Chrome and guard request/response ledgers are not equal")
    result = {"w01_scope": "formal smoke machine evidence, not team acceptance", "role_coverage": coverage,
              "full_page_skipped_due_candidate_risk": sample["full_unsafe_pending"] != 0,
              "sample_status_counts": sample["status_counts"], "matched_documents":len(browsers),
              "business_and_acl_unchanged": True, "automated_dom": args.automated}
    with args.result.open("x",encoding="utf-8") as out:
        json.dump(result,out,ensure_ascii=False,indent=2)
        out.write("\n")
    print("STORY25_W01_SMOKE_EVIDENCE_OK")


if __name__ == "__main__":
    main()
