"""Regenerate backend/app/demo/sample_result.json by running the real pipeline.

Needs the backend running on :8000 and a user row in the local dev db whose email is in
PRO_EMAILS. Spends real Gemini quota. Writes only if every clip is fully populated.
Usage (from repo root):  backend/venv/Scripts/python.exe backend/scripts/generate_demo.py
"""
import datetime
import json
import sqlite3
import sys
from pathlib import Path

import httpx
import jwt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
import os
os.chdir(ROOT / "backend")  # config.py's Settings reads ".env" relative to cwd
from app.config import get_settings  # noqa: E402

VIDEO = "https://youtu.be/jEnxvZXzo0E"
OUT = ROOT / "backend/app/demo/sample_result.json"

settings = get_settings()
email = settings.pro_emails[0]
db = sqlite3.connect(ROOT / "backend/data/clipforge.db")
db.execute("delete from processed_videos")  # don't reuse stale cached results
db.commit()
sub = db.execute("select id from users where email=?", (email,)).fetchone()[0]
token = jwt.encode(
    {"sub": sub, "email": email, "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)},
    settings.auth_secret, algorithm="HS256",
)

merged = None
for offset in range(3):
    r = httpx.post("http://localhost:8000/api/v1/process", json={"youtube_url": VIDEO, "chunk_offset": offset},
                   headers={"Authorization": f"Bearer {token}"}, timeout=900)
    d = r.json()
    print(offset, r.status_code, d.get("status"), len(d.get("clips", [])), d.get("errors"))
    if not d.get("clips"):
        break
    if merged is None:
        merged = d
    else:
        merged["clips"] += d["clips"]

good = merged and all(c["end_time"] > c["start_time"] and c["hook"] and c["virality_reasoning"] for c in merged["clips"])
if good:
    OUT.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved {len(merged['clips'])} clips to {OUT}")
else:
    print("NOT saved: no clips, or some clips were incomplete. Try again later.")
