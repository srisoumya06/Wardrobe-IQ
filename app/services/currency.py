import os
import time
import requests

# In-memory cache for exchange rate
_EXCHANGE_CACHE = {
    "rate": float(os.getenv("USD_TO_INR_RATE", "86.50")),
    "timestamp": 0,
    "is_live": False,
    "source": "RBI Reference Benchmark (1 USD ≈ ₹86.50)"
}

CACHE_TTL_SECONDS = 3600 # 1 hour cache

def get_usd_to_inr_rate_info():
    """
    Returns (rate: float, is_live: bool, source_description: str).
    Uses a reliable, open exchange-rate API with graceful fallback to benchmark.
    """
    now = time.time()
    if now - _EXCHANGE_CACHE["timestamp"] < CACHE_TTL_SECONDS and _EXCHANGE_CACHE["timestamp"] > 0:
        return _EXCHANGE_CACHE["rate"], _EXCHANGE_CACHE["is_live"], _EXCHANGE_CACHE["source"]

    # Try fetching live rate
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=1.5)
        if resp.status_code == 200:
            data = resp.json()
            inr_rate = data.get("rates", {}).get("INR")
            if inr_rate and isinstance(inr_rate, (int, float)):
                _EXCHANGE_CACHE["rate"] = float(inr_rate)
                _EXCHANGE_CACHE["timestamp"] = now
                _EXCHANGE_CACHE["is_live"] = True
                _EXCHANGE_CACHE["source"] = f"Live Market Exchange Rate (1 USD ≈ ₹{inr_rate:.2f})"
                return _EXCHANGE_CACHE["rate"], _EXCHANGE_CACHE["is_live"], _EXCHANGE_CACHE["source"]
    except Exception:
        # Graceful fallback without failing application
        pass

    # Fallback to configured or standard benchmark
    fallback_rate = float(os.getenv("USD_TO_INR_RATE", "86.50"))
    _EXCHANGE_CACHE["rate"] = fallback_rate
    _EXCHANGE_CACHE["timestamp"] = now
    _EXCHANGE_CACHE["is_live"] = False
    _EXCHANGE_CACHE["source"] = f"Configured Benchmark Rate (1 USD ≈ ₹{fallback_rate:.2f})"
    return _EXCHANGE_CACHE["rate"], _EXCHANGE_CACHE["is_live"], _EXCHANGE_CACHE["source"]


def get_current_rate():
    rate, _, _ = get_usd_to_inr_rate_info()
    return rate


def convert_usd_to_inr(amount_usd):
    if amount_usd is None:
        return None
    try:
        usd_val = float(amount_usd)
        rate = get_current_rate()
        return round(usd_val * rate)
    except (ValueError, TypeError):
        return None


def format_inr(amount):
    """
    Formats a numeric amount into Indian Currency standard format:
    e.g. 1250 -> ₹1,250
         125000 -> ₹1,25,000
    """
    if amount is None or amount == "":
        return "₹0"
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return f"₹{amount}"

    is_negative = val < 0
    val = abs(val)

    # Format with 2 decimals
    parts = f"{val:.2f}".split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3

    prefix = "-₹" if is_negative else "₹"
    if decimal_part == "00":
        return f"{prefix}{formatted}"
    return f"{prefix}{formatted}.{decimal_part}"
