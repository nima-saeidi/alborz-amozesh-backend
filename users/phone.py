"""
Phone number helpers, one-time codes (OTP) and SMS sending.

SMS provider is chosen with SMS_BACKEND in .env:
- console (default): the code is only written to the log (development)
- kavenegar: Kavenegar "verify lookup" (KAVENEGAR_API_KEY, KAVENEGAR_TEMPLATE)
- smsir: sms.ir "verify" (SMSIR_API_KEY, SMSIR_TEMPLATE_ID)
Only the standard library is used (the server cannot reach PyPI).
"""
import hashlib
import hmac
import json
import logging
import re
import secrets
import urllib.parse
import urllib.request

from django.conf import settings
from django.core import signing

logger = logging.getLogger(__name__)

_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
MOBILE_RE = re.compile(r'^09\d{9}$')


def normalize_phone(_value):
    """
    Iranian mobile number in the 09xxxxxxxxx form (Persian digits, +98, 0098 and spaces accepted).
    Returns None when the value is not a valid mobile number.
    """
    if not _value:
        return None
    digits = re.sub(r'\D', '', str(_value).translate(_DIGITS))
    if digits.startswith('0098'):
        digits = '0' + digits[4:]
    elif digits.startswith('98') and len(digits) == 12:
        digits = '0' + digits[2:]
    elif digits.startswith('9') and len(digits) == 10:
        digits = '0' + digits
    return digits if MOBILE_RE.match(digits) else None


# -------------------- OTP --------------------
def generate_code():
    return f"{secrets.randbelow(10 ** settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}"


def hash_code(_phone, _code):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{_phone}:{_code}".encode(), hashlib.sha256).hexdigest()


def code_matches(_otp, _code):
    code = str(_code or '').translate(_DIGITS).strip()
    return hmac.compare_digest(_otp.code_hash, hash_code(_otp.phone_number, code))


# -------------------- Verification token (after a correct code) --------------------
_TOKEN_SALT = 'users.phone-verification'


def make_verification_token(_phone, _purpose):
    return signing.dumps({'phone': _phone, 'purpose': _purpose}, salt=_TOKEN_SALT)


def read_verification_token(_token, _purpose):
    """Phone number of a valid token for this purpose, otherwise None"""
    try:
        data = signing.loads(_token, salt=_TOKEN_SALT, max_age=settings.OTP_VERIFICATION_MAX_AGE)
    except signing.BadSignature:
        return None
    if data.get('purpose') != _purpose:
        return None
    return data.get('phone')


# -------------------- SMS --------------------
def _post_json(_url, _payload, _headers):
    request = urllib.request.Request(_url, data=json.dumps(_payload).encode(), headers={'Content-Type': 'application/json', **_headers}, method='POST')
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status


def send_code_sms(_phone, _code):
    """Send the code; returns True when the provider accepted it"""
    backend = settings.SMS_BACKEND
    try:
        if backend == 'kavenegar':
            query = urllib.parse.urlencode({'receptor': _phone, 'token': _code, 'template': settings.KAVENEGAR_TEMPLATE})
            url = f"https://api.kavenegar.com/v1/{settings.KAVENEGAR_API_KEY}/verify/lookup.json?{query}"
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.status == 200
        if backend == 'smsir':
            payload = {'mobile': _phone, 'templateId': int(settings.SMSIR_TEMPLATE_ID), 'parameters': [{'name': 'Code', 'value': _code}]}
            return _post_json('https://api.sms.ir/v1/send/verify', payload, {'x-api-key': settings.SMSIR_API_KEY, 'Accept': 'text/plain'}) == 200
    except Exception:
        logger.exception('Sending the SMS code to %s failed', _phone)
        return False

    logger.warning('SMS code for %s: %s (SMS_BACKEND=console)', _phone, _code)
    return True
