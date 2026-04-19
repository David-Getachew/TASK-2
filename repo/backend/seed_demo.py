"""Seed deterministic demo users for local/dev verification.

Creates one user per role (candidate, reviewer, admin, proctor) with a known
password. Intended for development and README verification only — DO NOT run
against a production database.

Usage (inside the backend container):
    python seed_demo.py

Credentials and override env var:
    DEMO_PASSWORD (default: MeritTrack!23456)

Users created:
    demo_candidate / demo_reviewer / demo_admin / demo_proctor
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.config import get_settings
from src.persistence.models.auth import User
from src.security.passwords import hash_password


DEMO_USERS = [
    ("demo_candidate", "candidate", "Demo Candidate"),
    ("demo_reviewer", "reviewer", "Demo Reviewer"),
    ("demo_admin", "admin", "Demo Admin"),
    ("demo_proctor", "proctor", "Demo Proctor"),
]


def _sync_db_url() -> str:
    url = get_settings().database_url
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")
    return url


def main() -> int:
    if os.getenv("ENVIRONMENT", "production") == "production":
        print(
            "Refusing to seed demo users: ENVIRONMENT=production. "
            "Set ENVIRONMENT=development to override.",
            file=sys.stderr,
        )
        return 2

    password = os.getenv("DEMO_PASSWORD", "MeritTrack!23456")
    engine = create_engine(_sync_db_url(), future=True)
    try:
        with Session(engine) as session:
            for username, role, full_name in DEMO_USERS:
                existing = session.execute(
                    select(User).where(User.username == username)
                ).scalar_one_or_none()
                if existing is not None:
                    existing.password_hash = hash_password(password)
                    existing.role = role
                    existing.is_active = True
                    existing.is_locked = False
                    print(f"updated {username} ({role})")
                    continue
                session.add(
                    User(
                        username=username,
                        password_hash=hash_password(password),
                        role=role,
                        full_name=full_name,
                        is_active=True,
                        is_locked=False,
                    )
                )
                print(f"created {username} ({role})")
            session.commit()
    finally:
        engine.dispose()

    print(f"\nDemo credentials ready. Password: {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
