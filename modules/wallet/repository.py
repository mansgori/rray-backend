from rray.core.database import mongodb
from rray.modules.users.user.models import User
from rray.modules.wallet.wallet.models import Wallet
from rray.modules.auth.schemas import UserRegister
from rray.modules.wallet.schemas import creditTransaction

class WalletRepository:
    async def wallet_exists(self, email: str) -> bool:
        return await mongodb.db.wallet.find_one({"email":email}) is not None
    
    async def create_wallet(self, wallet:WalletRegister):
        return await mongodb.db.wallet.insert_one(user.model_dump())
    
    async def create_credit_transactions(self, creditTransaction: creditTransaction):
        return await mongodb.db.credit_transactions.insert_one(creditTransaction.model_dump())