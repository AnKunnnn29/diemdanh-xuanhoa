"""Cloud class administration and workbook planning in the same DB transaction."""
import copy
import csv
import io
import json
import re
import secrets
from collections import Counter
from datetime import date, datetime
from sqlalchemy import select, insert, update, delete, func
from . import models as m
from .security import CloudError
from .workflows import Workflow, LOCAL_TZ
from .planning_rules import PlanningRules, clean, normalize_vi
from .workbooks import Workbook
from .persistence import document, save_document, fingerprint, Download
from .validation import profile_date
from .backups import BackupRules
from .years import YearRules


def csv_file(rows, filename):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    for row in rows:
        writer.writerow(["'"+str(value) if str(value).lstrip().startswith(('=', '+', '-', '@')) else value for value in row])
    return Download(stream.getvalue().encode('utf-8-sig'), filename, 'text/csv; charset=utf-8')


class Office(BackupRules, YearRules, PlanningRules, Workflow):
    READ_ACTIONS = {'system','notifications','excel-details','snapshot-export','snapshot-part','year-export','year-file','export-manifest',
        'admin/staff','admin/audit','admin/audit-export','admin/years','admin/year-history','admin/import-template','admin/admission-options'}
    def __init__(self, service, db, user):
        self.service, self.actor_user = service, user
        self.year = service.year(db)
        self.user = service.public_user(db, user)
        self.store = self
        self.books = {}
        super().__init__(db, self.year['id'])

    def book(self, cid):
        if cid not in self.books:
            self.books[cid] = Workbook(self.connection, self.year_id, cid, self.catalog)
        return self.books[cid]

    def book_revision(self, cid):
        return self.book(cid).revision

    def state_revision(self):
        state = self.dump()
        state['tables']['issued_codes'] = sorted(r['code'] for r in state['tables']['issued_codes'])
        return fingerprint(state)

    def read_grades(self, cid, semester):
        return self.book(cid).response(semester)

    def parity_guard(self, ids):
        for cid in ids:
            if cid not in self.catalog.classes or self.catalog.classes[cid]['archived']:
                raise CloudError('Chọn lớp đang hoạt động trước khi chỉnh sửa.')

    def parity_read(self, cid):
        book = self.book(cid)
        engine = book.engine
        schedules = []
        for row in range(3, 18):
            label = clean(engine.cell('OPTION', f'G{row}'))
            if label:
                schedules.append({'row':row, 'label':label,
                    'massDays':[d for d in range(7) if engine.cell('OPTION', f'{chr(72+d)}{row}') == 1],
                    'lessonDays':[d for d in range(7) if engine.cell('OPTION', f'{chr(81+d)}{row}') == 1]})
        notes = [{'cell':ref, 'content':str(value), 'editable': isinstance(value, str) and not value.startswith('=')}
            for (sheet, ref), value in engine.cells.items() if sheet == 'Ghi Chú' and value is not None
            and int(''.join(c for c in ref if c.isdigit())) > 1]
        last = max((int(''.join(c for c in n['cell'] if c.isdigit())) for n in notes), default=2)
        used = {r[0] for r in self.memory.execute('SELECT code FROM issued_codes')}
        numbers = [int(s[2:]) for s in used if re.fullmatch(r'XH\d{5}', s)]
        dates = sorted(d for c in self.catalog.classes.values() for d in c['calendar']['mass'])
        return {'classId':cid, 'className':book.info['name'], 'revision':book.revision,
            'configuration':{'semesters':[engine.cell('OPTION', f'B{r}') for r in range(4,16)],
                'allowMass':engine.cell('OPTION','E3'), 'allowLesson':engine.cell('OPTION','E4'),
                'catechismThreshold':engine.cell('Tổng kết','D3'), 'attendanceThreshold':engine.cell('Tổng kết','D4'),
                'schedules':schedules}, 'notes':notes, 'nextNoteCell':f'A{max(3,last+1)}',
            'supplements':[dict(r) for r in self.memory.execute('SELECT * FROM supplemental_mass ORDER BY actual_day DESC')
                if r['code'] in book.people],
            'suggestedCode':'XH'+str(max(numbers, default=0)+1).zfill(5) if len(numbers) == len(used) else '',
            'yearStart':(dates[0][:4]+'-09-01') if dates else self.year['label'][:4]+'-09-01',
            'history':[dict(r) for r in self.memory.execute('SELECT * FROM management_events ORDER BY id DESC LIMIT 100')]}

    def parity_preview(self, values):
        plan = self.parity_plan(values)
        if plan['operation'] == 'configuration':
            for cid in plan['classIds']:
                options = copy.deepcopy(self.book(cid).options)
                options.setdefault('cells', {}).setdefault('OPTION', {}).update(plan['payload']['optionCells'])
                options['cells'].setdefault('Tổng kết', {}).update(plan['payload']['thresholdCells'])
                try:
                    trial = Workbook(self.connection, self.year_id, cid, self.catalog, options_override=options)
                    before, after = self.catalog.classes[cid]['calendar'], trial.calendar
                    removed = {a: set(before[a])-set(after[a]) for a in before}
                    codes = set(trial.people)
                    for r in self.memory.execute('SELECT * FROM locks WHERE class_id=?', (cid,)):
                        if r['day'] in removed[r['activity']]:
                            plan['issues'].append('Lịch mới sẽ mất buổi đã chốt: '+r['day'])
                    for r in self.requests():
                        if r['code'] in codes and r['status'] in ('pending','approved','completed') and r['day'] in removed[r['activity']]:
                            plan['issues'].append('Lịch mới sẽ mất ngày của đơn: '+r['day'])
                    for r in self.memory.execute("SELECT * FROM supplemental_mass WHERE status='active'"):
                        if r['code'] in codes and r['actual_day'] in after['mass']:
                            plan['issues'].append('Lịch mới trùng ngày đã cộng lễ bổ sung: '+r['actual_day'])
                    plan.setdefault('calendarChanges', []).append({'className':trial.info['name'],
                        'removed':{a:sorted(v) for a,v in removed.items()},
                        'added':{a:sorted(set(after[a])-set(before[a])) for a in before}})
                except CloudError as error:
                    plan['issues'].append(str(error))
        return plan

    def student_add(self, cid, payload):
        code = payload['code']
        if code in self.used_student_codes():
            raise CloudError('Mã đã được cấp hoặc có lịch sử. Không tái cấp mã cũ.')
        row = {k:v for k,v in payload.items() if k != 'code'}
        row['name'] = clean(row.get('saintName','')+' '+row['fullName'])
        self.connection.execute(insert(m.students).values(year_id=self.year_id, code=code, class_id=cid, payload=row, revision=1))
        self.memory.execute('INSERT INTO issued_codes VALUES (?,?)', (code, self.stamp()))
        self.catalog.students[code] = {**row, 'id':code, 'classId':cid,
            'className':self.catalog.classes[cid]['name'], 'revision':1}
        self.catalog.classes[cid]['count'] += 1
        self.books.pop(cid, None)

    def used_student_codes(self):
        used=set(self.connection.execute(select(m.students.c.code)).scalars())
        used.update(r[0] for r in self.memory.execute('SELECT code FROM issued_codes'))
        for row in self.connection.execute(select(m.records.c.kind,m.records.c.id,m.records.c.payload).where(
            m.records.c.kind.in_(('workflow-state','source-table')))).mappings():
            entries=row['payload'].get('tables',{}).get('issued_codes',[]) if row['kind']=='workflow-state' else row['payload'].get('rows',[]) if row['id']=='issued_codes' else []
            used.update(r['code'] for r in entries if r.get('code'))
        return used

    def admission_options(self):
        used=self.used_student_codes()
        numeric=[int(code[2:]) for code in used if re.fullmatch(r'XH\d+',code)]
        start=self.year['label'][:4]+'-09'
        end=str(int(self.year['label'][:4])+1)+'-08'
        month=min(end,max(start,datetime.now(LOCAL_TZ).strftime('%Y-%m')))
        return {'suggestedCode':'XH'+str(max(numeric,default=0)+1).zfill(5),'startMonth':start,'endMonth':end,'enrolledMonth':month}

    def create_student(self, values):
        values={**values,'operation':'student-add','reason':values.get('reason') or 'Tiếp nhận thiếu nhi vào giáo xứ và lớp giáo lý'}
        plan=self.parity_plan(values)
        if plan['issues']:
            raise CloudError(' '.join(plan['issues']))
        payload=plan['payload']
        for key in ('birthDate','baptismDate'):
            parsed=profile_date(payload[key])
            payload[key]=parsed.date().isoformat() if parsed else ''
            if parsed and parsed.date()>datetime.now(LOCAL_TZ).date():
                raise CloudError('Ngày sinh / rửa tội không được ở tương lai.')
        self.snapshot('Trước tiếp nhận thiếu nhi '+payload['code'])
        self.student_add(plan['classId'],payload)
        self.management_event(self.memory,'student',payload['code'],'created',values['actor'],values['reason'])
        self.flush()
        return {'saved':True,'code':payload['code'],'classId':plan['classId']}

    def create_class(self, values):
        values={**values,'operation':'create','reason':values.get('reason') or 'Tạo lớp giáo lý mới'}
        plan=self.class_preview(values)
        return self.save_class({**values,'previewToken':plan['token']})

    def save_class_payload(self, cid, values):
        group = self.catalog.classes[cid]
        group.update(values)
        self.connection.execute(update(m.classes).where(m.classes.c.year_id == self.year_id, m.classes.c.id == cid)
            .values(payload={k:v for k,v in group.items() if k not in ('id','name','revision','archived')}, revision=m.classes.c.revision+1))
        self.books.pop(cid, None)

    def parity_commit(self, values):
        plan = self.parity_preview(values)
        if plan['issues'] or values.get('previewToken') != plan['token']:
            raise CloudError('Dữ liệu đã đổi hoặc còn xung đột. Xem trước lại trước khi lưu.', 409, 'revision_conflict')
        payload, op, cid = plan['payload'], plan['operation'], plan['classId']
        identifier = secrets.token_hex(12)
        if op == 'student-add':
            self.student_add(cid, payload)
        elif op == 'enrollment':
            person = self.catalog.students[payload['code']]
            data = {k:v for k,v in person.items() if k not in ('id','classId','revision','className')}
            data['enrolledFrom'] = payload['enrolledFrom']
            self.connection.execute(update(m.students).where(m.students.c.year_id == self.year_id, m.students.c.code == person['id'])
                .values(payload=data, revision=m.students.c.revision+1))
            self.catalog.students[person['id']].update(enrolledFrom=payload['enrolledFrom'])
        elif op == 'supplemental':
            options = copy.deepcopy(self.book(cid).options)
            options.setdefault('supplements', {})[payload['code']] = payload['after']
            save_document(self.connection, self.year_id, 'workbook-options', cid, options)
            if payload['action'] == 'add':
                self.memory.execute('INSERT INTO supplemental_mass VALUES (?,?,?,?,?,?,?,?)',
                    (identifier,payload['code'],payload['actualDate'],plan['actor'],plan['reason'],'active',self.stamp(),self.stamp()))
                self.memory.execute('INSERT INTO scans VALUES (?,?,?,?,?,?,?,?)',
                    (identifier,payload['code'],'mass',payload['actualDate'],payload['actualDate'],'supplemental:'+identifier,'supplemental',self.stamp()))
            else:
                self.memory.execute("UPDATE supplemental_mass SET status='cancelled',updated_at=? WHERE id=?", (self.stamp(),payload['id']))
                self.memory.execute('DELETE FROM scans WHERE request_id=?', ('supplemental:'+payload['id'],))
        elif op == 'configuration':
            for target in plan['classIds']:
                options = copy.deepcopy(self.book(target).options)
                options.setdefault('cells', {}).setdefault('OPTION', {}).update(payload['optionCells'])
                options['cells'].setdefault('Tổng kết', {}).update(payload['thresholdCells'])
                save_document(self.connection, self.year_id, 'workbook-options', target, options)
                trial = Workbook(self.connection, self.year_id, target, self.catalog)
                semesters = {name:sorted({d[:7] for d in trial.calendar['mass'] if
                    payload['optionCells']['B'+str(([9,10,11,12,1,2,3,4,5,6,7,8].index(int(d[5:7])))+4)] == label})
                    for name,label in (('hk1','HKI'),('hk2','HKII'))}
                self.save_class_payload(target, {'calendar':trial.calendar, 'semesterMonths':semesters})
        elif op == 'note':
            notes = dict(self.book(cid).notes)
            notes[payload['cell']] = payload['content']
            save_document(self.connection, self.year_id, 'workbook-notes', cid, notes)
        elif op == 'scratch':
            options = copy.deepcopy(self.book(cid).options)
            options['scratchMode'] = payload['mode']
            save_document(self.connection, self.year_id, 'workbook-options', cid, options)
        self.books.clear()
        self.management_event(self.memory, op, payload.get('code',cid), 'updated', plan['actor'], plan['reason'])
        self.flush()
        return {'saved':True, 'id':identifier, 'details':self.parity_read(cid)}

    def class_preview(self, values):
        self.reason(values)
        op, cid = values.get('operation'), values.get('classId')
        info = self.catalog.classes.get(cid)
        if op not in ('create','rename','archive','reopen') or not info:
            raise CloudError('Chọn thao tác lớp và bản mẫu hợp lệ.')
        name = clean(values.get('name') or info['name'])
        if op in ('create','rename'):
            if not 3 <= len(name) <= 80 or ' ' not in name or re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
                raise CloudError('Tên lớp cần gồm khối và số/tên lớp hợp lệ.')
            if any(normalize_vi(c['name']) == normalize_vi(name) and (op == 'create' or c['id'] != cid) for c in self.catalog.classes.values()):
                raise CloudError('Tên lớp đã tồn tại.')
        plan = {'operation':op, 'classId':cid, 'name':name, 'count':info['count'], 'reason':values['reason']}
        plan['token'] = fingerprint({'plan':plan, 'classes':self.catalog.classes, 'state':self.state_revision()})
        return plan

    def save_class(self, values):
        plan = self.class_preview(values)
        if values.get('previewToken') != plan['token']:
            raise CloudError('Danh sách lớp đã thay đổi. Xem trước lại.', 409, 'revision_conflict')
        self.snapshot('Trước thay đổi lớp: '+plan['name'])
        cid, op = plan['classId'], plan['operation']
        info = self.catalog.classes[cid]
        if op == 'create':
            identifier = secrets.token_hex(8)
            payload = {k:v for k,v in info.items() if k not in ('id','name','archived','revision')}
            payload.update(teachers={}, fresh=True, count=0, filename=plan['name']+'.xlsm')
            payload.pop('staffPlan',None)
            self.connection.execute(insert(m.classes).values(id=identifier, year_id=self.year_id, name=plan['name'], archived=False, payload=payload, revision=1))
            source = document(self.connection, self.year_id, 'source-workbook', cid)
            save_document(self.connection, self.year_id, 'source-workbook', identifier, source)
            self.catalog.classes[identifier] = {**payload, 'id':identifier, 'name':plan['name'], 'archived':False, 'revision':1}
            # Compile before committing so unsupported class schedules roll back.
            compiled = Workbook(self.connection, self.year_id, identifier, self.catalog)
            if not compiled.calendar['mass']:
                raise CloudError('Tên khối chưa có lịch trong bản mẫu. Chọn tên khối đã được cấu hình.')
            self.save_class_payload(identifier, {'calendar':compiled.calendar})
        elif op == 'rename':
            # Renaming identifies the same teaching group. A different group can
            # change attendance formulas; use reviewed configuration/transfer.
            if plan['name'].rsplit(' ',1)[0] != info['name'].rsplit(' ',1)[0]:
                raise CloudError('Đổi tên trong cùng khối; dùng chuyển lớp để đổi khối giáo lý.')
            self.connection.execute(update(m.classes).where(m.classes.c.year_id == self.year_id, m.classes.c.id == cid)
                .values(name=plan['name'], revision=m.classes.c.revision+1))
            self.catalog.classes[cid] = {**info,'name':plan['name']}
            compiled = Workbook(self.connection,self.year_id,cid,self.catalog)
            self.save_class_payload(cid,{'calendar':compiled.calendar})
            self.memory.execute('UPDATE sessions SET scope=? WHERE scope=?', (plan['name'],info['name']))
        else:
            self.connection.execute(update(m.classes).where(m.classes.c.year_id == self.year_id, m.classes.c.id == cid)
                .values(archived=op == 'archive', revision=m.classes.c.revision+1))
        self.flush()
        return {'saved':True,'classId':identifier if op=='create' else cid}

    def import_preview(self, values):
        self.reason(values)
        rows, normalized, issues, warnings = self.import_rows(values), [], [], []
        seen, profiles, counts = set(), set(), Counter()
        for number, row in enumerate(rows, 2):
            cid = row.get('classId') or values.get('classId')
            cid = next((c['id'] for c in self.catalog.classes.values() if c['name'] == cid), cid)
            try:
                if clean(row.get('code')).upper() in seen:
                    raise ValueError('Mã trùng trong file nhập.')
                plan = self.parity_plan({**row, 'classId':cid, 'operation':'student-add', 'actor':values['actor'],
                    'reason':values['reason'], '_manager':True})
                payload = plan['payload']
                seen.add(payload['code'])
                counts[cid] += 1
                for key in ('birthDate','baptismDate'):
                    parsed = profile_date(payload[key])
                    payload[key] = parsed.date().isoformat() if parsed else ''
                key = (normalize_vi(payload['fullName']), payload['birthDate'])
                if key in profiles or any((normalize_vi(s['fullName']),s.get('birthDate','')) == key for s in self.catalog.students.values()):
                    warnings.append(f'Dòng {number}: trùng họ tên/ngày sinh, cần kiểm tra.')
                profiles.add(key)
                normalized.append({'classId':cid, **payload})
            except (ValueError, CloudError, KeyError, TypeError) as error:
                issues.append(f'Dòng {number}: {error}')
        for cid, count in counts.items():
            if self.catalog.classes[cid]['count']+count > 40:
                issues.append(self.catalog.classes[cid]['name']+': vượt sức chứa 40 em.')
        plan = {'rows':normalized, 'issues':issues, 'warnings':warnings, 'counts':dict(counts)}
        plan['token'] = fingerprint({'plan':plan, 'revisions':{cid:self.book_revision(cid) for cid in counts}, 'state':self.state_revision(), 'reason':values['reason']})
        return plan

    def import_commit(self, values):
        plan = self.import_preview(values)
        if plan['issues'] or plan['warnings'] and values.get('acceptWarnings') is not True:
            raise CloudError('Sửa lỗi và xác nhận đã kiểm tra các hồ sơ có thể trùng trước khi nhập.')
        if values.get('previewToken') != plan['token']:
            raise CloudError('Dữ liệu đã thay đổi. Xem trước danh sách lại.', 409, 'revision_conflict')
        self.snapshot('Trước nhập hồ sơ hàng loạt')
        for row in plan['rows']:
            self.student_add(row['classId'], {k:v for k,v in row.items() if k != 'classId'})
        self.flush()
        return {'saved':True, 'count':len(plan['rows'])}

    def staff(self):
        history = []
        for r in self.connection.execute(select(m.records).where(
            ((m.records.c.kind == 'source-accounts') & (m.records.c.id == 'assignment_history')) |
            (m.records.c.kind == 'staff-assignment-history'))).mappings():
            history.extend(r['payload'].get('rows',[]))
        return {'profiles':[{'id':r['id'], 'user_id':r['user_id'], **r['payload']}
            for r in self.connection.execute(select(m.staff)).mappings()],
            'history':sorted(history,key=lambda r:r.get('stamp',''),reverse=True),
            'accounts':self.service.account_list(self.connection),
            'historyAccounts':[{'id':r['id'],'displayName':r['display_name']} for r in
                self.connection.execute(select(m.users.c.id,m.users.c.display_name)).mappings()]}

    def save_staff(self, values):
        name = clean(values.get('full_name'))
        status = values.get('status', 'active')
        if not 2 <= len(name) <= 100 or status not in ('active','paused','retired'):
            raise CloudError('Nhập họ tên và chọn trạng thái phục vụ hợp lệ.')
        fields = ('phone','email','birth_date','address','service_from','service_to','note')
        data = {key:str(values.get(key) or '').strip() for key in fields}
        if any(len(value) > 500 or '\x00' in value for value in data.values()):
            raise CloudError('Thông tin hồ sơ quá dài hoặc chứa ký tự không hợp lệ.')
        for key in ('birth_date','service_from','service_to'):
            if data[key]:
                date.fromisoformat(data[key])
        current = datetime.now(LOCAL_TZ).date()
        raw_year = str(values.get('birth_year') or '').strip()
        if raw_year and (not re.fullmatch(r'\d{4}', raw_year) or not 1900 <= int(raw_year) <= current.year):
            raise CloudError('Năm sinh phải từ 1900 đến năm hiện tại.')
        birth_year = int(raw_year) if raw_year else None
        if data['birth_date']:
            birthday = date.fromisoformat(data['birth_date'])
            if birthday > current or birth_year and birth_year != birthday.year:
                raise CloudError('Ngày sinh ở tương lai hoặc không khớp năm sinh.')
            birth_year = birthday.year
        if data['service_from'] and data['service_to'] and data['service_from'] > data['service_to']:
            raise CloudError('Ngày kết thúc phải sau ngày bắt đầu phục vụ.')
        if data['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', data['email']):
            raise CloudError('Email không hợp lệ.')
        linked, identifier = values.get('user_id') or None, values.get('id') or secrets.token_hex(16)
        existing = self.connection.execute(select(m.staff).where(m.staff.c.id == identifier)).mappings().first()
        if values.get('id') and not existing:
            raise CloudError('Hồ sơ GLV không tồn tại.')
        if linked and not self.connection.execute(select(m.users.c.id).where(m.users.c.id == linked, m.users.c.deleted_at.is_(None))).first():
            raise CloudError('Tài khoản liên kết không tồn tại.')
        if linked and self.connection.execute(select(m.staff.c.id).where(m.staff.c.user_id == linked, m.staff.c.id != identifier)).first():
            raise CloudError('Tài khoản đã liên kết hồ sơ GLV khác.')
        if 'birth_year' not in values and not data['birth_date'] and existing:
            birth_year = existing['payload'].get('birth_year')
        data.update(full_name=name, status=status, birth_year=birth_year, updated_at=self.stamp())
        if existing:
            self.connection.execute(update(m.staff).where(m.staff.c.id == identifier).values(user_id=linked, payload=data))
        else:
            self.connection.execute(insert(m.staff).values(id=identifier, user_id=linked, payload=data))
        return {'saved':True, 'staff':self.staff()}

    def audit_read(self, query, export=False):
        rows = [dict(r) for r in self.connection.execute(select(m.audit, m.users.c.display_name, m.users.c.username)
            .outerjoin(m.users, m.users.c.id == m.audit.c.user_id).order_by(m.audit.c.stamp.desc(),m.audit.c.id.desc())).mappings()]
        for name in ('from','to'):
            if query.get(name):
                date.fromisoformat(query[name])
        def matches(r):
            return (not query.get('from') or r['stamp'][:10] >= query['from']) and \
                (not query.get('to') or r['stamp'][:10] <= query['to']) and \
                (not query.get('actor') or r['user_id'] == query['actor']) and \
                (not query.get('action') or query['action'].casefold() in r['action'].casefold()) and \
                (not query.get('search') or normalize_vi(query['search']) in normalize_vi(json.dumps(r,ensure_ascii=False)))
        filtered = [r for r in rows if matches(r)]
        offset = max(0, int(query.get('offset') or 0))
        if export:
            if len(filtered) > 10000:
                raise CloudError('Lọc nhật ký xuống dưới 10.000 dòng trước khi xuất.')
            return csv_file([['Thời gian UTC','Người thực hiện','Tên đăng nhập','Thao tác','Chi tiết']]+
                [[r['stamp'],r['display_name'] or 'Hệ thống',r['username'] or '',r['action'],json.dumps(r['details'],ensure_ascii=False)] for r in filtered], 'Nhat-ky-he-thong.csv')
        return {'items':filtered[offset:offset+100], 'total':len(filtered), 'offset':offset, 'limit':100,
            'actors':self.service.account_list(self.connection)}

    def notifications(self, values=None, preferences=False):
        state = self.service.bootstrap(self.connection, self.actor_user)
        today = datetime.now(LOCAL_TZ).date().isoformat()
        items = []
        def add(key, kind, title, detail, target):
            items.append({'id':self.year_id+':'+key, 'kind':kind, 'title':title, 'detail':detail, 'target':target})
        for r in state['requests']:
            if r['status'] == 'pending':
                add('request:'+r['id'],'requests','Đơn chờ duyệt',r['code']+' · '+r['day'],'requests')
        inactive = {c['name'] for c in state['classes'] if c['archived']}
        for s in state['sessions']:
            if s['date'] <= today and not s['closed'] and s['scope'] not in inactive:
                add('session:'+s['id'],'sessions','Buổi chưa chốt',s['date']+' · '+s['scope'],'attendance')
        for n in state['careNotes']:
            if n['status'] != 'done' and n['due_day'] and n['due_day'] <= today:
                add('care:'+n['id']+':'+n['updated_at'],'care','Đến hạn theo dõi',n['code']+' · '+n['content'][:160],'care')
        for c in state['classes']:
            if c['archived']:
                continue
            for sem,key in ((1,'hk1'),(2,'hk2')):
                months = c.get('semesterMonths', {}).get(key, [])
                if months and today[:7] > max(months):
                    missing = sum(s.get('thiHk') in (None,'') for s in self.read_grades(c['id'],sem)['students'])
                    if missing:
                        add(f'grades:{c["id"]}:{sem}','grades','Thiếu điểm thi học kỳ',c['name']+f' · HK{sem}: {missing} em','grades')
            if self.user['role'] == 'Admin' and not any(c.get('teachers', {}).values()):
                add('teacher:'+c['id'],'system','Lớp chưa phân công GLV',c['name'],'teachers')
        key = self.user['id']
        model = document(self.connection, self.year_id, 'notifications', key,
            {'reads':[], 'preferences':{k:True for k in ('requests','sessions','care','grades','system')}})
        if values is not None:
            if preferences:
                pref = values.get('preferences')
                if not isinstance(pref,dict) or set(pref) != set(model['preferences']) or any(type(v) is not bool for v in pref.values()):
                    raise CloudError('Tùy chọn nhắc việc không hợp lệ.')
                model['preferences'] = pref
            else:
                selected = values.get('ids')
                allowed = {i['id'] for i in items if model['preferences'].get(i['kind'], True)}
                if not isinstance(selected,list) or len(selected) > 2000 or any(i not in allowed for i in selected):
                    raise CloudError('Thông báo ngoài phạm vi tài khoản.', 403, 'forbidden')
                model['reads'] = sorted(set(model['reads']) | set(selected))[-5000:]
            save_document(self.connection, self.year_id, 'notifications', key, model)
        result = [{**item, 'read':item['id'] in model['reads']} for item in items if model['preferences'].get(item['kind'],True)]
        return {'items':result, 'unread':sum(not i['read'] for i in result), 'preferences':model['preferences']}

    def read(self, action, query):
        if action == 'notifications':
            return self.notifications()
        self.service.admin(self.actor_user)
        if action == 'system':
            return self.system_info()
        if action == 'admin/staff':
            return self.staff()
        if action == 'admin/admission-options':
            return self.admission_options()
        if action in ('admin/audit','admin/audit-export'):
            return self.audit_read(query, action.endswith('export'))
        if action == 'admin/years':
            return self.years()
        if action == 'admin/year-history':
            return self.year_history(query)
        if action == 'admin/import-template':
            return csv_file([['classId','code','saintName','fullName','gender','birthDate','baptismDate','parents','address','subParish','phone','enrolledFrom']], 'Mau-nhap-thieu-nhi.csv')
        if action == 'excel-details':
            return self.parity_read(query.get('classId'))
        if action == 'snapshot-export':
            return self.snapshot_manifest(query.get('id'))
        if action == 'snapshot-part':
            return self.snapshot_part(query)
        if action == 'year-file':
            if not self.connection.execute(select(m.years.c.id).where(m.years.c.id == query.get('id'))).first():
                raise CloudError('Không tìm thấy năm học.',404,'not_found')
            return Workbook(self.connection,query['id'],query.get('classId')).export()
        if action in ('year-export','export-manifest'):
            target = query.get('id') if action == 'year-export' else self.year_id
            classes = [dict(r) for r in self.connection.execute(select(m.classes).where(m.classes.c.year_id == target)).mappings()]
            if action == 'export-manifest':
                session = self.session(query.get('sessionId'))
                classes = [c for c in classes if session['scope'] == 'all' or session['scope'] == c['name']]
            if not classes:
                raise CloudError('Không có lớp trong phạm vi tải đã chọn.')
            return {'format':'xuanhoa-download-v1', 'filename':f'XuanHoa-SoLop-{target}.zip',
                'items':[{'filename':c['name']+'.xlsm',
                    'url':f'/api/year-file?id={target}&classId={c["id"]}' if action == 'year-export'
                        else '/api/grade-export?classId='+c['id']} for c in classes]}
        raise CloudError('Không tìm thấy chức năng.',404,'not_found')

    def bulk_commit(self, values):
        plan = self.bulk_preview(values)
        if plan['issues'] or values.get('previewToken') != plan['token']:
            raise CloudError('Danh sách còn lỗi hoặc đã thay đổi. Xem trước lại.',409,'revision_conflict')
        if plan['kind'] == 'grades':
            return self.book(plan['classId']).save(plan['semester'],plan['entries'],plan['revision'])
        session = self.create_session({'date':plan['date'],'activity':plan['activity'], 'scope':self.catalog.classes[plan['classId']]['name']})
        completed = []
        for item in plan['entries']:
            self.workflow_scan({**values,'code':item['code'],'sessionId':session['id'],'manual':True})
            completed.append(item['code'])
        self.flush()
        return {'saved':True,'completed':completed}

    def dispatch(self, action, incoming):
        if action in ('notifications/read','notifications/preferences'):
            return self.notifications(incoming, action.endswith('preferences'))
        self.service.admin(self.actor_user)
        values = {k:v for k,v in incoming.items() if k not in ('actor','_manager','_bypass_time','user')}
        values.update(actor=self.user['displayName'],_manager=True)
        methods = {'admin/class-preview':self.class_preview, 'admin/class-save':self.save_class,
            'admin/class-create':self.create_class,'admin/student-create':self.create_student,
            'admin/import-preview':self.import_preview, 'admin/import-save':self.import_commit,
            'admin/staff-save':self.save_staff, 'admin/year-activate-preview':self.year_activate_preview,
            'admin/year-activate':self.activate_year, 'excel-preview':self.parity_preview, 'excel-save':self.parity_commit,
            'bulk-preview':self.bulk_preview, 'bulk-save':self.bulk_commit, 'transfer-preview':self.transfer_preview,
            'transfer':self.transfer, 'year-preview':self.year_preview, 'year-plan':self.save_year_plan,
            'prepare-year':self.prepare_year, 'backup-settings':self.backup_settings}
        if action == 'snapshot':
            self.reason(values)
            result = {'saved':True,'snapshot':self.snapshot(values.get('label') or values['reason'])}
            result['system'] = self.system_info()
        elif action in ('restore-preview','admin/accounts-restore-preview'):
            result = self.restore_preview(values,action.startswith('admin/'))
        elif action in ('restore','admin/accounts-restore'):
            result = self.restore(values,action.startswith('admin/'))
        elif action in methods:
            result = methods[action](values)
        else:
            raise CloudError('Chức năng này đang được chuyển sang cloud; chưa ghi dữ liệu.',503,'cloud_workflow_pending')
        if not result.get('requireReauth'):
            self.flush()
        return result
