# 🤖 Bet More Tech v1

> A Solana auto-buyer that swaps SOL → target token using **Jupiter Swap API v1**

The bot periodically buys a token using a percentage of your wallet balance while protecting a minimum SOL floor.

---

## ✨ Features

- Jupiter Swap API v1 quote + swap
- SOL floor protection + tapering
- Priority fee support
- Clean terminal banner
- Prints banner after each confirmed buy + transaction link

---

## 📋 Requirements

- Python 3.10+
- A Solana wallet keypair file (`id.json`)
- A Jupiter API key

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/betmore-tech-v1.git
cd betmore-tech-v1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🔑 Wallet Setup

> ⚠️ **IMPORTANT**

You must provide a Solana keypair file. This is typically the same file used by the Solana CLI.

**Place `id.json` in the project folder next to `betmore.py`:**

```
betmore-tech-v1/
│
├── betmore.py
├── id.json
├── requirements.txt
├── README.md
```

> 🚨 **Never upload `id.json` to GitHub.** Your `.gitignore` should already exclude it.

---

## 🪐 Jupiter API Key Setup

The bot reads your Jupiter API key from an environment variable.

**Windows (PowerShell) — Temporary session:**

```powershell
$env:JUP_API_KEY="YOUR_JUPITER_API_KEY"
```

**Windows (PowerShell) — Permanent:**

```powershell
setx JUP_API_KEY "YOUR_JUPITER_API_KEY"
```

> Restart PowerShell after using `setx`.

---

## ⚡ Optional RPC Setup (Recommended)

You can use:
- Solana public RPC
- [Helius](https://helius.dev)
- [QuickNode](https://quicknode.com)
- [Triton](https://triton.one)

**Example using Helius:**

```powershell
$env:SOL_RPC_URL="https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_KEY"
```

Then launch with:

```powershell
py betmore.py --rpc $env:SOL_RPC_URL --mint TOKEN_MINT --keypair id.json
```

---

## ▶️ Running the Bot

**Basic launch command:**

```bash
py betmore.py --mint TOKEN_MINT --keypair id.json
```

**Example:**

```bash
py betmore.py --mint H4hioLVHLuG4YLYrc7xzqNQe5JhsjKrv5rEFfbbRpump --keypair id.json
```

### Optional Parameters

| Parameter | Description |
|---|---|
| `--buy-percent` | Percent of wallet to buy each cycle |
| `--interval` | Seconds between buys |
| `--sol-floor` | Minimum SOL balance to keep |
| `--slippage-bps` | Slippage in basis points |
| `--priority-fee` | Priority fee in micro-lamports |

**Example with custom settings:**

```bash
py betmore.py \
  --mint TOKEN_MINT \
  --keypair id.json \
  --buy-percent 0.003 \
  --interval 10 \
  --slippage-bps 500
```

**Recommended settings:**

```
--buy-percent 0.003
--interval 10
```

---

## 🖥️ Example Output

```
██████╗ ███████╗████████╗     ███╗   ███╗ ██████╗ ██████╗ ███████╗
██╔══██╗██╔════╝╚══██╔══╝     ████╗ ████║██╔═══██╗██╔══██╗██╔════╝
██████╔╝█████╗     ██║        ██╔████╔██║██║   ██║██████╔╝█████╗
██╔══██╗██╔══╝     ██║        ██║╚██╔╝██║██║   ██║██╔══██╗██╔══╝
██████╔╝███████╗   ██║        ██║ ╚═╝ ██║╚██████╔╝██║  ██║███████╗

BET MORE TECH v1
=======================================================

Balance   : 0.190 SOL
Buy amount: 0.019 SOL
TX sent   : https://solscan.io/tx/...
TX confirmed
```

---

## 🔐 Security Notes

- Never share `id.json`
- Never commit private keys to version control
- Rotate any API keys that have been posted publicly
- Use a burner wallet for testing

---

## ⚠️ Disclaimer

This software is **experimental**. Use at your own risk. The author is not responsible for any financial losses incurred through use of this software.
