from backend.core.database import mongodb

class InvoiceRepository:
    async def generate_invoice_number(self, date):
        return await mongodb.db.invoices.count_documents({
                    "invoice_number": {"$regex": f"^INV-{date}-"}
                })
    async def add_invoice(self, data):
        return await mongodb.db.invoices.insert_one(data)