"""Offline review of an actual Story 2.5 evidence batch. Never connects to a database."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode


CASES = (
    "navigation-history", "filtered-affected", "ordered-locks", "no-pending-clock", "edge-input",
    "permissions", "revoked-while-waiting", "frozen-concurrent-additions", "crossed-start",
    "submit-first", "query-first", "commit-after-end", "late-projection-failed", "history-second",
    "commit-rejected", "commit-disconnected", "confirmation-lost",
)
STAGES = (
    "verification-locks", "preflight", "baseline-before", "check", "migration-drift", "targeted",
    "baseline-after-targeted", "regression", "baseline-after-regression", "independent",
    "baseline-after-independent", "complete",
)
IDENTITY = ["test_lab_booking", "lab_booking_test", "lab_booking_test", "127.0.0.1", 5433,
            "170012", "read committed", False, False]
DEVELOPER_RUN = "story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4"
CASE_ID = re.compile(r"^(test_\w+) \(([a-zA-Z_][a-zA-Z0-9_.]+)\) \.\.\. ok$")


def need(condition, label):
    if not condition:
        raise SystemExit(f"STORY25_AUDIT_FAILED {label}")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(path):
    return path.read_text(encoding="utf-8-sig")


def jsonl(path):
    return [json.loads(line) for line in read(path).splitlines()]


def time(value):
    return datetime.fromisoformat(value)


def data(snapshot):
    return {key: value for key, value in snapshot.items() if key != "observed_at"}


def trace(record, key="result"):
    return record[key]["server"]


def status(record, key="result"):
    return record[key]["response"]["status"]


def locks(server):
    return [s["bind"][0] for s in server["statements"] if "FOR UPDATE" in s["sql"]]


def writes(server):
    return [s for s in server["statements"] if s["sql"].startswith(('UPDATE "reservations_reservation"',
                                                                    'INSERT INTO "audit_operationhistory"'))]


def audit_m01(group):
    m = group["edge-input"].get("m01")
    need(isinstance(m, dict), "missing M01 evidence in edge-input")
    pk, before = m["reservation_id"], m["before"]
    path = f"/reservations/manage/{pk}/"
    old = before["rows"]
    need(len(old) == 1 and old[0]["id"] == pk and old[0]["status"] == "pending"
         and time(old[0]["start_at"]) <= time(before["observed_at"])
         and not before["effective"] and not before["history"], "M01 overdue pending baseline")
    suffixes = ("?equipment=", "?equipment=%20", "?equipment=a&equipment=b",
                "?equipment=" + "x" * 33, "?equipment=%00")
    need(len(m["invalid"]) == len(suffixes), "M01 invalid case count")
    for item, suffix in zip(m["invalid"], suffixes, strict=True):
        result = item["result"]
        server = result["server"]
        need(result["path"] == path + suffix and result["response"]["status"] == 400
             and "设备编号参数无效。" in result["response"]["body"]
             and "操作历史" not in result["response"]["body"]
             and server["principal"]["role"] == "admin"
             and not any(server[key] for key in ("statements", "decisions", "commits", "history_attempts"))
             and data(item["after"]) == data(before), "M01 invalid detail SQL or durable effects")
    legal, repeated, after = m["legal"], m["repeated"], m["after_legal"]
    query = "?" + urlencode({"equipment": before["device"]["number"]})
    server = legal["server"]
    need(legal["path"] == path + query and legal["response"]["status"] == 200
         and f'href="/reservations/manage/{query}"' in legal["response"]["body"]
         and locks(server) == [before["device"]["id"]] and len(server["decisions"]) == len(server["commits"]) == 1
         and server["history_attempts"] == 1 and len(writes(server)) == 2
         and after["rows"] == [{**old[0], "status": "expired"}]
         and after["device"] == before["device"] and not after["effective"] and len(after["history"]) == 1,
         "M01 legal detail must persist exactly one expiry")
    history = after["history"][0]
    need(history["reservation_id"] == pk and history["action"] == "expire" and history["actor_type"] == "system"
         and history["actor_id"] is None and history["before_status"] == "pending"
         and history["after_status"] == "expired" and history["reason"] == "开始时间已到仍待审核"
         and time(history["decision_at"]) == time(server["decisions"][0]), "M01 system history fields")
    server = repeated["server"]
    need(repeated["path"] == path and repeated["response"]["status"] == 200
         and 'href="/reservations/manage/"' in repeated["response"]["body"]
         and not locks(server) and not server["decisions"] and not writes(server)
         and data(m["after_repeat"]) == data(after), "M01 repeat must not write or sample again")
    return {"invalid_400": len(suffixes), "legal_200": 1, "repeat_200": 1, "system_history_rows": 1}


def historical(artifacts):
    source = artifacts / "story-2-1-remediation-run-20261126-205236-052-255e13d05b24/historical-evidence.json"
    entry = json.loads(read(source))["nfr001-standard"]
    path = Path(entry["path"])
    if not path.is_file():
        path = artifacts / path.parent.parent.name / path.parent.name / path.name
    need(sha(path) == entry["sha256"].upper(), "historical standard group SHA-256")
    rounds = [j for j in jsonl(path) if "round" in j]
    need([r["round"] for r in rounds] == list(range(1, 11)), "historical rounds")
    for r in rounds:
        requests = r["responses"]
        need(len(requests) == len({x["server"]["pid"] for x in requests}) == 20,
             "historical independent connections")
        need(Counter(x["response"]["status"] for x in requests) == {201: 1, 409: 19}
             and r["counts"] == {"success": 1, "conflict": 19, "no_response": 0, "other": 0},
             "historical 1 success, 19 conflicts")
        need(bool(r["observed_overlaps"]) and len(r["after"]["effective"]) == 1
             and r["after"]["effective"][0]["status"] == "pending" and not r["before"]["effective"],
             "historical overlapping lock intervals and effective row")
    return {"rounds": len(rounds), "requests_per_round": 20, "sha256": sha(path), "not_replayed": True}


def run_audit(repo, run, developer):
    art = repo / "_bmad-output/implementation-artifacts"
    if developer:
        need(run.name == DEVELOPER_RUN, "only the archived developer batch can use the old spec snapshot")
    names = []
    for line in read(run / "stages.txt").splitlines():
        m = re.fullmatch(r"\S+ ([a-z-]+) exit=0", line)
        need(m is not None, "native stage exit code")
        names.append(m[1])
    need(tuple(names) == STAGES, "all twelve stages")
    expected_legacy = set(read(art / "story-2-3-run-20261127-111101-492-41d9eb74/passed-tests.txt").splitlines())
    collected = {}
    for name, n in [("targeted", 5), ("regression", 125)]:
        lines = (read(run / f"{name}.stderr.txt") + "\n" + read(run / f"{name}.stdout.txt")).splitlines()
        tests = [match[2] for line in lines if (match := CASE_ID.fullmatch(line))]
        need(len(tests) == len(set(tests)) == n, f"{name}: distinct successful tests")
        need(lines.count("OK") == 1 and lines.count(f"Found {n} test(s).") == 1
             and sum(bool(re.fullmatch(fr"Ran {n} tests in [0-9.]+s", line)) for line in lines) == 1
             and not any("... skipped " in line for line in lines), f"{name}: run footer or skip count")
        collected[name] = set(tests)
    need(len(expected_legacy) == 113 and expected_legacy <= collected["regression"]
         and len(collected["regression"] - expected_legacy) == 12
         and all(t.startswith("reservations.test_admin_reservations.") for t in collected["regression"] - expected_legacy)
         and collected["targeted"] <= collected["regression"], "legacy and new test identities")
    expected_target_names = {"test_ac1_role_navigation_and_actual_201_contract",
                             "test_ac6_unauthorized_and_tampered_requests_never_touch_foreign_rows",
                             "test_identity_navigation_uses_business_role",
                             "test_active_admin_can_follow_create_link_from_identity_and_catalog",
                             "test_service_enforces_active_admin_and_allowlist_before_database_access"}
    need({name.rsplit(".", 1)[1] for name in collected["targeted"]} == expected_target_names,
         "targeted navigation and authorization identities")
    need(sha(run / "before.sha256") == sha(run / "after.sha256"), "input lists changed")
    entries = {}
    for line in read(run / "before.sha256").splitlines():
        digest, rel = line.split("  ", 1)
        need(re.fullmatch(r"[0-9A-F]{64}", digest) and rel not in entries, "invalid input manifest row")
        path = (repo / rel).resolve()
        need(path.is_relative_to(repo) and path.is_file(), "manifest path outside repo or absent")
        if developer and path.name == "spec-2-5-admin-reservation-query.md":
            path = art / "story-2-5-tested-spec.md"
        need(sha(path) == digest, f"input byte drift: {rel}")
        entries[rel] = digest
    code_set = {p.relative_to(repo).as_posix() for name in ("accounts", "equipment", "lab_booking", "audit", "reservations")
                for p in (repo / name).rglob("*") if p.is_file() and p.suffix in {".py", ".html"}}
    need(code_set == {rel for rel in entries if rel.split("/")[0] in
                      {"accounts", "equipment", "lab_booking", "audit", "reservations"}}
         and len(entries) == 87, "input manifest distinct count and source enumeration")
    bases = [run / f"baseline-{p}.json" for p in ("before", "after-targeted", "after-regression", "after-independent")]
    need(len({sha(p) for p in bases}) == 1, "outer business/ACL/schema snapshots")
    records = jsonl(run / "independent.jsonl")
    need(len(records) == 19 and records[0]["database"][:9] == IDENTITY
         and tuple(j["case"] for j in records[1:-1]) == CASES
         and records[-1]["cleanup"] is True
         and records[0]["before"] == records[-1]["after"] == json.loads(read(bases[0])),
         "probe cases, isolated identity or cleanup")
    need(read(run / "independent.stdout.txt").splitlines().count("STORY25_PROBE_OK cases=17") == 1,
         "probe terminal marker")
    group = {j["case"]: j for j in records[1:-1]}
    m01 = None
    if not developer:
        need(read(run / "batch-marker.txt").splitlines() == ["STORY25_VERIFICATION_OK"], "batch terminal marker")
        m01 = audit_m01(group)
    deny = group["permissions"]
    need(Counter(x["response"]["status"] for x in deny["denied"]) == {302: 8, 403: 12}
         and all(not x["server"]["statements"] and data(x["before"]) == data(x["after"]) for x in deny["denied"])
         and status(deny, "positive") == 200, "denials, no business SQL or durable effects and positive control")
    revoked = group["revoked-while-waiting"]
    need(status(revoked) == 403 and bool(revoked["blockers"]) and len(locks(trace(revoked))) == 1
         and not trace(revoked)["decisions"] and not writes(trace(revoked))
         and not trace(revoked)["commits"] and data(revoked["before"]) == data(revoked["after"]), "wait-time revocation")
    ordered = trace(group["ordered-locks"])
    ordered_locks = locks(ordered)
    need(len(ordered_locks) == 4 and ordered_locks == sorted(set(ordered_locks))
         and len(ordered["decisions"]) == len(ordered["commits"]) == 1
         and len(writes(ordered)) == 6, "ordered distinct locks, one decision, three atomic pairs")
    no_pending = trace(group["no-pending-clock"])
    need(len(no_pending["decisions"]) == 1 and not locks(no_pending) and not writes(no_pending), "no-pending filter")
    frozen = group["frozen-concurrent-additions"]
    need(bool(frozen["blockers"]) and not writes(trace(frozen, "second")), "freeze, wait and repeat")
    cross = group["crossed-start"]
    need(time(cross["waiting_at"]) < time(cross["start"]) <= time(trace(cross)["decisions"][0])
         and len(cross["after"]["history"]) == 1, "real wait crossed start")
    end = group["commit-after-end"]
    need(time(trace(end)["decisions"][0]) < time(end["end"]) <= time(trace(end, "next_result")["decisions"][0]),
         "filter bound to original decision, next request crosses end")
    for case, sqlstate, attempts, durable in (
        ("late-projection-failed", "42703", 0, 0), ("history-second", "23514", 0, 0),
        ("commit-rejected", "23505", 1, 0), ("commit-disconnected", None, 1, 0),
        ("confirmation-lost", None, 1, 2),
    ):
        record = group[case]
        server = trace(record)
        body = record["result"]["response"]["body"]
        unknown = case in {"commit-disconnected", "confirmation-lost"}
        needle = "\u7ed3\u679c\u5f85\u6838\u67e5" if unknown else "\u6570\u636e\u5e93\u4e8b\u52a1\u5df2\u56de\u6eda"
        need(status(record) == 503 and (server.get("sqlstate") == sqlstate or
             (case == "commit-disconnected" and
              str(server.get("sqlstate")).startswith(("08", "57P01"))))
             and len(server["commits"]) == attempts and len(record["after"]["history"]) == durable
             and needle in body and record.get("retry", False) is False, f"{case}: classification or durable effects")
        if not durable:
            need(data(record["before"]) == data(record["after"]), f"{case}: complete rollback")
        else:
            need(record["driver_confirmation_simulated"] is True
                 and all(row["status"] == "expired" for row in record["after"]["rows"]),
                 "confirmation loss simulation preserved actual committed expiry")
    return {"kind": "developer archive, independently audited offline" if developer else "new reviewer-run archive",
            "targeted": 5, "django": 125, "legacy": 113, "new": 12, "skipped": 0, "postgres_probes": len(CASES),
            "zero_exit_stages": len(STAGES), "input_hashes": len(entries), "identical_baselines": len(bases),
            "raw_denials": 20, "revoked_after_wait": 1, "legal_control": 200, "m01": m01,
            "nfr001": historical(art), "baseline_sha256": sha(bases[0]), "probe_sha256": sha(run / "independent.jsonl")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--developer", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_audit(args.repo.resolve(), args.run.resolve(), args.developer), ensure_ascii=False, indent=2))
    print("STORY25_OFFLINE_AUDIT_OK")


if __name__ == "__main__":
    main()
