#!/usr/bin/env python3
from __future__ import annotations
"""
FortiManager Field Datasrc

For a given table+field, return the valid source-table entries that can be
referenced in that field. Uses GET with option=datasrc + attr=<field>.

Author: Ulysses Project
Version: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

_SDK_PATH = Path(__file__).resolve().parents[2] / "sdk"
if _SDK_PATH.exists() and str(_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_SDK_PATH))

from fortimanager_client import FortiManagerClient  # noqa: E402

logger = logging.getLogger(__name__)

# Compact representation — pick a few identifying fields per item to avoid
# overwhelming the LLM. Extend as needed.
_IDENT_FIELDS = ("name", "mkey", "id", "policyid", "obj description")


def _compact(entry: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(entry, dict):
        return {"value": entry}
    compact = {}
    for k in _IDENT_FIELDS:
        if k in entry and entry[k] not in (None, ""):
            compact[k] = entry[k]
    if not compact and entry:
        first = next(iter(entry.items()))
        compact[first[0]] = first[1]
    return compact


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    fmg_host = params.get("fmg_host")
    if not fmg_host:
        return {"success": False, "error": "Missing required parameter: fmg_host"}
    url = params.get("url")
    if not url:
        return {"success": False, "error": "Missing required parameter: url"}
    attr = params.get("attr")
    if not attr:
        return {"success": False, "error": "Missing required parameter: attr (field name)"}
    max_per_cat = int(params.get("max_per_category", 50))

    try:
        client = FortiManagerClient(host=fmg_host)
        # Ensure session — login if session-auth
        if client.auth_method == "session" and not client.session:
            client.login()

        # Construct the raw JSON-RPC call since `attr` isn't a first-class client arg
        payload: Dict[str, Any] = {
            "id": client._next_id(),
            "method": "get",
            "params": [{
                "url": url,
                "attr": attr,
                "option": "datasrc",
            }],
        }
        if client.session:
            payload["session"] = client.session

        resp = client._request(payload)
        result = resp.get("result", [{}])[0]
        status = result.get("status") or {}
        if status.get("code") != 0:
            return {"success": False, "url": url, "attr": attr, "error": f"FMG {status}"}

        data = result.get("data") or {}
        if not isinstance(data, dict):
            return {"success": False, "url": url, "attr": attr,
                    "error": f"Unexpected datasrc shape: {type(data).__name__}"}

        categories: List[Dict[str, Any]] = []
        for cat_name, entries in data.items():
            if not isinstance(entries, list):
                continue
            total = len(entries)
            compact_items = [_compact(e) for e in entries[:max_per_cat]]
            categories.append({
                "category": cat_name,
                "total": total,
                "items": compact_items,
            })

        return {
            "success": True,
            "url": url,
            "attr": attr,
            "category_count": len(categories),
            "categories": categories,
        }

    except Exception as e:
        logger.exception("field-datasrc failed")
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


def main(context) -> Dict[str, Any]:
    params = context.parameters if hasattr(context, "parameters") else context
    return asyncio.run(execute(params))


if __name__ == "__main__":
    import json
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.215.17"
    raw = sys.argv[2] if len(sys.argv) > 2 else "/pm/config/adom/root/pkg/howard-sdwan-spoke-1/firewall/policy"
    idx = raw.find("/pm/") if "/pm/" in raw else raw.find("/dvmdb/") if "/dvmdb/" in raw else 0
    url = raw[idx:] if idx > 0 else raw
    attr = sys.argv[3] if len(sys.argv) > 3 else "srcaddr"
    print(json.dumps(asyncio.run(execute({
        "fmg_host": host, "url": url, "attr": attr, "max_per_category": 20
    })), indent=2)[:4000])
