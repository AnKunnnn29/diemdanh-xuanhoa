"""Replay a durable device outbox under the current account and transaction."""
import re
from datetime import datetime, timezone
from .security import CloudError
from .persistence import document, save_document, fingerprint
from .workflows import Workflow, LOCAL_TZ


def replay_scan(service, db, user, values):
    year = service.year(db)
    if values.get('ownerId') != user['id']:
        raise CloudError('Lượt chờ thuộc tài khoản khác. Đăng nhập đúng tài khoản đã quét.', 403, 'offline_owner_changed')
    if values.get('yearId') != year['id']:
        raise CloudError('Năm học đã thay đổi. Giữ lượt chờ và nhờ Admin đối chiếu.', 409, 'offline_year_changed')
    identifier = values.get('id')
    if not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9-]{16,64}', identifier):
        raise CloudError('Mã lượt chờ không hợp lệ.')
    if not isinstance(values.get('manual'), bool):
        raise CloudError('Hình thức điểm danh không hợp lệ.')
    try:
        captured = datetime.fromisoformat(values['capturedAt'])
        if captured.tzinfo is None:
            raise ValueError()
        age = (datetime.now(timezone.utc) - captured).total_seconds()
        if not -300 <= age <= 30 * 86400:
            raise ValueError()
    except (KeyError, TypeError, ValueError, OverflowError):
        raise CloudError('Giờ quét không hợp lệ hoặc lượt chờ đã quá 30 ngày. Nhờ Admin đối chiếu.', 409, 'offline_time_invalid')
    body = {k: values.get(k) for k in ('sessionId', 'code', 'manual', 'obligationDate', 'capturedAt', 'yearId')}
    workflow = Workflow(db, year['id'])
    try:
        principal = service.public_user(db, user)
        student = workflow.catalog.students.get(body['code'])
        if not student or student['classId'] not in principal['classIds']:
            raise CloudError('Thiếu nhi không còn thuộc lớp được phân công. Giữ lượt chờ để đối chiếu.', 403, 'forbidden')
        session = workflow.session(body['sessionId'])
        if session['date'] > datetime.now(LOCAL_TZ).date().isoformat():
            raise CloudError('Buổi điểm danh chưa diễn ra. Kiểm tra ngày và đồng hồ thiết bị.', 409, 'offline_date_mismatch')
        workflow.authorize(principal, 'scan', dict(body))
        if session['scope'] != 'all' and session['scope'] != student['className']:
            raise CloudError('Thiếu nhi đã đổi lớp hoặc không thuộc buổi đã lưu.', 409, 'offline_scope_changed')
        if captured.astimezone(LOCAL_TZ).date().isoformat() != session['date']:
            raise CloudError('Ngày quét trên thiết bị khác ngày của buổi. Nhờ Admin kiểm tra.', 409, 'offline_date_mismatch')
        receipt_id = fingerprint([user['id'], identifier])
        digest = fingerprint(body)
        receipt = document(db, year['id'], 'offline-scan-receipt', receipt_id)
        if receipt:
            if receipt['fingerprint'] != digest:
                raise CloudError('Mã lượt chờ đã dùng cho nội dung khác.', 409, 'offline_id_conflict')
            return {**receipt['result'], 'replayed': True}
        if session['activity'] == 'early':
            # Device clocks are untrusted. A delayed early-Mass scan must follow
            # the same Admin confirmation rule as an online late entry.
            minute = captured.astimezone(LOCAL_TZ).hour * 60 + captured.astimezone(LOCAL_TZ).minute
            if captured.astimezone(LOCAL_TZ).weekday() != 6 or not 360 <= minute <= 380:
                raise CloudError('Giờ quét lễ sớm trên thiết bị phải từ 06:00 đến 06:20 sáng Chủ Nhật.', 409, 'offline_early_review')
            now = datetime.now(LOCAL_TZ)
            if now.date().isoformat() != session['date'] or not 360 <= now.hour * 60 + now.minute <= 380:
                mark = workflow.catalog.marks.get(f"{session['date']}|early|{student['id']}", {})
                if mark.get('status') == 'X':
                    result = {'saved': True, 'duplicate': True, 'creditedDate': session['date'], 'student': student}
                else:
                    raise CloudError('Lượt lễ sớm được gửi lại sau khung giờ. Nhờ Admin xác nhận giờ thực tế trước khi thử lại.', 409, 'offline_early_review')
            else:
                result = workflow.execute(principal, 'scan', body)
        else:
            result = workflow.execute(principal, 'scan', body)
        if result.get('choiceRequired'):
            return result
        public_result = {k: v for k, v in result.items() if k != 'state'}
        if public_result.get('student'):
            public_result['student'] = {k: student.get(k, '') for k in ('id', 'saintName', 'fullName', 'classId', 'className')}
        save_document(db, year['id'], 'offline-scan-receipt', receipt_id,
                      {'fingerprint': digest, 'capturedAt': values['capturedAt'], 'result': public_result})
        service.audit(db, user['id'], 'offline-scan', {**body, 'submissionId': identifier})
        return public_result
    except (ValueError, TypeError, KeyError) as error:
        raise CloudError(str(error) if isinstance(error, ValueError) else 'Lượt chờ không hợp lệ.') from error
    finally:
        workflow.shutdown()
