
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = fileURLToPath(new URL('.', import.meta.url));
const repo = resolve(here, '../../..');
const root = resolve(here, '..');
const original = join(root, 'story-2-1-run-20261126-171347-146-27af94f2');
const rechecks = join(root, 'story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c');
const inter = join(rechecks, 'story-2-1-run-20261126-173530-191-df47c547');
const last = join(rechecks, 'story-2-1-run-20261126-173610-155-37026c15');
const bytes = f => readFileSync(f);
const read = f => bytes(f).toString('utf8').replace(/^\uFEFF/, '');
const sha = f => createHash('sha256').update(bytes(f)).digest('hex').toUpperCase();
const lines = f => read(f).split(/\r?\n/).filter(Boolean);
const jsonl = (d, n) => lines(join(d, n + '.jsonl')).map(JSON.parse);
const eq = (a,b,why) => assert.deepEqual(a,b,why);
const need = (a,why) => assert.ok(a,why);
const identity = ['test_lab_booking','lab_booking_test','lab_booking_test','127.0.0.1',5433,'170012','read committed',false,false];
const trustedTarget = trace => eq(trace.identity.slice(0,-1), identity, 'actual request target');
const business = s => [s.device,s.rows,s.effective,s.history];
const parseTime = s => {
  const m = String(s).match(/^(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?([+-]\d\d:\d\d)$/);
  need(m, 'timestamp with UTC offset');
  return Date.parse(m[1]+'T'+m[2]+m[4])*1000 + Number((m[3]??'').padEnd(6,'0'));
};
const pure = p => /^(accounts|equipment|audit|reservations|lab_booking)\//.test(p) || ['manage.py','requirements.txt'].includes(p);
const manifest = d => new Map(lines(join(d,'after.sha256')).map(l => {
  const m = l.match(/^([A-F0-9]{64}) {2}(.+)$/);
  need(m, 'manifest row'); return [m[2],m[1]];
}));
const stage = (d,n,code=0,marker) => {
  eq(lines(join(d,'stages.txt')).filter(x=>x.includes(' '+n+' exit=')).map(x=>+x.split('exit=').at(-1)),[code],n+' exit');
  if(marker) eq([...lines(join(d,n+'.stdout.txt')),...lines(join(d,n+'.stderr.txt'))].filter(x=>x===marker).length,1,n+' marker');
};
const inputs = {};
for(const [name,d] of Object.entries({original,inter,last})) {
  eq(sha(join(d,'before.sha256')),sha(join(d,'after.sha256')),name+' input stability');
  const m = manifest(d);
  const mismatches = [...m].filter(([p,h])=>sha(join(repo,p))!==h).map(([p])=>p);
  const codeMismatch = mismatches.filter(pure).filter(p => name!=='original' || p!=='reservations/management/commands/verify_reservation_transactions.py');
  eq(codeMismatch,[],name+' runtime and test code fingerprint');
  inputs[name] = { entries:m.size, differentNonruntimeOrHistoricalProbe: mismatches };
}
eq([...manifest(inter)], [...manifest(last)], 'recheck input equivalence');
const baselineFiles = [[original,'regression-before'],[original,'regression-after'],[inter,'resume-before'],[inter,'resume-after'],[last,'resume-before'],[last,'resume-after']];
const baseline = jsonl(original,'regression-before')[0];
for(const [d,n] of baselineFiles) {
  eq(sha(join(d,n+'.jsonl')),sha(join(original,'regression-before.jsonl')),n+' full digest');
  stage(d,n,0,'STORY21_PROBE_OK baseline');
}
eq(Object.values(baseline.rows).map(x=>x.count),[0,0,0,0,0]);
eq(baseline.schema[0].length,12);
eq(baseline.schema[1].length,19);
const beforeMigrate = jsonl(original,'migration-before')[0];
eq(beforeMigrate.database.slice(0,-1),identity);
eq(beforeMigrate.forward_plan,[['reservations','0001_initial',false],['audit','0001_initial',false]]);
for(const [k,v] of Object.entries(beforeMigrate.rows)) eq(baseline.rows[k],v);
stage(original,'migrate-isolated');
const migrated = lines(join(original,'migrate-isolated.stdout.txt')).filter(x=>/^\s*Applying /.test(x));
eq(migrated.map(x=>x.trim()),['Applying reservations.0001_initial... OK','Applying audit.0001_initial... OK']);
const migrationSql = lines(join(original,'audit-sql.stdout.txt')).join('\n');
need(/"object_type" varchar\(16\) NOT NULL/.test(migrationSql) && /CHECK/.test(migrationSql) &&
  /FOREIGN KEY \("equipment_id"\) REFERENCES "equipment_equipment"/.test(migrationSql) &&
  /FOREIGN KEY \("reservation_id"\) REFERENCES "reservations_reservation"/.test(migrationSql),'R-04 migration SQL');
stage(original,'regression',0,'OK');
const reg = [...lines(join(original,'regression.stdout.txt')),...lines(join(original,'regression.stderr.txt'))];
eq(reg.filter(x=>/^Found \d+ test\(s\)\.$/.test(x)),['Found 90 test(s).']);
eq(reg.filter(x=>/^Ran 90 tests in [0-9.]+s$/.test(x)).length,1);
const passed = reg.filter(x=>x==='ok'||/\.{3} ok$/.test(x));
eq(passed.length,90);
eq(reg.filter(x=>/\.{3} skipped /.test(x)).length,0);
need(passed.some(x=>x.includes('test_r04_database_checks_both_fk_and_protects_referenced_rows')),'R-04 regression actually executed');
const probe = (d,n) => {
  stage(d,n,0,'STORY21_PROBE_OK '+n);
  const [h,...xs] = jsonl(d,n);
  const f=xs.pop();
  eq(h.group,n);
  eq(h.database.slice(0,-1),identity);
  eq(h.python,'3.13.17');
  eq(h.before,baseline.rows);
  eq(h.schema_before,baseline.schema);
  eq(f.cleanup,true);
  eq(f.after,h.before);
  eq(f.schema_after,h.schema_before);
  return {h,xs};
};
const accountSQL = /^SELECT "accounts_user"\."(?:is_active|role)"(?: AS "(?:is_active|role)")?, "accounts_user"\."(?:is_active|role)"(?: AS "(?:is_active|role)")? FROM "accounts_user" WHERE "accounts_user"\."id" = %s\b/i;
// Placeholders end with a non-word character in most patterns. The %s here ends in s.
const checkProtocol = (r,table) => {
  const t=r.server;
  trustedTarget(t);
  const lock=t.sql.map((v,i)=>/\bFOR UPDATE\b/.test(v)?i:-1).filter(i=>i>=0);
  const clock=t.sql.map((v,i)=>/^SELECT clock_timestamp\(\) AS decision_at$/.test(v)?i:-1).filter(i=>i>=0);
  eq([lock.length,clock.length,t.decisions.length,t.commit_attempts],[1,1,1,1]);
  need(/FROM "equipment_equipment" WHERE "equipment_equipment"\."id" = %s/.test(t.sql[lock[0]]),'primary key device lock');
  need(lock[0]<clock[0] && t.lock_attempt_ns<=t.lock_acquired_ns,'lock before clock');
  const between=t.sql.slice(lock[0]+1,clock[0]);
  need(between.some(s=>accountSQL.test(s)&&s.includes('"is_active"')&&s.includes('"role"')),'separate account authorization reread');
  need(between.some(s=>s.startsWith('SELECT ')&&s.includes('"'+table+'"."status"')),'separate target status reread');
};
const permission = probe(original,'permissions').xs;
const deny = {'admin-get':403,'anon-get':302,'inactive-get':302,'admin-post':403,'anon-post':302,'inactive-post':302,'missing-csrf':403,'wrong-csrf':403,'foreign-result':404,'admin-result':403,'anon-result':302,'inactive-result':302};
for(const [key,expected] of Object.entries(deny)) {
  const [r,...rest]=permission.filter(x=>x.case===key);
  need(r&&rest.length===0,'exactly one '+key);
  const {response,server}=r.response;
  trustedTarget(server);
  eq(response.status,expected);
  eq(business(r.before),business(r.after));
  eq(server.decisions,[]);
  eq(server.lock_attempt_ns,undefined);
  for(const token of [r.before.device.name,r.before.device.number,'待审核','已失效']) need(!response.body.includes(token),'no business content on denial');
}
eq(permission.find(x=>x.case==='foreign-result').response.response.body,permission.find(x=>x.case==='missing-result').response.response.body);
eq(permission.find(x=>x.case==='result-post').response.response.status,405);
for(const n of ['authorized','tampered-authorized','own-ended-repeat']) {
  const r=permission.find(x=>x.case===n);
  eq(r.responses.map(x=>x.response.status),n==='own-ended-repeat'?[200,200]:[201,200]);
}
stage(original,'interleavings',1);
need(read(join(original,'interleavings.stderr.txt')).includes('No separate reread of target and account after locking'),'original failed probe retained');
const ints = probe(inter,'interleavings').xs;
eq(Object.fromEntries([...new Set(ints.map(x=>x.case))].map(k=>[k,ints.filter(x=>x.case===k).length])),{I1:1,I2:2,I3:2,I4:2,I5:3,I6:4,I7:1});
const faults = probe(last,'faults').xs;
eq(faults.map(x=>x.case),['F1-history','F1-reservation','F2','F3','F4']);
for(const x of faults) {
  const {case:n,before,after,response:r}=x;
  trustedTarget(r.server);
  eq(r.response.status,503);
  const unknown=n==='F3'||n==='F4';
  need(r.response.body.includes(unknown?'结果待核查，请勿重复提交。':'数据库事务已回滚'),'fault feedback '+n);
  need(!r.response.body.includes('记录编号') && !r.response.body.includes('所选时段与有效预约冲突') &&
       (!unknown || !r.response.body.includes('已回滚')),'no false success, conflict or rollback '+n);
  eq([r.server.history_attempts,r.server.reservation_attempts,r.server.commit_attempts,r.server.decisions.length],
     [1,n==='F1-history'?0:1,n.startsWith('F1')?0:1,1]);
  if(!unknown) eq(r.server.sqlstate,n==='F2'?'23505':'23514');
  else need(r.server.sqlstate==null || /^08|^57P0[123]$/.test(r.server.sqlstate),'loss SQLSTATE');
  eq(x.confirmation_simulated,n==='F4');
  if(n==='F4') eq([after.rows.length,after.history.length,after.effective.length],[2,1,1]);
  else eq(business(before),business(after));
}
const rounds = probe(last,'nfr001-standard').xs;
eq(rounds.map(x=>x.round),[1,2,3,4,5,6,7,8,9,10]);
eq(new Set(rounds.map(x=>x.before.device.id)).size,10);
const nfr = rounds.map(round => {
  const {before,after,responses,release}=round;
  eq(responses.length,20);
  eq([before.device.status,before.rows.length,before.effective.length,before.history.length],['available',0,0,0]);
  eq(after.device,before.device);
  eq(new Set(responses.map(x=>x.server.pid)).size,20);
  const counts={student:0,teacher:0};
  for(const r of responses) {
    checkProtocol(r,'equipment_equipment');
    need(r.path==='/equipment/'+before.device.id+'/reserve/','same device URL');
    eq(r.input,responses[0].input);
    need(r.response.client_start_ns>=release.monotonic_ns && r.response.client_end_ns>r.response.client_start_ns,'barrier and request interval');
    counts[r.role]++;
  }
  eq(counts,{student:10,teacher:10});
  eq(responses.map(x=>x.response.client_start_ns-release.monotonic_ns),round.start_distribution_ns);
  const wait = responses.flatMap(a=>responses.filter(b=>a!==b && a.server.lock_acquired_ns<=b.server.lock_attempt_ns &&
      b.server.lock_attempt_ns<a.server.commit_enter_ns).map(b=>[a.server.pid,b.server.pid]));
  need(wait.length>0,'real hold overlap');
  eq(wait,round.observed_overlaps);
  const [winner,...extra]=responses.filter(x=>x.response.status===201);
  need(winner&&extra.length===0,'exact winner');
  eq(responses.filter(x=>x.response.status===409&&x.response.body.includes('所选时段与有效预约冲突，请选择其他时段。')).length,19);
  eq(after.rows,after.effective);
  eq([after.rows.length,after.history.length],[1,0]);
  const row=after.rows[0];
  eq([row.status,row.equipment_id,row.applicant_id,row.applied_at],['pending',before.device.id,round.accounts[winner.role],winner.server.decisions[0]]);
  need(winner.response.body.includes('/reservations/'+row.id+'/result/'),'success response matches persisted ID');
  for(const r of responses)
    need(parseTime(r.server.decisions[0])<parseTime(row.start_at),'future throughout standard competition');
  return {round:round.round,responses:20,backendPids:20,success:1,conflict:19,effective:1,lockOverlapPairs:wait.length};
});
const [schedule,b3,b4,rb]=probe(last,'time-boundaries').xs;
eq([schedule.case,b3.case,b4.case,rb.case],['schedule','B3','B4','B4-readback']);
eq(schedule.boundary,'2026-11-26 18:00:00+08:00');
for(const x of [b3,b4,rb])checkProtocol(x.response,x===rb?'reservations_reservation':'equipment_equipment');
const boundary=parseTime(schedule.boundary);
const decision=x=>parseTime(x.response.server.decisions[0]);
need(parseTime(b3.real_blocked_at)<boundary&&boundary<=parseTime(b3.release_at)&&parseTime(b3.release_at)<=decision(b3),'real wait crosses start');
need(b3.blockers.length>0 && b3.response.server.lock_acquired_ns>b3.response.server.lock_attempt_ns,'B3 actual blocker');
need(decision(b4)<boundary&&boundary<=parseTime(b4.release_at)&&parseTime(b4.before.observed_at)<boundary&&boundary<=parseTime(b4.after.observed_at),'B4 visibility and release cross actual start');
need(b4.response.server.commit_return_ns>b4.response.server.commit_enter_ns,'B4 commit completed');
eq([b3.response.response.status,b4.response.response.status,rb.response.response.status],[400,201,200]);
eq([b3.before.rows.length,b3.after.rows.length,b3.after.rows[0].status,b3.after.history.length],[1,1,'expired',1]);
eq([b4.before.rows.length,b4.after.rows.length,b4.after.rows[0].status,b4.after.effective.length,b4.after.history.length],[0,1,'pending',0,0]);
eq(b4.after.rows[0].applied_at,b4.response.server.decisions[0]);
eq([rb.after.rows.length,rb.after.rows[0].status,rb.after.history.length,rb.after.history[0].reservation_id],[1,'expired',1,b4.after.rows[0].id]);
eq(rb.after.history[0].decision_at,rb.response.server.decisions[0]);
need(decision(rb)>=boundary,'authorized fresh result sampled after start');
const files = [];
function walk(dir) {
  for(const f of readdirSync(dir,{withFileTypes:true})){
    const p=join(dir,f.name);
    if(f.isDirectory()) walk(p); else files.push({path:relative(root,p).replaceAll('\\','/'),sha256:sha(p),bytes:bytes(p).length});
  }
}
for(const f of readdirSync(root,{withFileTypes:true}))
  if(f.isDirectory()&&/^story-2-1-(run-|recheck-)/.test(f.name)) walk(join(root,f.name));
console.log(JSON.stringify({kind:'independent-offline-audit-of-developer-logs-not-new-execution',inputs,
  originals:files,regression:{passed:90,skipped:0},permissions:Object.keys(deny).length,interleavings:ints.length,faults:faults.length,nfr,
  boundary:{at:schedule.boundary,b3Decision:b3.response.server.decisions[0],b4Decision:b4.response.server.decisions[0],readback:rb.response.server.decisions[0]}},null,2));
