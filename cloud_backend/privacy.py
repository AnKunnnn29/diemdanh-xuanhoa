"""Explicit student projections and assignment-scoped capabilities. No client claims."""
from .security import CloudError

CAPABILITIES = ('contactRead', 'contactWrite', 'privateExport', 'proxy', 'reports')
# Mọi quyền dữ liệu (xem/sửa liên hệ, tải hồ sơ, quét hộ, báo cáo) đúng bằng phạm vi
# lớp được phân công; Admin gồm toàn bộ lớp. Không còn cấp quyền thủ công.
CONTACT_FIELDS = {'phone', 'parents', 'address'}
PROFILE_FIELDS = ('saintName', 'fullName', 'gender', 'birthDate', 'baptismDate',
                  'subParish', 'enrolledFrom', 'feastDay', 'feastConfirmed', 'feastConfirmedBy', 'feastConfirmedAt')


def grants(db, year, principal):
    ids = sorted(set(principal['classIds']))
    return {key: ids for key in CAPABILITIES}


def require(db, year, principal, capability, class_id):
    if class_id not in grants(db, year, principal).get(capability, []):
        raise CloudError('Bạn chưa được cấp quyền cho dữ liệu này.', 403, 'forbidden')


def identity(person):
    return {key: person.get(key, '') for key in ('id', 'saintName', 'fullName', 'classId', 'className')}


def directory(person):
    return {'id': person['id'], 'name': person.get('name') or
            ' '.join(filter(None, (person.get('saintName'), person.get('fullName')))), 'classId': person['classId']}


def detail(person):
    return {**identity(person), **{key: person.get(key, '') for key in PROFILE_FIELDS},
            'name': person.get('name', ''), 'revision': person['revision']}


def public_result(value):
    """Defense in depth for nested workflow/preview results, never a denylist alone.

    Student objects have a positive projection. Family fields anywhere else are
    removed too, including legacy audit payloads. Explicit contact and staff APIs
    use their own projections instead of this function.
    """
    if isinstance(value, list):
        return [public_result(item) for item in value]
    if not isinstance(value, dict):
        return value
    if 'classId' in value and ('id' in value or 'code' in value) and any(k in value for k in ('fullName', 'saintName', 'parents')):
        projected = {key: value[key] for key in ('id', 'code', 'name', 'saintName', 'fullName', 'classId', 'className',
                     'revision', 'rosterRow', 'khaoBai', 'kt15', 'kt1Tiet', 'thiKinh', 'thiHk', 'tbHk', 'xepLoai', 'xepHang',
                     'massRatio', 'lessonRatio', 'diemHk1', 'diemHk2', 'diemGiaoLy', 'massScore', 'lessonScore',
                     'combinedMassScore', 'assessment', 'totalScore', 'yearRank', 'supplementalMass',
                     'studentName', 'sessionId', 'date', 'activity', 'scannedById', 'scannedByName', 'scannedAt', 'status') if key in value}
        return {key: public_result(item) for key, item in projected.items()}
    return {key: public_result(item) for key, item in value.items()
            if key not in CONTACT_FIELDS | {'before', 'after', 'password_hash'}}
