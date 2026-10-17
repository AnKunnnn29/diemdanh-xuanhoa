"""Offline import of approved private contacts and explicit Sr Admin promotion."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT/'excel_bridge'))
from accounts import Accounts
from server import Store
from management import Management

def key(name):return ' '.join(unicodedata.normalize('NFC',name).casefold().split())
def run(args):
    source=json.loads(args.source.read_text(encoding='utf-8'))
    if source['year']!='2026-2027' or len(source['profiles'])!=43 or sum(p['is_sister'] for p in source['profiles'])!=5:raise ValueError('Nguồn hồ sơ không khớp danh sách đã đối chiếu.')
    doc=args.root/source['source']
    if doc.exists() and hashlib.sha256(doc.read_bytes()).hexdigest()!=source['sourceSha256']:raise ValueError('Tài liệu nguồn đã thay đổi.')
    if not args.apply:print(json.dumps({'profiles':43,'sistersToAdmin':5,'phones':43,'birthYears':38,'fullBirthDatesInferred':0}));return
    if not (args.state_dir/'accounts.sqlite3').is_file():raise ValueError('Không tìm thấy cơ sở dữ liệu tài khoản.')
    backup=args.state_dir/('staff-profiles-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
    with sqlite3.connect(args.state_dir/'accounts.sqlite3') as current,sqlite3.connect(backup/'accounts-before.sqlite3') as saved:current.backup(saved)
    store=Store(args.root,args.state_dir,grade_mode='portable');accounts=Accounts(args.state_dir,store.catalog);management=Management(store,accounts)
    if store.catalog.public()['year']!=source['year']:raise ValueError('Năm làm việc không khớp nguồn hồ sơ.')
    users=accounts.users();profiles=management.staff()['profiles'];jobs=[]
    actor=next((u for u in users if u['role']=='Admin' and u['active']),None)
    if not actor:raise ValueError('Không tìm thấy Admin đang hoạt động.')
    for item in source['profiles']:
        matches=[u for u in users if key(u['displayName'])==key(item['full_name'])]
        if len(matches)>1 or not matches and not item['future']:raise ValueError('Kiểm tra tài khoản liên kết: '+item['full_name'])
        user=matches[0] if matches else None
        if user and not user['active']:raise ValueError('Tài khoản đang bị khoá: '+item['full_name'])
        existing=[p for p in profiles if (user and p['user_id']==user['id']) or (not user and not p['user_id'] and key(p['full_name'])==key(item['full_name']))]
        if len(existing)>1:raise ValueError('Trùng hồ sơ: '+item['full_name'])
        values=dict(existing[0]) if existing else {'full_name':item['full_name'],'status':'active','user_id':user['id'] if user else ''}
        if values.get('birth_date') and item['birth_year'] and int(values['birth_date'][:4])!=item['birth_year']:raise ValueError('Ngày sinh đã có không khớp năm sinh nguồn: '+item['full_name'])
        values.update(phone=item['phone'],birth_year=item['birth_year'] or values.get('birth_year'))
        if item['future'] and 'HKII' not in (values.get('note') or ''):values['note']=((values.get('note') or '')+' Phụ trách Hiệp Sĩ 1 B từ HKII; chưa cấp quyền lớp trong HKI.').strip()
        jobs.append((item,user,values))
    promoted=0
    for item,user,values in jobs:
        if item['is_sister'] and user['role']!='Admin':
            accounts.update(actor,{'id':user['id'],'role':'Admin','active':True});promoted+=1
        management.save_staff(actor,values)
    # Keep the previously delivered credentials' role column accurate; no password changes.
    role_changes={key(item['full_name']) for item in source['profiles'] if item['is_sister']}
    for credentials in args.state_dir.glob('staff-import-*/tai-khoan-glv-moi.csv'):
        with credentials.open(encoding='utf-8-sig',newline='') as file:reader=csv.DictReader(file);fields=reader.fieldnames;rows=list(reader)
        changed=False
        for row in rows:
            if key(row.get('Họ tên','')) in role_changes and row.get('Vai trò')!='Admin':row['Vai trò']='Admin';changed=True
        if changed:
            shutil.copy2(credentials,backup/(credentials.parent.name+'-credentials-before.csv'))
            stage=credentials.with_suffix('.tmp')
            with stage.open('w',encoding='utf-8-sig',newline='') as file:writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader();writer.writerows(rows)
            os.replace(stage,credentials)
    actual=management.staff()
    for item,user,_ in jobs:
        profile=next(p for p in actual['profiles'] if p['user_id']==user['id']) if user else next(p for p in actual['profiles'] if not p['user_id'] and key(p['full_name'])==key(item['full_name']))
        if profile['phone']!=item['phone'] or item['birth_year'] and profile['birth_year']!=item['birth_year']:raise ValueError('Hồ sơ lưu chưa khớp nguồn.')
        if item['is_sister'] and next(u for u in actual['accounts'] if u['id']==user['id'])['role']!='Admin':raise ValueError('Chưa cập nhật quyền Sr.')
    with accounts.db() as db:accounts.audit(db,actor['id'],'staff-profiles-imported',{'source':source['source'],'sourceSha256':source['sourceSha256'],'profiles':43,'sistersPromoted':promoted,'phones':43,'birthYears':38,'fullBirthDatesInferred':0,'method':'local-offline-maintenance'})
    result={'profiles':43,'sistersPromoted':promoted,'phones':43,'birthYears':38,'fullBirthDatesInferred':0,'backup':str(backup)}
    (backup/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');store.shutdown();print(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--state-dir',type=Path,required=True);parser.add_argument('--source',type=Path,default=PROJECT/'.local/staff-profiles-source-2026-2027.json');parser.add_argument('--apply',action='store_true');args=parser.parse_args();args.root=args.root.resolve();args.state_dir=args.state_dir.resolve()
    mutex=None
    try:
        if os.name=='nt' and args.apply:
            import win32api,win32event
            mutex=win32event.CreateMutex(None,False,'Local\\XuanHoaExcel-'+hashlib.sha256(str(args.root).casefold().encode()).hexdigest())
            if win32api.GetLastError()==183:raise RuntimeError('Dừng dịch vụ của thư mục dữ liệu này trước khi cập nhật.')
        run(args)
    finally:
        if mutex is not None:mutex.Close()
