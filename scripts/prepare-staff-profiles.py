"""Extract private staff contact details. Never place this output under src/dist."""
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from zipfile import ZipFile
from lxml import etree

NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def text(cell):return ' '.join(' '.join(cell.xpath('.//w:t/text()',namespaces=NS)).split())
def clean_name(value):return re.sub(r'^(?:Anh|Chị|Dì)\s+','',' '.join(value.replace('(HKII)','').split()))
def key(value):
    value=unicodedata.normalize('NFD',clean_name(value)).casefold().replace('đ','d')
    return re.sub(r'[^a-z0-9]','',value)
def extract(source,plan):
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=plan['sourceSha256']:raise ValueError('Tài liệu không khớp bản phân công đã duyệt.')
    sisters={c['teachers']['souer'] for c in plan['classes'] if c['teachers']['souer']}
    active={n for c in plan['classes'] for n in c['teachers'].values() if n}
    future={t['name'] for c in plan['classes'] for t in c['futureTeachers']}
    records={name:{'full_name':name,'phone':'','birth_year':None,'is_sister':name in sisters,'future':name in future and name not in active} for name in active|future}
    with ZipFile(source) as archive:root=etree.fromstring(archive.read('word/document.xml'))
    tables=root.xpath('//w:body/w:tbl',namespaces=NS)
    source_classes={c['sourceClass'] for c in plan['classes']}
    for table in tables:
        rows=table.findall('w:tr',NS);header=[text(c) for c in rows[0].findall('w:tc',NS)]
        if 'Giáo Lý viên' in header and 'Năm sinh' in header:
            for row in rows[1:]:
                cells=row.findall('w:tc',NS)
                if len(cells)<6 or text(cells[2]) not in source_classes:continue
                names=[clean_name(''.join(p.xpath('.//w:t/text()',namespaces=NS))) for p in cells[4].findall('w:p',NS)]
                names=[n for n in names if n and n not in sisters]
                year_text=' '.join(''.join(p.xpath('.//w:t/text()',namespaces=NS)) for p in cells[5].findall('w:p',NS))
                years=re.findall(r'\b(?:19|20)\d{2}\b',year_text)
                if len(names)!=len(years):raise ValueError('Năm sinh chưa khớp số GLV: '+text(cells[2]))
                for name,year in zip(names,years):
                    if name not in records:raise ValueError('Tên chưa có trong phân công: '+name)
                    records[name]['birth_year']=int(year)
        if 'ĐIỆN THOẠI' not in header:continue
        glv_table='HỌ VÀ TÊN' in header
        sister_table='TÊN THÁNH – HỌ VÀ TÊN' in header
        if not (glv_table or sister_table):continue
        for row in rows[1:]:
            cells=row.findall('w:tc',NS)
            if len(cells)<4:continue
            raw=text(cells[2] if glv_table else cells[1])
            if sister_table and not raw.startswith('Dì '):continue
            matches=[name for name in records if key(name).endswith(key(raw))] if key(raw) else []
            if len(matches)!=1:raise ValueError('Không ghép được duy nhất thông tin liên hệ: '+raw)
            phone=re.sub(r'\D','',text(cells[-1]))
            if not re.fullmatch(r'0\d{9}',phone):raise ValueError('Kiểm tra số điện thoại: '+raw)
            record=records[matches[0]]
            if record['phone'] and record['phone']!=phone:raise ValueError('Số điện thoại mâu thuẫn: '+raw)
            record['phone']=phone
    if len(sisters)!=5 or sum(bool(r['phone']) for r in records.values())!=43 or sum(bool(r['birth_year']) for r in records.values())!=38:raise ValueError('Chưa trích đủ 5 Sr, 43 số điện thoại và 38 năm sinh.')
    return {'source':source.name,'sourceSha256':digest,'year':plan['year'],'profiles':sorted(records.values(),key=lambda p:p['full_name'])}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--plan',type=Path,default=Path('src/data/staff-plan-2026-2027.json'));parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve();project=Path(__file__).resolve().parents[1]
    if output.is_relative_to(project/'src') or output.is_relative_to(project/'dist'):raise ValueError('Thông tin liên hệ phải lưu ngoài mã nguồn và thư mục web.')
    result=extract(args.source,json.loads(args.plan.read_text(encoding='utf-8')));output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared 43 private profiles: 5 Sr, 43 phone numbers, 38 birth years; no full birth dates inferred.')
