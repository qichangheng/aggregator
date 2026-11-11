# -*- coding: utf-8 -*-

# Fork customization: only keep encrypted proxy protocols.
# Plain-text protocols (http, socks5) are removed after the liveness
# check and before the subscription files are generated and pushed.

import argparse
import json
import os
import sys
from collections import Counter

from logger import logger

# Unencrypted proxy protocols (Clash "type" field, case-insensitive)
UNENCRYPTED_TYPES = ("http", "socks5")

# sing-box names for the same protocols
SINGBOX_UNENCRYPTED_TYPES = ("http", "socks", "socks5")


def proxy_type(proxy) -> str:
    if not isinstance(proxy, dict):
        return ""
    value = proxy.get("type", "")
    if isinstance(value, str):
        return value.strip().lower()
    return str(value or "").strip().lower()


def drop_unencrypted(proxies, unencrypted=UNENCRYPTED_TYPES):
    """Remove proxies whose type is an unencrypted protocol; keep everything else unchanged."""
    if not proxies:
        return []
    removed = Counter()
    kept = []
    for proxy in proxies:
        ptype = proxy_type(proxy)
        if ptype in unencrypted:
            removed[ptype] += 1
            continue
        kept.append(proxy)
    total = sum(removed.values())
    if total:
        detail = ", ".join(f"{name}: {count}" for name, count in sorted(removed.items()))
        logger.info(f"drop unencrypted protocols: removed {total} nodes ({detail}), kept {len(kept)} nodes")
    else:
        logger.info(f"drop unencrypted protocols: no unencrypted nodes found, kept {len(kept)} nodes")
    return kept


def filter_clash_file(path):
    """Filter a generated Clash YAML file in place and return {"removed": n, "kept": n}."""
    import yaml

    with open(path, "r", encoding="utf8") as f:
        data = yaml.safe_load(f) or {}
    proxies = data.get("proxies", []) if isinstance(data, dict) else []
    kept = drop_unencrypted(proxies)
    removed = len(proxies) - len(kept)
    if removed:
        data["proxies"] = kept
        with open(path, "w", encoding="utf8") as f:
            yaml.dump(data, f, allow_unicode=True)
    return {"removed": removed, "kept": len(kept)}


def filter_singbox_file(path):
    """Filter a generated sing-box JSON file in place and return {"removed": n, "kept": n}."""
    with open(path, "r", encoding="utf8") as f:
        data = json.load(f) or {}
    outbounds = data.get("outbounds", []) if isinstance(data, dict) else []
    kept = drop_unencrypted(outbounds, SINGBOX_UNENCRYPTED_TYPES)
    removed = len(outbounds) - len(kept)
    if removed:
        data["outbounds"] = kept
        with open(path, "w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return {"removed": removed, "kept": len(kept)}


def main():
    parser = argparse.ArgumentParser(description="Remove unencrypted (http/socks5) proxies from a subscription file.")
    parser.add_argument("path", help="clash YAML file (.yaml/.yml) or sing-box JSON file (.json)")
    args = parser.parse_args()
    path = args.path
    if not os.path.isfile(path):
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    if path.lower().endswith(".json"):
        result = filter_singbox_file(path)
    else:
        result = filter_clash_file(path)
    print(f"removed {result['removed']} unencrypted nodes, kept {result['kept']} nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
