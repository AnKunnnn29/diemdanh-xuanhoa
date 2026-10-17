"""Durable grade changes and an export outbox; SQLite locally, optional MySQL online."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone


class GradeRepository:
    def __init__(self,database):
        self.database=database
        self.mysql=bool(os.environ.get('XH_MYSQL_DATABASE'))
        with self.connection() as db:
            if self.mysql:
                db.execute('''CREATE TABLE IF NOT EXISTS xh_grade_jobs(class_id VARCHAR(32) PRIMARY KEY,
                    expected_sha CHAR(64) NOT NULL,result_sha CHAR(64) NOT NULL,package LONGBLOB,
                    status VARCHAR(16) NOT NULL,inputs LONGTEXT NOT NULL,stamp VARCHAR(40) NOT NULL)
                    ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
                db.execute('''CREATE TABLE IF NOT EXISTS xh_grade_changes(id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    class_id VARCHAR(32) NOT NULL,inputs LONGTEXT NOT NULL,result_sha CHAR(64) NOT NULL,
                    stamp VARCHAR(40) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
                db.execute('''CREATE TABLE IF NOT EXISTS xh_grade_books(class_id VARCHAR(32) PRIMARY KEY,
                    result_sha CHAR(64) NOT NULL,book LONGTEXT NOT NULL,stamp VARCHAR(40) NOT NULL)
                    ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            else:
                db.execute('''CREATE TABLE IF NOT EXISTS xh_grade_jobs(class_id TEXT PRIMARY KEY,
                    expected_sha TEXT,result_sha TEXT,package BLOB,status TEXT,inputs TEXT,stamp TEXT)''')
                db.execute('''CREATE TABLE IF NOT EXISTS xh_grade_changes(id INTEGER PRIMARY KEY,
                    class_id TEXT,inputs TEXT,result_sha TEXT,stamp TEXT)''')
                db.execute('''CREATE TABLE IF NOT EXISTS xh_grade_books(class_id TEXT PRIMARY KEY,
                    result_sha TEXT,book TEXT,stamp TEXT)''')

    @contextmanager
    def connection(self):
        if self.mysql:
            import pymysql
            required=('XH_MYSQL_HOST','XH_MYSQL_USER','XH_MYSQL_PASSWORD')
            if any(not os.environ.get(k) for k in required):raise ValueError('Thiếu cấu hình MySQL trong biến môi trường của server.')
            ca=os.environ.get('XH_MYSQL_SSL_CA')
            conn=pymysql.connect(host=os.environ['XH_MYSQL_HOST'],port=int(os.environ.get('XH_MYSQL_PORT','3306')),
                user=os.environ['XH_MYSQL_USER'],password=os.environ['XH_MYSQL_PASSWORD'],database=os.environ['XH_MYSQL_DATABASE'],
                charset='utf8mb4',cursorclass=pymysql.cursors.DictCursor,autocommit=False,connect_timeout=10,
                ssl_ca=ca,ssl_verify_cert=bool(ca),ssl_verify_identity=bool(ca))
            cursor=conn.cursor()
            class DB:
                def execute(self,sql,params=()):cursor.execute(sql.replace('?','%s'),params);return cursor
            db=DB()
        else:
            conn=sqlite3.connect(self.database,timeout=30)
            conn.row_factory=sqlite3.Row
            conn.execute('BEGIN IMMEDIATE')
            cursor=None;db=conn
        try:
            yield db
            conn.commit()
        except Exception:
            conn.rollback();raise
        finally:
            if cursor:cursor.close()
            conn.close()

    def job(self,class_id):
        with self.connection() as db:
            row=db.execute('SELECT * FROM xh_grade_jobs WHERE class_id=?',(class_id,)).fetchone()
            return dict(row) if row else None

    def enqueue(self,class_id,expected,result,package,inputs):
        stamp=datetime.now(timezone.utc).isoformat()
        values=(class_id,expected,result,package,'pending',json.dumps(inputs,ensure_ascii=False),stamp)
        with self.connection() as db:
            sql='SELECT * FROM xh_grade_jobs WHERE class_id=?'+(' FOR UPDATE' if self.mysql else '')
            old=db.execute(sql,(class_id,)).fetchone()
            if old and old['status']=='pending':raise ValueError('Còn file Excel chờ cập nhật. Hoàn tất lượt trước trước khi nhập tiếp.')
            if old:db.execute('DELETE FROM xh_grade_jobs WHERE class_id=?',(class_id,))
            db.execute('INSERT INTO xh_grade_jobs VALUES (?,?,?,?,?,?,?)',values)
            db.execute('INSERT INTO xh_grade_changes(class_id,inputs,result_sha,stamp) VALUES (?,?,?,?)',
                       (class_id,json.dumps(inputs['changes'],ensure_ascii=False),result,stamp))
            db.execute('DELETE FROM xh_grade_books WHERE class_id=?',(class_id,))
            db.execute('INSERT INTO xh_grade_books VALUES (?,?,?,?)',
                       (class_id,result,json.dumps(inputs['book'],ensure_ascii=False),stamp))

    def complete(self,class_id):
        with self.connection() as db:
            db.execute("UPDATE xh_grade_jobs SET status='applied',package=NULL WHERE class_id=?",(class_id,))

    def forget_conflict(self,class_id):
        with self.connection() as db:
            db.execute("UPDATE xh_grade_jobs SET status='conflict' WHERE class_id=?",(class_id,))

    def accept_file(self,class_id,revision,book,actor,reason):
        stamp=datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            row=db.execute('SELECT status FROM xh_grade_jobs WHERE class_id=?',(class_id,)).fetchone()
            if not row or row['status']!='conflict':raise ValueError('Xung đột đã được xử lý ở phiên khác.')
            db.execute("UPDATE xh_grade_jobs SET status='resolved',package=NULL WHERE class_id=?",(class_id,))
            db.execute('DELETE FROM xh_grade_books WHERE class_id=?',(class_id,))
            db.execute('INSERT INTO xh_grade_books VALUES (?,?,?,?)',(class_id,revision,json.dumps(book,ensure_ascii=False),stamp))
            db.execute('INSERT INTO xh_grade_changes(class_id,inputs,result_sha,stamp) VALUES (?,?,?,?)',
                       (class_id,json.dumps({'decision':'keep-file','actor':actor,'reason':reason},ensure_ascii=False),revision,stamp))

    def import_books(self,records):
        stamp=datetime.now(timezone.utc).isoformat();imported=0
        with self.connection() as db:
            for key,revision,book in records:
                if db.execute('SELECT 1 FROM xh_grade_books WHERE class_id=?',(key,)).fetchone():continue
                db.execute('INSERT INTO xh_grade_books VALUES (?,?,?,?)',(key,revision,json.dumps(book,ensure_ascii=False),stamp))
                imported+=1
        return imported
