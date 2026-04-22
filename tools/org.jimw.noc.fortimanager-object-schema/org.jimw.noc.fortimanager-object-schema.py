#!/usr/bin/env python3
from __future__ import annotations
"""
FortiManager Object Schema

Introspect the schema of any FMG table via option=syntax.

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


def _flatten_fields(attr_dict: Dict[str, Any], include_help: bool) -> List[Dict[str, Any]]:
    """Convert FMG's 'attr' dict into a flat field list."""
    fields: List[Dict[str, Any]] = []
    for name, spec in sorted(attr_dict.items()):
        if not isinstance(spec, dict):
            continue
        field: Dict[str, Any] = {"name": name, "type": spec.get("type") or "unknown"}
        if "default" in spec:
            field["default"] = spec["default"]
        if "opts" in spec and isinstance(spec["opts"], dict):
            field["options"] = spec["opts"]
        if "max" in spec:
            field["max"] = spec["max"]
        if "ref" in spec:
            field["datasrc_refs"] = spec["ref"]
        if spec.get("excluded") is True:
            field["excluded"] = True
        if include_help and spec.get("help"):
            field["help"] = spec["help"]
        fields.append(field)
    return fields


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    fmg_host = params.get("fmg_host")
    if not fmg_host:
        return {"success": False, "error": "Missing required parameter: fmg_host"}
    url = params.get("url")
    if not url:
        return {"success": False, "error": "Missing required parameter: url"}
    summarize = params.get("summarize", True)
    include_help = bool(params.get("include_help", False))

    try:
        client = FortiManagerClient(host=fmg_host)
        resp = client.get(url, option=["syntax"])
        result = resp.get("result", [{}])[0]
        status = result.get("status") or {}
        if status.get("code") != 0:
            return {"success": False, "url": url, "error": f"FMG {status}"}

        data = result.get("data") or {}
        if not summarize:
            return {"success": True, "url": url, "raw": data}

        # Data is typically {"table name": {"alimit": N, "attr": {...}}}.
        # For parent-category queries (e.g. /pm/config/adom/root/obj), there
        # are multiple tables under the root.
        if not isinstance(data, dict):
            return {"success": True, "url": url, "raw": data}

        if len(data) == 1:
            # Single-table case
            table_name, spec = next(iter(data.items()))
            if not isinstance(spec, dict):
                return {"success": True, "url": url, "table_name": table_name,
                        "field_count": 0, "fields": [], "required_datasrc_fields": []}

            attr = spec.get("attr") or {}
            alimit = spec.get("alimit")
            fields = _flatten_fields(attr, include_help)

            required_datasrc = [
                {"name": f["name"], "refs": f["datasrc_refs"]}
                for f in fields
                if f.get("type") == "datasrc" and f.get("datasrc_refs")
            ]

            return {
                "success": True,
                "url": url,
                "table_name": table_name,
                "alimit": alimit,
                "field_count": len(fields),
                "required_datasrc_fields": required_datasrc,
                "fields": fields,
            }

        # Parent-category case: return compact per-table summary + raw
        tables = []
        for tname, spec in data.items():
            if not isinstance(spec, dict):
                continue
            attr = spec.get("attr") or {}
            tables.append({
                "table_name": tname,
                "alimit": spec.get("alimit"),
                "field_count": len(attr),
            })
        return {
            "success": True,
            "url": url,
            "table_count": len(tables),
            "tables": tables,
        }

    except Exception as e:
        logger.exception("object-schema failed")
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


def main(context) -> Dict[str, Any]:
    params = context.parameters if hasattr(context, "parameters") else context
    return asyncio.run(execute(params))


if __name__ == "__main__":
    import json
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.215.17"
    raw = sys.argv[2] if len(sys.argv) > 2 else "/pm/config/adom/root/obj/firewall/address"
    idx = raw.find("/pm/") if "/pm/" in raw else raw.find("/dvmdb/") if "/dvmdb/" in raw else 0
    url = raw[idx:] if idx > 0 else raw
    print(json.dumps(asyncio.run(execute({"fmg_host": host, "url": url, "summarize": True})), indent=2)[:4000])
