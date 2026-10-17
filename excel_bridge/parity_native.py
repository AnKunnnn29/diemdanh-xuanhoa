"""Prepare reviewed workbook changes on isolated copies, before committing any source."""
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from catalog import Catalog, clean, macro_signature
from validation import profile_date


class NativeParity:
    def parity_package(self, class_id, operation, values):
        info = self.catalog.classes[class_id]
        with tempfile.TemporaryDirectory(prefix='.parity-stage-', dir=info['path'].parent) as folder:
            root = Path(folder)
            target = root / info['filename']
            shutil.copy2(info['path'], target)
            copied = Catalog(root, root / 'state', self.catalog.trusted_signature)
            # Reuse the initialized STA/app; do not accumulate CoInitialize calls.
            worker = object.__new__(type(self))
            worker.catalog = copied
            worker.app = self.excel()
            with worker.staged_book(class_id) as (app, book, _, checks):
                if operation == 'student-add':
                    roster = book.Worksheets('Danh Sách')
                    row = next((r for r in range(7,47) if not roster.Cells(r,2).Value), None)
                    if row is None:
                        raise ValueError('Lớp đã đủ 40 em. Chưa thêm thiếu nhi.')
                    words=values['fullName'].rsplit(' ',1)
                    family,given=('',words[0]) if len(words)==1 else words
                    with worker.editable_sheet(roster):
                        for col,value in ((2,values['code']),(3,clean(values['saintName']+' '+family)),(4,given),
                                          (7,roster.Range('B2').Value),(8,roster.Range('E2').Value),
                                          (9,profile_date(values['enrolledFrom'])),(10,values.get('gender',''))):
                            cell=roster.Cells(row,col)
                            cell.NumberFormat='dd/mm/yyyy' if col==9 else '@'
                            worker.set_cell(cell,value or None,checks)
                    worker.set_saint_property(book,values['code'],values['saintName'])
                    app.Calculate()
                    # Resolve each linked row by code, including independently sorted sheets.
                    spans=[('HK 1',6,45,5,28),('HK 2',6,45,5,28),('Tổng kết',7,46,15,15),('Lý Lịch',5,46,5,11)]
                    spans += [(f'T{m:02}',8,47,5,28) for m in range(1,13)]
                    for name,first,last,col_first,col_last in spans:
                        sheet=book.Worksheets(name)
                        r=worker.rows_for_codes(sheet,first,last,[values['code']])[values['code']]
                        raw=sheet.Range(sheet.Cells(r,col_first),sheet.Cells(r,col_last)).Formula
                        raw=(raw,) if col_first==col_last else raw[0]
                        for i,value in enumerate(raw,col_first):
                            if value not in (None,'') and not (isinstance(value,str) and value.startswith('=')):
                                raise ValueError(f'Dòng mới còn dữ liệu tại {name}, cột {i}. Cần đối chiếu trước khi thêm.')
                    profile=book.Worksheets('Lý Lịch')
                    profile_row=worker.rows_for_codes(profile,5,46,[values['code']])[values['code']]
                    with worker.editable_sheet(profile):
                        for name,col in {'gender':5,'birthDate':6,'baptismDate':7,'parents':8,'address':9,'subParish':10,'phone':11}.items():
                            cell=profile.Cells(profile_row,col)
                            value=values.get(name,'')
                            if name in ('birthDate','baptismDate'):
                                value=profile_date(value);cell.NumberFormat='dd/mm/yyyy'
                            else:cell.NumberFormat='@'
                            worker.set_cell(cell,value or None,checks)
                    app.Calculate()
                    for name,first,last in [('HK 1',6,45),('HK 2',6,45),('Tổng kết',7,46)]+[(f'T{m:02}',8,47) for m in range(1,13)]:
                        worker.rows_for_codes(book.Worksheets(name),first,last,[values['code']])
                elif operation == 'enrollment':
                    sheet=book.Worksheets('Danh Sách')
                    row=worker.rows_for_codes(sheet,7,46,[values['code']])[values['code']]
                    with worker.editable_sheet(sheet):
                        cell=sheet.Cells(row,9);cell.NumberFormat='dd/mm/yyyy'
                        worker.set_cell(cell,profile_date(values['enrolledFrom']),checks)
                elif operation == 'supplemental':
                    sheet=book.Worksheets('Tổng kết')
                    row=worker.rows_for_codes(sheet,7,46,[values['code']])[values['code']]
                    with worker.editable_sheet(sheet):
                        cell=sheet.Cells(row,15)
                        if cell.HasFormula:raise ValueError('Cột Đi Lễ Bù có công thức. Chưa ghi đè.')
                        current=cell.Value or 0
                        if current!=values['before']:raise ValueError('Số lễ bổ sung đã thay đổi. Xem trước lại.')
                        worker.set_cell(cell,values['after'],checks)
                elif operation == 'configuration':
                    option=book.Worksheets('OPTION')
                    with worker.editable_sheet(option):
                        for ref,value in values['optionCells'].items():
                            if option.Range(ref).HasFormula:raise ValueError('Không sửa ô cấu hình có công thức: '+ref)
                            worker.set_cell(option.Range(ref),value,checks)
                    total=book.Worksheets('Tổng kết')
                    with worker.editable_sheet(total):
                        for ref,value in values['thresholdCells'].items():
                            if total.Range(ref).HasFormula:raise ValueError('Không sửa ngưỡng có công thức.')
                            worker.set_cell(total.Range(ref),value,checks)
                    app.Calculate()
                    targets={}
                    for m in range(1,13):
                        sheet=book.Worksheets(f'T{m:02}')
                        headers=sheet.Range('E7:AB7').Value[0]
                        for activity,cols in {'mass':range(5,19),'early':range(19,24),'lesson':range(24,29)}.items():
                            for col in cols:
                                date=headers[col-5]
                                if isinstance(date,datetime):targets[(date.date().isoformat(),activity)]=(sheet,col)
                    # Remap by actual date, activity and code when columns move.
                    oldmarks=[(key,mark) for key,mark in self.catalog.marks.items()
                              if self.catalog.students[key.rsplit('|',1)[-1]]['classId']==class_id]
                    for key,_ in oldmarks:
                        d,a,_=key.split('|')
                        if (d,a) not in targets:raise ValueError('Thay lịch sẽ mất chuyên cần đã ghi ngày '+d)
                    for m in range(1,13):
                        sheet=book.Worksheets(f'T{m:02}')
                        grid=sheet.Range('E8:AB47')
                        before=grid.Formula
                        cleared=tuple(tuple(None if v in ('X','P','O') else v for v in row) for row in before)
                        if cleared!=before:
                            with worker.editable_sheet(sheet):grid.Formula=cleared
                    for key,mark in oldmarks:
                        d,a,code=key.split('|');sheet,col=targets[(d,a)]
                        row=worker.rows_for_codes(sheet,8,47,[code])[code]
                        with worker.editable_sheet(sheet):
                            if sheet.Cells(row,col).HasFormula:raise ValueError('Ô chuyên cần có công thức. Chưa di chuyển.')
                            worker.set_cell(sheet.Cells(row,col),mark['status'],checks)
                elif operation == 'note':
                    sheet=book.Worksheets('Ghi Chú');cell=sheet.Range(values['cell'])
                    if cell.HasFormula or cell.Value not in (values['before'],None if values['before']=='' else values['before']):
                        raise ValueError('Ghi chú đã thay đổi hoặc là ô công thức. Đọc lại trước khi lưu.')
                    if cell.MergeCells and cell.MergeArea.Cells(1,1).Address!=cell.Address:
                        raise ValueError('Chỉ sửa ô đầu của vùng ghi chú gộp.')
                    with worker.editable_sheet(sheet):
                        cell.NumberFormat='@';cell.WrapText=True
                        worker.set_cell(cell,values['content'] or None,checks)
                elif operation == 'scratch':
                    sheet=book.Worksheets('DiemDanhAuto')
                    with worker.editable_sheet(sheet):
                        source=sheet.Range('CL4:CM503').Formula
                        for ref in ('K4:L503','R4:S503','Y4:Z503'):
                            if values['mode']=='restore':sheet.Range(ref).Formula=source
                            else:sheet.Range(ref).ClearContents()
                else:raise ValueError('Thao tác Excel chưa được hỗ trợ.')
            # Read the saved, recalculated copy; the original is still untouched.
            copied.refresh()
            result=copied.classes[class_id]
            if operation=='student-add' and values['code'] not in copied.students:
                raise ValueError('Sổ sau khi thêm chưa đọc được mã mới.')
            if macro_signature(target)[0]!=self.catalog.trusted_signature:raise ValueError('VBA sau cập nhật không khớp mẫu.')
            return target.read_bytes(),result['calendar']
