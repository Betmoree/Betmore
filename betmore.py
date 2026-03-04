import argparse
import base64
import json
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc.types import TxOpts

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG DEFAULTS
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_RPC_URL = "https://api.mainnet-beta.solana.com"
ENV_RPC_URL = "SOL_RPC_URL"

LAMPORTS_PER_SOL = 1_000_000_000
SOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL mint

# Jupiter Swap API v1
JUPITER_QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
JUPITER_SWAP_URL = "https://api.jup.ag/swap/v1/swap"

DEFAULT_BUY_PERCENT = 0.10       # 0.10 = 10 percent. For 0.3 percent use 0.003
DEFAULT_INTERVAL_SEC = 33
DEFAULT_SOL_FLOOR = 0.08
DEFAULT_TAPER_BUFFER = 0.09
DEFAULT_SLIPPAGE_BPS = 500       # 500 bps = 5 percent
DEFAULT_PRIORITY_FEE = 100_000   # micro-lamports

HTTP_TIMEOUT = 20
HTTP_RETRIES = 3
HTTP_BACKOFF_SEC = 1.5

# ──────────────────────────────────────────────────────────────────────────────


def print_banner() -> None:
    print()
    print("██████╗ ███████╗████████╗     ███╗   ███╗ ██████╗ ██████╗ ███████╗")
    print("██╔══██╗██╔════╝╚══██╔══╝     ████╗ ████║██╔═══██╗██╔══██╗██╔════╝")
    print("██████╔╝█████╗     ██║        ██╔████╔██║██║   ██║██████╔╝█████╗")
    print("██╔══██╗██╔══╝     ██║        ██║╚██╔╝██║██║   ██║██╔══██╗██╔══╝")
    print("██████╔╝███████╗   ██║        ██║ ╚═╝ ██║╚██████╔╝██║  ██║███████╗")
    print()
    print("                BET MORE TECH v1")
    print("=" * 55)
    print()


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_keypair_from_json(path: str) -> Keypair:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Keypair JSON must be a list of ints (Solana id.json format).")

    return Keypair.from_bytes(bytes(data))


def get_sol_balance(client: Client, pubkey: Pubkey) -> float:
    resp = client.get_balance(pubkey)
    return resp.value / LAMPORTS_PER_SOL


def compute_buy_amount(balance: float, buy_percent: float, sol_floor: float, taper_buffer: float) -> float:
    available = balance - sol_floor
    if available <= 0:
        return 0.0

    raw = balance * buy_percent

    if available < taper_buffer:
        raw *= (available / taper_buffer)

    if raw > available:
        raw = available * 0.9

    return max(0.0, raw)


def _headers_with_jup_key() -> Dict[str, str]:
    api_key = os.getenv("JUP_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JUP_API_KEY is not set in this terminal session.")
    return {"x-api-key": api_key}


def _request_with_retries(method: str, url: str, **kwargs) -> requests.Response:
    last_err: Optional[Exception] = None
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            return requests.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)
        except Exception as e:
            last_err = e
            if attempt < HTTP_RETRIES:
                time.sleep(HTTP_BACKOFF_SEC * attempt)
    raise last_err  # type: ignore


def get_jupiter_quote(input_mint: str, output_mint: str, amount_lamports: int, slippage_bps: int) -> Dict[str, Any]:
    # IMPORTANT: Jupiter expects lowercase "true"/"false"
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": str(amount_lamports),
        "slippageBps": str(slippage_bps),
        "swapMode": "ExactIn",
        "restrictIntermediateTokens": "true",
    }

    resp = _request_with_retries(
        "GET",
        JUPITER_QUOTE_URL,
        params=params,
        headers=_headers_with_jup_key(),
    )

    if resp.status_code != 200:
        raise Exception(f"Jupiter quote HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        raise Exception(f"Jupiter quote error: {data['error']}")
    return data


def get_jupiter_swap_tx(quote: Dict[str, Any], payer_pubkey: str, priority_fee: int) -> str:
    payload = {
        "quoteResponse": quote,
        "userPublicKey": payer_pubkey,
        "wrapAndUnwrapSol": True,
        "prioritizationFeeLamports": priority_fee,
        "dynamicComputeUnitLimit": True,
    }

    headers = {"Content-Type": "application/json", **_headers_with_jup_key()}
    resp = _request_with_retries("POST", JUPITER_SWAP_URL, json=payload, headers=headers)

    if resp.status_code != 200:
        raise Exception(f"Jupiter swap HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        raise Exception(f"Jupiter swap error: {data['error']}")
    return data["swapTransaction"]


def buy_token(client: Client, payer: Keypair, mint: str, sol_amount: float, slippage_bps: int, priority_fee: int) -> str:
    lamports = int(sol_amount * LAMPORTS_PER_SOL)

    log(f"Getting Jupiter quote: {sol_amount:.6f} SOL -> {mint[:8]}...")
    quote = get_jupiter_quote(SOL_MINT, mint, lamports, slippage_bps)

    log(f"Expected output (raw units): {quote.get('outAmount', '0')}")

    log("Building swap transaction...")
    swap_tx_b64 = get_jupiter_swap_tx(quote, str(payer.pubkey()), priority_fee)

    raw_tx = base64.b64decode(swap_tx_b64)
    tx = VersionedTransaction.from_bytes(raw_tx)

    signed_tx = VersionedTransaction(tx.message, [payer])

    opts = TxOpts(skip_preflight=False, preflight_commitment="confirmed", max_retries=3)
    sig = client.send_raw_transaction(bytes(signed_tx), opts=opts).value

    log(f"TX sent: https://solscan.io/tx/{sig}")
    client.confirm_transaction(sig, commitment="confirmed")
    log("TX confirmed OK")

    # Print banner after each buy + tx confirmation
    print_banner()

    return sig


def main() -> None:
    parser = argparse.ArgumentParser(description="Bet More Tech v1")
    parser.add_argument("--rpc", default=os.getenv(ENV_RPC_URL, DEFAULT_RPC_URL), help="Solana RPC URL")
    parser.add_argument("--mint", required=True, help="Token mint address to buy")
    parser.add_argument("--keypair", required=True, help="Path to Solana keypair JSON (id.json)")

    # No percent characters in help strings (your argparse build treats percent as formatting)
    parser.add_argument("--buy-percent", type=float, default=DEFAULT_BUY_PERCENT, help="Balance fraction to spend each cycle")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SEC, help="Seconds between buys")
    parser.add_argument("--sol-floor", type=float, default=DEFAULT_SOL_FLOOR, help="Minimum SOL to keep")
    parser.add_argument("--taper-buffer", type=float, default=DEFAULT_TAPER_BUFFER, help="Taper when close to floor")
    parser.add_argument("--slippage-bps", type=int, default=DEFAULT_SLIPPAGE_BPS, help="Slippage in basis points")
    parser.add_argument("--priority-fee", type=int, default=DEFAULT_PRIORITY_FEE, help="Priority fee in micro-lamports")

    args = parser.parse_args()

    # Startup banner
    print_banner()

    # Fail fast if Jupiter key missing
    if not os.getenv("JUP_API_KEY", "").strip():
        log('FATAL: JUP_API_KEY not set. PowerShell: $env:JUP_API_KEY="YOUR_KEY"')
        return

    payer = load_keypair_from_json(args.keypair)

    # Validate mint
    Pubkey.from_string(args.mint)

    client = Client(args.rpc)

    log(f"Wallet : {payer.pubkey()}")
    log(f"Token  : {args.mint}")
    log(f"Floor  : {args.sol_floor} SOL | Buy fraction: {args.buy_percent} every {args.interval}s")
    log("Route  : Jupiter Swap API v1")
    log("-" * 45)

    cycle = 0
    while True:
        cycle += 1
        log(f"\n-- Cycle {cycle} --")
        try:
            balance = get_sol_balance(client, payer.pubkey())
            buy_amount = compute_buy_amount(balance, args.buy_percent, args.sol_floor, args.taper_buffer)

            log(f"Balance : {balance:.6f} SOL")

            if buy_amount <= 0:
                log("Balance at or below floor. Skipping.")
            else:
                log(f"Buy amount: {buy_amount:.6f} SOL")
                buy_token(client, payer, args.mint, buy_amount, args.slippage_bps, args.priority_fee)

        except KeyboardInterrupt:
            log("Stopped by user. Goodbye.")
            break
        except Exception as err:
            log(f"ERROR ({type(err).__name__}): {err!r}")
            traceback.print_exc()

        log(f"Sleeping {args.interval}s...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
