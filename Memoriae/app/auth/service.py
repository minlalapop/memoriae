from __future__ import annotations

import hashlib
import os
import secrets
from datetime import timedelta

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_local_env
from app.persistence.database import get_session, utc_now
from app.persistence.models import ResearcherSession
from app.security import verify_password

COOKIE_RESEARCHER = "memoriae_researcher"
load_local_env()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_researcher_credentials(username: str, password: str) -> bool:
    configured_username = os.getenv("MEMORIAE_RESEARCHER_USERNAME")
    configured_hash = os.getenv("MEMORIAE_RESEARCHER_PASSWORD_HASH")
    if not configured_username or not configured_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le compte chercheur n'est pas configuré",
        )
    username_matches = secrets.compare_digest(username, configured_username)
    password_matches = verify_password(password, configured_hash)
    return username_matches and password_matches


def create_researcher_session(session: Session, username: str) -> tuple[str, ResearcherSession]:
    token = secrets.token_urlsafe(32)
    duration = int(os.getenv("MEMORIAE_RESEARCHER_SESSION_HOURS", "8"))
    stored = ResearcherSession(
        username=username,
        token_hash=_token_hash(token),
        expires_at=utc_now() + timedelta(hours=duration),
    )
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return token, stored


def require_researcher(
    token: str | None = Cookie(default=None, alias=COOKIE_RESEARCHER),
    session: Session = Depends(get_session),
) -> ResearcherSession:
    if not token:
        raise HTTPException(status_code=401, detail="Authentification chercheur requise")
    stored = session.scalar(
        select(ResearcherSession).where(
            ResearcherSession.token_hash == _token_hash(token),
            ResearcherSession.expires_at > utc_now(),
        )
    )
    if stored is None:
        raise HTTPException(status_code=401, detail="Session chercheur invalide ou expirée")
    return stored


def delete_researcher_session(session: Session, token: str | None) -> None:
    if not token:
        return
    stored = session.scalar(
        select(ResearcherSession).where(
            ResearcherSession.token_hash == _token_hash(token)
        )
    )
    if stored is not None:
        session.delete(stored)
        session.commit()
