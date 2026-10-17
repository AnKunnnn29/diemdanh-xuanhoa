"""Extract only class staffing from the supplied Word plan; no contact details."""
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from zipfile import ZipFile
from lxml import etree

NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def clean(text):
    return ' '.join(unicodedata.normalize('NFC',text).split())
def extract(source):
    with ZipFile(source) as archive:
        root=etree.fromstring(archive.read('word/document.xml'))
    tables=root.xpath('//w:body/w:tbl',namespaces=NS)
    matches=[t for t in tables if 'Giáo Lý viên' in clean(' '.join(t.find('w:tr',NS).xpath('.//w:t/text()',namespaces=NS))) and 'Địa điểm' in clean(' '.join(t.find('w:tr',NS).xpath('.//w:t/text()',namespaces=NS)))]
    if len(matches)!=1:raise ValueError('Không xác định được duy nhất bảng phân công GLV.')
    classes=[]
    for row in matches[0].findall('w:tr',NS)[1:]:
        cells=row.findall('w:tc',NS)
        if len(cells)<5:continue
        label=clean(' '.join(cells[2].xpath('.//w:t/text()',namespaces=NS)))
        if not label:continue
        if label!='DB GLV' and not clean(''.join(cells[0].xpath('.//w:t/text()',namespaces=NS))).isdigit():continue
        location=clean(' '.join(cells[3].xpath('.//w:t/text()',namespaces=NS)))
        names=[clean(''.join(p.xpath('.//w:t/text()',namespaces=NS))) for p in cells[4].findall('w:p',NS)]
        names=[n for n in names if n]
        if label=='DB GLV':targets=['DB GLV 1 A','DB GLV 2 A']
        else:
            match=re.fullmatch(r'(Chiên|Ấu|Thiếu|Nghĩa|Hiệp sĩ) ([12])([AB])',label)
            if not match:raise ValueError('Lớp chưa có ánh xạ: '+label)
            level={'Chiên':'Chiên Con','Ấu':'Ấu Nhi','Thiếu':'Thiếu Nhi','Nghĩa':'Nghĩa Sĩ','Hiệp sĩ':'Hiệp Sĩ'}[match[1]]
            targets=[f'{level} {match[2]} {match[3]}']
        teachers=dict.fromkeys(('glv1','glv2','glv3','souer'),'');future=[];slot=0
        for original in names:
            sister=bool(re.match(r'^Dì\s',original))
            name=re.sub(r'^(Anh|Chị|Dì)\s+','',original)
            if '(HKII)' in name:
                future.append({'name':clean(name.replace('(HKII)','')),'term':'HKII','note':'Phụ trách HKII; chưa cấp quyền lớp trong HKI.'})
                continue
            if sister:
                if teachers['souer']:raise ValueError('Nhiều Dì trong một lớp.')
                teachers['souer']=name
            else:
                slot+=1
                if slot>3:raise ValueError('Quá ba GLV trong lớp.')
                teachers[f'glv{slot}']=name
        for name in targets:classes.append({'name':name,'sourceClass':label,'location':location,'teachers':teachers.copy(),'futureTeachers':future})
    if len(classes)!=20 or len({c['name'] for c in classes})!=20:raise ValueError('Bảng phân công phải khớp 20 lớp.')
    return {'year':'2026-2027','source':source.name,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'topic':'Yêu thương như Chúa Giêsu','classes':classes}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    plan=extract(args.source);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Prepared {len(plan['classes'])} classes; {len({name for c in plan['classes'] for name in c['teachers'].values() if name})} active staff; {sum(len(c['futureTeachers']) for c in plan['classes'])} future assignment.")
