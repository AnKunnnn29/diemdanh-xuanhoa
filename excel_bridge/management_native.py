"""Build class workbooks in isolation; never edit the supplied template in place."""
import secrets
import shutil
import tempfile
from pathlib import Path
from catalog import Catalog, macro_signature


def class_package(engine, class_id, name, create=False):
    source = engine.catalog.classes[class_id]['path']
    identifier = secrets.token_hex(8) if create else class_id
    with tempfile.TemporaryDirectory(prefix='.class-stage-', dir=source.parent) as folder:
        path = Path(folder) / source.name
        shutil.copy2(source, path)
        catalog = Catalog(folder, Path(folder)/'state', engine.catalog.trusted_signature)
        worker = object.__new__(type(engine))
        worker.catalog, worker.app = catalog, engine.excel()
        with worker.staged_book(class_id) as (app, book, _, checks):
            roster = book.Worksheets('Danh Sách')
            words = name.rsplit(' ', 1)
            with worker.editable_sheet(roster):
                roster.Range('B2').NumberFormat='@'
                roster.Range('E2').NumberFormat='@'
                worker.set_cell(roster.Range('B2'), words[0], checks)
                worker.set_cell(roster.Range('E2'), words[1], checks)
                if create:
                    for ref in ('B3', 'E3', 'B4', 'E4'):
                        worker.set_cell(roster.Range(ref), None, checks)
            props = book.CustomDocumentProperties
            # Stable class identity keeps assignments and historical references on rename.
            import pythoncom
            import win32com.client
            existing = None
            for index in range(1, props.Count+1):
                item = win32com.client.Dispatch(props._oleobj_.Invoke(0,0,pythoncom.DISPATCH_PROPERTYGET,True,index))
                if item.Name == 'XH_ClassId': existing = item
            if existing is None: props.Add('XH_ClassId',False,4,identifier)
            else: existing.Value = identifier
            if create:
                spans = {'Danh Sách':(7,46,10), 'Lý Lịch':(5,46,11), 'HK 1':(6,45,28),
                         'HK 2':(6,45,28), 'Tổng kết':(7,46,4)}
                spans.update({f'T{m:02}':(8,47,28) for m in range(1,13)})
                for sheet_name,(first,last,end) in spans.items():
                    sheet = book.Worksheets(sheet_name)
                    with worker.editable_sheet(sheet):
                        cells = sheet.Range(sheet.Cells(first,2),sheet.Cells(last,end))
                        # Clear constants only; formulas and VBA remain intact.
                        try: cells.SpecialCells(2).ClearContents()
                        except pythoncom.com_error as error:
                            if not error.excepinfo or error.excepinfo[5] != -2146827284: raise
                sheet = book.Worksheets('Tổng kết')
                with worker.editable_sheet(sheet):
                    for row in range(7,47):
                        cell = sheet.Cells(row,15)
                        if not cell.HasFormula: worker.set_cell(cell,None,checks)
                # Remove per-student identity metadata from the copied class.
                for index in range(props.Count,0,-1):
                    item = win32com.client.Dispatch(props._oleobj_.Invoke(0,0,pythoncom.DISPATCH_PROPERTYGET,True,index))
                    if item.Name.startswith('XH_Saint_'): item.Delete()
                sheet = book.Worksheets('DiemDanhAuto')
                with worker.editable_sheet(sheet):
                    for ref in ('K4:L503','R4:S503','Y4:Z503'): sheet.Range(ref).ClearContents()
                sheet = book.Worksheets('Ghi Chú')
                with worker.editable_sheet(sheet):
                    try: sheet.UsedRange.SpecialCells(2,2).ClearContents()
                    except pythoncom.com_error as error:
                        if not error.excepinfo or error.excepinfo[5] != -2146827284: raise
            app.Calculate()
        verified = Catalog(folder,Path(folder)/'verify',engine.catalog.trusted_signature)
        if identifier not in verified.classes or verified.classes[identifier]['name'] != name:
            raise ValueError('Tên hoặc mã lớp chưa được tính đúng trong Excel.')
        if create and (verified.students or verified.marks):
            raise ValueError('Bản mẫu lớp mới còn dữ liệu cũ; chưa tạo lớp.')
        if create:
            for semester in (1,2):
                if verified.read_grades(identifier,semester)['students']:
                    raise ValueError('Lớp mới còn danh sách điểm cũ.')
        if macro_signature(path)[0] != engine.catalog.trusted_signature:
            raise ValueError('Bản lớp mới không giữ nguyên VBA.')
        return identifier, path.read_bytes()
