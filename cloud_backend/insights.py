"""Scoped summaries: compute on the server, return no family profiles."""
import csv
import io
import re
from datetime import date
from sqlalchemy import select
from . import models as m, privacy
from .security import CloudError
from .persistence import Download


def attendance_report(service, db, user, query):
    from .workflows import LOCAL_TZ
    from datetime import datetime
    principal = service.public_user(db, user)
    year = service.year(db)['id']
    allowed = privacy.grants(db, year, principal)['reports']
    if not allowed:
        raise CloudError('Bạn chưa được cấp quyền xem báo cáo tổng hợp.', 403, 'forbidden')
    month = query.get('month') or datetime.now(LOCAL_TZ).strftime('%Y-%m')
    activity = query.get('activity', 'mass')
    if not re.fullmatch(r'\d{4}-\d{2}', month) or activity not in ('mass', 'lesson', 'early'):
        raise CloudError('Tháng hoặc hoạt động không hợp lệ.', 400)
    try:
        current = date.fromisoformat(month+'-01')
    except ValueError:
        raise CloudError('Tháng không hợp lệ.', 400)
    previous = date(current.year-1, 12, 1) if current.month == 1 else date(current.year, current.month-1, 1)
    before = previous.strftime('%Y-%m')
    requested = query.get('classId')
    if requested:
        if requested not in allowed:
            raise CloudError('Lớp ngoài phạm vi báo cáo.', 403, 'forbidden')
        allowed = [requested]
    classes = {r['id']: dict(r) for r in db.execute(select(m.classes).where(m.classes.c.year_id == year,
        m.classes.c.id.in_(allowed))).mappings()}
    people = {r['code']: r['class_id'] for r in db.execute(select(m.students.c.code, m.students.c.class_id).where(
        m.students.c.year_id == year, m.students.c.class_id.in_(allowed))).mappings()}
    counts = {cid: {period: {'X': 0, 'P': 0, 'O': 0} for period in (month, before)} for cid in classes}
    rows = db.execute(select(m.marks).where(m.marks.c.year_id == year, m.marks.c.activity == activity,
        m.marks.c.code.in_(people), m.marks.c.day >= before+'-01', m.marks.c.day <= month+'-31')).mappings()
    for row in rows:
        period = row['day'][:7]
        if period in (month, before) and row['status'] in ('X', 'P', 'O'):
            counts[people[row['code']]][period][row['status']] += 1
    def ratio(values):
        total = sum(values.values())
        return round(100*values['X']/total, 1) if total else None
    output = []
    mappings = db.execute(select(m.settings.c.value).where(m.settings.c.key == 'report-groups:'+year)).scalar_one_or_none() or {}
    grouped = {}
    for cid, info in classes.items():
        values, earlier = counts[cid][month], counts[cid][before]
        value, old = ratio(values), ratio(earlier)
        label = mappings.get(cid) or 'Chưa phân khối'
        bucket = grouped.setdefault(label, {period: {'X': 0, 'P': 0, 'O': 0} for period in (month, before)})
        for period in (month, before):
            for status in ('X', 'P', 'O'):
                bucket[period][status] += counts[cid][period][status]
        output.append({'classId': cid, 'className': info['name'], 'group': mappings.get(cid, ''), **values, 'recorded': sum(values.values()),
            'ratio': value, 'previousRatio': old, 'changePoints': round(value-old, 1) if value is not None and old is not None else None})
    totals = {status: sum(row[status] for row in output) for status in ('X', 'P', 'O')}
    return {'yearId': year, 'month': month, 'activity': activity, 'previousMonth': before,
        'classAttribution': 'current', 'notice': 'Nhóm theo lớp hiện tại. Ô trống chưa tính vắng; tỷ lệ chỉ tính trên X/P/O đã ghi, không phải mức hoàn tất nhập liệu.',
        'classes': sorted(output, key=lambda row: row['className']),
        'groups': [{'name': name, **bucket[month], 'ratio': ratio(bucket[month])} for name,bucket in sorted(grouped.items())],
        'totals': {**totals, 'ratio': ratio(totals)}}


def report_csv(report):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['Tháng', 'Hoạt động', 'Lớp hiện tại', 'Có mặt', 'Nghỉ phép', 'Vắng không phép', 'Đã ghi', 'Tỷ lệ %', 'Thay đổi điểm %'])
    for row in report['classes']:
        name = row['className']
        if name.lstrip().startswith(('=', '+', '-', '@')):
            name = "'"+name
        writer.writerow([report['month'], report['activity'], name, row['X'], row['P'], row['O'], row['recorded'],
            row['ratio'] if row['ratio'] is not None else '', row['changePoints'] if row['changePoints'] is not None else ''])
    return Download(('\ufeff'+stream.getvalue()).encode('utf8'), 'Chuyen-can-'+report['month']+'.csv', 'text/csv; charset=utf-8')
