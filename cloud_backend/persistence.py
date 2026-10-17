"""Private, content-addressed artifacts and versioned PostgreSQL documents."""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import select, insert, update, func
from . import models as m
from .security import CloudError


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def document(db, year, kind, identifier, default=None):
    row = db.execute(select(m.records.c.payload).where(m.records.c.year_id == year,
        m.records.c.kind == kind, m.records.c.id == identifier)).scalar_one_or_none()
    return row if row is not None else default


def save_document(db, year, kind, identifier, payload):
    conditions = (m.records.c.year_id == year, m.records.c.kind == kind, m.records.c.id == identifier)
    exists = db.execute(select(m.records.c.revision).where(*conditions)).scalar_one_or_none()
    if exists is None:
        db.execute(insert(m.records).values(year_id=year, kind=kind, id=identifier, payload=payload, revision=1))
    else:
        db.execute(update(m.records).where(*conditions).values(payload=payload, revision=exists+1))


def store_blob(db, content):
    digest = hashlib.sha256(content).hexdigest()
    if db.execute(select(m.blobs.c.digest).where(m.blobs.c.digest == digest)).scalar_one_or_none():
        return digest
    used = db.execute(select(func.coalesce(func.sum(m.blobs.c.size), 0))).scalar_one()
    if used + len(content) > 300_000_000:
        raise CloudError('Kho file thử nghiệm đã gần đầy. Tải và dọn bản sao cũ trước khi thêm.', 507, 'storage_full')
    db.execute(insert(m.blobs).values(digest=digest, content=content, size=len(content),
        created_at=datetime.now(timezone.utc).isoformat()))
    return digest


def load_blob(db, digest):
    content = db.execute(select(m.blobs.c.content).where(m.blobs.c.digest == digest)).scalar_one_or_none()
    if content is None:
        raise CloudError('Thiếu file sổ gốc trên cloud. Cần hoàn tất nhập sổ trước khi sử dụng.', 503, 'workbook_not_imported')
    return bytes(content)


@dataclass
class Download:
    content: bytes
    filename: str
    content_type: str
