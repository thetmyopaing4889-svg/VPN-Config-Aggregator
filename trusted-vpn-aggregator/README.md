# Trusted VPN Aggregator

A safe, GitHub-ready tool that collects public VPN configuration links from trusted allowlisted sources and exports clean subscription files you can import into **Karing**, **Hiddify**, **v2rayNG**, or **NekoBox**.

> ⚠️ **Safety warning:** Free public VPN configs are **NOT safe** for banking, Binance, crypto wallets, Gmail login, or any sensitive account. Use them only for general browsing and always verify trust before routing sensitive traffic.

---

## What it does

- Fetches VPN configs from trusted public GitHub repositories only
- Automatically decodes base64-encoded subscription content
- Extracts and deduplicates configs by protocol (`vless`, `vmess`, `trojan`, `ss`, `hysteria2`, `hy2`, `tuic`)
- Exports clean subscription `.txt` files to the `output/` folder
- Skips any source that fails — no crash, just a warning
- **No TCP checks. No ping. No port scanning. No latency testing.** All delay testing must be done inside your VPN client.

---

## Project structure

```
trusted-vpn-aggregator/
├── README.md
├── sources.json              ← list of trusted source URLs
├── requirements.txt
├── fetch_configs.py          ← HTTP fetcher with retry + base64 detection
├── parse_configs.py          ← config link extractor and deduplicator
├── export_subscription.py    ← full pipeline runner
├── output/
│   ├── configs.txt           ← mixed subscription (up to 5000 configs)
│   ├── all_raw_configs.txt   ← all unique configs, no cap
│   ├── vless.txt
│   ├── vmess.txt
│   ├── trojan.txt
│   ├── ss.txt
│   ├── hysteria2.txt
│   ├── hy2.txt
│   ├── tuic.txt
│   └── summary.json          ← run stats and warnings
└── .github/
    └── workflows/
        └── update-configs.yml  ← daily auto-update via GitHub Actions
```

---

## How to run locally (Replit)

1. Open the **Shell** tab in Replit.

2. Navigate into the project folder:
   ```bash
   cd trusted-vpn-aggregator
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the aggregator:
   ```bash
   python export_subscription.py --max-total 5000 --max-per-protocol 1000
   ```

5. Check the `output/` folder for your subscription files.

### Command line options

| Option | Default | Description |
|---|---|---|
| `--max-total` | 5000 | Max configs in `configs.txt` |
| `--max-per-protocol` | 1000 | Max configs per protocol file |
| `--no-header` | off | Omit comment header from output files |
| `--sources` | `sources.json` | Path to sources file |

---

## How to push to GitHub

1. Create a new repository on GitHub (name it `trusted-vpn-aggregator`).

2. In Replit shell, from the `trusted-vpn-aggregator/` folder:
   ```bash
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/trusted-vpn-aggregator.git
   git push -u origin main
   ```

3. Push updated output files after each run:
   ```bash
   git add output/
   git commit -m "update configs"
   git push
   ```

---

## How to enable GitHub Actions (auto daily update)

1. Go to your GitHub repository → **Settings** → **Actions** → **General**.
2. Under **Workflow permissions**, select **Read and write permissions** → **Save**.
3. Go to **Actions** tab — you will see the `Update VPN Configs` workflow.
4. Click **Run workflow** to test it manually first.
5. After that it will run automatically every day at **03:00 UTC**.

The workflow runs `export_subscription.py` and commits the updated `output/` files back to your repo automatically.

---

## How to use as a subscription URL in your VPN client

After pushing to GitHub, your raw subscription URL will be:

```
https://raw.githubusercontent.com/YOUR-USERNAME/trusted-vpn-aggregator/main/output/configs.txt
```

### Karing
1. Open Karing → **Profiles** → **Add**
2. Select **URL** → paste the raw URL above → **Save**
3. Tap **Update** to fetch configs

### Hiddify
1. Open Hiddify → **Add Profile**
2. Paste the raw URL → **Add**
3. Tap the profile to test and connect

### v2rayNG (Android)
1. Open v2rayNG → Menu (≡) → **Subscription group settings**
2. Tap **+** → paste URL → **OK**
3. Menu → **Update subscription**

### NekoBox (Android)
1. Open NekoBox → **Profiles** → **New group**
2. Enable **Subscription** → paste URL → **OK**
3. Long-press the group → **Update**

> **Tip:** Use your VPN client's built-in delay/speed test to find working servers. Do **not** run TCP checks or ping tests on Replit.

---

## Adding or disabling sources

Edit `sources.json`. Set `"enabled": false` to disable any source without deleting it:

```json
{
  "name": "My Source",
  "url": "https://raw.githubusercontent.com/...",
  "enabled": false,
  "notes": "Disabled because it 404s"
}
```

Only URLs in `sources.json` are ever fetched — the tool never scrapes random websites or uses search engines.

---

## Safety rules (important for Replit users)

- This tool makes **HTTP GET requests only** to the URLs in `sources.json`.
- It does **not** run TCP connectivity checks, ping sweeps, port scans, or latency measurements.
- All working/delay testing must be done **inside Karing, Hiddify, v2rayNG, or NekoBox** — not on Replit.
- Do **not** route sensitive traffic (banking, crypto, email logins) through free public VPN configs.

---

## License

MIT — use freely, no warranty.
