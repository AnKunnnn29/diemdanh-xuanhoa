"""Validated preview rules shared in behavior with the local parish application.

Only pure validation and planning methods are included; no native engine, disk
transaction, local database or background timer is imported.
"""
import base64
import csv
import hashlib
import io
import json
import re
import secrets
import unicodedata
from calendar import monthrange
from datetime import date, datetime, timedelta
from .workflow_rules import day, normalize_vi
from .validation import PROFILE_FIELDS, profile_date

def clean(value):
    return ' '.join(unicodedata.normalize('NFC', str(value or '')).split())

def token(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

class PlanningRules:
    def parity_manager(self,values):
        if not values.get('_manager'):raise ValueError('Thực hiện thao tác quản lý sổ bằng tài khoản Admin.')
        return self.actor(values)

    def parity_dates(self,value):
        d=day(value)
        dates=sorted(x for c in self.catalog.classes.values() for x in c['calendar']['mass'])
        start=date(int(dates[0][:4]),9,1).isoformat();end=date(int(dates[0][:4])+1,8,31).isoformat()
        if not start<=d<=end:raise ValueError('Ngày phải trong năm học đang sử dụng.')
        return d

    def parity_plan(self,values):
        actor,reason=self.parity_manager(values)
        operation=values.get('operation');class_id=values.get('classId')
        self.parity_guard([class_id])
        info=self.catalog.classes[class_id]
        if values.get('expectedRevision') and values['expectedRevision']!=self.book_revision(class_id):
            raise ValueError('Sổ lớp đã thay đổi. Làm mới thông tin trước khi nhập lại.')
        payload={};description=[];issues=[];identifiers=[class_id]
        if operation=='student-add':
            code=clean(values.get('code')).upper()
            if not re.fullmatch(r'XH\d+',code):raise ValueError('Mã phải có dạng XH và chữ số, dùng mã đã được xác nhận cấp.')
            with self.db() as db:
                if code in self.catalog.students or db.execute('SELECT 1 FROM issued_codes WHERE code=?',(code,)).fetchone():
                    raise ValueError('Mã đã được cấp hoặc có lịch sử. Không tái cấp mã cũ.')
            if info['count']>=40:raise ValueError('Lớp đã đủ 40 em.')
            payload={k:clean(values.get(k)) for k in PROFILE_FIELDS|{'saintName','fullName'}}
            if not 2<=len(payload['fullName'])<=150 or len(payload['saintName'])>100:raise ValueError('Nhập họ tên từ 2 đến 150 ký tự, tên thánh tối đa 100 ký tự.')
            if any(len(v)>500 for v in payload.values()):raise ValueError('Thông tin hồ sơ quá dài.')
            if payload['gender'] not in ('','Nam','Nữ'):raise ValueError('Giới tính phải là Nam hoặc Nữ.')
            for k in ('birthDate','baptismDate'):profile_date(payload[k])
            enrollment=self.parity_dates(values.get('enrolledFrom'))
            if enrollment[-2:]!='01':raise ValueError('Mẫu Excel quản lý nhập học theo tháng. Chọn ngày đầu tháng nhập học.')
            payload.update(code=code,enrolledFrom=enrollment)
            description=[f'Thêm {code} · {payload["fullName"]} vào {info["name"]}.',f'Nhập học từ tháng {enrollment[:7]}; giữ mã đã xác nhận cấp.',
                         'Cập nhật Danh Sách, Lý Lịch và kiểm tra liên kết 12 tháng, HK1, HK2, Tổng kết.']
        elif operation=='enrollment':
            code=clean(values.get('code')).upper();student=self.catalog.students.get(code)
            if not student or student['classId']!=class_id:raise ValueError('Thiếu nhi không thuộc lớp.')
            enrollment=self.parity_dates(values.get('enrolledFrom'))
            if enrollment[-2:]!='01':raise ValueError('Chọn ngày đầu tháng nhập học.')
            before=student['enrolledFrom']
            if enrollment==before:raise ValueError('Tháng nhập học chưa thay đổi.')
            marked=[k for k in self.catalog.marks if k.endswith('|'+code) and k.split('|')[0]<enrollment]
            if marked:issues.append('Có chuyên cần trước tháng nhập học mới; giữ nguyên lịch sử, chưa đổi tháng.')
            with self.db() as db:
                if db.execute("SELECT 1 FROM requests WHERE code=? AND status IN ('pending','approved','completed') AND (day<? OR COALESCE(exception_day,target_day)<?)",(code,enrollment,enrollment)).fetchone():
                    issues.append('Có đơn trước tháng nhập học mới. Xử lý đơn trước khi đổi.')
                if db.execute("SELECT 1 FROM supplemental_mass WHERE code=? AND status='active' AND actual_day<?",(code,enrollment)).fetchone():issues.append('Có lễ bổ sung trước tháng nhập học mới.')
            # Changing HK eligibility with entered points needs explicit separate reconciliation.
            old_sem='hk1' if not before or before[:7] in info['semesterMonths']['hk1'] else 'hk2'
            new_sem='hk1' if enrollment[:7] in info['semesterMonths']['hk1'] else 'hk2'
            if old_sem!=new_sem:
                for sem in (1,2):
                    r=next((r for r in self.read_grades(class_id,sem)['students'] if r['code']==code),None)
                    if r and any(v not in (None,'') for v in r['khaoBai']+[r['kt15'],r['kt1Tiet'],r['thiKinh'],r['thiHk']]):issues.append('Đổi học kỳ nhập học khi đã có điểm cần đối chiếu riêng; chưa áp dụng.');break
            payload={'code':code,'enrolledFrom':enrollment}
            description=[f'{code}: {before or "Cả năm"} → {enrollment[:7]}.','Chuyên cần và công thức học kỳ sẽ tính từ tháng nhập học mới.']
        elif operation=='supplemental':
            code=clean(values.get('code')).upper();student=self.catalog.students.get(code)
            if not student or student['classId']!=class_id:raise ValueError('Thiếu nhi không thuộc lớp.')
            existing_id=values.get('id');action=values.get('action','add')
            with self.db() as db:
                existing=db.execute('SELECT * FROM supplemental_mass WHERE id=?',(existing_id,)).fetchone() if existing_id else None
            if action not in ('add','cancel'):raise ValueError('Chỉ thêm hoặc hủy lượt; hủy rồi lập lại để sửa ngày.')
            if action=='cancel':
                if not existing or existing['code']!=code or existing['status']!='active':raise ValueError('Lượt lễ bổ sung không còn hiệu lực.')
                actual=existing['actual_day']
            else:
                actual=self.parity_dates(values.get('actualDate'))
                if actual>datetime.now(self.local_tz).date().isoformat():raise ValueError('Không ghi nhận lễ chưa diễn ra.')
                if not self.student_active(code,actual) or student['enrolledFrom'] and actual<student['enrolledFrom']:raise ValueError('Em chưa nhập học hoặc đang nghỉ vào ngày này.')
                if actual in info['calendar']['mass']:raise ValueError('Ngày này có lễ theo lịch lớp. Dùng điểm danh/đổi lễ, không cộng bổ sung.')
                with self.db() as db:
                    if db.execute("SELECT 1 FROM supplemental_mass WHERE code=? AND actual_day=? AND status='active'",(code,actual)).fetchone():raise ValueError('Đã ghi lễ bổ sung ngày này.')
                    if db.execute("SELECT 1 FROM scans WHERE code=? AND activity='mass' AND actual_day=?",(code,actual)).fetchone():raise ValueError('Lượt đi lễ đã dùng cho điểm danh/đổi lễ.')
                    if db.execute("SELECT 1 FROM requests WHERE code=? AND activity='mass' AND status IN ('pending','approved','completed') AND (day=? OR COALESCE(exception_day,target_day)=? OR actual_day=?)",(code,actual,actual,actual)).fetchone():raise ValueError('Ngày đi lễ đang có đơn hoặc đã dùng cho đổi lễ.')
            total=self.read_grades(class_id,3)
            current=next(r for r in total['students'] if r['code']==code)['supplementalMass'] or 0
            if isinstance(current,bool) or not isinstance(current,(int,float)) or current<0 or int(current)!=current:raise ValueError('Số lễ bù cũ không hợp lệ. Cần đối chiếu sổ.')
            after=current+(1 if action=='add' else -1)
            if after<0:raise ValueError('Số lễ bù trong sổ đã thay đổi; không thể trừ thêm.')
            payload={'code':code,'actualDate':actual,'action':action,'id':existing_id,'before':current,'after':after}
            tracked=sum(r['status']=='active' for r in self.parity_read(class_id)['supplements'] if r['code']==code)
            if current<tracked:raise ValueError('Số lễ bổ sung trong sổ nhỏ hơn các lượt đang có hiệu lực. Cần đối chiếu trước khi thêm/hủy.')
            description=[f'{code} · lễ thực tế {actual}: {"thêm" if action=="add" else "hủy"} 1 buổi.',f'Cột Đi Lễ Bù: {current} → {after}.',
                         f'{max(0,current-tracked)} buổi đã có trong sổ chưa có lịch sử từng ngày; giữ nguyên phần này.',
                         'Tính lại điểm chuyên cần, đánh giá, tổng điểm và hạng; không ghi thêm X vào ngày khác.']
        elif operation=='configuration':
            config=values.get('configuration')
            if not isinstance(config,dict):raise ValueError('Cấu hình không hợp lệ.')
            current=self.parity_read(class_id)['configuration']
            semesters=config.get('semesters');schedules=config.get('schedules')
            if not isinstance(semesters,list) or len(semesters)!=12 or any(v not in ('HKI','HKII') for v in semesters):raise ValueError('Chọn học kỳ cho đủ 12 tháng.')
            if 'HKI' not in semesters or 'HKII' not in semesters:raise ValueError('Năm học phải có cả hai học kỳ.')
            cells={f'B{i+4}':v for i,v in enumerate(semesters)}
            for key,ref in (('allowMass','E3'),('allowLesson','E4')):
                v=config.get(key)
                if type(v) is not int or not 0<=v<=31:raise ValueError('Số buổi được nghỉ phải là số nguyên 0–31.')
                cells[ref]=v
            thresholds={}
            for key,ref in (('catechismThreshold','D3'),('attendanceThreshold','D4')):
                v=config.get(key)
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<=v<=10:raise ValueError('Ngưỡng đạt phải từ 0 đến 10.')
                thresholds[ref]=v
            expected={s['row'] for s in current['schedules']}
            if not isinstance(schedules,list) or len(schedules)!=len(expected) or {s.get('row') for s in schedules}!=expected:raise ValueError('Danh sách khối cấu hình không khớp mẫu.')
            for schedule in schedules:
                mass=schedule.get('massDays');lesson=schedule.get('lessonDays')
                if not isinstance(mass,list) or not mass or len(set(mass))!=len(mass) or any(type(d) is not int or not 0<=d<=6 for d in mass):raise ValueError('Chọn các ngày lễ hợp lệ; Chủ Nhật=0, thứ Hai=1.')
                if 0 not in mass:raise ValueError('Giữ lịch Thánh lễ Chủ Nhật; chỉ điều chỉnh ngày lễ trong tuần.')
                if len(mass)>3:raise ValueError('Mẫu có 14 cột lễ mỗi tháng, chỉ hỗ trợ tối đa 3 ngày lễ mỗi tuần. Cần mở rộng mẫu nếu muốn thêm.')
                start_year=int(self.catalog.public()['year'][:4])
                for m in range(1,13):
                    y=start_year if m>=9 else start_year+1
                    count=sum((date(y,m,d).weekday()+1)%7 in mass for d in range(1,monthrange(y,m)[1]+1))
                    if count>14:raise ValueError(f'Lịch {y}-{m:02} có {count} buổi, vượt 14 cột lễ của mẫu. Chọn lịch khác hoặc mở rộng mẫu trước.')
                if lesson!=[0]:raise ValueError('Giáo lý chỉ vào Chủ Nhật.')
                for d in range(7):cells[f'{chr(72+d)}{schedule["row"]}']=1 if d in mass else None
                for d in range(7):cells[f'{chr(81+d)}{schedule["row"]}']=1 if d in lesson else None
            identifiers=list(self.catalog.classes) if values.get('scope')=='all' else [class_id]
            self.parity_guard(identifiers)
            payload={'optionCells':cells,'thresholdCells':thresholds}
            description=[f'Áp dụng {len(identifiers)} lớp; kiểm tra lịch, đơn và chuyên cần trước khi ghi.',
                         f'Ngưỡng Giáo Lý {thresholds["D3"]}; Thánh Lễ {thresholds["D4"]}.']
        elif operation=='note':
            content=str(values.get('content','')).strip()
            if len(content)>2000 or content.startswith('='):raise ValueError('Ghi chú tối đa 2.000 ký tự, không nhập công thức.')
            read=self.parity_read(class_id);ref=values.get('cell') or read['nextNoteCell']
            if not re.fullmatch(r'[A-G](?:[2-9]|[1-9]\d{1,2})',str(ref)):raise ValueError('Ô ghi chú phải trong vùng A2:G999.')
            old=next((n for n in read['notes'] if n['cell']==ref),None)
            if old and not old['editable']:raise ValueError('Ô ghi chú có công thức/số. Chưa hỗ trợ sửa từ web.')
            if not old and ref!=read['nextNoteCell']:raise ValueError('Chỉ thêm tại dòng trống được đề xuất.')
            payload={'cell':ref,'before':old['content'] if old else '', 'content':content}
            description=[f'Ghi vào Ghi Chú!{ref}; giữ các ghi chú còn lại.']
        elif operation=='scratch':
            mode=values.get('mode')
            if mode not in ('clear','restore'):raise ValueError('Chọn xóa hoặc khôi phục vùng nhập.')
            payload={'mode':mode}
            description=['Chỉ tác động K:L, R:S, Y:Z, hàng 4–503 của DiemDanhAuto.',
                         'Không xóa điểm, chuyên cần đã ghi hoặc nhật ký web.',
                         'Khôi phục lấy vùng mẫu CL:CM giống macro gốc.' if mode=='restore' else 'Xóa các dữ liệu đang chờ trong ba vùng nhập.']
        else:raise ValueError('Thao tác không hợp lệ.')
        revisions={cid:self.book_revision(cid) for cid in identifiers}
        plan={'operation':operation,'classId':class_id,'classIds':identifiers,'payload':payload,
              'actor':actor,'reason':reason,'description':description,'issues':issues,'revisions':revisions}
        # Requests, scans and status changes between preview and save invalidate confirmation.
        plan['token']=token({**plan,'database':self.state_revision()})
        return plan

    def bulk_preview(self,values):
        actor,reason=self.parity_manager(values)
        self.catalog.refresh()
        class_id=values.get('classId');self.parity_guard([class_id])
        info=self.catalog.classes[class_id];kind=values.get('kind');text=values.get('text')
        if values.get('expectedRevision') and values['expectedRevision']!=self.book_revision(class_id):raise ValueError('Sổ lớp đã thay đổi. Làm mới trước khi nhập hàng loạt.')
        if not isinstance(text,str) or not text.strip() or len(text)>30000:raise ValueError('Dán danh sách từ 1 đến 40 dòng, tối đa 30.000 ký tự.')
        lines=[line.split('\t') for line in text.strip('\r\n').splitlines() if line.strip()]
        if not 1<=len(lines)<=40:raise ValueError('Mỗi lượt nhập từ 1 đến 40 dòng của một lớp.')
        entries=[];issues=[];seen=set()
        for n,line in enumerate(lines,1):
            code=line[0].strip().upper();student=self.catalog.students.get(code)
            if code in seen or not student or student['classId']!=class_id:issues.append(f'Dòng {n}: mã trùng hoặc không thuộc lớp.');continue
            seen.add(code)
            if kind=='grades':
                from .validation import validate_grades
                if len(line)!=25:issues.append(f'Dòng {n}: cần 25 cột (mã + 20 khảo bài + 4 điểm kiểm tra/thi).');continue
                item={'code':code,'khaoBai':line[1:21],**dict(zip(('kt15','kt1Tiet','thiKinh','thiHk'),line[21:]))}
                try:entries.extend(validate_grades([item],class_id,self.catalog.students))
                except ValueError as e:issues.append(f'Dòng {n}: {e}')
            elif kind=='attendance':
                if len(line)!=1:issues.append(f'Dòng {n}: chỉ nhập mã; ngày và hoạt động chọn chung phía trên.');continue
                actual=day(values.get('date'));activity=values.get('activity')
                if activity not in ('mass','lesson','early'):raise ValueError('Hoạt động không hợp lệ.')
                if actual>datetime.now(self.local_tz).date().isoformat():issues.append('Không điểm danh có mặt cho ngày chưa diễn ra.');continue
                if not self.student_active(code,actual) or student['enrolledFrom'] and actual<student['enrolledFrom']:
                    issues.append(f'{code}: chưa nhập học hoặc đang nghỉ.');continue
                makeups=[r for r in self.requests() if r['code']==code and r['kind']=='makeup' and r['status']=='approved' and r['effective_target_day']==actual]
                target=makeups[0]['day'] if activity=='mass' and makeups else actual
                if not makeups and actual not in info['calendar'][activity]:issues.append(f'{code}: ngày không có trong lịch/đơn đổi lễ.');continue
                status=self.status_at(code,target,activity)
                if status in ('P','O'):issues.append(f'{code}: đã có {status}; chỉnh riêng từng em có lý do trước khi nhập hàng loạt.');continue
                if activity=='early':
                    try:self.validate_early_attendance({'date':actual,'activity':activity},{**values,'manual':True})
                    except ValueError as e:issues.append(str(e));continue
                with self.db() as db:
                    used=db.execute("SELECT status FROM scans WHERE code=? AND activity=? AND actual_day=?",(code,activity,actual)).fetchone()
                if used and used['status']=='supplemental':issues.append(f'{code}: lượt đã cộng lễ bổ sung.');continue
                if not status and self.locked({'date':target,'activity':activity},class_id):issues.append(f'{code}: buổi đã chốt; chỉnh riêng từng em.');continue
                entries.append({'code':code,'name':student['name'],'targetDate':target,'duplicate':status=='X'})
            else:raise ValueError('Loại nhập hàng loạt không hợp lệ.')
        semester=values.get('semester',1)
        if kind=='grades' and (type(semester) is not int or semester not in (1,2)):raise ValueError('Chọn học kỳ 1 hoặc 2.')
        plan={'kind':kind,'classId':class_id,'entries':entries,'issues':issues,'revision':self.book_revision(class_id),
              'semester':semester,'date':values.get('date'),'activity':values.get('activity'),'actor':actor,'reason':reason,
              'attendedTime':values.get('attendedTime')}
        plan['token']=token({**plan,'database':self.state_revision()})
        return plan

    def reason(self, values):
        value=str(values.get('reason') or '').strip()
        if not 3<=len(value)<=500: raise ValueError('Nhập lý do từ 3 đến 500 ký tự.')
        return value

    def import_rows(self, values):
        columns=['classId','code','saintName','fullName','gender','birthDate','baptismDate','parents','address','subParish','phone','enrolledFrom']
        if isinstance(values.get('rows'),list):
            rows=values['rows']
        elif values.get('fileBase64'):
            try: data=base64.b64decode(values['fileBase64'],validate=True)
            except (ValueError,TypeError): raise ValueError('File tải lên không hợp lệ.')
            if len(data)>2_000_000: raise ValueError('File nhập tối đa 2 MB.')
            filename=str(values.get('filename') or '').lower()
            if filename.endswith('.xlsx'):
                import zipfile
                import openpyxl
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if sum(i.file_size for i in archive.infolist())>20_000_000: raise ValueError('File Excel giải nén quá lớn.')
                book=openpyxl.load_workbook(io.BytesIO(data),read_only=True,data_only=False)
                try:
                    if book.active.max_column > 50 or book.active.max_row > 802:
                        raise ValueError('File nhập chỉ được có tối đa 800 dòng hồ sơ và 50 cột.')
                    iterator=book.active.iter_rows(values_only=True)
                    header=[str(c or '').strip() for c in next(iterator)]
                    rows=[]
                    for row in iterator:
                        if len(rows)>800: raise ValueError('Chỉ nhập tối đa 800 dòng một lần.')
                        if any(v not in (None,'') for v in row):
                            rows.append({key:(value.date().isoformat() if isinstance(value,datetime) else str(value or '')) for key,value in zip(header,row)})
                finally: book.close()
            elif filename.endswith(('.csv','.tsv','.txt')):
                text=data.decode('utf-8-sig');rows=self.parse_text(text)
            else: raise ValueError('Chỉ nhận .xlsx, CSV hoặc TSV UTF-8.')
        else: rows=self.parse_text(str(values.get('text') or ''))
        if not 1<=len(rows)<=800: raise ValueError('Nhập từ 1 đến 800 dòng hồ sơ.')
        if any(not isinstance(r,dict) or set(r)-set(columns) for r in rows): raise ValueError('Có tên cột không được hỗ trợ. Dùng file mẫu.')
        return rows

    def parse_text(self, text):
        if len(text)>2_000_000: raise ValueError('Danh sách quá lớn.')
        delimiter='\t' if '\t' in text.split('\n',1)[0] else ','
        reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),delimiter=delimiter)
        if not reader.fieldnames or 'code' not in reader.fieldnames or 'fullName' not in reader.fieldnames:
            raise ValueError('Dòng đầu cần tên cột theo file mẫu: code, fullName…')
        rows=[]
        for row in reader:
            if len(rows)>=800: raise ValueError('Chỉ nhập tối đa 800 dòng một lần.')
            if any(v for v in row.values()): rows.append(row)
        return rows

    def year_preview(self, values):
        self.catalog.refresh()
        year = values.get('startYear')
        current_year = int(self.catalog.public()['year'][:4])
        if type(year) is not int or year not in range(current_year+1,2100):
            raise ValueError('Chọn năm bắt đầu sau năm học hiện tại, đến 2099.')
        placements = values.get('placements')
        if not isinstance(placements,list) or len(placements)!=len(self.catalog.students):
            raise ValueError('Danh sách lên lớp phải bao gồm từng thiếu nhi hiện tại.')
        codes,counts,issues=set(),{},[]
        for p in placements:
            if not isinstance(p,dict) or p.get('code') not in self.catalog.students or p['code'] in codes:
                raise ValueError('Mã thiếu nhi không hợp lệ hoặc bị trùng.')
            codes.add(p['code'])
            if p.get('classId') not in self.catalog.classes and p.get('classId')!='graduate':
                issues.append(p['code']+': chưa chọn lớp đích.')
            elif p['classId']!='graduate':
                counts[p['classId']]=counts.get(p['classId'],0)+1
            if p.get('approved') is not True:
                issues.append(p['code']+': chưa duyệt lên lớp.')
        for identifier,count in counts.items():
            if count>40:
                issues.append(self.catalog.classes[identifier]['name']+f': {count} em, vượt 40 dòng.')
        fingerprint={'startYear':year,'placements':placements,'hashes':{i:self.book_revision(i) for i in self.catalog.classes}}
        return {'startYear':year,'placements':placements,'issues':issues,'counts':counts,
                'token':hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()}

    def save_year_plan(self, values):
        if not values.get('_manager'):
            raise ValueError('Lập kế hoạch năm học bằng tài khoản Admin.')
        actor,reason=self.actor(values)
        plan=self.year_preview(values)
        identifier=secrets.token_hex(12)
        with self.db() as db:
            db.execute('INSERT INTO year_plans VALUES (?,?,?,?,?,?,?,?)',
                       (identifier,plan['startYear'],json.dumps(plan['placements']),actor,reason,'draft',self.stamp(),None))
            self.management_event(db,'year',identifier,'draft',actor,reason)
        return {'saved':True,'id':identifier,'state':self.bootstrap()}
