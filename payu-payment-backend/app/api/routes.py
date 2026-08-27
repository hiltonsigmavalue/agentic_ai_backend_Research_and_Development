from decimal import Decimal
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db import get_db
from app.models import PaymentTransaction
from app.schemas import CreatePaymentRequest, CreatePaymentResponse, RefundRequest
from app.services.payu import generate_payment_hash, generate_txnid, money, refund_payment, verify_payment, verify_response_hash

router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {"status": "ok", "service": "SigmaValue PayU API"}

@router.post("/payments/create", response_model=CreatePaymentResponse)
def create_payment(payload: CreatePaymentRequest, db: Session = Depends(get_db)):
    settings = get_settings()

    if payload.payment_category == "international":
        if not settings.international_enabled:
            raise HTTPException(status_code=400, detail="International payments are disabled. Enable only after PayU enables the required cross-border capability.")
        required = {
            "lastname": payload.lastname, "address1": payload.address1,
            "city": payload.city, "state": payload.state,
            "country": payload.country, "zipcode": payload.zipcode,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise HTTPException(status_code=422, detail=f"International payment requires: {', '.join(missing)}")

    txnid = generate_txnid()
    amount = money(payload.amount)

    params = {
        "key": settings.payu_merchant_key,
        "txnid": txnid,
        "amount": amount,
        "productinfo": payload.productinfo,
        "firstname": payload.firstname,
        "lastname": payload.lastname or "",
        "email": str(payload.email),
        "phone": payload.phone,
        "surl": f"{settings.public_base_url.rstrip('/')}/api/payments/callback/success",
        "furl": f"{settings.public_base_url.rstrip('/')}/api/payments/callback/failure",
        "udf1": "", "udf2": "", "udf3": "", "udf4": "", "udf5": "",
    }

    if payload.payment_category == "international":
        params.update({
            "address1": payload.address1 or "", "address2": payload.address2 or "",
            "city": payload.city or "", "state": payload.state or "",
            "country": payload.country or "", "zipcode": payload.zipcode or "",
        })

    params["hash"] = generate_payment_hash(
        key=settings.payu_merchant_key, salt=settings.payu_salt,
        txnid=txnid, amount=amount, productinfo=payload.productinfo,
        firstname=payload.firstname, email=str(payload.email),
    )

    transaction = PaymentTransaction(
        txnid=txnid, amount=payload.amount, currency="INR",
        payment_category=payload.payment_category, productinfo=payload.productinfo,
        firstname=payload.firstname, lastname=payload.lastname,
        email=str(payload.email), phone=payload.phone, status="created",
    )
    db.add(transaction)
    db.commit()

    return CreatePaymentResponse(txnid=txnid, payu_url=settings.payu_payment_url, fields=params)

def _handle_callback(form_data: dict[str, str], db: Session):
    settings = get_settings()
    txnid = form_data.get("txnid")
    if not txnid:
        raise HTTPException(status_code=400, detail="PayU response did not contain txnid")

    transaction = db.query(PaymentTransaction).filter(PaymentTransaction.txnid == txnid).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    verified = verify_response_hash(form_data, settings.payu_salt)
    transaction.response_hash_verified = "true" if verified else "false"
    transaction.status = form_data.get("status", "unknown")
    transaction.unmappedstatus = form_data.get("unmappedstatus")
    transaction.mihpayid = form_data.get("mihpayid")
    transaction.bank_ref_num = form_data.get("bank_ref_num")
    transaction.error_message = form_data.get("error_Message") or form_data.get("error")
    db.commit()

    result = "success" if verified and form_data.get("status") == "success" else "failure"
    query = urlencode({"status": result, "txnid": txnid, "message": form_data.get("error_Message") or form_data.get("error") or ""})
    return RedirectResponse(url=f"{settings.frontend_url.rstrip('/')}/payment/result?{query}", status_code=303)

@router.post("/payments/callback/success")
async def payment_success(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    return _handle_callback({key: str(value) for key, value in form.items()}, db)

@router.post("/payments/callback/failure")
async def payment_failure(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    return _handle_callback({key: str(value) for key, value in form.items()}, db)

@router.get("/payments/{txnid}")
def get_payment(txnid: str, db: Session = Depends(get_db)):
    transaction = db.query(PaymentTransaction).filter(PaymentTransaction.txnid == txnid).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "txnid": transaction.txnid, "amount": str(transaction.amount),
        "currency": transaction.currency, "payment_category": transaction.payment_category,
        "status": transaction.status, "unmappedstatus": transaction.unmappedstatus,
        "mihpayid": transaction.mihpayid, "bank_ref_num": transaction.bank_ref_num,
        "response_hash_verified": transaction.response_hash_verified,
        "created_at": transaction.created_at, "updated_at": transaction.updated_at,
    }

@router.post("/payments/{txnid}/verify")
async def verify_payment_endpoint(txnid: str, db: Session = Depends(get_db)):
    transaction = db.query(PaymentTransaction).filter(PaymentTransaction.txnid == txnid).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return await verify_payment(txnid)

@router.post("/payments/{txnid}/refund")
async def refund_payment_endpoint(txnid: str, payload: RefundRequest, db: Session = Depends(get_db)):
    transaction = db.query(PaymentTransaction).filter(PaymentTransaction.txnid == txnid).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if not transaction.mihpayid:
        raise HTTPException(status_code=400, detail="No PayU mihpayid is stored for this transaction.")
    if payload.amount > Decimal(str(transaction.amount)):
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed the original transaction amount.")

    import secrets
    refund_token = "SVREF" + secrets.token_hex(10)
    result = await refund_payment(mihpayid=transaction.mihpayid, amount=payload.amount, refund_token=refund_token)
    return {"txnid": txnid, "refund_token": refund_token, "payu_response": result}
