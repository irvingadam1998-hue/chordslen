"""Atomic admission and reusable results for a single worker process."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager


class JobStore:
    def __init__(self, path, ttl=3600, capacity=1):
        self.path, self.ttl, self.capacity = path, ttl, capacity
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY, status TEXT NOT NULL, result TEXT, error TEXT,
                created_at REAL NOT NULL, updated_at REAL NOT NULL)''')
            columns = {row[1] for row in db.execute('PRAGMA table_info(jobs)')}
            if 'request_key' not in columns:
                db.execute('ALTER TABLE jobs ADD COLUMN request_key TEXT')
            db.execute('CREATE INDEX IF NOT EXISTS idx_jobs_key ON jobs(request_key)')
            db.execute('''CREATE TABLE IF NOT EXISTS upload_tickets (
                token TEXT PRIMARY KEY, origin TEXT NOT NULL, expires_at REAL NOT NULL,
                used INTEGER NOT NULL DEFAULT 0)''')
            # In-process threads cannot survive a restart. Free their slots explicitly.
            db.execute("UPDATE jobs SET status='failed', error=?, updated_at=? WHERE status='processing'",
                       ('El servidor se reinició. Vuelve a intentar el análisis.', time.time()))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def cleanup(self):
        with self.connect() as db:
            db.execute("DELETE FROM jobs WHERE status != 'processing' AND updated_at < ?", (time.time() - self.ttl,))
            db.execute('DELETE FROM upload_tickets WHERE expires_at < ?', (time.time(),))

    def get(self, job_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE job_id=?', (job_id,)).fetchone()
        if not row or (row['status'] != 'processing' and row['updated_at'] < time.time() - self.ttl):
            return None
        return {**dict(row), 'result': json.loads(row['result']) if row['result'] else None}

    def reserve(self, request_key=None):
        """Return (job id, is new); identical pending/completed requests share work."""
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if request_key:
                row = db.execute('''SELECT job_id FROM jobs WHERE request_key=?
                    AND (status='processing' OR (status='done' AND updated_at>=?))
                    ORDER BY created_at DESC LIMIT 1''', (request_key, now - self.ttl)).fetchone()
                if row:
                    return row['job_id'], False
            active = db.execute("SELECT COUNT(*) FROM jobs WHERE status='processing'").fetchone()[0]
            if active >= self.capacity:
                return None, False
            job_id = uuid.uuid4().hex
            db.execute('''INSERT INTO jobs
                (job_id, status, created_at, updated_at, request_key) VALUES (?, 'processing', ?, ?, ?)''',
                       (job_id, now, now, request_key))
            return job_id, True

    def finish(self, job_id, result):
        success = result.get('success') is True
        with self.connect() as db:
            db.execute('UPDATE jobs SET status=?, result=?, error=?, updated_at=? WHERE job_id=?', (
                'done' if success else 'failed', json.dumps(result, ensure_ascii=False),
                None if success else result.get('error', 'El procesamiento falló.'), time.time(), job_id,
            ))

    def issue_ticket(self, origin):
        token = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO upload_tickets(token, origin, expires_at) VALUES (?, ?, ?)',
                       (token, origin, time.time() + 600))
        return token

    def consume_ticket(self, token, origin):
        with self.connect() as db:
            updated = db.execute('''UPDATE upload_tickets SET used=1
                WHERE token=? AND origin=? AND expires_at>? AND used=0''', (token, origin, time.time()))
            return updated.rowcount == 1

    def allows_origin(self, origin):
        with self.connect() as db:
            return db.execute('SELECT 1 FROM upload_tickets WHERE origin=? AND expires_at>? LIMIT 1',
                              (origin, time.time())).fetchone() is not None
