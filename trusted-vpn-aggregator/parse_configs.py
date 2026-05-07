"""
parse_configs.py — Extract and deduplicate VPN config links from raw text.

Supported protocols:
  vless://  vmess://  trojan://  ss://  hysteria2://  hy2://  tuic://

Safety rules:
  - Pure text parsing only — no network access whatsoever
  - No TCP checks, no ping, no port scanning
"""

import re
from collections import defaultdict

PROTOCOLS = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "hysteria2://",
    "hy2://",
    "tuic://",
)

# Regex: match a protocol prefix followed by non-whitespace characters
_CONFIG_PATTERN = re.compile(
    r"(?:vless|vmess|trojan|ss|hysteria2|hy2|tuic)://[^\s]+"
)


def extract_configs(raw_text: str) -> list[str]:
    """
    Extract all VPN config links from raw_text.

    Handles links separated by newlines, spaces, or embedded in surrounding text.
    Returns a list of unique config strings preserving first-seen order.
    """
    found = _CONFIG_PATTERN.findall(raw_text)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for link in found:
        link = link.strip().rstrip(".,;\"')")
        if link and link not in seen:
            seen.add(link)
            unique.append(link)

    return unique


def split_by_protocol(configs: list[str]) -> dict[str, list[str]]:
    """
    Split a flat list of config links into per-protocol buckets.

    Returns a dict keyed by protocol prefix (without "://"), e.g.:
      {"vless": [...], "vmess": [...], ...}
    """
    buckets: dict[str, list[str]] = defaultdict(list)
    for link in configs:
        for proto in PROTOCOLS:
            if link.startswith(proto):
                key = proto.rstrip(":/")
                buckets[key].append(link)
                break
    return dict(buckets)


def count_by_protocol(configs: list[str]) -> dict[str, int]:
    """Return a dict of {protocol: count} for a list of config links."""
    buckets = split_by_protocol(configs)
    return {proto: len(links) for proto, links in buckets.items()}


def deduplicate(configs: list[str]) -> list[str]:
    """Remove duplicates from a config list while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for link in configs:
        if link not in seen:
            seen.add(link)
            result.append(link)
    return result


if __name__ == "__main__":
    sample = """
    vless://abc123@host:443?type=tcp#MyVless
    vmess://eyJhZGQiOiJob3N0IiwicG9ydCI6NDQzfQ==
    trojan://password@host:443#Trojan1
    ss://YWVzLTI1Ni1nY206cGFzcw@host:8388#SS1
    hysteria2://auth@host:443
    hy2://auth@host:443
    tuic://uuid:password@host:443
    vless://abc123@host:443?type=tcp#MyVless
    """
    configs = extract_configs(sample)
    counts = count_by_protocol(configs)
    print(f"Unique configs: {len(configs)}")
    print(f"By protocol: {counts}")
    for c in configs:
        print(" ", c)
