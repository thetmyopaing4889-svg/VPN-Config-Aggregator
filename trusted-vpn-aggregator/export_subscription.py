"""
export_subscription.py — Run the full safe VPN aggregator pipeline.

Pipeline:
  1. Load sources from sources.json
  2. Fetch enabled sources (HTTP only — no TCP probing)
  3. Extract and deduplicate VPN config links
  4. Apply per-protocol and total caps
  5. Export output files and summary.json

Safety rules enforced:
  - No TCP checks, no ping, no port scanning
  - No latency testing
  - No bulk connection tests
  - Only HTTP GET requests to allowlisted GitHub raw URLs
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fetch_configs import fetch_all, load_sources
from parse_configs import count_by_protocol, extract_configs, split_by_protocol

OUTPUT_DIR = Path("output")

PROTOCOL_FILES: dict[str, str] = {
    "vless": "vless.txt",
    "vmess": "vmess.txt",
    "trojan": "trojan.txt",
    "ss": "ss.txt",
    "hysteria2": "hysteria2.txt",
    "hy2": "hy2.txt",
    "tuic": "tuic.txt",
}

SUBSCRIPTION_HEADER = (
    "# Trusted VPN Aggregator — https://github.com/your-username/trusted-vpn-aggregator\n"
    "# Auto-generated. Import this URL into Karing / Hiddify / v2rayNG / NekoBox.\n"
    "# WARNING: Free public VPN configs are NOT safe for banking, crypto, or sensitive accounts.\n"
    "#          Test working configs inside your VPN client — do NOT run TCP/ping tests here.\n\n"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trusted VPN Aggregator — safe subscription exporter"
    )
    parser.add_argument(
        "--sources",
        default="sources.json",
        help="Path to sources.json (default: sources.json)",
    )
    parser.add_argument(
        "--max-total",
        type=int,
        default=5000,
        help="Maximum total configs in configs.txt (default: 5000)",
    )
    parser.add_argument(
        "--max-per-protocol",
        type=int,
        default=1000,
        help="Maximum configs per protocol file (default: 1000)",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Omit the comment header from output files",
    )
    return parser.parse_args()


def write_text_file(path: Path, lines: list[str], header: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write("\n".join(lines))
        if lines:
            f.write("\n")


def main() -> None:
    args = parse_args()
    warnings: list[str] = []
    run_ts = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("  Trusted VPN Aggregator")
    print(f"  Run: {run_ts}")
    print("=" * 60)
    print()

    # ── 1. Load sources ──────────────────────────────────────────
    sources = load_sources(args.sources)
    total_sources = len(sources)
    print()

    # ── 2. Fetch ─────────────────────────────────────────────────
    combined_text, succeeded, failed = fetch_all(sources)
    print()

    if failed:
        for name in failed:
            warnings.append(f"Source failed or returned no data: {name}")

    # ── 3. Parse ─────────────────────────────────────────────────
    print("[PARSE] Extracting config links from fetched text …")
    all_configs = extract_configs(combined_text)
    print(f"[PARSE] Found {len(all_configs):,} unique configs total.")
    print()

    if not all_configs:
        warnings.append("No VPN configs were extracted. Check sources or network access.")

    # ── 4. Split by protocol ──────────────────────────────────────
    buckets = split_by_protocol(all_configs)

    # ── 5. Export per-protocol files ─────────────────────────────
    OUTPUT_DIR.mkdir(exist_ok=True)
    header = "" if args.no_header else SUBSCRIPTION_HEADER
    file_counts: dict[str, int] = {}

    for proto, filename in PROTOCOL_FILES.items():
        links = buckets.get(proto, [])
        capped = links[: args.max_per_protocol]
        out_path = OUTPUT_DIR / filename
        write_text_file(out_path, capped, header)
        file_counts[filename] = len(capped)
        if len(links) > args.max_per_protocol:
            warnings.append(
                f"{proto}: capped at {args.max_per_protocol} "
                f"(total available: {len(links)})"
            )
        print(f"[EXPORT] {out_path}  →  {len(capped):,} configs")

    # ── 6. Export all_raw_configs.txt ────────────────────────────
    all_raw_path = OUTPUT_DIR / "all_raw_configs.txt"
    write_text_file(all_raw_path, all_configs)
    file_counts["all_raw_configs.txt"] = len(all_configs)
    print(f"[EXPORT] {all_raw_path}  →  {len(all_configs):,} configs")

    # ── 7. Export configs.txt (mixed, capped) ────────────────────
    mixed_capped = all_configs[: args.max_total]
    configs_path = OUTPUT_DIR / "configs.txt"
    write_text_file(configs_path, mixed_capped, header)
    file_counts["configs.txt"] = len(mixed_capped)
    if len(all_configs) > args.max_total:
        warnings.append(
            f"configs.txt capped at {args.max_total} "
            f"(total available: {len(all_configs)})"
        )
    print(f"[EXPORT] {configs_path}  →  {len(mixed_capped):,} configs (mixed, capped)")

    # ── 8. Export summary.json ───────────────────────────────────
    counts_by_proto = {p: len(v) for p, v in buckets.items()}
    summary = {
        "run_timestamp_utc": run_ts,
        "total_fetched_sources": total_sources,
        "succeeded_sources": len(succeeded),
        "failed_sources": len(failed),
        "failed_source_names": failed,
        "total_unique_configs": len(all_configs),
        "counts_by_protocol": counts_by_proto,
        "output_file_counts": file_counts,
        "max_total_cap": args.max_total,
        "max_per_protocol_cap": args.max_per_protocol,
        "warnings": warnings,
    }
    summary_path = OUTPUT_DIR / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[EXPORT] {summary_path}  →  summary written")

    # ── 9. Final report ──────────────────────────────────────────
    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Sources succeeded : {len(succeeded)} / {total_sources}")
    print(f"  Sources failed    : {len(failed)}")
    print(f"  Total unique configs extracted : {len(all_configs):,}")
    print()
    print("  Configs by protocol:")
    for proto, count in sorted(counts_by_proto.items()):
        print(f"    {proto:<12} {count:>6,}")
    print()
    print(f"  Mixed subscription file : {configs_path.resolve()}")
    print(f"  Summary JSON           : {summary_path.resolve()}")
    if warnings:
        print()
        print("  Warnings:")
        for w in warnings:
            print(f"    ⚠  {w}")
    print()
    print("  Import configs.txt into Karing / Hiddify / v2rayNG / NekoBox.")
    print("  After pushing to GitHub, use the raw URL as your subscription link.")
    print("=" * 60)


if __name__ == "__main__":
    main()
