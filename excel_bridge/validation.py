"""Validate complete updates before opening a native Excel workbook."""
import math
from datetime import datetime

GRADE_FIELDS = {'kt15', 'kt1Tiet', 'thiKinh', 'thiHk'}
PROFILE_FIELDS = {'gender', 'birthDate', 'baptismDate', 'parents', 'address', 'subParish', 'phone'}


def score(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError('Điểm phải là số từ 0 đến 10, P (nghỉ phép), hoặc để trống.')
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.upper() == 'P':
            return 'P'
        value = value.replace(',', '.')
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValueError('Điểm phải là số từ 0 đến 10, P (nghỉ phép), hoặc để trống.')
    if not math.isfinite(value) or not 0 <= value <= 10:
        raise ValueError('Điểm phải nằm trong khoảng 0 đến 10.')
    return value


def validate_grades(grades, class_id, students):
    if not isinstance(grades, list) or not 1 <= len(grades) <= 40:
        raise ValueError('Danh sách cập nhật điểm phải có từ 1 đến 40 học sinh.')
    normalized, seen = [], set()
    for item in grades:
        if not isinstance(item, dict) or not isinstance(item.get('code'), str):
            raise ValueError('Mỗi dòng điểm cần mã học sinh hợp lệ.')
        code = item['code'].strip().upper()
        student = students.get(code)
        if not student or student['classId'] != class_id or code in seen:
            raise ValueError(f'Mã {code} không thuộc lớp, không tồn tại hoặc bị lặp trong lượt cập nhật.')
        if set(item) - ({'code', 'khaoBai'} | GRADE_FIELDS):
            raise ValueError('Có cột điểm không được hỗ trợ.')
        seen.add(code)
        result = {'code': code}
        if 'khaoBai' in item:
            if not isinstance(item['khaoBai'], list) or not 1 <= len(item['khaoBai']) <= 20:
                raise ValueError('Khảo bài cần từ 1 đến 20 cột điểm.')
            result['khaoBai'] = [score(value) for value in item['khaoBai']]
        for field in GRADE_FIELDS:
            if field in item:
                result[field] = score(item[field])
        if len(result) == 1:
            raise ValueError('Chưa có điểm nào cần cập nhật.')
        normalized.append(result)
    return normalized


def profile_date(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise ValueError('Ngày sinh / rửa tội cần định dạng dd/mm/yyyy hoặc yyyy-mm-dd.')
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            pass
    raise ValueError('Ngày sinh / rửa tội không hợp lệ. Nhập dd/mm/yyyy hoặc yyyy-mm-dd.')
