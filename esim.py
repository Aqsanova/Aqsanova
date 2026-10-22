#!/usr/bin/env python3
"""
eSIM Go API connection test (v2.5)
- Uses only the Python standard library (no pip install needed)
- Read-only checks + a "validate" order, which does NOT charge your balance
- Never places a real order

Usage:
    export ESIMGO_API_KEY="your_key_here"      (Windows PowerShell: $env:ESIMGO_API_KEY="your_key_here")
    python3 test_esimgo_api.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://api.esim-go.com/v2.5"
API_KEY = os.environ.get("ESIMGO_API_KEY", "rWxa7lFn3otRcUM28FEO2gr0AyEtxLdj0yH_NDtH").strip()
TEST_BUNDLE = "esim_1GB_7D_NL_V2"  # from the docs; case sensitive


def call(method, path, body=None):
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json",
        # Cloudflare blocks Python's default "Python-urllib" User-Agent (error 1010)
        "User-Agent": "esimgo-connection-test/1.0 (curl-compatible)",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:300]}
    except urllib.error.URLError as e:
        return 0, {"network_error": str(e.reason)}


def explain(status, resp=None):
    if isinstance(resp, dict) and resp.get("error_code") == 1010:
        return ("Cloudflare blocked the client signature (error 1010), not your IP/key. "
                "Make sure the User-Agent header is set; if it still happens, try the curl command from the docs.")
    return {
        0: "Network problem - check your internet/firewall/DNS.",
        401: "API key rejected - re-copy the key from Account Settings > API Details.",
        403: "Forbidden - most often your IP is not whitelisted yet (or you are calling from a different IP than the one you whitelisted). Also check key permissions.",
        429: "Rate limited - wait a moment and retry.",
    }.get(status, "Unexpected response - see details above.")


def check(name, method, path, body=None, show=None):
    status, resp = call(method, path, body)
    ok = 200 <= status < 300
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  (HTTP {status})")
    if ok and show:
        print("       ", show(resp))
    if not ok:
        print("        Response:", json.dumps(resp)[:400])
        print("        Hint:", explain(status, resp))
    return ok


def validate_order():
    """Validate-only order (no charge). The live API wants the bundle inside an
    order-items array; the flat body shown in the Quick Start returns
    'Order must contain Order Items'. Tries 'Order' first, then 'order'."""
    name = "3. Validate order       POST /orders (type=validate, no charge)"
    item = {"type": "bundle", "quantity": 1, "item": TEST_BUNDLE, "allowReassign": False}
    for key in ("Order", "order"):
        status, resp = call("POST", "/orders", {"type": "validate", "assign": True, key: [item]})
        if 200 <= status < 300:
            print(f"[PASS] {name}  (HTTP {status}, body key '{key}')")
            print(f"        Order total: {resp.get('total')}  currency: {resp.get('currency')}")
            return True
        if "Order Items" not in json.dumps(resp):
            break
    print(f"[FAIL] {name}  (HTTP {status})")
    print("        Response:", json.dumps(resp)[:400])
    print("        Hint:", explain(status, resp))
    print("        If the message says the bundle is not found/available, change TEST_BUNDLE "
          "at the top to a name from your own catalogue (case sensitive).")
    return False


def main():
    if not API_KEY:
        sys.exit("Set ESIMGO_API_KEY first (see top of this file).")

    print("Public IP check (this is the IP eSIM Go will see - it must be whitelisted):")
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=10) as r:
            print("   ", r.read().decode())
    except Exception:
        print("    (could not detect - skip)")
    print()

    results = [
        check("1. Auth + IP whitelist  GET /organisation", "GET", "/organisation",
              show=lambda r: "Organisation: " + str(
                  ((r.get("organisations") or [{}])[0]).get("name") or r.get("name") or "OK")),
        check("2. Catalogue            GET /catalogue", "GET", "/catalogue?perPage=5",
              show=lambda r: f"Bundles returned: {len(r.get('bundles', []))}"),
        validate_order(),
    ]

    print()
    if all(results):
        print("ALL GOOD: key works, IP is whitelisted, and ordering would succeed.")
    else:
        print("Some checks failed - fix the first FAIL above, then re-run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
