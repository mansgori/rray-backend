from fastapi import Depends
from backend.modules.invoice.repository import InvoiceRepository
from backend.modules.invoice.service import InvoiceService

def get_invoice_service(
    invoice_repo: InvoiceRepository = Depends(),
) -> InvoiceService:
    return InvoiceService(invoice_repo)