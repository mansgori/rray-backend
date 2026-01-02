from fastapi import Depends
from backend.modules.sessions.repository import SessionRepository
from backend.modules.sessions.service import SessionService

def get_session_service(
    session_repo: SessionRepository = Depends(),
) -> SessionService:
    return SessionService(session_repo)