"""
fetch_configs.py — Fetch VPN config text from trusted allowlisted sources only.

Safety rules enforced:
- Only fetches URLs explicitly listed in sources.json
- No TCP checks, no ping, no port scanning
- No scraping of arbitrary websites
- No search engine queries
- No private or paid sources
"""

import base64
import json
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CONNECT_TIMEOUT = 15
READ_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.0


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "TrustedVPNAggregator/1.0"})
    return session


def _is_base64(text: str) -> bool:
    """Detect if content looks like a base64-encoded subscription."""
    stripped = text.strip()
    if len(stripped) < 20:
        return False
    try:
        # Base64 content typically has no protocol prefixes on first line
        first_line = stripped.split("\n")[0].strip()
        if any(first_line.startswith(p) for p in (
            "vless://", "vmess://", "trojan://", "ss://",
            "hysteria2://", "hy2://", "tuic://", "#"
        )):
            return False
        decoded = base64.b64decode(stripped + "==", validate=False)
        decoded_str = decoded.decode("utf-8", errors="ignore")
        return any(p in decoded_str for p in (
            "vless://", "vmess://", "trojan://", "ss://",
            "hysteria2://", "hy2://", "tuic://"
        ))
    except Exception:
        return False


def _decode_base64(text: str) -> str:
    """Attempt to base64-decode subscription content."""
    try:
        decoded = base64.b64decode(text.strip() + "==", validate=False)
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return text


def load_sources(sources_file: str = "sources.json") -> list[dict]:
    """Load and return enabled sources from sources.json."""
    path = Path(sources_file)
    if not path.exists():
        print(f"[ERROR] sources file not found: {sources_file}", file=sys.stderr)
        sys.exit(1)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    all_sources = data.get("sources", [])
    enabled = [s for s in all_sources if s.get("enabled", False)]
    print(f"[INFO] Loaded {len(enabled)} enabled sources out of {len(all_sources)} total.")
    return enabled


def fetch_all(
    sources: list[dict],
    *,
    session: requests.Session | None = None,
) -> tuple[str, list[str], list[str]]:
    """
    Fetch all enabled sources and return (combined_text, succeeded_names, failed_names).

    Parameters
    ----------
    sources : list of source dicts from sources.json
    session : optional requests.Session (one is created if not supplied)

    Returns
    -------
    combined_text  : all raw text concatenated (newline-separated)
    succeeded      : list of source names that were fetched successfully
    failed         : list of source names that failed
    """
    if session is None:
        session = _build_session()

    parts: list[str] = []
    succeeded: list[str] = []
    failed: list[str] = []

    for source in sources:
        name = source.get("name", "<unnamed>")
        url = source.get("url", "").strip()

        if not url:
            print(f"[WARN] Source '{name}' has no URL — skipping.", file=sys.stderr)
            failed.append(name)
            continue

        print(f"[FETCH] {name}  →  {url}")
        try:
            resp = session.get(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
            resp.raise_for_status()
            text = resp.text.strip()

            if not text:
                print(f"[WARN] '{name}' returned empty body — skipping.")
                failed.append(name)
                continue

            if _is_base64(text):
                print(f"[INFO] '{name}' looks base64-encoded — decoding.")
                text = _decode_base64(text)

            parts.append(text)
            succeeded.append(name)
            print(f"[OK]   '{name}' — {len(text):,} chars fetched.")

        except requests.exceptions.Timeout:
            print(f"[WARN] '{name}' timed out — skipping.", file=sys.stderr)
            failed.append(name)
        except requests.exceptions.ConnectionError as exc:
            print(f"[WARN] '{name}' connection error: {exc} — skipping.", file=sys.stderr)
            failed.append(name)
        except requests.exceptions.HTTPError as exc:
            print(f"[WARN] '{name}' HTTP {exc.response.status_code} — skipping.", file=sys.stderr)
            failed.append(name)
        except Exception as exc:
            print(f"[WARN] '{name}' unexpected error: {exc} — skipping.", file=sys.stderr)
            failed.append(name)

        # Small polite delay between requests (no TCP probing — purely HTTP)
        time.sleep(0.3)

    combined = "\n".join(parts)
    print(
        f"\n[FETCH SUMMARY] succeeded={len(succeeded)}, failed={len(failed)}, "
        f"total_chars={len(combined):,}"
    )
    return combined, succeeded, failed


if __name__ == "__main__":
    sources = load_sources()
    combined, ok, fail = fetch_all(sources)
    print(f"\nSucceeded: {ok}")
    print(f"Failed:    {fail}")
    print(f"Total chars fetched: {len(combined):,}")
