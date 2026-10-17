"""Import real class grades to the selected local/MySQL repository; no Excel writes."""
import argparse
from pathlib import Path

from catalog import Catalog
from portable_grades import PortableGrades,sha

TRUSTED_VBA='eb99a820b87a4277893f5e867dae51229a02a3f82546fa99cf1faa3b7a9b00ea'


def import_real_grades(root,state_dir):
    state_dir=Path(state_dir);state_dir.mkdir(parents=True,exist_ok=True)
    catalog=Catalog(root,state_dir,TRUSTED_VBA)
    service=PortableGrades(catalog,state_dir/'attendance.sqlite3')
    records=[];fingerprints={}
    for info in catalog.classes.values():
        package=info['path'].read_bytes();revision=sha(package);fingerprints[info['path']]=revision
        engine=service.model(package);engine.grade_outputs()
        book={str(s):service.response(engine,info,s,revision) for s in (1,2,3)}
        records.append((service.key(info['id']),revision,book))
    if any(sha(path.read_bytes())!=revision for path,revision in fingerprints.items()):
        raise ValueError('Excel đã thay đổi trong lúc nhập. Chưa ghi dữ liệu vào database.')
    return {'classes':len(records),'imported':service.repository.import_books(records),
            'students':len(catalog.students),'storage':service.status()}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--state-dir',type=Path,required=True)
    args=parser.parse_args()
    result=import_real_grades(args.root,args.state_dir)
    print(f'Imported {result["imported"]}/{result["classes"]} real class grade books; {result["students"]} pupils; storage={result["storage"]}. Existing books retained.')
