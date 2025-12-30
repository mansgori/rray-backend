from fastapi import  Depends
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.auth.service import AuthService

def get_auth_service(
    auth_repo: AuthRepository = Depends(),
    wallet_repo: WalletRepository = Depends(),
) -> AuthService:
    return AuthService(
        auth_repo=auth_repo,
        wallet_repo=wallet_repo,
    )