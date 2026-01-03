from fastapi import Depends
from backend.modules.wallet.repository import WalletRepository
from backend.modules.wallet.service import WalletService

def get_wallet_service(
    wallet_repo: WalletRepository = Depends(),
) -> WalletService:
    return WalletService(wallet_repo)