"""Patch worksheet inputs/cached results while preserving every other ZIP member."""
import hashlib
import io
import math
import posixpath
import zipfile
from dataclasses import dataclass

from lxml import etree
from openpyxl.utils.cell import coordinate_to_tuple

from .formula_engine import ExcelError

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q=lambda name:f'{{{NS}}}{name}'

@dataclass(frozen=True)
class TemplateCell:
    """Only trusted template scratch cells may replace formulas."""
    value: object


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
                template_cell = isinstance(value,TemplateCell)
                if not is_cache and cell.find(Q('f')) is not None and not template_cell:
                    raise ValueError(f'Không ghi đè công thức tại {name}!{ref}.')
                for child in list(cell):
                    if child.tag in (Q('v'),Q('is')) or template_cell and child.tag == Q('f'):cell.remove(child)
                cell.attrib.pop('t',None)
                if template_cell:
                    value = value.value
                    if isinstance(value,str) and value.startswith('='):
                        etree.SubElement(cell,Q('f')).text=value[1:]
                        changed=True
                        continue
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


def remove_unused_identity_data(package, current_saints, class_id):
    """Remove orphan strings/custom saint metadata after roster moves or clones."""
    replacements = {}
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        paths = [name for name in archive.namelist() if name.startswith('xl/worksheets/') and name.endswith('.xml')]
        if 'xl/sharedStrings.xml' in archive.namelist():
            sheets = {name:etree.fromstring(archive.read(name)) for name in paths}
            references = [c for root in sheets.values() for c in root.iter(Q('c')) if c.get('t') == 's']
            used = sorted({int(c.find(Q('v')).text) for c in references})
            shared = etree.fromstring(archive.read('xl/sharedStrings.xml'))
            original = list(shared)
            mapping = {old:new for new,old in enumerate(used)}
            for child in list(shared):
                shared.remove(child)
            for old in used:
                shared.append(original[old])
            shared.set('uniqueCount',str(len(used)))
            shared.set('count',str(len(references)))
            for c in references:
                c.find(Q('v')).text = str(mapping[int(c.find(Q('v')).text)])
            replacements.update({name:etree.tostring(root,encoding='utf-8') for name,root in sheets.items()})
            replacements['xl/sharedStrings.xml'] = etree.tostring(shared,encoding='utf-8')
        cp = 'http://schemas.openxmlformats.org/officeDocument/2006/custom-properties'
        vt = 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
        if 'docProps/custom.xml' in archive.namelist():
            root = etree.fromstring(archive.read('docProps/custom.xml'))
        else:
            root = etree.Element('{'+cp+'}Properties',nsmap={None:cp,'vt':vt})
            types = etree.fromstring(archive.read('[Content_Types].xml'))
            ct = 'http://schemas.openxmlformats.org/package/2006/content-types'
            etree.SubElement(types,'{'+ct+'}Override',PartName='/docProps/custom.xml',
                ContentType='application/vnd.openxmlformats-officedocument.custom-properties+xml')
            replacements['[Content_Types].xml'] = etree.tostring(types,encoding='utf-8')
            rels = etree.fromstring(archive.read('_rels/.rels'))
            rel = 'http://schemas.openxmlformats.org/package/2006/relationships'
            existing = {r.get('Id') for r in rels}
            number = 1
            while 'rIdXHCustom'+str(number) in existing:
                number += 1
            etree.SubElement(rels,'{'+rel+'}Relationship',Id='rIdXHCustom'+str(number),Target='docProps/custom.xml',
                Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties')
            replacements['_rels/.rels'] = etree.tostring(rels,encoding='utf-8')
        for prop in list(root):
            name = prop.get('name','')
            if name.startswith('XH_Saint_') and name[len('XH_Saint_'):] not in current_saints:
                root.remove(prop)
        values = {'XH_ClassId':class_id, **{'XH_Saint_'+code:saint or '__XH_EMPTY__' for code,saint in current_saints.items()}}
        for name,value in values.items():
            prop = next((p for p in root if p.get('name') == name),None)
            if prop is None:
                pid = max((int(p.get('pid','1')) for p in root),default=1)+1
                prop = etree.SubElement(root,'{'+cp+'}property',fmtid='{D5CDD505-2E9C-101B-9397-08002B2CF9AE}',pid=str(pid),name=name)
            for child in list(prop):
                prop.remove(child)
            etree.SubElement(prop,'{'+vt+'}lpwstr').text = str(value)
        replacements['docProps/custom.xml'] = etree.tostring(root,encoding='utf-8')
        output = io.BytesIO()
        with zipfile.ZipFile(output,'w') as target:
            target.comment = archive.comment
            for info in archive.infolist():
                target.writestr(info,replacements.get(info.filename,archive.read(info.filename)))
            for name,content in replacements.items():
                if name not in archive.namelist():
                    target.writestr(name,content)
        return output.getvalue()
