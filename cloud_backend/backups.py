"""Transactional snapshots; immutable file blobs are shared rather than copied.

Backups include business data, accounts and assignments but never login sessions,
provider credentials or rate-limit buckets. Large exports use authenticated
parts below Vercel's response limit and are zipped in the admin's browser.
"""
import copy
import hashlib
import json
import secrets
from datetime import datetime
from sqlalchemy import select, insert, update, delete, func
from . import models as m
from .workflows import LOCAL_TZ
from .persistence import document, save_document, fingerprint, Download, load_blob
from .security import CloudError

BUSINESS = (m.years, m.classes, m.students, m.assignments, m.marks, m.records)
ACCOUNT_TABLES = (m.users, m.staff)
ALL = BUSINESS+ACCOUNT_TABLES


class BackupRules:
    def backup_rows(self):
        result = {}
        for table in ALL:
            statement = select(table)
            if table is m.records:
                statement = statement.where(m.records.c.kind != 'snapshot')
            rows = [dict(r) for r in self.connection.execute(statement).mappings()]
            result[table.name] = sorted(rows, key=fingerprint)
        return result

    def backup_revision(self):
        return fingerprint(self.backup_rows())

    def snapshot(self, label):
        tables = self.backup_rows()
        digests = sorted({r['payload'].get('blobDigest') or r['payload'].get('sha256')
            for r in tables[m.records.name] if r['kind'] == 'source-workbook'}-{None})
        info = {'id':secrets.token_hex(16), 'stamp':self.stamp(), 'label':str(label or 'Sao lưu đầy đủ')[:150],
            'actor':self.user['displayName'], 'count':len(self.catalog.classes), 'includesAccounts':True}
        payload = {**info, 'format':'xuanhoa-cloud-backup-v2', 'tables':tables, 'blobDigests':digests}
        payload['digest'] = fingerprint(payload)
        save_document(self.connection, self.year_id, 'snapshot', info['id'], payload)
        policy = self.connection.execute(select(m.settings.c.value).where(m.settings.c.key == 'backup-policy')).scalar_one_or_none() or {'hours':24}
        self.save_backup_policy({**policy,'lastAt':info['stamp']})
        return info

    def save_backup_policy(self, policy):
        exists = self.connection.execute(select(m.settings.c.key).where(m.settings.c.key == 'backup-policy')).first()
        if exists:
            self.connection.execute(update(m.settings).where(m.settings.c.key == 'backup-policy').values(value=policy))
        else:
            self.connection.execute(insert(m.settings).values(key='backup-policy',value=policy))

    def snapshots(self):
        return sorted([r['payload'] for r in self.connection.execute(select(m.records).where(m.records.c.kind == 'snapshot')).mappings()],
            key=lambda row:row['stamp'], reverse=True)

    def system_info(self):
        policy = self.connection.execute(select(m.settings.c.value).where(m.settings.c.key == 'backup-policy')).scalar_one_or_none() or {'hours':24}
        return {'mode':'cloud', 'dataRoot':'Supabase · dữ liệu riêng của giáo xứ', 'localFiles':len(self.catalog.classes),
            'backupHours':policy['hours'], 'lastBackupError':'', 'backupTrigger':'activity',
            'storageBytes':self.connection.execute(select(func.coalesce(func.sum(m.blobs.c.size),0))).scalar_one(),
            'storageLimitBytes':300_000_000,
            'snapshots':[{key:s[key] for key in ('id','stamp','label','actor','count','includesAccounts')} for s in self.snapshots()]}

    def backup_settings(self, values):
        hours = values.get('hours')
        if type(hours) is not int or hours not in (0,12,24,168):
            raise CloudError('Chu kỳ sao lưu không hợp lệ.')
        policy = self.connection.execute(select(m.settings.c.value).where(m.settings.c.key == 'backup-policy')).scalar_one_or_none() or {}
        self.save_backup_policy({**policy,'hours':hours})
        return {'saved':True, 'system':self.system_info()}

    def scheduled_backup(self):
        policy = self.connection.execute(select(m.settings.c.value).where(m.settings.c.key == 'backup-policy')).scalar_one_or_none() or {'hours':24}
        snapshots = self.snapshots()
        previous = datetime.fromisoformat(snapshots[0]['stamp']) if snapshots else None
        if policy['hours'] and (previous is None or (datetime.now(LOCAL_TZ)-previous).total_seconds() >= policy['hours']*3600):
            self.snapshot('Sao lưu định kỳ khi cập nhật dữ liệu')

    def selected_snapshot(self, identifier):
        result = next((s for s in self.snapshots() if s['id'] == identifier), None)
        if not result:
            raise CloudError('Không tìm thấy bản sao lưu.', 404, 'not_found')
        if fingerprint({key:value for key,value in result.items() if key != 'digest'}) != result['digest']:
            raise CloudError('Bản sao không khớp mã kiểm tra; chưa khôi phục.')
        return result

    def snapshot_manifest(self, identifier):
        snapshot = self.selected_snapshot(identifier)
        content = json.dumps(snapshot,ensure_ascii=False,separators=(',',':')).encode()
        count = max(1,(len(content)+2_999_999)//3_000_000)
        items = [{'filename':'data.json' if count == 1 else f'data.part{index+1:04}',
            'url':f'/api/snapshot-part?id={identifier}&part=data-{index}'} for index in range(count)]
        items += [{'filename':'blobs/'+digest+'.bin', 'url':f'/api/snapshot-part?id={identifier}&part='+digest}
            for digest in snapshot['blobDigests']]
        return {'format':'xuanhoa-download-v1', 'filename':'XuanHoa-'+identifier+'.zip', 'items':items,
            'readme':{'format':'xuanhoa-cloud-backup-v2', 'dataParts':[i['filename'] for i in items[:count]],
                'dataSha256':hashlib.sha256(content).hexdigest(), 'note':'Nếu có nhiều data.part, ghép các phần theo thứ tự trước khi đọc JSON. Bản sao chứa thông tin riêng và mã băm mật khẩu; lưu ở nơi riêng tư.'}}

    def snapshot_part(self, query):
        snapshot = self.selected_snapshot(query.get('id'))
        part = query.get('part','')
        if part.startswith('data-') and part[5:].isdigit():
            content = json.dumps(snapshot,ensure_ascii=False,separators=(',',':')).encode()
            offset = int(part[5:])*3_000_000
            if offset >= len(content):
                raise CloudError('Phần tải không tồn tại.', 404, 'not_found')
            return Download(content[offset:offset+3_000_000], 'data.part', 'application/octet-stream')
        if part not in snapshot['blobDigests']:
            raise CloudError('File không thuộc bản sao đã chọn.', 403, 'forbidden')
        return Download(load_blob(self.connection, part), part+'.bin', 'application/octet-stream')

    def restore_preview(self, values, accounts=False):
        self.reason(values)
        snapshot = self.selected_snapshot(values.get('id'))
        plan = {'id':snapshot['id'], 'stamp':snapshot['stamp'], 'count':snapshot['count'],
            'addedFiles':[], 'removedFiles':[], 'warning':'Khôi phục tài khoản sẽ kết thúc mọi phiên đăng nhập.' if accounts
                else 'Khôi phục dữ liệu các năm học; giữ tài khoản và mật khẩu hiện tại.'}
        if accounts:
            plan['users'] = [{'username':r['username'],'name':r['display_name'],'role':r['role'],'active':r['active']}
                for r in snapshot['tables'][m.users.name] if not r.get('deleted_at')]
        plan['token'] = fingerprint({'id':snapshot['id'], 'digest':snapshot['digest'], 'current':self.backup_revision(), 'accounts':accounts})
        return plan

    def restore(self, values, accounts=False):
        preview = self.restore_preview(values, accounts)
        expected = 'KHÔI PHỤC TÀI KHOẢN' if accounts else 'KHÔI PHỤC'
        if values.get('previewToken') != preview['token'] or values.get('confirmation') != expected:
            raise CloudError('Xem trước lại và nhập đúng nội dung xác nhận trước khi khôi phục.', 409, 'revision_conflict')
        saved = self.selected_snapshot(values['id'])
        tables = saved['tables']
        self.snapshot('Trước khôi phục '+values['id'][:8])
        if accounts:
            users = tables[m.users.name]
            if not any(r['role'] == 'Admin' and r['active'] and not r.get('deleted_at') for r in users):
                raise CloudError('Bản sao không có Admin hoạt động; chưa khôi phục.')
            for table in (m.sessions,m.assignments,m.staff,m.users):
                self.connection.execute(delete(table))
            self.connection.execute(insert(m.users),users)
            if tables[m.staff.name]:
                self.connection.execute(insert(m.staff),tables[m.staff.name])
            valid = {(r['year_id'],r['id']) for r in self.connection.execute(select(m.classes)).mappings()}
            rows = [r for r in tables[m.assignments.name] if (r['year_id'],r['class_id']) in valid]
            if rows:
                self.connection.execute(insert(m.assignments),rows)
            return {'saved':True, 'requireReauth':True}
        retained = [dict(r) for r in self.connection.execute(select(m.records).where(m.records.c.kind == 'snapshot')).mappings()]
        current_assignments = [dict(r) for r in self.connection.execute(select(m.assignments)).mappings()]
        for table in reversed(BUSINESS):
            self.connection.execute(delete(table))
        for table in (m.years,m.classes,m.students,m.marks,m.records):
            if tables[table.name]:
                self.connection.execute(insert(table),tables[table.name])
        valid = {(r['year_id'],r['id']) for r in tables[m.classes.name]}
        assignments = [r for r in current_assignments if (r['year_id'],r['class_id']) in valid]
        if assignments:
            self.connection.execute(insert(m.assignments),assignments)
        active = next(y['id'] for y in tables[m.years.name] if y['active'])
        for row in retained:
            row['year_id'] = active
            self.connection.execute(insert(m.records),row)
        # Class rights and active year may have changed. Every browser reauthenticates.
        self.connection.execute(delete(m.sessions))
        return {'saved':True, 'requireReauth':True}
