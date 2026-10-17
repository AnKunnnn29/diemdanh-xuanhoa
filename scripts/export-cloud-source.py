"""Read-only source package for the cloud migration; never writes workbooks/DBs."""
import argparse
import base64
import hashlib
import json
import secrets
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT/'excel_bridge'))
from catalog import Catalog
from server import TRUSTED_VBA


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tables(path, *, accounts=False):
    if not path.is_file():
        raise ValueError('Thiếu cơ sở dữ liệu nguồn; chưa xuất dữ liệu không đầy đủ.')
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        result = {}
        for name in names:
            if accounts and name in ('auth_sessions', 'login_limits'):
                continue
            safe_name = '"'+name.replace('"', '""')+'"'
            result[name] = [dict(r) for r in db.execute('SELECT * FROM '+safe_name)]
        return result


def binary_json(value):
    if isinstance(value, bytes):
        return {'$binaryBase64':base64.b64encode(value).decode()}
    raise TypeError('Unsupported source value')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--state-dir', required=True)
    args = parser.parse_args()
    source_root, state_dir = Path(args.root).resolve(), Path(args.state_dir).resolve()
    if not source_root.is_dir() or not state_dir.is_dir():
        raise ValueError('Thư mục dữ liệu nguồn không tồn tại.')
    folder = PROJECT/'.local'/('cloud-source-'+datetime.now().strftime('%Y%m%d-%H%M%S-')+secrets.token_hex(4))
    folder.mkdir(parents=True)
    registry = state_dir/'school-years.json'
    registry_data = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else {
        'active':'initial','years':[{'id':'initial','root':str(source_root),'state':str(state_dir)}]}
    accounts = source_tables(state_dir/'accounts.sqlite3', accounts=True)
    exported, manifest = [], []
    file_sets = []
    for entry in registry_data['years']:
        root, working_state = Path(entry['root']).resolve(), Path(entry['state']).resolve()
        if not all(any(path.is_relative_to(base) for base in (source_root,state_dir)) for path in (root,working_state)):
            raise ValueError('Năm học nguồn trỏ ra ngoài thư mục dữ liệu đã chọn.')
        paths = [p for p in sorted(root.glob('*.xlsm'))+sorted((root/'outputs/cac-lop-2026-2027').glob('*.xlsm')) if not p.name.startswith('~$')]
        before_files = {str(p):digest(p) for p in paths}
        file_sets.append((root, before_files, working_state))
        # Explicit cache location is in the private package; source remains read-only.
        catalog = Catalog(root, folder/'catalog-cache', TRUSTED_VBA)
        public = catalog.public()
        tables = source_tables(working_state/'attendance.sqlite3')
        statuses = {r['class_id']:bool(r['archived']) for r in tables.get('class_settings',[])}
        for group in public['classes']:
            group['archived'] = statuses.get(group['id'],False)
        staff_source = PROJECT/'src/data/staff-plan-2026-2027.json'
        if staff_source.is_file():
            staff_plan = json.loads(staff_source.read_text(encoding='utf-8'))
            if staff_plan.get('year') == public['year']:
                plans = {r['name']:r for r in staff_plan['classes']}
                for group in public['classes']:
                    source_plan = plans.get(group['name'])
                    if source_plan:
                        group['staffPlan'] = {'location':source_plan.get('location',''),
                            'futureTeachers':source_plan.get('futureTeachers',[])}
        if entry['id'] == registry_data['active']:
            assignments = accounts.get('assignments',[])
        else:
            assignments = [{k:r[k] for k in ('class_id','slot','user_id')} for r in accounts.get('year_assignments',[]) if r['year_id']==entry['id']]
        exported.append({'id':entry['id'],'active':entry['id']==registry_data['active'],
                         'catalog':public,'assignments':assignments,'sourceTables':tables})
        for identifier, group in catalog.classes.items():
            original = group['path']
            initial = digest(original)
            relative = Path('workbooks')/entry['id']/(identifier+'.xlsm')
            target = folder/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original,target)
            if digest(original) != initial or digest(target) != initial:
                raise ValueError('Sổ thay đổi khi xuất. Chưa có bộ chuyển đổi nhất quán.')
            manifest.append({'yearId':entry['id'],'classId':identifier,'relative':relative.as_posix(),'sha256':initial})
    # Verify the whole source boundary, not only the individual copy operations.
    # Do not import a package if any business history/workbook changed mid-export.
    def comparable(value):
        return json.dumps(value,sort_keys=True,ensure_ascii=False,default=binary_json)
    if comparable(source_tables(state_dir/'accounts.sqlite3',accounts=True)) != comparable(accounts):
        raise ValueError('Tài khoản/lịch sử nguồn thay đổi trong lúc xuất. Thử xuất lại khi không có thao tác ghi.')
    for (root,before,working_state),year in zip(file_sets,exported):
        paths = [p for p in sorted(root.glob('*.xlsm'))+sorted((root/'outputs/cac-lop-2026-2027').glob('*.xlsm')) if not p.name.startswith('~$')]
        if {str(p):digest(p) for p in paths} != before:
            raise ValueError('Sổ nguồn thay đổi trong lúc xuất. Chưa có gói chuyển đổi nhất quán.')
        if comparable(source_tables(working_state/'attendance.sqlite3')) != comparable(year['sourceTables']):
            raise ValueError('Nghiệp vụ nguồn thay đổi trong lúc xuất. Thử xuất lại trước khi chuyển cloud.')
    if registry.exists() and comparable(json.loads(registry.read_text(encoding='utf-8'))) != comparable(registry_data):
        raise ValueError('Danh sách năm học nguồn thay đổi trong lúc xuất. Thử xuất lại.')
    bundle = {'format':'xuanhoa-cloud-source-v1','exportedAt':datetime.now(timezone.utc).isoformat(),
              'accounts':accounts,'years':exported,'workbooks':manifest}
    path = folder/'source.json'
    path.write_text(json.dumps(bundle,ensure_ascii=False,default=binary_json),encoding='utf-8')
    # Never print hashes, student names, phone numbers, passwords, or raw DSNs.
    print(json.dumps({'source':str(path),'users':len(accounts.get('users',[])),
                      'classes':sum(len(y['catalog']['classes']) for y in exported),
                      'students':sum(len(y['catalog']['students']) for y in exported),
                      'workbooks':len(manifest),'sourceModified':False},ensure_ascii=False))


if __name__ == '__main__':
    main()
