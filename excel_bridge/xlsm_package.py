"""Patch worksheet inputs/cached results while preserving every other ZIP member."""
import hashlib
import io
import math
import posixpath
import zipfile

from lxml import etree
from openpyxl.utils.cell import coordinate_to_tuple

from formula_engine import ExcelError

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q=lambda name:f'{{{NS}}}{name}'


def vba_hashes(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {name:hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist()
                if 'vba' in name.lower() and name.lower().endswith('.bin')}


def sheet_paths(archive):
    workbook=etree.fromstring(archive.read('xl/workbook.xml'))
    rels=etree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    paths={r.get('Id'):posixpath.normpath('xl/'+r.get('Target')) if not r.get('Target').startswith('/')
           else r.get('Target').lstrip('/') for r in rels}
    return {s.get('name'):paths[s.get(f'{{{REL}}}id')] for s in workbook.find(Q('sheets'))}


def _cached_value(cell):
    v=cell.find(Q('v'))
    if v is None or v.text is None:return None
    if cell.get('t') in ('str','e'):return v.text
    if cell.get('t')=='b':return v.text=='1'
    try:return float(v.text)
    except ValueError:return v.text


def _same(a,b):
    if isinstance(b,ExcelError):return a==b.code
    if a in (None,'') and b in (None,''):return True
    if type(a) is bool or type(b) is bool:return type(a) is type(b) and a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isclose(a,b,rel_tol=1e-14,abs_tol=1e-14)
    return a==b


def patch_package(original,inputs,caches):
    by_sheet={}
    for (sheet,ref),value in inputs.items():by_sheet.setdefault(sheet,{})[ref]=(value,False)
    for (sheet,ref),value in caches.items():
        if (sheet,ref) not in inputs:by_sheet.setdefault(sheet,{})[ref]=(value,True)
    replacements={}
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        paths=sheet_paths(archive)
        for name,updates in by_sheet.items():
            path=paths[name]
            root=etree.fromstring(archive.read(path))
            data=root.find(Q('sheetData'))
            rows={int(row.get('r')):row for row in data}
            cells={c.get('r'):c for row in data for c in row if c.tag==Q('c')}
            changed=False
            for ref,(value,is_cache) in updates.items():
                cell=cells.get(ref)
                if is_cache:
                    if cell is None or cell.find(Q('f')) is None:continue
                    if _same(_cached_value(cell),value):continue
                if cell is None:
                    rowno,colno=coordinate_to_tuple(ref)
                    row=rows.get(rowno)
                    if row is None:
                        row=etree.Element(Q('row'),r=str(rowno))
                        index=next((i for i,r in enumerate(data) if int(r.get('r'))>rowno),len(data))
                        data.insert(index,row);rows[rowno]=row
                    cell=etree.Element(Q('c'),r=ref)
                    index=next((i for i,c in enumerate(row) if c.tag==Q('c') and coordinate_to_tuple(c.get('r'))[1]>colno),len(row))
                    row.insert(index,cell);cells[ref]=cell
                if not is_cache and cell.find(Q('f')) is not None:
                    raise ValueError(f'Không ghi đè công thức tại {name}!{ref}.')
                for child in list(cell):
                    if child.tag in (Q('v'),Q('is')):cell.remove(child)
                cell.attrib.pop('t',None)
                if isinstance(value,ExcelError):
                    cell.set('t','e');etree.SubElement(cell,Q('v')).text=value.code
                elif isinstance(value,bool):
                    cell.set('t','b');etree.SubElement(cell,Q('v')).text='1' if value else '0'
                elif isinstance(value,(int,float)):
                    if not math.isfinite(value):raise ValueError('Kết quả tính không hữu hạn.')
                    etree.SubElement(cell,Q('v')).text=format(value,'.17g')
                elif value not in (None,''):
                    if is_cache:
                        cell.set('t','str');etree.SubElement(cell,Q('v')).text=str(value)
                    else:
                        cell.set('t','inlineStr');t=etree.SubElement(etree.SubElement(cell,Q('is')),Q('t'))
                        t.text=str(value);t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                changed=True
            if changed:replacements[path]=etree.tostring(root,encoding='utf-8')
        if not replacements:return original
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as z:
            z.comment=archive.comment
            for info in archive.infolist():z.writestr(info,replacements.get(info.filename,archive.read(info.filename)))
    result=output.getvalue()
    if not vba_hashes(original) or vba_hashes(result)!=vba_hashes(original):
        raise ValueError('Phần VBA không được bảo toàn. Chưa xuất file.')
    return result
