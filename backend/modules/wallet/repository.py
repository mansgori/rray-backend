from backend.core.database import mongodb
from backend.modules.wallet.models import Wallet, CreditTransaction


class WalletRepository:
    async def wallet_exists(self, email: str) -> bool:
        return await mongodb.db.wallet.find_one({"email":email}) is not None
    
    async def create_wallet(self, wallet:Wallet):
        return await mongodb.db.wallet.insert_one(wallet.model_dump())
    
    async def create_credit_transactions(self, creditTransaction: CreditTransaction):
        return await mongodb.db.credit_transactions.insert_one(creditTransaction.model_dump())