"""Apply an explicit staffing plan offline, preserving XLSM packages and accounts.

The service mutex must be free. Each class uses the application's assignment
journal; account passwords are never reset. New temporary credentials stay local.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from lxml import etree

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'excel_bridge'))
from accounts import Accounts, SLOTS
from catalog import Catalog
from server import TRUSTED_VBA
from xlsm_package import patch_package,sheet_paths,Q

CELLS={'glv1':'B3','glv2':'E3','glv3':'E4','souer':'B4'}
def name_key(value):return ' '.join(unicodedata.normalize('NFC',value).casefold().split())
def teacher_package(original,teachers):
    inputs={('Danh Sách',ref):teachers[slot] or None for slot,ref in CELLS.items()};caches={}
    with ZipFile(io.BytesIO(original)) as archive:
        paths=sheet_paths(archive)
        for sheet,path in paths.items():
            root=etree.fromstring(archive.read(path))
            for cell in root.findall('.//'+Q('c')):
                formula=cell.find(Q('f'))
                if formula is not None:
                    match=re.fullmatch(r"'Danh Sách'!\$?([BE])\$?([34])",formula.text or '')
                    if match:
                        ref=match[1]+match[2];slot=next(s for s,r in CELLS.items() if r==ref)
                        caches[(sheet,cell.get('r'))]=teachers[slot] or ''
    changed=patch_package(original,inputs,caches)
    # Every unrelated ZIP member, formula, and worksheet node must survive intact.
    with ZipFile(io.BytesIO(original)) as before,ZipFile(io.BytesIO(changed)) as after:
        if before.namelist()!=after.namelist():raise ValueError('Thành phần XLSM bị thay đổi.')
        allowed={}
        for sheet,ref in {*inputs,*caches}:allowed.setdefault(paths[sheet],set()).add(ref)
        for path in before.namelist():
            a,b=before.read(path),after.read(path)
            if a==b:continue
            if path not in allowed:raise ValueError('Thay đổi ngoài ô phân công: '+path)
            roots=[etree.fromstring(value) for value in (a,b)]
            for root in roots:
                for cell in list(root.findall('.//'+Q('c'))):
                    if cell.get('r') in allowed[path]:
                        # Formula text is independently required to remain identical.
                        f=cell.find(Q('f'))
                        if f is not None:
                            counterpart=next((c for c in (roots[1] if root is roots[0] else roots[0]).findall('.//'+Q('c')) if c.get('r')==cell.get('r')),None)
                            if counterpart is not None and counterpart.findtext(Q('f'))!=f.text:raise ValueError('Công thức bị đổi.')
                        cell.getparent().remove(cell)
            if etree.tostring(roots[0],method='c14n')!=etree.tostring(roots[1],method='c14n'):raise ValueError('Thay đổi ngoài phạm vi ô phân công.')
    return changed

class StaffingStore:
    def __init__(self,catalog):self.catalog=catalog
    def update_teachers(self,values):
        info=self.catalog.classes[values['classId']];path=info['path'];original=path.read_bytes()
        changed=teacher_package(original,{s:values[s] for s in SLOTS})
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.staff-stage',delete=False) as output:
            stage=Path(output.name);output.write(changed);output.flush();os.fsync(output.fileno())
        try:
            if path.read_bytes()!=original:raise ValueError('File vừa được sửa từ bên ngoài; chưa thay thế.')
            os.replace(stage,path)
        finally:
            if stage.exists():stage.unlink()
        self.catalog.refresh()
        if self.catalog.classes[info['id']]['teachers']!={s:values[s] for s in SLOTS}:raise ValueError('Tên trong sổ chưa khớp phân công.')
        return {'saved':True}

def run(args):
    plan=json.loads(args.plan.read_text(encoding='utf-8'))
    source=args.root/plan['source']
    if source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()!=plan['sourceSha256']:raise ValueError('Tài liệu nguồn đã thay đổi; trích lại bảng phân công trước khi nhập.')
    catalog=Catalog(args.root,args.state_dir,TRUSTED_VBA)
    if catalog.public()['year']!=plan['year']:raise ValueError('Năm học không khớp nguồn phân công.')
    by_name={c['name']:c for c in catalog.classes.values()}
    if set(by_name)!={c['name'] for c in plan['classes']}:raise ValueError('Danh sách lớp không khớp nguồn.')
    names={name for c in plan['classes'] for name in c['teachers'].values() if name}
    if not args.apply:
        print(json.dumps({'classes':len(by_name),'activeStaff':len(names),'futureAssignments':sum(len(c['futureTeachers']) for c in plan['classes'])}));return
    if not (args.state_dir/'accounts.sqlite3').is_file():raise ValueError('Chưa tìm thấy cơ sở dữ liệu tài khoản của dịch vụ.')
    if any(c['path'].with_name('~$'+c['path'].name).exists() for c in catalog.classes.values()):raise ValueError('Đóng các sổ lớp đang mở trong Excel trước khi nhập phân công.')
    backup=args.state_dir/('staff-import-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(parents=True)
    manifest={'source':plan['source'],'sourceSha256':plan['sourceSha256'],'year':plan['year'],'workbooks':[]}
    for c in catalog.classes.values():
        destination=backup/'workbooks'/c['path'].relative_to(args.root);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(c['path'],destination)
        manifest['workbooks'].append({'path':str(c['path']),'backup':str(destination),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
    with sqlite3.connect(args.state_dir/'accounts.sqlite3') as source,sqlite3.connect(backup/'accounts-before.sqlite3') as target:source.backup(target)
    (backup/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    accounts=Accounts(args.state_dir,catalog);accounts.recover_assignments(catalog);created=[];selections={}
    credentials=backup/'tai-khoan-glv-moi.csv'
    with credentials.open('x',encoding='utf-8-sig',newline='') as output:
        writer=csv.writer(output);writer.writerow(['Tên đăng nhập','Mật khẩu tạm','Họ tên','Vai trò'])
        with accounts.db() as db:
            actor=db.execute("SELECT * FROM users WHERE role='Admin' AND active=1 ORDER BY created_at LIMIT 1").fetchone()
            if not actor:raise ValueError('Chưa có tài khoản quản trị đang hoạt động.')
            for name in sorted(names):
                matches=[row for row in db.execute('SELECT * FROM users') if name_key(row['display_name'])==name_key(name)]
                if len(matches)>1 or matches and not matches[0]['active']:raise ValueError('Tài khoản trùng tên hoặc đã khoá: '+name)
                if matches:selections[name]=matches[0]['id']
                else:
                    account=accounts._create(db,name,'GLV');selections[name]=account['id'];created.append(account['id'])
                    writer.writerow([account['username'],account['temporaryPassword'],account['displayName'],'GLV'])
            output.flush();os.fsync(output.fileno())
            accounts.audit(db,actor['id'],'staff-plan-import-started',{'source':plan['source'],'sourceSha256':plan['sourceSha256'],'classes':len(by_name),'newAccounts':len(created),'method':'local-offline-maintenance'})
            actor={'id':actor['id'],'displayName':actor['display_name']}
    store=StaffingStore(catalog);changed=0
    for item in plan['classes']:
        info=by_name[item['name']];chosen={slot:selections.get(item['teachers'][slot],'') for slot in SLOTS}
        with accounts.db() as db:current={slot:'' for slot in SLOTS}|{r['slot']:r['user_id'] for r in db.execute('SELECT * FROM assignments WHERE class_id=?',(info['id'],))}
        if current==chosen and info['teachers']==item['teachers']:continue
        accounts.assign_class(store,actor,{'classId':info['id'],'accountAssignments':chosen});changed+=1
    with accounts.db() as db:
        for item in plan['classes']:
            actual={r['slot']:r['display_name'] for r in db.execute('SELECT a.slot,u.display_name FROM assignments a JOIN users u ON u.id=a.user_id WHERE a.class_id=?',(by_name[item['name']]['id'],))}
            if actual!={s:n for s,n in item['teachers'].items() if n}:raise ValueError('Quyền truy cập chưa khớp sổ lớp.')
        accounts.audit(db,actor['id'],'staff-plan-import-completed',{'source':plan['source'],'classes':len(by_name),'changed':changed,'newAccounts':len(created),'futureAssignmentsDeferred':sum(len(c['futureTeachers']) for c in plan['classes'])})
    report={'classes':len(by_name),'changed':changed,'newAccounts':len(created),'activeStaff':len(names),'backup':str(backup),'credentials':str(credentials),'futureAssignmentsDeferred':sum(len(c['futureTeachers']) for c in plan['classes'])}
    (backup/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--state-dir',type=Path,required=True);parser.add_argument('--plan',type=Path,default=PROJECT/'src/data/staff-plan-2026-2027.json');parser.add_argument('--apply',action='store_true');args=parser.parse_args();args.root=args.root.resolve();args.state_dir=args.state_dir.resolve()
    mutex=None
    try:
        if os.name=='nt' and args.apply:
            import win32api,win32event
            mutex=win32event.CreateMutex(None,False,'Local\\XuanHoaExcel-'+hashlib.sha256(str(args.root).casefold().encode()).hexdigest())
            if win32api.GetLastError()==183:raise RuntimeError('Dừng dịch vụ của thư mục này trước khi nhập phân công.')
        run(args)
    finally:
        if mutex is not None:mutex.Close()
