"""Deny by default; authorize and execute in the same serialized server queue."""
from datetime import datetime
from accounts import AccessError
from exceptions import normalize_vi


class Gateway:
    def __init__(self, store, accounts):
        self.store, self.accounts = store, accounts

    def require_admin(self, user):
        if user['role'] != 'Admin':
            raise AccessError('Chức năng này dành cho Admin.')

    def class_access(self, user, identifier):
        if identifier not in self.store.catalog.classes or identifier not in user['classIds']:
            raise AccessError('Bạn chưa được phân công quản lý lớp này.')

    def student_access(self, user, code):
        student = self.store.catalog.students.get(str(code or '').strip().strip('*').upper())
        if not student:
            raise AccessError('Thiếu nhi không thuộc lớp được phân công.')
        self.class_access(user, student['classId'])
        return student

    def scope_access(self, user, scope):
        info = next((c for c in self.store.catalog.classes.values() if c['name'] == scope), None)
        self.class_access(user, info['id'] if info else None)

    def session_access(self, user, identifier):
        session = self.store.session(identifier)
        self.scope_access(user, session['scope'])
        return session

    def filter_state(self, data, user):
        data = dict(data)
        data['user'] = {k:v for k,v in user.items() if k != 'csrfToken'}
        data['isManager'] = user['role'] == 'Admin'
        data['accounts'] = self.accounts.users() if data['isManager'] else []
        statuses=self.store.management.class_statuses() if getattr(self.store,'management',None) else {}
        data['classes']=[{**c,'archived':statuses.get(c['id'],False)} for c in data['classes']]
        if data['isManager']:
            return data
        ids = set(user['classIds'])
        data['classes'] = [c for c in data['classes'] if c['id'] in ids]
        names = {c['name'] for c in data['classes']}
        data['students'] = [s for s in data['students'] if s['classId'] in ids]
        codes = {s['id'] for s in data['students']}
        data['marks'] = {k:v for k,v in data['marks'].items() if k.split('|')[-1] in codes}
        data['sessions'] = [s for s in data['sessions'] if s['scope'] in names]
        data['requests'] = [r for r in data.get('requests',[]) if r['code'] in codes]
        request_ids = {r['id'] for r in data['requests']}
        data['requestEvents'] = [e for e in data.get('requestEvents',[]) if e['request_id'] in request_ids]
        for field in ('recurringMass','studentStatuses','careNotes'):
            data[field] = [r for r in data.get(field,[]) if r['code'] in codes]
        data['pendingScans'] = [p for p in data.get('pendingScans',[]) if p.get('classId') in ids]
        data['managementEvents'], data['yearPlans'] = [], []
        return data

    def bootstrap(self, user):
        if user['role'] != 'Admin':
            today = datetime.now(self.store.local_tz).date().isoformat()
            for identifier in user['classIds']:
                info = self.store.catalog.classes.get(identifier)
                if info and not (self.store.management.class_statuses().get(identifier) if getattr(self.store,'management',None) else False):
                    self.store.create_session({'date':today,'activity':'mass','scope':info['name']})
        return self.filter_state(self.store.bootstrap(), user)

    def get(self, path, query, token):
        user = self.accounts.principal(token, allow_change=path == '/api/auth/me')
        if path == '/api/auth/me':
            return {'user':{k:v for k,v in user.items() if k != 'csrfToken'},'csrfToken':user['csrfToken']}
        self.store.catalog.refresh()
        value = lambda key, default='': query.get(key,[default])[0]
        if path == '/api/bootstrap':
            return self.bootstrap(user)
        management=getattr(self.store,'management',None)
        if path=='/api/notifications': return management.notifications(user,self.bootstrap(user))
        if path.startswith('/api/admin/'):
            self.require_admin(user)
            query={key:items[0] for key,items in query.items()}
            name=path.removeprefix('/api/admin/')
            if name=='staff': return management.staff()
            if name=='celebrations': return management.staff_celebrations()
            if name=='audit': return management.audit(query)
            if name=='audit-export': return management.audit(query,True)
            if name=='years': return management.years()
            if name=='year-history': return management.year_history(query.get('id',''),query.get('code',''))
            if name=='import-template':
                from management import csv_bytes
                return csv_bytes([['classId','code','saintName','fullName','gender','birthDate','baptismDate','parents','address','subParish','phone','enrolledFrom']]),'Mau-nhap-thieu-nhi.csv','text/csv; charset=utf-8'
            raise AccessError('Không tìm thấy chức năng.',404,'not_found')
        teacher = user['role'] != 'Admin'
        if teacher:
            if path in ('/api/grades','/api/grade-export'):
                self.class_access(user,value('classId'))
            elif path == '/api/export':
                self.class_access(user,value('classId'))
                self.session_access(user,value('sessionId'))
            elif path == '/api/request-history':
                self.student_access(user,self.store.request(value('id'))['code'])
            elif path == '/api/qr':
                self.student_access(user,value('code'))
            else:
                self.require_admin(user)
        if path == '/api/accounts': return {'accounts':self.accounts.users()}
        if path == '/api/grades': return self.store.read_grades(value('classId'),int(value('semester','1')))
        if path == '/api/export': return self.store.export(query)
        if path == '/api/grade-export': return self.store.export_grades(value('classId'))
        if path == '/api/grade-pending-export': return self.store.grade_service().pending_export(value('classId'))
        if path == '/api/request-history': return self.store.request_history(value('id'))
        if path == '/api/excel-details': return self.store.parity_read(value('classId'))
        if path == '/api/system': return self.store.system_info()
        if path == '/api/snapshot-export': return self.store.snapshot_export(value('id'))
        if path == '/api/year-export': return self.store.year_export(value('id'))
        if path == '/api/qr':
            import qrcode
            from qrcode.image.svg import SvgPathImage
            code = value('code')
            if code not in self.store.catalog.students: raise ValueError('Mã thẻ không có trong danh sách.')
            return qrcode.make(code,image_factory=SvgPathImage,border=4).to_string(), '', 'image/svg+xml'
        raise AccessError('Không tìm thấy chức năng.',404,'not_found')

    def authorize_write(self, user, path, values):
        if path.startswith('/api/notifications/'): return
        if path.startswith('/api/admin/'):
            self.require_admin(user)
            return
        statuses=self.store.management.class_statuses() if getattr(self.store,'management',None) else {}
        cid=values.get('classId')
        touched={cid} if cid else set()
        code=str(values.get('code') or '').strip().strip('*').upper()
        if code in self.store.catalog.students:
            cid=self.store.catalog.students[code]['classId'];touched.add(cid)
        if values.get('id') and path in ('/api/review','/api/reschedule-makeup'):
            code=self.store.request(values['id'])['code']
            cid=self.store.catalog.students.get(code,{}).get('classId')
            if cid: touched.add(cid)
        if values.get('sessionId') and path in ('/api/scan','/api/scan-preview','/api/mark','/api/close'):
            session=self.store.session(values['sessionId'])
            scoped=next((c for c in self.store.catalog.classes.values() if c['name']==session['scope']),None)
            if scoped: cid=scoped['id']
            if cid: touched.add(cid)
        if any(statuses.get(c) for c in touched): raise AccessError('Lớp đã lưu trữ. Admin cần mở lại trước khi chỉnh sửa.')
        if user['role'] == 'Admin': return
        if path in ('/api/sessions','/api/close-makeup'):
            self.scope_access(user,values.get('scope'))
        elif path in ('/api/scan','/api/scan-preview','/api/mark','/api/close','/api/close-preview'):
            session = self.session_access(user,values.get('sessionId'))
            if path == '/api/mark': self.student_access(user,values.get('code'))
            if path == '/api/scan':
                raw = str(values.get('code') or '').strip().strip('*')
                if raw.upper() in self.store.catalog.students:
                    values['code'] = raw.upper()
                else:
                    query = normalize_vi(raw)
                    people = [s for s in self.store.catalog.students.values() if s['className']==session['scope']]
                    exact = [s for s in people if query and query in (normalize_vi(s['fullName']),normalize_vi(s['name']))]
                    matches = exact or [s for s in people if query and any(query in normalize_vi(s[k]) for k in ('fullName','name','id'))]
                    if not matches:
                        all_people = list(self.store.catalog.students.values())
                        all_exact = [s for s in all_people if query and query in (normalize_vi(s['fullName']),normalize_vi(s['name']))]
                        all_matches = all_exact or [s for s in all_people if query and any(query in normalize_vi(s[k]) for k in ('fullName','name','id'))]
                        if len(all_matches) == 1:
                            matches = all_matches
                        elif len(all_matches) > 1:
                            raise ValueError('Có nhiều em trùng tên. Vui lòng chọn em hoặc nhập mã thẻ.')
                        else:
                            raise AccessError('Không tìm thấy thiếu nhi trong lớp hoặc giáo xứ.')
                    values['code'] = matches[0]['id']
        elif path in ('/api/pending-scans-approve', '/api/pending-scans-reject'):
            rows = self.store.select_pending_scans(values)
            if values.get('classId'):
                self.class_access(user, values.get('classId'))
            if values.get('sessionId'):
                self.session_access(user, values.get('sessionId'))
            for row in rows:
                self.class_access(user, row['class_id'])
                self.student_access(user, row['code'])
        elif path == '/api/grades':
            self.class_access(user,values.get('classId'))
            for grade in values.get('grades',[]): self.student_access(user,grade.get('code'))
        elif path in ('/api/student-profile','/api/requests','/api/recurring-preview','/api/recurring-mass','/api/student-status','/api/care-note'):
            self.student_access(user,values.get('code'))
        elif path in ('/api/review','/api/reschedule-makeup'):
            self.student_access(user,self.store.request(values.get('id'))['code'])
        elif path == '/api/recurring-stop':
            with self.store.db() as db:
                record = db.execute('SELECT code FROM recurring_mass WHERE id=?',(values.get('id'),)).fetchone()
            self.student_access(user,record['code'] if record else None)
        else: self.require_admin(user)

    def post(self, path, values, token, csrf):
        user = self.accounts.principal(token,csrf)
        self.store.catalog.refresh()
        values = dict(values)
        for key in ('_bypass_time','_manager','actor','user'): values.pop(key,None)
        values.update(actor=user['displayName'],_manager=user['role']=='Admin',_user_id=user['id'])
        choice = self.authorize_write(user,path,values)
        if choice: return choice
        management=getattr(self.store,'management',None)
        if path.startswith('/api/notifications/'):
            return management.notification_write(user,values,self.bootstrap(user),path=='/api/notifications/preferences')
        if path.startswith('/api/admin/'):
            name=path.removeprefix('/api/admin/')
            previews={'class-preview':management.class_preview,'import-preview':management.import_preview,
                      'accounts-restore-preview':management.accounts_restore_preview,'year-activate-preview':management.year_activate_preview}
            writes={'class-save':management.save_class,'staff-save':management.save_staff,'import-save':management.import_commit,
                    'accounts-restore':management.restore_accounts,'year-activate':management.activate_year}
            if name in previews: return previews[name](values)
            if name not in writes: raise AccessError('Không tìm thấy chức năng.',404,'not_found')
            result=writes[name](user,values)
            if 'state' in result: result['state']=self.filter_state(result['state'],self.accounts.principal(token))
            return result
        before=management.capture(path,values) if management else None
        if path.startswith('/api/accounts/'):
            self.require_admin(user)
            method = {'/api/accounts/create':self.accounts.create,'/api/accounts/update':self.accounts.update,
                      '/api/accounts/reset-password':self.accounts.reset_password}.get(path)
            if not method: raise AccessError('Không tìm thấy chức năng.',404,'not_found')
            result = method(user,values)
            result['accounts'] = self.accounts.users()
            return result
        if path == '/api/teachers':
            self.require_admin(user)
            result = self.accounts.assign_class(self.store,user,values)
        else:
            names = {'sessions':'create_session','scan':'scan','scan-preview':'scan_preview','mark':'set_mark','close':'close_session',
                'requests':'create_request','review':'review_request','reschedule-makeup':'reschedule_makeup',
                'close-preview':'close_preview','close-makeup':'close_makeups','student-profile':'update_profile','grades':'update_grades',
                'excel-preview':'parity_preview','excel-save':'parity_commit','bulk-preview':'bulk_preview','bulk-save':'bulk_commit',
                'recurring-preview':'recurring_preview','recurring-mass':'create_recurring','recurring-stop':'stop_recurring',
                'student-status':'set_student_status','care-note':'save_care_note','snapshot':'snapshot','restore-preview':'restore_preview',
                'restore':'restore_snapshot','backup-settings':'backup_settings','transfer-preview':'transfer_preview','transfer':'transfer_student',
                'year-preview':'year_preview','year-plan':'save_year_plan','prepare-year':'prepare_year','grade-reconcile':'resolve_grade_conflict',
                'pending-scans-approve':'approve_pending_scans','pending-scans-reject':'reject_pending_scans'}
            name = names.get(path.removeprefix('/api/'))
            if not name: raise AccessError('Không tìm thấy chức năng.',404,'not_found')
            result = getattr(self.store,name)(values)
        if not path.endswith(('preview','excel-details')):
            self.accounts.audit_operation(user,path,values,before,management.capture(path,values) if management else None)
        if isinstance(result,dict) and 'state' in result:
            result['state'] = self.filter_state(result['state'],self.accounts.principal(token))
        return result
