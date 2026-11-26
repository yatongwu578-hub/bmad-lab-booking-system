"""D-041 release stages. Only the approved local production DB and demo device."""
from datetime import datetime, time, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
import json, os, re, subprocess, sys

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row

DB = 'lab_booking'
MIGRATOR = 'lab_booking_migrator'
APP = 'lab_booking_app'
DEV = 'EQ-DEMO-S12-20261125'
MIGRATIONS = [('reservations', '0001_initial'), ('audit', '0001_initial')]
TABLES = ('reservations_reservation', 'audit_operationhistory')
T = TABLES[0]
H = TABLES[1]
ROLE = {'student': '学生', 'teacher': '教师', 'admin': '业务管理员'}
BJ = ZoneInfo('Asia/Shanghai')
BASE = 'http://127.0.0.1:8001'
JSON = lambda data: json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
mode, run_path = sys.argv[1:3]
RUN = Path(run_path).resolve()

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def record(name, data):
    with (RUN / (name + '.jsonl')).open('a', encoding='utf-8', newline='\n') as f:
        f.write(JSON(data) + '\n')

def create(name, data):
    with (RUN / (name + '.json')).open('x', encoding='utf-8') as f:
        f.write(JSON(data) + '\n')
        f.flush()
        os.fsync(f.fileno())

def read(name):
    return json.loads((RUN / (name + '.json')).read_text(encoding='utf-8-sig'))

def intent(phase, data):
    # Persist before each possible write. There is no automatic write recovery.
    create(phase + '-intent', {'at':datetime.now(BJ), **data})

def digest(path):
    with path.open('rb') as f:
        import hashlib
        return hashlib.file_digest(f, 'sha256').hexdigest().upper()

def args(role):
    return ['-h','127.0.0.1','-p','5433','-U',role,'-d',DB,'-w']

def native(stage, binary, arguments, seconds=90):
    with (RUN / (stage+'.stdout.txt')).open('xb') as out, (RUN / (stage+'.stderr.txt')).open('xb') as err:
        try:
            result = subprocess.run([binary,*arguments],stdout=out,stderr=err,timeout=seconds,check=False)
        except subprocess.TimeoutExpired:
            record('native-exits',{'stage':stage,'exit':'TIMEOUT; result not confirmed'})
            raise RuntimeError('Timeout at '+stage) from None
    record('native-exits',{'stage':stage,'exit':result.returncode})
    need(result.returncode==0, 'Nonzero exit at '+stage)
    return (RUN / (stage+'.stdout.txt')).read_text(encoding='utf-8-sig',errors='replace')

def connect(role):
    need(role in (MIGRATOR,APP), 'Unexpected DB role')
    return psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=5433,dbname=DB,user=role,
                           passfile=os.environ['PGPASSFILE'],connect_timeout=5,row_factory=dict_row,autocommit=True)

def rows(c, sql, params=None):
    return c.execute(sql, params).fetchall()

def one(c, sql, params=None):
    values=rows(c,sql,params)
    need(len(values)==1,'Expected a unique database result')
    return values[0]

def identity(c, role):
    got=one(c,"""SELECT current_database() AS db, session_user AS login, current_user AS role,
      pg_catalog.host(pg_catalog.inet_server_addr()) AS host, pg_catalog.inet_server_port() AS port,
      current_setting('server_version_num') AS version, current_setting('transaction_isolation') AS isolation,
      current_schema() AS schema_name, current_schemas(false) AS search_path,
      r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls AS elevated
      FROM pg_catalog.pg_roles AS r WHERE r.rolname=current_user""")
    need(list(got.values())==[DB,role,role,'127.0.0.1',5433,'170012','read committed','public',['public'],False],
         'Wrong production identity, search path, version or elevated role')
    return got

def readiness(c):
    return rows(c,"""SELECT m.app,m.name FROM public.django_migrations AS m
      WHERE m.app IN ('audit','reservations') ORDER BY m.app,m.name"""), rows(c,"""SELECT t.relname
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory')
      ORDER BY t.relname""")

def state_ready(state):
    return [(i['app'],i['name']) for i in state[0]]==sorted(MIGRATIONS) and [x['relname'] for x in state[1]]==sorted(TABLES)

COLUMNS = {
 T:{'id':('bigint',True,'d'),'applicant_id':('bigint',True,''),'equipment_id':('bigint',True,''),
    'start_at':('timestamp with time zone',True,''),'end_at':('timestamp with time zone',True,''),
    'applied_at':('timestamp with time zone',True,''),'status':('character varying(16)',True,'')},
 H:{'id':('bigint',True,'d'),'reservation_id':('bigint',False,''),'equipment_id':('bigint',False,''),
    'actor_id':('bigint',False,''),'object_type':('character varying(16)',True,''),'action':('character varying(32)',True,''),
    'before_status':('character varying(16)',True,''),'after_status':('character varying(16)',True,''),
    'actor_type':('character varying(16)',True,''),'reason':('text',True,''),
    'decision_at':('timestamp with time zone',True,''),'recorded_at':('timestamp with time zone',True,'')}}
FK = {(T,'applicant_id','accounts_user'),(T,'equipment_id','equipment_equipment'),
      (H,'actor_id','accounts_user'),(H,'reservation_id',T),(H,'equipment_id','equipment_equipment')}
CHECKS = {
 'reservation_status_valid': (T,"status=anyarray['pending','approved','rejected','cancelled','expired']"),
 'reservation_start_before_end':(T,'end_at>start_at'),
 'history_exactly_one_matching_object':(H,"equipment_idisnullandobject_type='reservation'andreservation_idisnotnullorequipment_idisnotnullandobject_type='equipment'andreservation_idisnull")}
def norm(check):
    s=re.sub(r'::(?:character varying|text)(?:\[\])?', '', check.lower())
    return re.sub(r'[\s()"]','',s)

def schema(c,stage):
    cols=rows(c,"""SELECT t.relname AS object, a.attname AS col,
      pg_catalog.format_type(a.atttypid,a.atttypmod) AS type, a.attnotnull AS required,
      a.attidentity::text AS "identity", pg_catalog.pg_get_userbyid(t.relowner) AS owner,
      t.relrowsecurity AS rls, t.relforcerowsecurity AS force_rls
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      JOIN pg_catalog.pg_attribute AS a ON a.attrelid=t.oid
      WHERE n.nspname='public' AND t.relkind='r' AND t.relname::text=ANY(%s)
        AND a.attnum>0 AND NOT a.attisdropped ORDER BY t.relname,a.attnum""",(list(TABLES),))
    found={t:{} for t in TABLES}
    for r in cols:
        need(r['owner']==MIGRATOR and not r['rls'] and not r['force_rls'],'Wrong owner or unexpected RLS')
        found[r['object']][r['col']]=(r['type'],r['required'],r['identity'])
    need(found==COLUMNS,'Schema columns/identity differ from migration')
    cons=rows(c,"""SELECT t.relname AS object,k.conname AS name,k.contype::text AS kind,k.convalidated AS valid,
      k.condeferrable AS deferrable,k.condeferred AS deferred,k.confdeltype::text AS delete_rule,k.confupdtype::text AS update_rule,
      ARRAY(SELECT a.attname::text FROM unnest(k.conkey) WITH ORDINALITY AS x(att,num)
        JOIN pg_catalog.pg_attribute AS a ON a.attrelid=t.oid AND a.attnum=x.att ORDER BY x.num) AS cols,
      rel.relname AS reference, ns.nspname AS refschema,
      ARRAY(SELECT a.attname::text FROM unnest(k.confkey) WITH ORDINALITY AS x(att,num)
        JOIN pg_catalog.pg_attribute AS a ON a.attrelid=rel.oid AND a.attnum=x.att ORDER BY x.num) AS refcols,
      pg_catalog.pg_get_expr(k.conbin,k.conrelid,true) AS predicate,
      pg_catalog.pg_get_constraintdef(k.oid) AS ddl
      FROM pg_catalog.pg_constraint AS k JOIN pg_catalog.pg_class AS t ON t.oid=k.conrelid
      JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      LEFT JOIN pg_catalog.pg_class AS rel ON rel.oid=k.confrelid
      LEFT JOIN pg_catalog.pg_namespace AS ns ON ns.oid=rel.relnamespace
      WHERE n.nspname='public' AND t.relname::text=ANY(%s) ORDER BY t.relname,k.conname""",(list(TABLES),))
    need(len(cons)==10 and all(r['valid'] for r in cons),'Unexpected constraint count or unvalidated constraint')
    fks=[r for r in cons if r['kind']=='f']
    need({(r['object'],r['cols'][0],r['reference']) for r in fks}==FK and len(fks)==5 and
         all(len(r['cols'])==1 and r['refschema']=='public' and r['refcols']==['id'] and r['delete_rule']==r['update_rule']=='a'
             and r['deferrable'] and r['deferred'] for r in fks),'Real foreign keys differ from R-04/Django DDL')
    need({(r['object'],tuple(r['cols'])) for r in cons if r['kind']=='p'}=={(t,('id',)) for t in TABLES},'Missing expected primary key')
    need({r['name']:(r['object'],norm(r['predicate'])) for r in cons if r['kind']=='c'}==CHECKS,'CHECK expressions differ')
    indexes=rows(c,"""SELECT t.relname AS object, i.relname AS name, x.indisvalid AS valid,
      pg_catalog.pg_get_indexdef(i.oid) AS ddl FROM pg_catalog.pg_index AS x
      JOIN pg_catalog.pg_class AS t ON t.oid=x.indrelid
      JOIN pg_catalog.pg_class AS i ON i.oid=x.indexrelid
      JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      WHERE n.nspname='public' AND t.relname::text=ANY(%s) ORDER BY t.relname,i.relname""",(list(TABLES),))
    need(len(indexes)==7 and all(r['valid'] for r in indexes),'Expected primary and FK indexes are not present')
    record('schema',dict(stage=stage,columns=cols,constraints=cons,indexes=indexes,identity_sequences=sequence_and_triggers(c)))

def frozen_sql():
    path=HERE/'runtime-release-plan-draft.md'
    need(digest(path)=='84F8FBD83282F4CB39A618C18BCB8D65EADC953C449879D6B9324A4777D19A4A','Frozen grant plan changed')
    blocks=re.findall(chr(96)*3+r'sql\s+(.*?)'+chr(96)*3,path.read_text(encoding='utf-8'),re.S)
    need(len(blocks)==2 and blocks[0].count('GRANT ')==3,'Expected pinned grant and matrix blocks')
    return blocks[0].strip(),blocks[1].strip().removesuffix(';')

GRANTS, MATRIX = frozen_sql()
ACL_GUARD = """SELECT bool_and(NOT pg_catalog.has_table_privilege('lab_booking_app'::name,t.oid,p.op)
        AND NOT pg_catalog.has_table_privilege('lab_booking_app'::name,t.oid,p.op||' WITH GRANT OPTION'))
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),
                         ('TRIGGER'),('MAINTAIN')) AS p(op)
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory')"""
RAW_ACL = """SELECT t.relname AS object,a.attname AS column_name,x.grantee,x.grantor,x.privilege_type,x.is_grantable
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      LEFT JOIN pg_catalog.pg_attribute AS a ON a.attrelid=t.oid AND a.attnum>0 AND NOT a.attisdropped
      CROSS JOIN LATERAL pg_catalog.aclexplode(
        CASE WHEN pg_catalog.cardinality(a.attacl)>0 THEN a.attacl END) AS x
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory')
      UNION ALL
      SELECT t.relname,NULL,x.grantee,x.grantor,x.privilege_type,x.is_grantable
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      CROSS JOIN LATERAL pg_catalog.aclexplode(CASE
        WHEN t.relacl IS NULL THEN pg_catalog.acldefault('r',t.relowner)
        WHEN pg_catalog.cardinality(t.relacl)>0 THEN t.relacl END) AS x
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory') AND x.grantee<>t.relowner"""
ROLE_SQL = """SELECT pg_catalog.has_schema_privilege('lab_booking_app','public','USAGE')
      AND NOT pg_catalog.has_schema_privilege('lab_booking_app','public','CREATE')
      AND NOT pg_catalog.has_database_privilege('lab_booking_app','lab_booking','CREATE')
      AND NOT pg_catalog.pg_has_role('lab_booking_app','lab_booking_migrator','MEMBER')
      AND NOT(r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls) AS ok
      FROM pg_catalog.pg_roles AS r WHERE r.rolname='lab_booking_app'"""
def old_privileges(c):
    need(one(c,ROLE_SQL)['ok'],'Runtime role attributes or schema permission out of scope')
    required = {'equipment_equipment':{'SELECT':('id','number','name','category','location','description','status'),
                     'UPDATE':('name','category','location','description')},'accounts_user':{'SELECT':('id','is_active','role')}}
    for table,opcols in required.items():
        for op,cols in opcols.items():
            for col in cols:
                need(one(c,"SELECT pg_catalog.has_column_privilege(%s::name,%s::text,%s::text,%s::text) AS ok",(APP,'public.'+table,col,op))['ok'],
                     'Missing existing account/device privilege; no extra GRANT authorized')
    need(not one(c,"SELECT pg_catalog.has_column_privilege(%s::name,%s::text,%s::text,%s::text) AS ok",(APP,'public.equipment_equipment','status','UPDATE'))['ok'],
         'Existing device-status update is out of approved scope')
    return rows(c,"""SELECT t.relname,t.relacl::text AS table_acl,a.attname,a.attacl::text AS column_acl
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      JOIN pg_catalog.pg_attribute AS a ON a.attrelid=t.oid AND a.attnum>0 AND NOT a.attisdropped
      WHERE n.nspname='public' AND t.relname IN ('accounts_user','equipment_equipment','django_session')
      ORDER BY t.relname,a.attnum""")

def acl(c,stage,allow_unknown=False):
    record('acl-probe',dict(stage=stage,check='effective column matrix'))
    data=rows(c,MATRIX)
    record('acl-probe',dict(stage=stage,check='explicit catalog ACL'))
    raw=rows(c,RAW_ACL)
    record('acl-probe',dict(stage=stage,check='effective table and delegation ACL'))
    cap=one(c,ACL_GUARD)
    role=one(c,"SELECT %s::regrole::oid AS app,%s::regrole::oid AS owner",(APP,MIGRATOR))
    allowed={(r['relation_name'],r['column_name'],r['operation']) for r in data if r['expected_after']}
    ready = all(r['effective']==r['expected_after'] for r in data)
    pristine = not any(r['effective'] for r in data)
    expected_raw={(r['object'],r['column_name'],r['privilege_type']) for r in raw}
    clean = len(data)==76 and len(allowed)==26 and all(r['object_owner']==MIGRATOR and not r['can_delegate'] for r in data)
    clean = clean and next(iter(cap.values())) is True and all(
        r['grantee']==role['app'] and r['grantor']==role['owner'] and not r['is_grantable'] and r['column_name']
        for r in raw)
    state='ready' if clean and ready and expected_raw==allowed else 'pristine' if clean and pristine and not raw else 'unapproved'
    record('acl',dict(stage=stage,state=state,matrix=data,actual_explicit_acl=raw))
    if not allow_unknown:
        need(state!='unapproved','Partial, broad, inherited or otherwise unapproved effective permissions')
    return state


def default_grants(c):
    extra=rows(c,"""SELECT n.nspname AS schema_name,d.defaclobjtype::text AS object_type,
        x.grantee,x.grantor,x.privilege_type,x.is_grantable
        FROM pg_catalog.pg_default_acl AS d
        LEFT JOIN pg_catalog.pg_namespace AS n ON n.oid=d.defaclnamespace
        CROSS JOIN LATERAL pg_catalog.aclexplode(
          CASE WHEN pg_catalog.cardinality(d.defaclacl)>0 THEN d.defaclacl END) AS x
        WHERE d.defaclrole='lab_booking_migrator'::regrole
          AND (d.defaclnamespace=0 OR n.nspname='public') AND d.defaclobjtype IN ('r','S')
          AND (x.grantee<>d.defaclrole OR x.grantor<>d.defaclrole)""")
    need(not extra,'Default grants would create unapproved table or identity-sequence privileges')

def sequence_and_triggers(c):
    info=rows(c,"""SELECT q.relname AS sequence_name,t.relname AS table_name,
        pg_catalog.pg_get_userbyid(q.relowner) AS owner,
        pg_catalog.has_sequence_privilege('lab_booking_app'::name,q.oid,'SELECT,USAGE,UPDATE') AS app_allowed
        FROM pg_catalog.pg_depend AS d JOIN pg_catalog.pg_class AS q ON q.oid=d.objid AND q.relkind='S'
        JOIN pg_catalog.pg_class AS t ON t.oid=d.refobjid
        JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
        JOIN pg_catalog.pg_attribute AS a ON a.attrelid=t.oid AND a.attnum=d.refobjsubid
        WHERE d.classid='pg_catalog.pg_class'::regclass AND d.refclassid=d.classid AND d.deptype='i'
          AND n.nspname='public' AND t.relname::text=ANY(%s) AND a.attname='id'""",(list(TABLES),))
    need(len(info)==2 and {x['table_name'] for x in info}==set(TABLES)
         and all(x['owner']==MIGRATOR and not x['app_allowed'] for x in info),'Unexpected identity ownership or sequence permission')
    count=one(c,"""SELECT count(*) AS n FROM pg_catalog.pg_trigger AS g JOIN pg_catalog.pg_class AS t ON t.oid=g.tgrelid
      JOIN pg_catalog.pg_namespace AS s ON s.oid=t.relnamespace
      WHERE s.nspname='public' AND t.relname::text=ANY(%s) AND NOT g.tgisinternal""",(list(TABLES),))
    need(count['n']==0,'Unexpected application trigger on a Story 2.1 table')
    return info

def accounts(c):
    try:
        pack=json.loads(Path(os.environ['STORY21_ACCOUNTS']).read_text(encoding='utf-8-sig'))
    except Exception:
        raise RuntimeError('Cannot read existing protected account manifest; no values logged') from None
    need(isinstance(pack,list),'Expected protected existing accounts list')
    out={}
    for role in ROLE:
        data=[r for r in pack if isinstance(r,dict) and r.get('role')==role
              and all(isinstance(r.get(k),str) and r[k] for k in ('username','password'))]
        need(len(data)==1,'Expected one existing approved account per role')
        account=data[0]
        db=one(c,'SELECT u.id,u.role,u.is_active FROM public.accounts_user AS u WHERE u.username=%s',(account['username'],))
        need(db['role']==role and db['is_active'] is True,'Approved account inactive or role mismatch')
        out[role]={'id':db['id'],'username':account['username'],'password':account['password']}
    need(len({a['id'] for a in out.values()})==3,'Expected three different approved active accounts')
    return out

def equipment(c):
    return one(c,'SELECT e.id,e.number,e.status FROM public.equipment_equipment AS e WHERE e.number=%s',(DEV,))


def check_backup_protection():
    import base64
    text=r"""
$ErrorActionPreference='Stop'
$path=$env:STORY21_BACKUP_FILE
$me=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$safe=@($me,'S-1-5-18','S-1-5-32-544')
$item=Get-Item -LiteralPath $path
if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Unexpected backup file object'}
foreach($ace in (Get-Acl -LiteralPath $path).Access){
 if($ace.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow){
  if($ace.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin $safe){throw 'Backup ACL exposes the archive'}
 }
}
Write-Output 'STORY21_D041_BACKUP_PROTECTED'
"""
    encoded=base64.b64encode(text.encode('utf-16-le')).decode('ascii')
    shell=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    output=native('backup-protection',str(shell),['-NoProfile','-NonInteractive','-EncodedCommand',encoded])
    need(output.splitlines().count('STORY21_D041_BACKUP_PROTECTED')==1,'Protected backup ACL was not confirmed')

def backup(c):
    target=Path(os.environ['STORY21_BACKUP_FILE'])
    need(target.is_absolute() and target.parent.is_dir() and not target.exists(),'Protected backup location unavailable or reused')
    d=one(c,"SELECT pg_catalog.clock_timestamp() AS time")
    native('backup',os.environ['STORY21_PG_DUMP'],[*args(MIGRATOR),'--format=custom',
           '--lock-wait-timeout=8000','--file',str(target)],240)
    need(target.is_file() and target.stat().st_size>0,'Custom backup file missing')
    check_backup_protection()
    listing=native('backup-toc',os.environ['STORY21_PG_RESTORE'],['--list',str(target)])
    need(all(re.search(r'TABLE DATA public '+table+r'\b',listing) for table in
             ('accounts_user','equipment_equipment','django_migrations','django_session')),
         'Protected backup directory listing is incomplete')
    record('backup-proof',dict(time=d['time'],size=target.stat().st_size,sha256=digest(target),toc_checked=True,
                               location='protected local backup; path supplied by ordinary PowerShell'))
    need((RUN/'backup.stderr.txt').stat().st_size==0,'Backup emitted warnings; inspect before writes')

def apply_migrations(c):
    import django
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor
    from django.core.management import call_command
    import io
    django.setup()
    db=connections['default']
    def plan():
        ex=MigrationExecutor(db)
        ex.loader.check_consistent_history(db)
        return [(m.app_label,m.name,backwards) for m,backwards in ex.migration_plan(ex.loader.graph.leaf_nodes())]
    with db.cursor() as cursor:
        cursor.execute("SET lock_timeout = '8s'")
        cursor.execute("SET statement_timeout = '60s'")
    first=plan()
    origin=readiness(c)
    record('migration-plan',dict(plan=first,before=origin))
    if not first:
        need(state_ready(origin),'Empty plan but the recorded or actual objects differ')
        record('migration-result',dict(outcome='already-applied; no migration invoked'))
        return
    need(first==[(a,b,False) for a,b in MIGRATIONS] and origin==([],[]),
         'Unexpected/partial/extra migrations or existing objects; no migration invoked')
    need(plan()==first and readiness(c)==origin,'Migration plan changed before execution')
    intent('migration',{'target':DB,'role':MIGRATOR,'approved':MIGRATIONS})
    output=io.StringIO()
    try:
        call_command('migrate','audit','0001_initial',interactive=False,stdout=output)
    finally:
        (RUN/'django-migrate.stdout.txt').write_text(output.getvalue(),encoding='utf-8')
    applied=[line.strip() for line in output.getvalue().splitlines() if 'Applying ' in line]
    need(applied==['Applying reservations.0001_initial... OK','Applying audit.0001_initial... OK'],
         'Migration confirmation differs from the two authorized operations; read back, do not re-run')
    need(not plan() and state_ready(readiness(c)),'Actual migration/object readback differs; do not re-run')
    record('migration-result',dict(outcome='confirmed by Django and readback',operations=applied,exit=0))

def grant_script():
    # One psql transaction. Qualified aliases, no PL/pgSQL variable reference, no BEGIN/COMMIT inside.
    guard=re.sub(r'\s+AS ok\s+FROM', ' FROM', ROLE_SQL)
    roles="SELECT 'lab_booking_app'::regrole::oid AS app,'lab_booking_migrator'::regrole::oid AS owner"
    identity_sql="""SELECT (current_database()='lab_booking' AND current_user='lab_booking_migrator'
          AND session_user='lab_booking_migrator' AND pg_catalog.host(pg_catalog.inet_server_addr())='127.0.0.1'
          AND pg_catalog.inet_server_port()=5433 AND current_setting('server_version_num')='170012'
          AND current_schema()='public' AND current_schemas(false)=ARRAY['public']::name[])"""
    def check_sql(ready):
        effective=('bool_and(m.effective=m.expected_after)' if ready else 'bool_and(NOT m.effective)')
        raw_check=(" AND (SELECT count(*)=26 AND bool_and(r.grantee=k.app AND r.grantor=k.owner "
                   "AND NOT r.is_grantable AND r.column_name IS NOT NULL) FROM rawacl AS r CROSS JOIN rr AS k)"
                   if ready else " AND NOT EXISTS (SELECT 1 FROM rawacl)")
        return (f"WITH mm AS ({MATRIX}), rawacl AS ({RAW_ACL}), rr AS ({roles})\n"
                "SELECT COALESCE(count(*)=76 AND count(*) FILTER (WHERE m.expected_after)=26 "
                "AND bool_and(m.object_owner='lab_booking_migrator' AND NOT m.can_delegate) AND "
                +effective+f" AND ({ACL_GUARD}) AND ({guard})"+raw_check+",false) AS ok FROM mm AS m\n")
    return ("SET LOCAL lock_timeout = '8s';\nSET LOCAL statement_timeout = '20s';\n"
            +identity_sql+" AS ok\n\\gset env_\n\\if :env_ok\n\\else\nSELECT 1 / 0;\n\\endif\n"
            +"LOCK TABLE public.reservations_reservation,public.audit_operationhistory IN SHARE ROW EXCLUSIVE MODE;\n"
            +check_sql(False)+"\\gset before_\n\\if :before_ok\n"+GRANTS
            +"\n\\else\nSELECT 1 / 0;\n\\endif\n"+check_sql(True)
            +"\\gset after_\n\\if :after_ok\n\\echo STORY21_D041_GRANT_ASSERTIONS_OK\n"
            +"\\else\nSELECT 1 / 0;\n\\endif\n")

def authorization(c):
    if acl(c,'before')=='ready':
        record('grant-result',dict(outcome='already exact; skipped GRANT'))
        return
    sql=RUN/'grant-transaction.sql'
    with sql.open('x',encoding='utf-8',newline='\n') as f:
        f.write(grant_script())
    intent('grant',{'target':DB,'role':MIGRATOR,'recipient':APP,'script_sha256':digest(sql)})
    out=native('grant',os.environ['STORY21_PSQL'],['-X',*args(MIGRATOR),'-v','ON_ERROR_STOP=1','--single-transaction','-f',str(sql)],45)
    need(out.splitlines().count('STORY21_D041_GRANT_ASSERTIONS_OK')==1,'GRANT receipt marker absent or duplicate')
    need(acl(c,'after-commit')=='ready','Committed ACL readback differs')
    record('grant-result',dict(outcome='confirmed: psql exit=0, exact marker and independent readback'))

def prepare():
    need(os.environ.get('LAB_BOOKING_DB_MODE')=='migration','Expected guarded migration mode')
    with connect(MIGRATOR) as c:
        record('identity',identity(c,MIGRATOR))
        need(one(c,'SELECT pg_catalog.pg_try_advisory_lock(21404121) AS locked')['locked'],'Another release gate is active')
        prior=old_privileges(c)
        default_grants(c)
        verified=accounts(c)
        dev=equipment(c)
        need(dev['status']=='available','The specifically approved demonstration device is unavailable')
        with connect(APP) as runtime:
            record('identity',identity(runtime,APP))
        origin=readiness(c)
        need(origin==([],[]) or state_ready(origin),'Unexpected migration/table mix, no changes authorized')
        if state_ready(origin):
            schema(c,'already-migrated')
            acl(c,'preflight')
        backup(c)
        apply_migrations(c)
        schema(c,'before-acl')
        authorization(c)
        need(old_privileges(c)==prior,'Account/device/session ACL changed outside scope')
        with connect(APP) as runtime:
            with runtime.transaction():
                runtime.execute('SET TRANSACTION READ ONLY')
                record('identity',identity(runtime,APP))
                need(acl(runtime,'independent-runtime-role')=='ready','Runtime effective ACL differs')
                need(equipment(runtime)==dev,'Approved device changed; no browser write authorized')
        create('ready-for-browser',{'device':dev,'authorized_account_ids':{role:a['id'] for role,a in verified.items()},
                                    'migrations':MIGRATIONS,'scope':DB,'acl':'exact','backup':'verified protected archive'})
    print('STORY21_D041_DATABASE_READY',flush=True)


def prepare_resume():
    # This entry point has no migration or backup-creation path.
    need(os.environ.get('LAB_BOOKING_DB_MODE')=='migration','Expected guarded migration mode')
    receipt=json.loads((Path(os.environ['STORY21_RESUME'])/'recovery-summary.json').read_text(encoding='utf-8'))
    proof=json.loads((Path(os.environ['STORY21_RECOVERY'])/'backup-proof.jsonl').read_text(encoding='utf-8'))
    backup_path=Path(os.environ['STORY21_BACKUP_FILE'])
    need(backup_path.is_file() and backup_path.stat().st_size==proof['size'] and digest(backup_path)==proof['sha256']
         and proof['toc_checked'] is True,'Prior protected backup does not match the original receipt')
    listing=native('backup-toc-recovery',os.environ['STORY21_PG_RESTORE'],['--list',str(backup_path)])
    need(all(re.search(r'TABLE DATA public '+table+r'\b',listing) for table in
             ('accounts_user','equipment_equipment','django_migrations','django_session')),
         'Prior backup directory listing is incomplete')
    record('backup-reused',{'size':proof['size'],'sha256':proof['sha256'],'toc_checked':True})
    with connect(MIGRATOR) as c:
        record('identity',identity(c,MIGRATOR))
        need(one(c,'SELECT pg_catalog.pg_try_advisory_lock(21404121) AS locked')['locked'],'Another release gate is active')
        need(state_ready(readiness(c)) and receipt['both_migrated'],'Both migrations must already be confirmed; no migration invoked')
        schema(c,'resume-before-acl')
        state=acl(c,'resume-preflight')
        need(state in ('pristine','ready') and state==receipt['acl'],'ACL changed since read-only recovery; stop')
        prior=old_privileges(c)
        default_grants(c)
        verified=accounts(c)
        with c.transaction():
            c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            dev=equipment(c)
            observed=one(c,"SELECT pg_catalog.clock_timestamp() AS now")['now']
            slot=demo_slot(observed,snapshot(c,dev['id']))
            record('demo-preflight',{'device':dev,'slot_beijing':[x.isoformat() for x in slot]})
        with connect(APP) as runtime:
            record('identity',identity(runtime,APP))
            need(equipment(runtime)==dev,'Approved device changed; stop')
        from reservations.management.commands._chrome_probe import chrome
        with chrome() as probe:
            version=probe.call('Browser.getVersion')['product']
            need(version.startswith('Chrome/'),'Expected installed Chrome before any GRANT or restart')
            record('chrome-preflight',{'product':version})
        authorization(c)
        need(old_privileges(c)==prior,'Account/device/session ACL changed outside scope')
        with connect(APP) as runtime:
            with runtime.transaction():
                runtime.execute('SET TRANSACTION READ ONLY')
                need(acl(runtime,'independent-runtime-role')=='ready','Runtime effective ACL differs')
                need(equipment(runtime)==dev,'Approved device changed; no browser write authorized')
        create('ready-for-browser',{'device':dev,'authorized_account_ids':{role:a['id'] for role,a in verified.items()},
                                    'migrations':MIGRATIONS,'scope':DB,'acl':'exact','backup':'original protected archive verified'})
    print('STORY21_D041_DATABASE_READY',flush=True)


def snapshot(c,did):
    return {
      'device':equipment(c),
      'reservations':rows(c,"""SELECT r.id,r.applicant_id,r.equipment_id,r.start_at,r.end_at,r.status,r.applied_at
                             FROM public.reservations_reservation AS r WHERE r.equipment_id=%s ORDER BY r.id""",(did,)),
      'history':rows(c,"""SELECT h.id,h.object_type,h.equipment_id,h.reservation_id,h.action,h.before_status,h.after_status,
                                   h.actor_type,h.decision_at,h.recorded_at
                            FROM public.audit_operationhistory AS h
                            LEFT JOIN public.reservations_reservation AS r ON r.id=h.reservation_id
                            WHERE r.equipment_id=%s OR h.equipment_id=%s ORDER BY h.id""",(did,did))}

def safe_pending(now,data):
    need(all(r['status']!='pending' or r['start_at']>now+timedelta(minutes=5) for r in data['reservations']),
         'Existing due/imminent pending rows could trigger unrelated expiry; no POST sent')

def free(start,end,observed,data):
    return not any((r['status']=='approved' or (r['status']=='pending' and r['start_at']>observed))
                   and r['start_at']<end and start<r['end_at'] for r in data['reservations'])

def demo_slot(observed,data):
    need(data['device']['status']=='available','The approved demonstration device is unavailable')
    safe_pending(observed,data)
    day=observed.astimezone(BJ).date()+timedelta(days=1)
    for h in (*range(10,22),8,9,22,*range(8)):
        start=datetime.combine(day,time(h),tzinfo=BJ)
        end=start+timedelta(hours=1)
        if start>observed and free(start,end,observed,data):
            return start,end
    raise RuntimeError('No legal conflict-free slot on the next Beijing day; no POST sent')

def recover():
    with connect(MIGRATOR) as c:
        with c.transaction():
            c.execute('SET TRANSACTION READ ONLY')
            record('identity',identity(c,MIGRATOR))
            current=readiness(c)
            summary={'both_migrated':state_ready(current),'acl':'not checked','slot_beijing':None}
            record('recovery-state',{'registration_and_objects':current,'both_migrated':state_ready(current)})
            if state_ready(current):
                schema(c,'read-only-recovery')
                summary['acl']=acl(c,'read-only-recovery',True)
                dev=equipment(c)
                observed=one(c,'SELECT pg_catalog.clock_timestamp() AS now')['now']
                data=snapshot(c,dev['id'])
                try:
                    summary['slot_beijing']=[x.isoformat() for x in demo_slot(observed,data)]
                except RuntimeError as e:
                    summary['demo_blocker']=str(e)
                summary['observed_at']=observed
                summary['device']=dev
                summary['reservation_count']=len(data['reservations'])
                p=Path(os.environ['STORY21_RECOVERY'])/'reservation-intent.json'
                if p.is_file():
                    i=json.loads(p.read_text(encoding='utf-8-sig'))
                    need(i['device_id']==dev['id'] and i['device_number']==DEV,'Prior intent not for the approved device')
                    data=snapshot(c,dev['id'])
                    hits=[r for r in data['reservations'] if r['applicant_id']==i['applicant_id']
                          and r['start_at']==datetime.fromisoformat(i['start_at'])
                          and r['end_at']==datetime.fromisoformat(i['end_at'])]
                    record('recovery-reservation',dict(intent=i,matching_rows=hits,
                         related_history=[h for h in data['history'] if h['reservation_id'] in {r['id'] for r in hits}]))
            create('recovery-summary',summary)
    print('STORY21_D041_READ_ONLY_RECOVERY_OK',flush=True)


def browser_run():
    need(os.environ.get('LAB_BOOKING_DB_MODE')=='runtime','Expected guarded runtime mode')
    from reservations.management.commands._chrome_probe import chrome, fill, poll
    # Django CommandError module is import-only here. The browser talks only to the local runtime.
    ready=read('ready-for-browser')
    did=ready['device']['id']
    need(type(did) is int and did>0,'Approved device ID is not a positive integer')
    detail=f'/equipment/{did}/'
    form=detail+'reserve/'
    button='form[aria-describedby="time-rules"] button[type=submit]'
    text="""document.querySelector('main')?.innerText ?? document.body?.innerText ?? ''"""
    details="""[...document.querySelectorAll('main dl dd')].map(x => x.innerText.trim())"""
    def scoped_snapshot(c,stage):
        with c.transaction():
            c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            observed=one(c,'SELECT pg_catalog.clock_timestamp() AS now')['now']
            data=snapshot(c,did)
        need(data['device']==ready['device'],'Approved device no longer matches release preflight')
        record('demo-db',dict(stage=stage,observed_at=observed,**data))
        return observed,data
    def values(s,e): return {'start_at':s.strftime('%Y-%m-%dT%H:%M'),'end_at':e.strftime('%Y-%m-%dT%H:%M')}
    with connect(MIGRATOR) as observer:
        with observer.transaction():
            observer.execute('SET TRANSACTION READ ONLY')
            record('identity',identity(observer,MIGRATOR))
            people=accounts(observer)
        need({role:a['id'] for role,a in people.items()}==ready['authorized_account_ids'],'Approved account scope changed')
        observed, initial=scoped_snapshot(observer,'before-browser')
        start,end=demo_slot(observed,initial)
        missing_id=9223372036854775807
        with observer.transaction():
            observer.execute('SET TRANSACTION READ ONLY')
            need(not one(observer,'SELECT EXISTS(SELECT 1 FROM public.reservations_reservation AS r WHERE r.id=%s) AS found',
                         (missing_id,))['found'],'Absent control not available; no POST sent')
        fields=values(start,end)
        with chrome() as b:
            def location():
                return b.evaluate("""({origin:location.origin,path:location.pathname,time:performance.timeOrigin,
                   status:performance.getEntriesByType('navigation')[0]?.responseStatus,ready:document.readyState})""")
            def transition(action,path,status):
                previous=(location() or {}).get('time')
                event_count=len(b.documents)
                action()
                def loaded():
                    x=location() or {}
                    wire=any(d['url']==BASE+path and d['status']==status for d in b.documents[event_count:])
                    return x if (x.get('origin')==BASE and x.get('path')==path and x.get('time')!=previous
                                 and x.get('ready')=='complete' and x.get('status')==status and wire) else None
                poll(loaded,f'{path} HTTP {status}',seconds=15)
            def go(path,status=200):
                transition(lambda:b.call('Page.navigate',url=BASE+path),path,status)
            def click(selector,path,status=200):
                transition(lambda:b.click(selector),path,status)
            def js_call(body,*xs):
                return b.evaluate('('+body+')('+','.join(json.dumps(x,ensure_ascii=False) for x in xs)+')')
            def login(role):
                go('/login/')
                a=people[role]
                need(js_call("""(u,p)=>{const f=document.querySelector('form[method="post"]');
                    if(location.pathname!='/login/'||!f?.querySelector('[name=csrfmiddlewaretoken]')||
                       new URL(f.action).pathname!='/login/')return false;
                    f.elements.username.value=u; f.elements.password.value=p; return true}""",
                    a['username'],a['password']), 'Protected Chrome login form absent')
                click('form[method="post"] button[type="submit"]','/identity/')
                need(b.evaluate(details)==[a['username'],ROLE[role]],'Real Chrome session has the wrong identity')
                record('chrome-cases',dict(case='identity',role=role,authenticated=True,http=200))
            def logout():
                go('/identity/')
                click('form[action="/logout/"] button[type="submit"]','/login/')
            def navigation(role):
                click('main a[href="/equipment/"]','/equipment/')
                selector=f'tbody a[href="{detail}"]'
                need(b.evaluate('document.querySelector('+json.dumps(selector)+')?.innerText.trim()')==DEV,
                     'Approved device catalog link does not match physical row')
                click(selector,detail)
                found=b.evaluate('!!document.querySelector('+json.dumps(f'main a[href="{form}"]')+')')
                need(found==(role!='admin'),'Reservation link does not match the actual role')
                if found: click(f'main a[href="{form}"]',form)
                record('chrome-cases',dict(case='navigation',role=role,detail=detail,form_link=found))
            phase='startup'
            try:
                version=b.call('Browser.getVersion')['product']
                need(version.startswith('Chrome/'),'Expected actual installed Chrome')
                record('chrome-cases',dict(case='version',product=version,origin=BASE))
                phase='student real navigation'
                login('student')
                navigation('student')
                valid=fill(b,fields)
                need(valid and valid['valid'] and not valid['formNoValidate'] and not valid['buttonNoValidate'],
                     'Ordinary submitted document has invalid or bypassed controls')
                now,before=scoped_snapshot(observer,'immediately-before-one-submit')
                safe_pending(now,before)
                need(before==initial and start>now and free(start,end,now,before),'Demo state or time changed; no POST sent')
                # Write-once intent is retained even if the process, browser or confirmation is lost.
                intent('reservation',{'device_id':did,'device_number':DEV,'applicant_id':people['student']['id'],
                    'start_at':start.isoformat(),'end_at':end.isoformat(),'slot_beijing':fields})
                phase='one student POST; never replay after intent'
                click(button,form,201)
                d=b.evaluate(details)
                need(len(d)==4 and d[0].isascii() and d[0].isdigit() and d[3]=='待审核' and DEV in d[1]
                     and d[2]==start.strftime('%Y-%m-%d %H:%M')+' 至 '+end.strftime('%Y-%m-%d %H:%M'),
                     'Unexpected confirmation fields; do not resubmit')
                rid=int(d[0])
                result_path=f'/reservations/{rid}/result/'
                click(f'main a[href="{result_path}"]',result_path)
                need(b.evaluate(details)==d,'Own result differs from confirmation')
                now,after=scoped_snapshot(observer,'committed-and-own-read')
                added=[r for r in after['reservations'] if r['id'] not in {x['id'] for x in before['reservations']}]
                need(len(added)==1 and after['history']==before['history'] and
                     [r for r in after['reservations'] if r['id']!=rid]==before['reservations'],'Exactly one new row and no other change were required')
                row=added[0]
                need((row['id'],row['applicant_id'],row['equipment_id'],row['start_at'],row['end_at'],row['status'])
                     ==(rid,people['student']['id'],did,start,end,'pending') and row['applied_at']<=now<start,
                     'Persistence and immediate pending occupancy not confirmed')
                record('chrome-cases',dict(case='student',post=201,own_read=200,result=result_path,form=form))
                logout()
                phase='teacher overlap, then foreign GET'
                login('teacher')
                navigation('teacher')
                now,control=scoped_snapshot(observer,'before-teacher')
                safe_pending(now,control)
                need(control==after and now<start and not free(start,end,now,control),'Expected unchanged active pending occupancy')
                valid=fill(b,fields)
                need(valid and valid['valid'] and not valid['buttonNoValidate'] and not valid['formNoValidate'],'Teacher controls invalid')
                click(button,form,409)
                need(b.evaluate("""document.querySelector('[role="alert"]')?.textContent.trim()""")==
                     '所选时段与有效预约冲突，请选择其他时段。','409 is not the explicit device overlap')
                go(result_path,404)
                denied=b.evaluate(text)
                go(f'/reservations/{missing_id}/result/',404)
                need(denied==b.evaluate(text) and all(v not in denied for v in d[1:]),'Foreign response exposed protected content')
                need(scoped_snapshot(observer,'after-teacher')[1]==after,'Teacher rejection changed reservation/history')
                record('chrome-cases',dict(case='teacher',post=409,foreign_read=404,absent_control=404,no_leak=True,no_write=True))
                logout()
                phase='admin link, direct GET and POST denial'
                login('admin')
                navigation('admin')
                go(form,403)
                need(not b.evaluate('!!document.querySelector(\'form[aria-describedby="time-rules"]\')'),'Admin received a protected reservation form')
                go('/identity/')
                def admin_post():
                    need(js_call("""(path,values)=>{const token=document.querySelector(
                       'form[action="/logout/"] [name=csrfmiddlewaretoken]')?.value;
                       if(!token||location.pathname!='/identity/')return false;
                       const f=document.createElement('form'); f.method='post';f.action=path;
                       for(const [k,v] of Object.entries({...values,csrfmiddlewaretoken:token})){
                           const i=document.createElement('input');i.type='hidden';i.name=k;i.value=v;f.append(i);}
                       document.body.append(f);setTimeout(()=>f.requestSubmit(),0);return true}""",form,fields),
                       'Missing valid CSRF control for admin POST')
                transition(admin_post,form,403)
                need(not b.evaluate('!!document.querySelector(\'form[aria-describedby="time-rules"]\')'),'Admin received a protected reservation form')
                go(result_path,403)
                need(scoped_snapshot(observer,'final-independent-readback')[1]==after,'Admin request changed reservation/history')
                record('chrome-cases',dict(case='admin',form_link=False,get=403,post=403,foreign_read=403,no_write=True))
                logout()
                create('runtime-result',dict(login=BASE+'/login/',catalog=BASE+'/equipment/',reservation_entry=BASE+form,
                       own_result=BASE+result_path,device=DEV,device_id=did,reservation_id=rid,applicant_id=row['applicant_id'],
                       slot=fields,status='pending',history_delta=0,live_chrome=version,
                       verified=['student new and own','teacher conflict and no foreign read','admin no entry or write']))
            except Exception as e:
                record('chrome-failure',dict(phase=phase,error_type=type(e).__name__))
                raise
            finally:
                record('chrome-documents',{'requests':b.documents})
    print('STORY21_D041_BROWSER_AND_DB_OK',flush=True)

if __name__=='__main__':
    try:
        need(mode in ('prepare','resume','browser','recover'),'Unknown release phase')
        {'prepare':prepare,'resume':prepare_resume,'browser':browser_run,'recover':recover}[mode]()
    except Exception as e:
        msg=str(e) if type(e) is RuntimeError else 'See phase details and read-only recovery. No automatic replay.'
        record('failure',{'phase':mode,'error_type':type(e).__name__,'message':msg})
        if mode!='browser':
            # DB errors preserve server SQLSTATE without credential details.
            diagnostic={'sqlstate':getattr(e,'sqlstate',None) or getattr(e.__cause__,'sqlstate',None)}
            if getattr(getattr(e,'diag',None),'message_primary',None)=='ACL arrays must be one-dimensional':
                diagnostic['primary']='ACL arrays must be one-dimensional'
            record('failure-diagnostics',diagnostic)
        print(f'D-041 {mode} stopped: {type(e).__name__}: {msg}',file=sys.stderr)
        sys.exit(1)

