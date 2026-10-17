"""Explicit username-only migration. Review the private plan before committing."""
import argparse
import json
import os
import secrets
from pathlib import Path
from sqlalchemy import select,update,insert,bindparam
from dotenv import load_dotenv
from . import models as m
from .account_naming import rename_plan
from .database import Database
from .persistence import fingerprint
from .security import CloudError
from .service import Service,stamp
from .office import Office


def prepare(db):
    users=[dict(r) for r in db.execute(select(m.users)).mappings()]
    sisters=set(db.execute(select(m.assignments.c.user_id).where(m.assignments.c.slot=='souer')).scalars())
    plan=rename_plan(users,sisters)
    plan['digest']=fingerprint({'users':sorted([{k:r[k] for k in ('id','username','display_name','role')} for r in users],key=lambda r:r['id']),
        'sisters':sorted(sisters)})
    return plan,users


def apply(database,secret,expected_digest):
    with database.transaction() as db:
        plan,users=prepare(db)
        if plan['digest']!=expected_digest:
            raise CloudError('Danh sách tài khoản đã thay đổi. Tạo lại bản xem trước.')
        if not plan['changes']:
            return {'changed':0,'alreadyApplied':True}
        actor=next((r for r in users if r['active'] and r['role']=='Admin' and r['username']=='admin'),None)
        actor=actor or next((r for r in users if r['active'] and r['role']=='Admin'),None)
        if not actor:raise CloudError('Cần một Admin hoạt động để ghi nhật ký.')
        service=Service(database,secret)
        office=Office(service,db,actor)
        try:
            before=office.snapshot('Trước đổi tên đăng nhập GLV và Sr')
            assignments=[dict(r) for r in db.execute(select(m.assignments)).mappings()]
            sessions=[dict(r) for r in db.execute(select(m.sessions)).mappings()]
            statement=update(m.users).where(m.users.c.id==bindparam('target_id')).values(
                username=bindparam('new_username'),revision=m.users.c.revision+1)
            db.execute(statement,[{'target_id':r['id'],'new_username':r['username']} for r in plan['changes']])
            db.execute(insert(m.audit),[{'id':secrets.token_hex(16),'user_id':actor['id'],
                'action':'account-username-renamed','stamp':stamp(),'details':{
                    'id':change['id'],'before':change['oldUsername'],'after':change['username']}}
                for change in plan['changes']])
            after={r['id']:dict(r) for r in db.execute(select(m.users)).mappings()}
            immutable=set(m.users.c.keys())-{'username','revision'}
            if any(any(old[k]!=after[old['id']][k] for k in immutable) for old in users):
                raise CloudError('Thông tin ngoài tên đăng nhập thay đổi; hủy giao dịch.')
            if sorted(assignments,key=fingerprint)!=sorted([dict(r) for r in db.execute(select(m.assignments)).mappings()],key=fingerprint) or sorted(sessions,key=fingerprint)!=sorted([dict(r) for r in db.execute(select(m.sessions)).mappings()],key=fingerprint):
                raise CloudError('Phân công hoặc phiên đăng nhập thay đổi; hủy giao dịch.')
            if any(after[r['id']]['username']!=r['username'] for r in plan['changes']):
                raise CloudError('Chưa đối chiếu được toàn bộ tên đăng nhập mới.')
            saved=office.snapshot('Sau đổi tên đăng nhập GLV và Sr')
        finally:
            office.shutdown()
        return {'changed':len(plan['changes']),'glv':sum(r['prefix']=='glv' for r in plan['changes']),
            'sr':sum(r['prefix']=='sr' for r in plan['changes']),'preserved':len(plan['preserved']),
            'passwordsRolesAssignmentsAndSessionsPreserved':True,'beforeSnapshot':before['id'],'afterSnapshot':saved['id']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='.local/account-usernames')
    parser.add_argument('--commit',action='store_true')
    parser.add_argument('--expected-digest')
    args=parser.parse_args()
    load_dotenv('.env.cloud.local')
    database=Database(os.environ['XH_DATABASE_URL'])
    folder=Path(args.output).resolve()
    private=Path('.local').resolve()
    if not folder.is_relative_to(private):raise CloudError('Danh sách tài khoản phải lưu trong .local riêng tư.')
    folder.mkdir(parents=True,exist_ok=True)
    with database.engine.connect() as db:
        plan,_=prepare(db)
    (folder/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.commit:
        print(json.dumps({'changed':len(plan['changes']),'preserved':len(plan['preserved']),
            'digest':plan['digest'],'written':False,'planFile':str(folder/'plan.json')}))
        return
    if not args.expected_digest:parser.error('--commit requires --expected-digest')
    report=apply(database,os.environ['XH_SESSION_SECRET'],args.expected_digest)
    with database.engine.connect() as db:
        rows=list(db.execute(select(m.users.c.username,m.users.c.display_name,m.users.c.role).order_by(m.users.c.username)).mappings())
    lines=['# Tài khoản đăng nhập Cổng giáo lý Xuân Hoà','',
        'Mật khẩu, quyền và phân công giữ nguyên. Tên đăng nhập không dấu, viết thường.','',
        '| Họ tên | Tên đăng nhập | Quyền |','| --- | --- | --- |']
    for r in rows:
        cells=[str(r[k]).replace('|','\\|').replace('\n',' ') for k in ('display_name','username','role')]
        lines.append('| '+' | '.join(cells)+' |')
    (folder/'danh-sach-dang-nhap.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (folder/'receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'error':type(error).__name__,'message':'Chua hoan tat; khong in secret. Kiem tra ban xem truoc rieng.'}))
        raise SystemExit(1)
