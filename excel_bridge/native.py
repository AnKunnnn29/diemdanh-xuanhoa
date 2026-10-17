"""An isolated Excel instance and one guarded staging path for every update."""
import hashlib
import math
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from catalog import macro_signature
from validation import PROFILE_FIELDS, profile_date, validate_grades
from parity_native import NativeParity


def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(65536),b''):
            value.update(chunk)
    return value.hexdigest()


class ExcelEngine(NativeParity):
    def __init__(self, catalog):
        self.catalog = catalog
        pythoncom.CoInitialize()
        self.app = None

    def excel(self):
        if self.app is not None:
            try:
                self.app.Workbooks.Count
            except (AttributeError,pythoncom.com_error):
                self.app=None
        if self.app is None:
            self.app = win32com.client.DispatchEx('Excel.Application')
            self.app.Visible = False
            self.app.DisplayAlerts = False
            self.app.EnableEvents = False
            self.app.AutomationSecurity = 1
        return self.app

    @contextmanager
    def staged_book(self, class_id):
        self.catalog.refresh()
        info = self.catalog.classes[class_id]
        source = info['path']
        digest = sha(source)
        if macro_signature(source)[0] != self.catalog.trusted_signature:
            raise ValueError('Macro đã thay đổi. Chưa ghi vào Excel.')
        app = self.excel()
        self.catalog.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.excel-stage-', dir=source.parent) as folder:
            stage = Path(folder) / source.name
            original = book = None
            try:
                try:
                    original = app.Workbooks.Open(str(source), UpdateLinks=0, ReadOnly=False, Notify=False)
                except pythoncom.com_error as error:
                    raise ValueError(f'Chưa mở được file {info["name"]} để ghi. Hãy đóng file trong Excel rồi thử lại.') from error
                if original.ReadOnly:
                    raise ValueError(f'File {info["name"]} đang mở hoặc chỉ đọc. Hãy đóng file trong Excel rồi thử lại.')
                original.SaveCopyAs(str(stage))
                original.Close(SaveChanges=False)
                original = None
                if macro_signature(stage)[0] != self.catalog.trusted_signature:
                    raise ValueError('VBA trong bản làm việc đã thay đổi; chưa mở bản này để ghi.')
                book = app.Workbooks.Open(str(stage), UpdateLinks=0, ReadOnly=False, Notify=False)
                app.Calculation = -4105
                checks = []
                yield app, book, info, checks
                app.Calculate()
                self.verify_cells(checks)
                if not book.HasVBProject:
                    raise ValueError('File không còn VBA. Chưa cập nhật file gốc.')
                book.Save()
                book.Close(SaveChanges=False)
                book = None
                if macro_signature(stage)[0] != self.catalog.trusted_signature:
                    raise ValueError('VBA trong bản làm việc đã thay đổi; chưa cập nhật file lớp.')
                if sha(source) != digest:
                    raise ValueError('File lớp vừa được thay đổi từ bên ngoài. Hãy tải lại rồi thử lại.')
                backup_dir = self.catalog.state_dir / 'backups' / class_id
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup = backup_dir / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.xlsm')
                shutil.copy2(source, backup)
                if sha(source) != digest or sha(backup) != digest:
                    raise ValueError('File lớp thay đổi trong lúc sao lưu. Chưa thay thế file gốc.')
                try:
                    os.replace(stage, source)
                except PermissionError as error:
                    raise ValueError('File lớp đang được sử dụng. Hãy đóng Excel rồi thử lại.') from error
                self.catalog.refresh()
            finally:
                if book is not None:
                    book.Close(SaveChanges=False)
                if original is not None:
                    original.Close(SaveChanges=False)

    @contextmanager
    def editable_sheet(self, sheet):
        flags = (sheet.ProtectDrawingObjects, sheet.ProtectContents, sheet.ProtectScenarios)
        names = ('AllowFormattingCells', 'AllowFormattingColumns', 'AllowFormattingRows',
                 'AllowInsertingColumns', 'AllowInsertingRows', 'AllowInsertingHyperlinks',
                 'AllowDeletingColumns', 'AllowDeletingRows', 'AllowSorting', 'AllowFiltering',
                 'AllowUsingPivotTables')
        permissions = {name: getattr(sheet.Protection, name) for name in names}
        sheet.Unprotect('')
        try:
            yield
        finally:
            if any(flags):
                sheet.Protect(Password='', DrawingObjects=flags[0], Contents=flags[1],
                              Scenarios=flags[2], **permissions)

    def rows_for_codes(self, sheet, first, last, codes):
        rows = {}
        for row, value in enumerate(sheet.Range(f'B{first}:B{last}').Value, first):
            if not value[0]:
                continue
            code = str(value[0]).strip().upper()
            if not code:
                continue
            if code in rows:
                raise ValueError(f'Mã {code} bị trùng trong sheet {sheet.Name}. Chưa ghi dữ liệu.')
            rows[code] = row
        for code in codes:
            if code not in rows:
                raise ValueError(f'Mã {code} không còn trong sheet {sheet.Name}. Hãy tải lại danh sách.')
        return rows

    def set_cell(self, cell, value, checks):
        if isinstance(value, datetime):
            # Excel dates are wall-clock serials; COM datetime conversion can shift them by the host timezone.
            epoch = datetime(1904, 1, 1) if cell.Worksheet.Parent.Date1904 else datetime(1899, 12, 30)
            cell.Value2 = (value.date() - epoch.date()).days
        else:
            cell.Value = value
        checks.append((cell, value))

    def verify_cells(self, checks):
        seen=set()
        for cell, expected in reversed(checks):
            key=(cell.Worksheet.Name,cell.Address)
            if key in seen:
                continue
            seen.add(key)
            actual = cell.Value
            if isinstance(expected, datetime):
                matches = isinstance(actual, datetime) and actual.date() == expected.date()
            elif isinstance(expected, (int, float)):
                matches = isinstance(actual, (int, float)) and math.isclose(actual, expected, abs_tol=1e-9)
            elif expected is None or expected == '':
                matches = actual is None or actual == ''
            else:
                matches = actual == expected
            if not matches:
                raise ValueError(f'Excel chưa lưu đúng dữ liệu ở {cell.Worksheet.Name}!{cell.Address}. Chưa thay file gốc.')

    def write(self, class_id, session, changes):
        if any(status not in ('', 'X', 'P', 'O') for status in changes.values()):
            raise ValueError('Trạng thái điểm danh không hợp lệ.')
        ran_macro = False
        with self.staged_book(class_id) as (app, book, info, checks):
            book.Activate()
            sheet_name, column = info['targets'][(session['date'], session['activity'])]
            sheet = book.Worksheets(sheet_name)
            sheet.Activate()
            app.Calculate()
            before = sheet.Range('E8:AB47').Formula
            scratch_before = sheet.Range('AQ8:BN47').Formula
            rows = self.rows_for_codes(sheet, 8, 47, changes)
            with self.editable_sheet(sheet):
                for code, status in changes.items():
                    cell = sheet.Cells(rows[code], column)
                    if cell.HasFormula:
                        raise ValueError('Ô điểm danh có công thức. Chưa ghi đè.')
                    self.set_cell(cell, status or None, checks)
                app.Calculate()
                if sheet.Cells(1, 46).Value == 'OK':
                    app.Run("'" + book.Name.replace("'", "''") + "'!" + info['macro'])
                    ran_macro = True
                    sheet.Unprotect('')
                    restored = [list(row) for row in before]
                    for code, status in changes.items():
                        restored[rows[code]-8][column-5] = status or None
                    sheet.Range('E8:AB47').Formula = tuple(tuple(row) for row in restored)
                    sheet.Range('AQ8:BN47').Formula = scratch_before
            app.CutCopyMode = False
        return {'workbook': info['filename'], 'sheet': sheet_name, 'column': column,
                'macro': info['macro'], 'vbaExecuted': ran_macro, 'saved': True}

    def write_profile(self, class_id, code, profile):
        self.catalog.refresh()
        student = self.catalog.students.get(code)
        if not student or student['classId'] != class_id:
            raise ValueError('Không tìm thấy học sinh thuộc lớp này.')
        if not profile or set(profile) - (PROFILE_FIELDS | {'saintName','fullName'}):
            raise ValueError('Thông tin hồ sơ cần cập nhật không hợp lệ.')
        values = dict(profile)
        for name in values:
            if name in ('birthDate', 'baptismDate'):
                values[name] = profile_date(values[name])
            elif values[name] is not None and not isinstance(values[name], str):
                raise ValueError('Thông tin hồ sơ phải là văn bản.')
        columns = {'gender': 5, 'birthDate': 6, 'baptismDate': 7, 'parents': 8,
                   'address': 9, 'subParish': 10, 'phone': 11}
        identity = bool(set(values) & {'saintName','fullName'})
        saint = values.pop('saintName', student['saintName'])
        full = values.pop('fullName', student['fullName'])
        if identity:
            if not isinstance(full, str) or not 2 <= len(full.strip()) <= 150 or not isinstance(saint, str) or len(saint) > 100:
                raise ValueError('Nhập họ tên (2–150 ký tự) và tên thánh tối đa 100 ký tự.')
            words = ' '.join(full.split()).rsplit(' ', 1)
            family, given = ('', words[0]) if len(words) == 1 else words
            family = ' '.join((saint.strip() + ' ' + family).split())
        with self.staged_book(class_id) as (_, book, _, checks):
            if identity:
                self.set_saint_property(book,code,saint.strip())
                ranges = {'Danh Sách': (7,46), 'Lý Lịch': (5,46), 'HK 1': (6,45), 'HK 2': (6,45), 'Tổng kết': (7,46)}
                ranges.update({f'T{m:02}': (8,47) for m in range(1,13)})
                for name, (first,last) in ranges.items():
                    target = book.Worksheets(name)
                    r = self.rows_for_codes(target, first, last, [code])[code]
                    with self.editable_sheet(target):
                        for column, text in ((3,family),(4,given)):
                            cell = target.Cells(r,column)
                            if not cell.HasFormula:
                                cell.NumberFormat = '@'
                                self.set_cell(cell, text or None, checks)
                book.Application.Calculate()
                for name, (first,last) in ranges.items():
                    target = book.Worksheets(name)
                    r = self.rows_for_codes(target, first, last, [code])[code]
                    checks.extend([(target.Cells(r,3),family or None),(target.Cells(r,4),given)])
            sheet = book.Worksheets('Lý Lịch')
            row = self.rows_for_codes(sheet, 5, 46, [code])[code]
            with self.editable_sheet(sheet):
                for name, value in values.items():
                    cell = sheet.Cells(row, columns[name])
                    cell.NumberFormat = 'dd/mm/yyyy' if name in ('birthDate', 'baptismDate') else '@'
                    self.set_cell(cell, value or None, checks)
        return {'saved': True, 'vbaExecuted': False}

    def write_teachers(self, class_id, teachers):
        cells = {'glv1': 'B3', 'glv2': 'E3', 'souer': 'B4', 'glv3': 'E4'}
        if not teachers or set(teachers) - set(cells) or any(
                value is not None and not isinstance(value, str) for value in teachers.values()):
            raise ValueError('Thông tin giáo lý viên cần cập nhật không hợp lệ.')
        with self.staged_book(class_id) as (_, book, _, checks):
            sheet = book.Worksheets('Danh Sách')
            with self.editable_sheet(sheet):
                for name, value in teachers.items():
                    self.set_cell(sheet.Range(cells[name]), value or None, checks)
        return {'saved': True, 'vbaExecuted': False}

    def write_grades(self, class_id, semester, grades):
        self.catalog.refresh()
        if type(semester) is not int or semester not in (1, 2):
            raise ValueError('Học kỳ phải là 1 hoặc 2.')
        grades = validate_grades(grades, class_id, self.catalog.students)
        columns = {'kt15': 25, 'kt1Tiet': 26, 'thiKinh': 27, 'thiHk': 28}
        with self.staged_book(class_id) as (_, book, _, checks):
            sheet = book.Worksheets('HK 1' if semester == 1 else 'HK 2')
            rows = self.rows_for_codes(sheet, 6, 45, [item['code'] for item in grades])
            with self.editable_sheet(sheet):
                for item in grades:
                    row = rows[item['code']]
                    for idx, value in enumerate(item.get('khaoBai', [])):
                        self.set_cell(sheet.Cells(row, 5 + idx), value, checks)
                    for name, column in columns.items():
                        if name in item:
                            self.set_cell(sheet.Cells(row, column), item[name], checks)
        return {'saved': True, 'vbaExecuted': False}

    def close(self):
        if self.app is not None:
            try:
                self.app.Quit()
            except (AttributeError,pythoncom.com_error):
                pass
            finally:
                self.app = None
        pythoncom.CoUninitialize()

    def transfer_student(self, code, target_id):
        """Prepare both workbooks off-line; journal and roll back partial replacements."""
        from catalog import Catalog
        self.catalog.refresh()
        student = self.catalog.students[code]
        source_id = student['classId']
        infos = [self.catalog.classes[source_id], self.catalog.classes[target_id]]
        sources = [info['path'] for info in infos]
        fingerprints = {str(p): sha(p) for p in sources}
        # Reject open/read-only originals before preparing either replacement.
        app = self.excel()
        for path in sources:
            original = app.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=False, Notify=False)
            try:
                if original.ReadOnly:
                    raise ValueError('Đóng cả hai file lớp trong Excel trước khi chuyển.')
            finally:
                original.Close(SaveChanges=False)
        root = self.catalog.state_dir / 'transfers'
        root.mkdir(exist_ok=True)
        transaction = root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        transaction.mkdir()
        data = transaction / 'data'; data.mkdir()
        for p in sources:
            shutil.copy2(p, data / p.name)
        shadow = Catalog(data, transaction / 'state', self.catalog.trusted_signature)
        worker = object.__new__(ExcelEngine)
        worker.catalog = shadow
        worker.app = app
        spans = {'Danh Sách': (7,46,10),'Lý Lịch': (5,46,11),'HK 1': (6,45,28),
                 'HK 2': (6,45,28),'Tổng kết': (7,46,4)}
        spans.update({f'T{m:02}': (8,47,28) for m in range(1,13)})
        payload = {}
        try:
            with worker.staged_book(source_id) as (_,book,_,checks):
                source_rows={name:worker.rows_for_codes(book.Worksheets(name),first,last,[code])[code]
                             for name,(first,last,end) in spans.items()}
                for name,(first,last,end) in spans.items():
                    sheet = book.Worksheets(name)
                    r = source_rows[name]
                    payload[name] = {col:sheet.Cells(r,col).Value for col in range(3,end+1) if not sheet.Cells(r,col).HasFormula}
                for name in [n for n in spans if n!='Danh Sách']+['Danh Sách']:
                    first,last,end=spans[name]
                    sheet=book.Worksheets(name)
                    r=source_rows[name]
                    with worker.editable_sheet(sheet):
                        for col in range(2,end+1):
                            cell = sheet.Cells(r,col)
                            if not cell.HasFormula:
                                worker.set_cell(cell,None,checks)
            with worker.staged_book(target_id) as (shadow_app,book,info,checks):
                roster = book.Worksheets('Danh Sách')
                empty = [r for r in range(7,47) if not roster.Cells(r,2).Value]
                if not empty:
                    raise ValueError('Không còn dòng trống ở lớp đích.')
                r = empty[0]
                with worker.editable_sheet(roster):
                    worker.set_cell(roster.Cells(r,2),code,checks)
                    for col,value in payload['Danh Sách'].items():
                        cell=roster.Cells(r,col)
                        if not cell.HasFormula:
                            cell.NumberFormat='@' if col in (3,4) else cell.NumberFormat
                            worker.set_cell(cell,value,checks)
                shadow_app.Calculate()
                worker.set_saint_property(book,code,student['saintName'])
                for name,(first,last,end) in spans.items():
                    if name=='Danh Sách':
                        continue
                    sheet=book.Worksheets(name)
                    rows=worker.rows_for_codes(sheet,first,last,[])
                    row=rows.get(code)
                    if row is None:
                        row=next((r for r in range(first,last+1) if not sheet.Cells(r,2).Value),None)
                        if row is None:
                            raise ValueError('Không còn dòng cho mã tại '+name)
                    with worker.editable_sheet(sheet):
                        for col,value in ((2,code),(3,payload['Danh Sách'].get(3)),(4,payload['Danh Sách'].get(4))):
                            cell=sheet.Cells(row,col)
                            if not cell.HasFormula:
                                worker.set_cell(cell,value,checks)
                        if not name.startswith('T') or name=='Tổng kết':
                            for col,value in payload[name].items():
                                if col>=5 and not sheet.Cells(row,col).HasFormula:
                                    cell=sheet.Cells(row,col)
                                    # Use Value2 for date serials; text phone numbers remain text.
                                    if name=='Lý Lịch' and col in (6,7) and isinstance(value,datetime):
                                        cell.NumberFormat='dd/mm/yyyy'
                                    if name=='Lý Lịch' and col==11:
                                        cell.NumberFormat='@'
                                    worker.set_cell(cell,value,checks)
                        else:
                            # Monthly columns can differ; map each recorded mark by actual date/activity.
                            for col in range(5,29):
                                if not sheet.Cells(row,col).HasFormula:
                                    worker.set_cell(sheet.Cells(row,col),None,checks)
                            for key,mark in self.catalog.marks.items():
                                d,activity,mark_code=key.split('|')
                                if mark_code==code:
                                    dest_name,col=info['targets'][(d,activity)]
                                    if dest_name==name:
                                        worker.set_cell(sheet.Cells(row,col),mark['status'],checks)
                shadow_app.Calculate()
                for name,(first,last,end) in spans.items():
                    worker.rows_for_codes(book.Worksheets(name),first,last,[code])
        finally:
            worker.app = None
        replacement_catalog=Catalog(data,transaction/'verify',self.catalog.trusted_signature)
        moved=replacement_catalog.students.get(code)
        if not moved or moved['classId']!=target_id:
            raise ValueError('Bản làm việc chưa chuyển đúng mã.')
        before_marks={k:v['status'] for k,v in self.catalog.marks.items() if k.endswith('|'+code)}
        after_marks={k:v['status'] for k,v in replacement_catalog.marks.items() if k.endswith('|'+code)}
        if before_marks!=after_marks:
            raise ValueError('Chuyên cần chưa được bảo toàn trong bản làm việc.')
        import json
        journal={'status':'prepared','files':[]}
        for index,path in enumerate(sources):
            rollback=transaction/f'original-{index}.xlsm'
            shutil.copy2(path,rollback)
            if sha(path)!=fingerprints[str(path)] or sha(rollback)!=fingerprints[str(path)]:
                raise ValueError('File lớp thay đổi khi chuẩn bị chuyển. Chưa thay file gốc.')
            journal['files'].append({'path':str(path),'original':str(rollback),'oldSha':sha(rollback),'newSha':sha(data/path.name)})
        journal_path=transaction/'journal.json'
        journal_path.write_text(json.dumps(journal),encoding='utf-8')
        replaced=[]
        try:
            for index,path in enumerate(sources):
                if sha(path)!=fingerprints[str(path)]:
                    raise ValueError('File lớp thay đổi sau khi xem trước.')
                stage=path.parent/('.transfer-'+transaction.name+'.xlsm')
                shutil.copy2(data/path.name,stage)
                try:
                    os.replace(stage,path)
                finally:
                    stage.unlink(missing_ok=True)
                replaced.append(index)
            self.catalog.stamps={}
            self.catalog.refresh()
            journal['status']='committed'
            journal_path.write_text(json.dumps(journal),encoding='utf-8')
        except Exception:
            for index in reversed(replaced):
                path=sources[index]
                stage=path.parent/('.rollback-'+transaction.name+'.xlsm')
                shutil.copy2(transaction/f'original-{index}.xlsm',stage)
                os.replace(stage,path)
            journal['status']='rolled-back'
            journal_path.write_text(json.dumps(journal),encoding='utf-8')
            self.catalog.stamps={}
            self.catalog.refresh()
            raise

    def prepare_year(self, plan, destination):
        """Generate a separate, recalculated school year; never replace current workbooks."""
        import json
        from catalog import Catalog
        from validation import profile_date
        self.catalog.refresh()
        year=plan['startYear']
        destination=Path(destination)
        if not destination.resolve().is_relative_to((self.catalog.state_dir/'year_exports').resolve()):
            raise ValueError('Thư mục xuất năm học không hợp lệ.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():
            raise ValueError('Thư mục năm học đã tồn tại.')
        fingerprints={str(c['path']):sha(c['path']) for c in self.catalog.classes.values()}
        with tempfile.TemporaryDirectory(prefix='.year-stage-',dir=destination.parent) as temporary:
            stage=Path(temporary)
            app=self.excel()
            for info in self.catalog.classes.values():
                path=stage/(f'{info["name"]} ({year}-{year+1}).xlsm')
                shutil.copy2(info['path'],path)
                if macro_signature(path)[0]!=self.catalog.trusted_signature:
                    raise ValueError('VBA mẫu không hợp lệ.')
                book=app.Workbooks.Open(str(path),UpdateLinks=0,ReadOnly=False,Notify=False)
                checks=[]
                try:
                    option=book.Worksheets('OPTION')
                    with self.editable_sheet(option):
                        for index,month in enumerate([9,10,11,12,1,2,3,4,5,6,7,8],4):
                            self.set_cell(option.Cells(index,1),datetime(year if month>=9 else year+1,month,1),checks)
                    spans={'Danh Sách':(7,46,10),'Lý Lịch':(5,46,11),'HK 1':(6,45,28),'HK 2':(6,45,28),'Tổng kết':(7,46,4)}
                    spans.update({f'T{m:02}':(8,47,28) for m in range(1,13)})
                    for name,(first,last,end) in spans.items():
                        sheet=book.Worksheets(name)
                        with self.editable_sheet(sheet):
                            try:
                                sheet.Range(sheet.Cells(first,2),sheet.Cells(last,end)).SpecialCells(2).ClearContents()
                            except pythoncom.com_error as error:
                                # Excel returns 1004 when this range has no constants to clear.
                                if 'No cells' not in str(error) and '1004' not in str(error) and error.excepinfo and error.excepinfo[5]!=-2146827284:
                                    raise
                    total=book.Worksheets('Tổng kết')
                    with self.editable_sheet(total):
                        for row in range(7,47):
                            cell=total.Cells(row,15)
                            if not cell.HasFormula:self.set_cell(cell,None,checks)
                    roster=book.Worksheets('Danh Sách')
                    assigned=[self.catalog.students[p['code']] for p in plan['placements'] if p['classId']==info['id']]
                    with self.editable_sheet(roster):
                        roster.Range('A1').Value=f'DANH SÁCH LỚP GIÁO LÝ NĂM {year}-{year+1}'
                        roster.Range('E5').Value=f'{year-1}-{year}'
                        roster.Range('G5').Value=f'{year}-{year+1}'
                        for row,student in enumerate(assigned,7):
                            words=student['fullName'].rsplit(' ',1)
                            family,given=('',words[0]) if len(words)==1 else words
                            family=' '.join((student['saintName']+' '+family).split())
                            for col,value in ((2,student['id']),(3,family),(4,given),(9,datetime(year,9,1)),(10,student['gender'])):
                                cell=roster.Cells(row,col)
                                if col in (2,3,4,10):cell.NumberFormat='@'
                                if col==9:cell.NumberFormat='dd/mm/yyyy'
                                self.set_cell(cell,value or None,checks)
                            property_name='XH_Saint_'+student['id']
                            self.set_saint_property(book,student['id'],student['saintName'])
                    app.Calculate()
                    profiles=book.Worksheets('Lý Lịch')
                    with self.editable_sheet(profiles):
                        rows=self.rows_for_codes(profiles,5,46,[s['id'] for s in assigned])
                        for s in assigned:
                            for name,col in {'gender':5,'birthDate':6,'baptismDate':7,'parents':8,'address':9,'subParish':10,'phone':11}.items():
                                value=s[name]
                                cell=profiles.Cells(rows[s['id']],col)
                                if name in ('birthDate','baptismDate'):
                                    value=profile_date(value)
                                    cell.NumberFormat='dd/mm/yyyy'
                                else:cell.NumberFormat='@'
                                self.set_cell(cell,value or None,checks)
                    app.Calculate()
                    self.verify_cells(checks)
                    book.Save()
                finally:
                    book.Close(SaveChanges=False)
                if macro_signature(path)[0]!=self.catalog.trusted_signature:
                    raise ValueError('Bộ năm mới không giữ VBA gốc.')
            catalog=Catalog(stage,stage/'verify',self.catalog.trusted_signature)
            expected={p['code'] for p in plan['placements'] if p['classId']!='graduate'}
            if set(catalog.students)!=expected or catalog.marks:
                raise ValueError('Danh sách năm mới không đúng kế hoạch hoặc còn chuyên cần cũ.')
            for p in plan['placements']:
                if p['classId']!='graduate' and catalog.students[p['code']]['classId']!=p['classId']:
                    raise ValueError('Thiếu nhi chưa vào đúng lớp đã duyệt.')
            for info in catalog.classes.values():
                for activity,days in info['calendar'].items():
                    if any(not f'{year}-09-01'<=d<=f'{year+1}-08-31' for d in days):
                        raise ValueError('Lịch năm học mới ngoài khoảng tháng 9 đến tháng 8.')
                    if activity in ('early','lesson') and any(datetime.fromisoformat(d).weekday()!=6 for d in days):
                        raise ValueError('Lịch Chủ Nhật của mẫu chưa tính đúng năm mới.')
                for semester in (1,2):
                    grades=catalog.read_grades(info['id'],semester)['students']
                    if any(any(v not in (None,'') for v in r['khaoBai']+[r['kt15'],r['kt1Tiet'],r['thiKinh'],r['thiHk']]) for r in grades):
                        raise ValueError('Bảng điểm năm mới còn điểm cũ.')
            if any(sha(path)!=value for path,value in fingerprints.items()):
                raise ValueError('Sổ hiện tại thay đổi trong lúc tạo năm mới. Xem trước lại.')
            manifest={'year':f'{year}-{year+1}','count':len(catalog.classes),'studentCount':len(expected),
                      'placements':plan['placements'],'issuedCodes':plan.get('issuedCodes',[]),
                      'files':{p.name:sha(p) for p in stage.glob('*.xlsm')}}
            (stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(stage,destination)

    def set_saint_property(self,book,code,saint):
        name='XH_Saint_'+code
        properties=book.CustomDocumentProperties
        for index in range(1,properties.Count+1):
            # Office exposes Item as the default PROPERTYGET; dynamic COM can emit METHOD instead.
            existing=win32com.client.Dispatch(properties._oleobj_.Invoke(0,0,pythoncom.DISPATCH_PROPERTYGET,True,index))
            if existing.Name==name:
                existing.Value=saint or '__XH_EMPTY__'
                return
        properties.Add(name,False,4,saint or '__XH_EMPTY__')
