
import datetime as dt, hashlib, json, pathlib, re, sys
from collections import Counter

# Read-only evidence audit. Does not open database, HTTP or browser connections.
from urllib.parse import urlsplit

if not __debug__: raise RuntimeError('The evidence assertions must not be optimized out.')

repo = pathlib.Path.cwd()
art = repo / "_bmad-output/implementation-artifacts"
run = pathlib.Path(sys.argv[1]).resolve()
assert run.parent == art.resolve()
old_audit = art / "story-2-1-independent-verification/development-evidence-audit.json"
def read(p):
    raw=p.read_bytes()
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe",b"\xfe\xff")) else "utf-8-sig")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def js(p): return json.loads(read(p))
def records(p): return [json.loads(s) for s in read(p).splitlines() if s.strip()]
def lines(p): return read(p).splitlines()
def timestamp(v): return dt.datetime.fromisoformat(v)
BJ = dt.timezone(dt.timedelta(hours=8))
identity = ["test_lab_booking", "lab_booking_test", "lab_booking_test", "127.0.0.1", 5433, "170012", "read committed", False, False]
def identity_ok(v): return len(v)==10 and v[:9]==identity and isinstance(v[9],int) and v[9]>0
def data(s): return {k:s[k] for k in ("device","rows","effective","history")}
def fingerprint(s): return hashlib.sha256(json.dumps(data(s), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
def reply(r): return r["response"]["status"]
def reply_path(r): return r["path"]
def check_trace(r):
    t=r["server"]; assert identity_ok(t["identity"]) and t["pid"]==t["identity"][-1]
    return t
def request_principal(response, expected_user_id):
    trace = check_trace(response)
    observed = trace.get("principal")
    expect = {"user_id":expected_user_id,"role":"student","is_active":True,
              "is_authenticated":True,"method":"GET","path":reply_path(response)}
    assert observed == expect, ("actual request principal missing or wrong", reply_path(response), observed)
    assert type(observed["user_id"]) is int and observed["user_id"] > 0
    assert observed["is_active"] is True and observed["is_authenticated"] is True
    return observed

def i7_bound_evidence(trace, target):
    applicant, reservation, device = (target[k] for k in ("applicant_id","id","equipment_id"))
    assert all(type(v) is int and v > 0 for v in (applicant, reservation, device))
    decision, = trace["decisions"]
    expected = [
        ("candidate",[applicant,reservation]),
        ("lock",[device]),
        ("account",[applicant]),
        ("fixed",[applicant,reservation,device]),
        ("decision",[]),
        ("due",[applicant,reservation,device,decision,"pending"]),
        ("update",["expired",applicant,reservation,device,decision,"pending",reservation]),
    ]
    got = trace.get("i7_bindings")
    assert isinstance(got, list) and got == [
        {"sql_index":i,"kind":kind,"params":params} for i,(kind,params) in enumerate(expected)
    ], ("I7 driver binding or order differs", got)
    raw = trace["sql"]
    assert len(raw) == 8 and raw[4] == "SELECT clock_timestamp() AS decision_at"
    assert sum("clock_timestamp() AS decision_at" in sql for sql in raw)==1
    def references(sql):
        return re.findall(r'"reservations_reservation"\."(applicant_id|id|equipment_id)" = %s',sql)
    for i,refs in ((0,["applicant_id","id"]),(3,["applicant_id","id","equipment_id"])):
        projection,_,rest=raw[i].partition(' FROM "reservations_reservation"')
        assert rest.startswith(' INNER JOIN "equipment_equipment"') and references(rest)==refs
        assert re.findall(r' AS "([^"]+)"',projection)==["id","equipment_id","equipment__number","equipment__name",
            "start_at","end_at","status"] and projection.startswith("SELECT ")
    assert raw[1].startswith('SELECT "equipment_equipment"."id" AS "pk" FROM "equipment_equipment" WHERE ')
    assert '"equipment_equipment"."id" = %s' in raw[1] and raw[1].endswith(" FOR UPDATE")
    assert raw[2].startswith('SELECT "accounts_user"."is_active" AS "is_active", "accounts_user"."role" AS "role" FROM "accounts_user" WHERE ')
    assert '"accounts_user"."id" = %s' in raw[2]
    assert raw[5].startswith('SELECT "reservations_reservation"."id" AS "pk" FROM "reservations_reservation" WHERE ')
    assert raw[6].startswith('UPDATE "reservations_reservation" SET "status" = %s WHERE ')
    assert references(raw[5])==["applicant_id","id","equipment_id"]
    assert references(raw[6])==["applicant_id","id","equipment_id","id"]
    assert all('"reservations_reservation"."start_at" <= %s' in s and '"reservations_reservation"."status" = %s' in s for s in raw[5:7])
    assert raw[7].startswith('INSERT INTO "audit_operationhistory"')
    return got

def expiry(s,rid,when):
    row, = [r for r in s["rows"] if r["id"]==rid]
    hist, = s["history"]
    assert row["status"]=="expired"
    assert hist["reservation_id"]==rid and hist["equipment_id"] is None and hist["actor_id"] is None
    assert (hist["object_type"],hist["action"],hist["before_status"],hist["after_status"],hist["actor_type"],hist["reason"]) == (
       "reservation","expire","pending","expired","system","开始时间已到仍待审核")
    assert timestamp(row["start_at"])<=timestamp(when)<=timestamp(hist["recorded_at"])<=timestamp(s["observed_at"])
    assert hist["decision_at"]==when
    return hist["id"]
def manifest(p):
    out={}
    for line in lines(p):
        digest,name=re.fullmatch(r"([A-F0-9]{64})  (.+)",line).groups()
        assert name not in out and (repo/name).resolve().is_relative_to(repo)
        out[name]=digest
    return out
def stage_ok(folder,stage,marker=None):
    match=[x for x in lines(folder/"stages.txt") if f" {stage} exit=" in x]
    assert len(match)==1 and match[0].endswith("exit=0"), (folder.name,stage,match)
    if marker:
        output=lines(folder/f"{stage}.stdout.txt")+lines(folder/f"{stage}.stderr.txt")
        assert output.count(marker)==1, (stage,marker)
    return match[0].split()[0]
stages={"before-db":"STORY21_PROBE_OK baseline","check":"System check identified no issues (0 silenced).",
        "migration-drift":"No changes detected","regression":"OK","navigation":"OK",
        "browser-correction":"STORY21_PROBE_OK browser-correction","permissions":"STORY21_PROBE_OK permissions",
        "interleavings":"STORY21_PROBE_OK interleavings","after-db":"STORY21_PROBE_OK baseline"}
assert not (run/"failure.txt").exists()
assert js(run/"summary.json").get("evidenceRevision") == "D-040", "Legacy run is not D-040 independent evidence"
completed=stage_ok(run,"remediation-complete")
stage_ok(run,"preflight")
assert sum(x.endswith("historical-evidence-integrity confirmed=true") for x in lines(run/"stages.txt"))==1
for name,marker in stages.items():
    stage_ok(run,name,marker)
    cmd=read(run/f"{name}.command.txt")
    assert str(repo/".venv/Scripts/python.exe").lower() in cmd.lower(),(name,cmd)
preflight=lines(run/"preflight.txt")
assert "python=Python 3.13.17 django=5.2.19" in preflight and "STORY21_PREFLIGHT_OK" in preflight
assert "isolated_identity=test_lab_booking|lab_booking_test|127.0.0.1|5433|170012" in preflight
before=manifest(run/"before.sha256")
assert len(before)==75 and sha(run/"before.sha256")==sha(run/"after.sha256") and manifest(run/"after.sha256")==before
for f,h in before.items(): assert sha(repo/f)==h, f
db=js(run/"before-db.jsonl")
assert sha(run/"before-db.jsonl")==sha(run/"after-db.jsonl")=="5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272"
assert len(db["schema"][0])==12 and len(db["schema"][1])==19 and db["schema"][2:]==[0,0]
assert set(db["rows"])=={"accounts_user","audit_operationhistory","django_session","equipment_equipment","reservations_reservation"}
assert all(v["count"]==0 and v["sha256"]==hashlib.sha256(b"[]").hexdigest() for v in db["rows"].values())

def regression(fold, name,n):
    stdout=lines(fold/f"{name}.stdout.txt")
    stderr=lines(fold/f"{name}.stderr.txt")
    assert stdout.count(f"Found {n} test(s).")==1
    assert sum(bool(re.fullmatch(rf"Ran {n} tests? in [0-9.]+s",x)) for x in stderr)==1
    passed=re.findall(r"(?m)^(test_[^ ]+ \([^)]+\)) \.\.\. ok$", "\n".join(stderr))
    assert len(passed)==len(set(passed))==n, (fold,name,len(passed))
    assert not any(" ... skipped" in x or x.startswith(("FAILED","ERROR:","FAIL:")) for x in stderr)
    return set(passed)
original=art/"story-2-1-run-20261126-171347-146-27af94f2"
previous=regression(original,"regression",90)
current=regression(run,"regression",91)
assert previous < current
new_test,=current-previous
assert new_test.startswith("test_ac3_rejected_half_hour_can_be_corrected_on_bound_form ")
assert any("test_r04_database_checks_both_fk_and_protects_referenced_rows" in x for x in current)
regression(run,"navigation",1)
nav=lines(run/"navigation.stdout.txt")
assert any(x.startswith("STORY21_NAVIGATION student /equipment/ ") for x in nav)
assert any(x.startswith("STORY21_NAVIGATION teacher /equipment/ ") for x in nav)

def probe(folder,name,n):
    out=records(folder/f"{name}.jsonl")
    assert len(out)==n+2 and out[0]["group"]==name and out[0]["python"]=="3.13.17" and identity_ok(out[0]["database"])
    assert out[-1]["cleanup"] is True and out[0]["before"]==out[-1]["after"]==db["rows"]
    assert out[0]["schema_before"]==out[-1]["schema_after"]==db["schema"]
    return out[1:-1]
b,=probe(run,"browser-correction",1)
assert b["case"]=="P01-chrome-correction" and b["chrome"].startswith("Chrome/")
assert [d["status"] for d in b["documents"]]==[200,200,400,201,200]
links=[urlsplit(d["url"]) for d in b["documents"]]
assert all(x.scheme=="http" and x.hostname=="127.0.0.1" and x.port==links[0].port for x in links)
device=b["before"]["device"]["id"]
assert links[0].path==f"/equipment/{device}/" and all(x.path==f"/equipment/{device}/reserve/" for x in links[1:4])
assert b["rejected"]["bound"]==b["invalid"] and "整点" in b["rejected"]["alert"]
assert b["initial_validity"]["buttonNoValidate"] is True
assert b["corrected_validity"]["valid"] is True and b["corrected_validity"]["formNoValidate"] is False and b["corrected_validity"]["buttonNoValidate"] is False
for choice,vi in (("invalid","initial_validity"),("corrected","corrected_validity")):
    assert [x["value"] for x in b[vi]["inputs"]]==list(b[choice].values())
assert all(x["valid"] and not x["stepMismatch"] and x["step"]=="any" for x in b["corrected_validity"]["inputs"])
start,end=(timestamp(t).replace(tzinfo=BJ) for t in b["corrected"].values())
assert start.date()==end.date() and start.hour==10 and end.hour==11 and start.minute==end.minute==0
assert (timestamp(b["before"]["observed_at"]).astimezone(BJ).date()+dt.timedelta(days=1))==start.date()
assert data(b["before"])==data(b["after_reject"]) and not b["before"]["rows"] and not b["before"]["history"] and not b["before"]["effective"]
row,=b["after_create"]["rows"]
assert (row["applicant_id"],row["equipment_id"],row["status"])==(b["student_id"],device,"pending")
assert timestamp(row["start_at"])==start and timestamp(row["end_at"])==end and timestamp(row["applied_at"])<start
assert b["after_create"]["effective"]==[row] and not b["after_create"]["history"] and data(b["after_create"])==data(b["after_read"])
assert links[4].path==b["confirmation"]["path"]==f'/reservations/{row["id"]}/result/'
assert b["confirmation"]["fields"]==b["readback"]["fields"] and b["confirmation"]["fields"][0]==str(row["id"])

p=probe(run,"permissions",22)
byname={x["case"]:x for x in p if "case" in x}
ordinary_denials={"admin-get":403,"anon-get":302,"inactive-get":302,"admin-post":403,"anon-post":302,"inactive-post":302,
  "missing-csrf":403,"wrong-csrf":403,"foreign-result":404,"admin-result":403,"anon-result":302,"inactive-result":302}
for name,status in ordinary_denials.items():
    x=byname[name]; t=check_trace(x["response"])
    assert reply(x["response"])==status and data(x["before"])==data(x["after"])
    assert not t["decisions"] and "lock_attempt_ns" not in t and not t["history_attempts"] and not t["reservation_attempts"]
assert byname["result-post"]["response"]["response"]["status"]==405
assert reply(byname["missing-result"]["response"])==404
x=byname["foreign-result-same-role"]; own=byname["own-ended-repeat"]; denied,absent=x["responses"]
assert x["role"]=="student" and x["owner_id"]!=x["requester_id"] and denied["role"]==absent["role"]=="student"
target,=x["before"]["rows"]
rid=target["id"]
assert target["status"]=="pending" and target["applicant_id"]==x["owner_id"] and timestamp(target["start_at"])<timestamp(x["before"]["observed_at"])
assert data(x["before"])==data(x["after"])==data(x["missing_after"])==data(own["before"])
assert not target.get("expired_at") and not x["after"]["effective"] and not x["after"]["history"]
assert [fingerprint(x[k]) for k in ("before","after","missing_after")]==x["fingerprints"] and len(set(x["fingerprints"]))==1
assert reply(denied)==reply(absent)==404 and denied["response"]["body"]==absent["response"]["body"]
assert denied["response"]["location"] is absent["response"]["location"] is None
assert reply_path(denied)==f"/reservations/{rid}/result/" and reply_path(denied)!=reply_path(absent)
p02_peer=request_principal(denied,x["requester_id"])
request_principal(absent,x["requester_id"])
for text in (x["before"]["device"]["name"],x["before"]["device"]["number"],"待审核","已失效",f"<dd>{rid}</dd>",
             *[timestamp(target[t]).astimezone(BJ).strftime("%Y-%m-%d %H:%M") for t in ("start_at","end_at")]):
    assert text not in denied["response"]["body"]
for r in (denied,absent):
    t=check_trace(r); assert t["pid"]!=x["observer_pid"] and not t["decisions"] and "lock_attempt_ns" not in t and not t["history_attempts"] and not t["reservation_attempts"]
    assert len(t["sql"])==1 and t["sql"][0].startswith("SELECT ") and '"applicant_id" = %s' in t["sql"][0]
first,repeat=own["responses"]; assert reply(first)==reply(repeat)==200 and own["target_id"]==rid and own["owner_id"]==x["owner_id"]
assert all(f'<dd>{rid}</dd>' in r["response"]["body"] for r in (first,repeat))
assert reply_path(first)==reply_path(repeat)==reply_path(denied)
p02_owner=request_principal(first,x["owner_id"])
request_principal(repeat,x["owner_id"])
t=check_trace(first); rep=check_trace(repeat)
assert len(t["decisions"])==t["history_attempts"]==1 and not rep["decisions"] and not rep["history_attempts"]
p02_history=expiry(own["after"],rid,t["decisions"][0])
assert [x["denied"] for x in p if "denied" in x]==[len(ordinary_denials)+1]==[13]

ii=probe(run,"interleavings",15)
assert Counter(r["case"] for r in ii)=={"I1":1,"I2":2,"I3":2,"I4":2,"I5":3,"I6":4,"I7":1}
i7,=[r for r in ii if r["case"]=="I7"]
term,read_target,repeat=i7["responses"]
assert [reply(r) for r in (term,read_target,repeat)]==[200,200,200]
t=check_trace(read_target)
assert t["pid"]==i7["blocked_pid"] and i7["blocker_pid"] in i7["blockers"] and len({i7["observer_pid"],i7["blocker_pid"],t["pid"]})==3
tim=i7["timing"]
assert t["lock_attempt_ns"]<tim["blocked_ns"]<tim["same_inserted_ns"]<tim["other_inserted_ns"]<tim["commit_enter_ns"] and tim["commit_enter_ns"]<=t["lock_acquired_ns"] and tim["commit_enter_ns"]<tim["commit_return_ns"]
assert data(i7["before"])==data(i7["during"]) and data(i7["after"])==data(i7["repeated_after"])
target,terminal,same,foreign=(i7["candidates"][k] for k in ("target","terminal","same_owner_added","other_owner_added"))
assert target["applicant_id"]==same["applicant_id"]!=foreign["applicant_id"]
assert all(c["equipment_id"]==target["equipment_id"] for c in (terminal,same,foreign))
assert target["initial_status"]==same["initial_status"]==foreign["initial_status"]=="pending"
assert all(timestamp(c["start_at"])<timestamp(t["decisions"][0]) for c in (target,same,foreign))
assert {k["id"]:k["status"] for k in i7["before"]["rows"]}=={target["id"]:"pending",terminal["id"]:"expired"}
assert {k["id"]:k["status"] for k in i7["after"]["rows"]}=={target["id"]:"expired",terminal["id"]:"expired",same["id"]:"pending",foreign["id"]:"pending"}
assert not i7["after"]["effective"] and len(t["decisions"])==t["history_attempts"]==t["commit_attempts"]==1 and not t["reservation_attempts"]
p03_history=expiry(i7["after"],target["id"],t["decisions"][0])
for r in (term,repeat):
    trace=check_trace(r); assert not trace["decisions"] and "lock_attempt_ns" not in trace and not trace["history_attempts"]
assert i7["before"]["device"]==i7["after"]["device"]
initial_rows={r["id"]:r for r in i7["before"]["rows"]}; final_rows={r["id"]:r for r in i7["after"]["rows"]}
assert final_rows[target["id"]]==dict(initial_rows[target["id"]],status="expired") and initial_rows[terminal["id"]]==final_rows[terminal["id"]]
for candidate in (same,foreign):
    assert all(final_rows[candidate["id"]][field]==candidate[field] for field in ("id","applicant_id","equipment_id","start_at","end_at"))
for r in (term,read_target,repeat):
    body=r["response"]["body"]
    assert body.count("<dl>")==1 and body.count("<dd>")==4 and not any(f'<dd>{c["id"]}</dd>' in body for c in (same,foreign))
p03_bindings=i7_bound_evidence(t,target)
sql=t["sql"]
lock,=[i for i,s in enumerate(sql) if "FOR UPDATE" in s]
clock,=[i for i,s in enumerate(sql) if s=="SELECT clock_timestamp() AS decision_at"]
assert lock==1 and clock==4 and all(x in sql[0] for x in ('"reservations_reservation"."id" = %s','"reservations_reservation"."applicant_id" = %s'))
assert all(any(fragment in sql[j] for j in range(lock+1,clock)) for fragment in ('"is_active" AS "is_active"', '"role" AS "role"','"reservations_reservation"."equipment_id" = %s'))
assert sum(s.startswith('UPDATE "reservations_reservation"') for s in sql[clock+1:])==1
assert sum(s.startswith('INSERT INTO "audit_operationhistory"') for s in sql[clock+1:])==1

historical=js(run/"historical-evidence.json")
assert historical==js(run/"summary.json")["reusedHistorical"]
assert set(historical)=={"faults","nfr001-standard","time-boundaries"}
prior={}
for name,ev in historical.items():
    f=pathlib.Path(ev["path"]).resolve()
    assert f.is_relative_to(art.resolve()) and f.name==name+".jsonl" and f.parent.name=="story-2-1-run-20261126-173610-155-37026c15"
    assert sha(f)==ev["sha256"] and not (run/f.name).exists()
    stage_ok(f.parent,name,"STORY21_PROBE_OK "+name)
    prior[name]=probe(f.parent,name,ev["records"])
old=js(old_audit)
assert len(old["originals"])==99
for f in old["originals"]: assert sha(art/f["path"])==f["sha256"],f["path"]
old_manifest=manifest(pathlib.Path(historical["faults"]["path"]).parent/"after.sha256")
runtime=lambda s: {k:v for k,v in s.items() if k in ("manage.py","requirements.txt") or k.split("/")[0] in ("accounts","audit","equipment","lab_booking","reservations")}
was,now=runtime(old_manifest),runtime(before)
probe_file="reservations/management/commands/verify_reservation_transactions.py"
assert set(now)-set(was)=={"reservations/management/commands/_chrome_probe.py"} and not (set(was)-set(now))
assert {k for k,v in was.items() if now[k]!=v}=={"reservations/forms.py","reservations/tests.py",probe_file}
rounds=prior["nfr001-standard"]
assert [r["round"] for r in rounds]==list(range(1,11))
for r in rounds:
    allr=r["responses"]; t=[check_trace(x) for x in allr]
    assert len(allr)==len({q["pid"] for q in t})==20
    assert Counter(reply(q) for q in allr)=={201:1,409:19}
    assert all("所选时段与有效预约冲突" in q["response"]["body"] for q in allr if reply(q)==409)
    assert r["before"]["device"]["status"]==r["after"]["device"]["status"]=="available" and not r["before"]["effective"]
    row,=r["after"]["effective"]
    assert row["status"]=="pending" and r["after"]["rows"]==[row]
    assert all(timestamp(k["decisions"][0])<timestamp(row["start_at"]) for k in t)
    real=[ [a["pid"],b["pid"]] for a in t for b in t if a is not b and a["lock_acquired_ns"]<=b["lock_attempt_ns"]<a["commit_enter_ns"]]
    assert real and real==r["observed_overlaps"]
faults=prior["faults"]
assert [f["case"] for f in faults]==["F1-history","F1-reservation","F2","F3","F4"]
for f in faults:
    case=f["case"]; r=f["response"]; trace=check_trace(r)
    assert reply(r)==503 and trace["history_attempts"]==1 and len(trace["decisions"])==1
    assert trace["commit_attempts"]==(0 if case.startswith("F1") else 1)
    unknown=case in ("F3","F4")
    assert ("结果待核查" if unknown else "数据库事务已回滚") in r["response"]["body"] and "所选时段与有效预约冲突" not in r["response"]["body"]
    if case!="F4": assert data(f["before"])==data(f["after"])
    else: assert len(f["after"]["rows"])==2 and len(f["after"]["history"])==1 and len(f["after"]["effective"])==1
sched,b3,b4,br=prior["time-boundaries"]
assert [k["case"] for k in (sched,b3,b4,br)]==["schedule","B3","B4","B4-readback"]
h=timestamp(sched["boundary"])
assert (h.hour,h.minute,h.utcoffset())==(18,0,dt.timedelta(hours=8))
d3,d4,dr=(timestamp(check_trace(r["response"])["decisions"][0]) for r in (b3,b4,br))
assert timestamp(b3["real_blocked_at"])<h<=timestamp(b3["release_at"])<d3 and d4<h<=timestamp(b4["release_at"])
assert [reply(r["response"]) for r in (b3,b4,br)]==[400,201,200]
assert b4["after"]["rows"][0]["status"]=="pending" and not b4["after"]["effective"] and not b4["after"]["history"]
assert br["after"]["rows"][0]["status"]=="expired" and len(br["after"]["history"])==1 and dr>=h
print(json.dumps({"run":run.name,"completed":completed,"evidence_revision":"D-040","targeted_run":{"Django":"91/91, 0 skipped","navigation":"1/1 student and teacher",
  "Chrome":b["chrome"],"P01_http":[d["status"] for d in b["documents"]],"P01_reservation":b["confirmation"]["fields"][0],
  "P02_denials":"13/13","P02_target":rid,"P02_state_fingerprint":x["fingerprints"][0],"P02_owner_history":p02_history,
  "P02_actual_authenticated_peer":p02_peer,"P02_actual_authenticated_owner":p02_owner,
  "interleavings":"15/15","P03_target":target["id"],"P03_same_owner":same["id"],"P03_other_owner":foreign["id"],"P03_history":p03_history,
  "P03_backend_pids":{k:i7[k] for k in ("observer_pid","blocked_pid","blocker_pid")},"P03_driver_bindings":p03_bindings},
  "reused_historical":{"NFR_001":"10/10, 200 responses","faults":"5/5","Beijing_boundary":h.isoformat()},
  "tested_files":len(before),"historic_raw_files_checked":len(old["originals"]),"database_baseline_digest":sha(run/"after-db.jsonl"),
  "evidence_file_digests":{p.name:sha(p) for p in sorted(run.iterdir()) if p.is_file()}},ensure_ascii=False,indent=2))
