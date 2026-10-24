"""Patch worksheet inputs/cached results while preserving every other ZIP member."""
import hashlib
import io
import math
import posixpath
import copy
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from lxml import etree
from openpyxl.utils.cell import coordinate_to_tuple

from .formula_engine import ExcelError
from .security import CloudError

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q=lambda name:f'{{{NS}}}{name}'

# Sheet thuộc mẫu sổ đã kiểm chứng; sheet khác không đi vào file xuất của GLV.
TEMPLATE_SHEET_TITLES=frozenset({'OPTION','Bia','Danh Sách','Lý Lịch','DiemDanhAuto','HK 1','HK 2','Tổng kết','HD','Ghi Chú'})|{f'T{month:02d}' for month in range(1,13)}

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


def _relationship_path(source):
    return posixpath.join(posixpath.dirname(source),'_rels',posixpath.basename(source)+'.rels') if source else '_rels/.rels'


def _relationship_source(path):
    if path=='_rels/.rels':return ''
    return posixpath.join(posixpath.dirname(posixpath.dirname(path)),posixpath.basename(path)[:-5])


def _relationship_target(source, relationship):
    if relationship.get('TargetMode')=='External':return None
    uri=urlsplit(relationship.get('Target',''))
    path=unquote(uri.path)
    if uri.scheme or uri.netloc or not path or '\\' in path:
        raise CloudError('Thành phần sổ mẫu không hợp lệ. Admin kiểm lại trước khi xuất.',409,'invalid_export_component')
    resolved=posixpath.normpath(path.lstrip('/') if path.startswith('/') else posixpath.join(posixpath.dirname(source),path))
    if resolved in ('','.','..') or resolved.startswith('../'):
        raise CloudError('Đường dẫn thành phần sổ mẫu không hợp lệ.',409,'invalid_export_component')
    return resolved


def _normalized_text(value):
    return ' '.join(unicodedata.normalize('NFKC',str(value)).casefold().split())


def _profile_constraints(foreign_profiles, own_profiles):
    """Additional rejection guard, not a substitute for rebuilding free-text areas."""
    def strings(value):
        if isinstance(value,str):yield value
        elif isinstance(value,dict):
            for item in value.values():yield from strings(item)
        elif isinstance(value,(list,tuple)):
            for item in value:yield from strings(item)
    def values(people):
        texts=set();phones=set()
        for person in people:
            for key in ('fullName','parents','address','phone'):
                for value in strings(person.get(key,'')):
                    text=_normalized_text(value)
                    if key!='phone' and len(text)>=6:texts.add(text)
                    if key=='phone':
                        for number in re.findall(r'\+?\d[\d ().-]{6,}\d',value):
                            digits=re.sub(r'\D','',number)
                            if 8<=len(digits)<=15:
                                phones.add(digits)
                                if len(digits)==10 and digits.startswith('0'):phones.update((digits[1:],'84'+digits[1:]))
                                if len(digits)==11 and digits.startswith('84'):phones.update((digits[2:],'0'+digits[2:]))
        return texts,phones
    other_texts,other_phones=values(foreign_profiles)
    own_texts,own_phones=values(own_profiles)
    return other_texts-own_texts,other_phones-own_phones


def _cell_values(root, shared):
    for cell in root.iter(Q('c')):
        value=cell.find(Q('v'))
        if value is not None and value.text:
            yield shared.get(int(value.text),'') if cell.get('t')=='s' else value.text
        yield from (text.text or '' for text in cell.iter(Q('t')))
        formula=cell.find(Q('f'))
        if formula is not None and formula.text:yield formula.text


def _notes_sheet(root, notes):
    # Keep layout/styles and VBA codeName, but no source text, formulas or attachments.
    safe=etree.Element(Q('worksheet'),nsmap=root.nsmap)
    for tag in ('sheetPr','dimension','sheetViews','sheetFormatPr','cols'):
        item=root.find(Q(tag))
        if item is not None:safe.append(copy.deepcopy(item))
    dimension=safe.find(Q('dimension'))
    if dimension is not None:safe.remove(dimension)
    data=etree.SubElement(safe,Q('sheetData'))
    styles={cell.get('r'):cell.get('s') for cell in root.iter(Q('c'))}
    rows={}
    for ref,value in sorted(notes.items(),key=lambda pair:coordinate_to_tuple(pair[0])):
        rowno,_=coordinate_to_tuple(ref)
        row=rows.get(rowno)
        if row is None:row=etree.SubElement(data,Q('row'),r=str(rowno));rows[rowno]=row
        cell=etree.SubElement(row,Q('c'),r=ref,t='inlineStr')
        if styles.get(ref):cell.set('s',styles[ref])
        text=etree.SubElement(etree.SubElement(cell,Q('is')),Q('t'))
        text.text=str(value);text.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    for tag in ('sheetProtection','mergeCells','printOptions','pageMargins','pageSetup'):
        item=root.find(Q(tag))
        if item is not None:
            item=copy.deepcopy(item)
            for key in list(item.attrib):
                if key.startswith('{'+REL+'}'):del item.attrib[key]
            safe.append(item)
    return safe


def restrict_export_to_template(package, foreign_codes, managed_titles=TEMPLATE_SHEET_TITLES,
                                *, trusted_notes=None, foreign_profiles=(), own_profiles=()):
    """Strip unverified source areas and owned ZIP parts; reject mixed-class data."""
    foreign=sorted({str(code).strip().upper() for code in foreign_codes if str(code).strip()},key=len,reverse=True)
    codes=re.compile(r'(?<![A-Z0-9])(?:'+'|'.join(re.escape(code) for code in foreign)+r')(?![A-Z0-9])',re.I) if foreign else None
    private_texts,private_phones=_profile_constraints(foreign_profiles,own_profiles)
    def reject(values,title):
        for value in values:
            text=_normalized_text(value)
            if codes and codes.search(unicodedata.normalize('NFKC',str(value))):
                raise CloudError(f'Sheet mẫu "{title}" chứa mã thiếu nhi ngoài lớp. Admin kiểm lại dữ liệu trước khi xuất.',409,'foreign_data_in_template')
            if any(item in text for item in private_texts) or any(phone in re.sub(r'\D','',str(value)) for phone in private_phones):
                raise CloudError('Sổ mẫu chứa thông tin ngoài lớp. Admin kiểm lại dữ liệu trước khi xuất.',409,'foreign_data_in_template')
    replacements={};removals=set();stripped_sources=set()
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        names=set(archive.namelist());paths=sheet_paths(archive)
        relationships={name:etree.fromstring(archive.read(name)) for name in names if name.endswith('.rels')}
        targets={name:[_relationship_target(_relationship_source(name),rel) for rel in root] for name,root in relationships.items()}
        shared={}
        if 'xl/sharedStrings.xml' in names:
            shared={i:''.join(text.text or '' for text in item.iter(Q('t'))) for i,item in enumerate(etree.fromstring(archive.read('xl/sharedStrings.xml')))}
        for title,path in paths.items():
            root=etree.fromstring(archive.read(path))
            if title in managed_titles:
                values=list(_cell_values(root,shared))
                # Codes in a template sheet require review even when in a free-text region.
                if codes:
                    reject((value for value in values if codes.search(unicodedata.normalize('NFKC',str(value)))),title)
                if title!='Ghi Chú':reject(values,title);continue
                notes=trusted_notes or {};reject(notes.values(),title)
                safe=_notes_sheet(root,notes)
            else:
                safe=etree.Element(Q('worksheet'),nsmap={None:NS})
                props=root.find(Q('sheetPr'))
                if props is not None and props.get('codeName'):
                    etree.SubElement(safe,Q('sheetPr'),codeName=props.get('codeName'))
                etree.SubElement(safe,Q('sheetData'))
            replacements[path]=etree.tostring(safe,encoding='utf-8',xml_declaration=True)
            stripped_sources.add(path)

        # Walk from each unverified sheet through drawing -> media/embedded object, not
        # only its first relationship. Resolve every Target from its own source part.
        pending=[]
        for source in stripped_sources:
            rels_path=_relationship_path(source)
            if rels_path in relationships:
                removals.add(rels_path);pending.extend(target for target in targets[rels_path] if target)
        # Comments and their authors are not part of an authorized profile export.
        pending.extend(name for name in names if re.match(r'xl/(?:comments(?:/|\d)|threadedComments/|persons/)',name))
        protected=set(paths.values())|{'[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels','xl/styles.xml','xl/sharedStrings.xml'}|set(vba_hashes(package))
        while pending:
            part=pending.pop()
            if part in removals:continue
            if part in protected:
                raise CloudError('Thành phần sổ chưa được kiểm chứng. Admin kiểm lại trước khi xuất.',409,'unsupported_export_component')
            if part not in names:continue
            removals.add(part)
            rels_path=_relationship_path(part)
            if rels_path in relationships:
                removals.add(rels_path);pending.extend(target for target in targets[rels_path] if target)

        # Refuse shared non-comment attachments rather than breaking a trusted sheet
        # or retaining private bytes because another worksheet still references them.
        for rels_path,refs in targets.items():
            source=_relationship_source(rels_path)
            if rels_path in removals or source in stripped_sources:continue
            for rel,target in zip(relationships[rels_path],refs):
                if target in removals and not any(kind in rel.get('Type','').lower() for kind in ('comment','person')):
                    raise CloudError('Phần đính kèm dùng chung chưa được kiểm chứng. Admin kiểm lại sổ.',409,'unsupported_export_component')
        if 'xl/calcChain.xml' in names:removals.add('xl/calcChain.xml')
        for rels_path,root in relationships.items():
            if rels_path in removals:continue
            removed_ids=set()
            for rel,target in list(zip(list(root),targets[rels_path])):
                if target in removals:removed_ids.add(rel.get('Id'));root.remove(rel)
            if not removed_ids:continue
            replacements[rels_path]=etree.tostring(root,encoding='utf-8')
            source=_relationship_source(rels_path)
            if source in names and source.endswith('.xml'):
                xml=etree.fromstring(replacements.get(source,archive.read(source)))
                for element in list(xml.iter()):
                    if any(value in removed_ids for key,value in element.attrib.items() if key.startswith('{'+REL+'}')):
                        parent=element.getparent()
                        if parent is not None:parent.remove(element)
                replacements[source]=etree.tostring(xml,encoding='utf-8')

        # A deleted relationship must not leave recoverable orphan parts in the ZIP.
        # VBA bytes remain opaque and unchanged, including synthetic test templates
        # whose vbaProject.bin is deliberately not linked from workbook.xml.rels.
        reachable={'[Content_Types].xml'};pending=['',*vba_hashes(package)];visited=set()
        while pending:
            source=pending.pop()
            if source in visited:continue
            visited.add(source)
            if source:reachable.add(source)
            rels_path=_relationship_path(source)
            if rels_path not in relationships or rels_path in removals:continue
            reachable.add(rels_path)
            for target in targets[rels_path]:
                if target and target not in removals and target in names:pending.append(target)
        removals.update(name for name in names if name not in reachable)
        unsupported=('customXml/','xl/embeddings/','xl/pivotCache/','xl/externalLinks/','xl/queryTables/')
        if any(name not in removals and (name.startswith(unsupported) or name=='xl/connections.xml') for name in names):
            raise CloudError('Sổ chứa nguồn dữ liệu hoặc đối tượng chưa được kiểm chứng. Admin kiểm lại trước khi xuất.',409,'unsupported_export_component')

        # Source author, free-form properties and old identity metadata are not
        # classroom data. remove_unused_identity_data adds only current-class
        # identity properties afterwards from the authorized database records.
        for name in ('docProps/core.xml','docProps/app.xml','docProps/custom.xml'):
            if name in names and name not in removals:
                original=etree.fromstring(archive.read(name))
                replacements[name]=etree.tostring(etree.Element(original.tag,nsmap=original.nsmap),encoding='utf-8')
        types=etree.fromstring(archive.read('[Content_Types].xml'))
        for item in list(types):
            if item.get('PartName','').lstrip('/') in removals:types.remove(item)
        replacements['[Content_Types].xml']=etree.tostring(types,encoding='utf-8')
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as target:
            for info in archive.infolist():
                if info.filename in removals:continue
                info=copy.copy(info);info.comment=b''
                target.writestr(info,replacements.get(info.filename,archive.read(info.filename)))
        result=output.getvalue()
        if vba_hashes(package)!=vba_hashes(result):
            raise CloudError('Phần VBA không được bảo toàn. Chưa xuất file.',500,'vba_changed')
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
