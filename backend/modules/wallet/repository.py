from backend.core.database import mongodb
from backend.modules.wallet.models import Wallet, CreditTransaction, CreditLedger


class WalletRepository:
    async def wallet_exists(self, email: str) -> bool:
        return await mongodb.db.wallet.find_one({"email":email}) is not None
    
    async def find_wallet_by_id(self, id: str):
        return await mongodb.db.wallet.find_one({"user_id":id}, {"_id": 0})
    
    async def get_credit_plans(self):
        return await mongodb.db.credit_plans.find({}, {"_id": 0}).to_list(100)
    
    async def get_credit_plans_by_id(self, id):
        return await mongodb.db.credit_plans.find_one({"id":id}, {"_id": 0})
    
    async def update_wallet(self, id: str, credits_used):
        return await mongodb.db.wallet.find_one({"user_id": id},
                    {"$inc": {"credits_balance": -credits_used}})
    
    async def grant_wallet_creadit(self, id, credit_balance, time ):
        return await mongodb.db.wallets.update_one(
            {"user_id": id},
            {
                "$inc": {"credits_balance": credit_balance},
                "$set": {"last_grant_at": time}
            }
        )
    
    async def refund_wallet_wallet(self, id: str, credits_balance):
        return await mongodb.db.wallets.update_one(
                {"user_id": id},
                {"$inc": {"credits_balance": credits_balance}}
            )
    
    async def create_wallet(self, wallet:Wallet):
        return await mongodb.db.wallet.insert_one(wallet.model_dump())
    
    async def create_credit_transactions(self, creditTransaction: CreditTransaction):
        return await mongodb.db.credit_transactions.insert_one(creditTransaction.model_dump())
    
    async def create_credit_ledger(self, creadit_leadger :CreditLedger):
        return await mongodb.db.credit_ledger.insert_one(creadit_leadger.model_dump())
    
    async def get_credit_ledger_by_id(self, id):
        return await mongodb.db.credit_ledger.find({"user_id": id}, {"_id": 0}).sort("created_at", -1).to_list(100)