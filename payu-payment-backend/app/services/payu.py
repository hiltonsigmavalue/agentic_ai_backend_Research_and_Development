import hashlib
import hmac
import secrets
import string
from decimal import Decimal
from typing import Mapping
import httpx
from app.core.config import get_settings

def sha512(value: str) -> str:
    return hashlib.sha512(value.encode("utf-8")).hexdigest()

def generate_txnid() -> str:
    alphabet = string.ascii_letters + string.digits
    return "SV" + "".join(secrets.choice(alphabet) for _ in range(20))

def money(value: Decimal) -> str:
    return f"{value:.2f}"

def generate_payment_hash(*, key: str, salt: str, txnid: str, amount: str,
                          productinfo: str, firstname: str, email: str,
                          udf1: str = "", udf2: str = "", udf3: str = "",
                          udf4: str = "", udf5: str = "") -> str:
    value = (
        f"{key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|"
        f"{udf1}|{udf2}|{udf3}|{udf4}|{udf5}||||||{salt}"
    )
    return sha512(value)

def generate_command_hash(*, key: str, command: str, var1: str, salt: str) -> str:
    return sha512(f"{key}|{command}|{var1}|{salt}")

def verify_response_hash(data: Mapping[str, str], salt: str) -> bool:
    received = data.get("hash", "")
    if not received:
        return False
    additional = data.get("additional_charges") or data.get("additionalCharges")
    tail = (
        f"{data.get('status', '')}||||||"
        f"{data.get('udf5', '')}|{data.get('udf4', '')}|{data.get('udf3', '')}|"
        f"{data.get('udf2', '')}|{data.get('udf1', '')}|{data.get('email', '')}|"
        f"{data.get('firstname', '')}|{data.get('productinfo', '')}|"
        f"{data.get('amount', '')}|{data.get('txnid', '')}|{data.get('key', '')}"
    )
    expected = sha512(f"{additional}|{salt}|{tail}" if additional else f"{salt}|{tail}")
    return hmac.compare_digest(expected.lower(), received.lower())

async def verify_payment(txnid: str) -> dict:
    settings = get_settings()
    command = "verify_payment"
    payload = {
        "key": settings.payu_merchant_key,
        "command": command,
        "var1": txnid,
        "hash": generate_command_hash(
            key=settings.payu_merchant_key, command=command,
            var1=txnid, salt=settings.payu_salt
        ),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(settings.payu_postservice_url, data=payload)
        response.raise_for_status()
        return response.json()

async def refund_payment(*, mihpayid: str, amount: Decimal, refund_token: str) -> dict:
    settings = get_settings()
    command = "cancel_refund_transaction"
    payload = {
        "key": settings.payu_merchant_key,
        "command": command,
        "var1": mihpayid,
        "var2": refund_token,
        "var3": money(amount),
        "hash": generate_command_hash(
            key=settings.payu_merchant_key, command=command,
            var1=mihpayid, salt=settings.payu_salt
        ),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(settings.payu_postservice_url, data=payload)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"raw_response": response.text}
