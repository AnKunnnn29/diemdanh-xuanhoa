"""Readable login names; identity and authorization remain separate from names."""
import re
import unicodedata


def name_words(value):
    value=unicodedata.normalize('NFKD',str(value).casefold().replace('đ','d').replace('œ','oe'))
    value=''.join(c for c in value if not unicodedata.combining(c))
    return re.findall(r'[a-z0-9]+',value)


def sister_name(value):
    words=name_words(value)
    return bool(words and (words[0] in ('sr','soeur','so','di') or words[:2]==['nu','tu']))


def choose_username(name,role,taken,*,prefix=None):
    if prefix is None:
        prefix='sr' if sister_name(name) else ('admin' if role=='Admin' else 'glv')
    if prefix not in ('admin','glv','sr'):
        raise ValueError('Chức vụ tài khoản không hợp lệ.')
    occupied={str(value).casefold() for value in taken}
    if prefix=='admin':
        number=1
        while f'admin{number:03}' in occupied:number+=1
        return f'admin{number:03}'
    words=name_words(name)
    if sister_name(name):
        words=words[2:] if words[:2]==['nu','tu'] else words[1:]
    if len(words)<2:
        raise ValueError('Cần họ tên đầy đủ để lấy hai thành phần cuối cho tên đăng nhập.')
    stem=prefix+'-'+''.join(words[-2:])
    if len(stem)>90:
        raise ValueError('Hai thành phần cuối của tên quá dài để tạo tài khoản.')
    result,number=stem,2
    while result in occupied:
        result=stem+str(number)
        number+=1
    return result


def rename_plan(users,sister_ids):
    ordered=sorted(users,key=lambda r:(r['username'].casefold(),r['id']))
    preserved=[]
    candidates=[]
    for row in ordered:
        is_sister=row['id'] in sister_ids or sister_name(row['display_name'])
        if row['role']=='Admin' and not is_sister:
            preserved.append({'id':row['id'],'username':row['username'],'displayName':row['display_name'],'reason':'admin'})
            continue
        prefix='sr' if is_sister else 'glv'
        try:
            choose_username(row['display_name'],row['role'],(),prefix=prefix)
        except ValueError:
            preserved.append({'id':row['id'],'username':row['username'],'displayName':row['display_name'],'reason':'full-name-needed'})
            continue
        candidates.append((row,prefix))
    # Existing readable names remain allocated to their owners on repeated runs.
    taken={r['username'].casefold() for r in users}
    changes=[]
    for row,prefix in candidates:
        base=choose_username(row['display_name'],row['role'],(),prefix=prefix)
        current=row['username'].casefold()
        suffix=re.fullmatch(re.escape(base)+r'([0-9]+)',current)
        if current==base or suffix and int(suffix[1])>=2:
            continue
        proposed=choose_username(row['display_name'],row['role'],taken,prefix=prefix)
        taken.add(proposed)
        changes.append({'id':row['id'],'oldUsername':row['username'],'username':proposed,
            'displayName':row['display_name'],'prefix':prefix})
    return {'changes':changes,'preserved':preserved}
