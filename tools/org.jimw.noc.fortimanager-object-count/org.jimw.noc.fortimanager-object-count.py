#!/usr/bin/env python3
from __future__ import annotations
"""
FortiManager Object Count

Return the number of entries in any FMG table via GET + option=count.

Author: Ulysses Project
Version: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

_SDK_PATH = Path(__file__).resolve().parents[2] / "sdk"
if _SDK_PATH.exists() and str(_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_SDK_PATH))

from fortimanager_client import FortiManagerClient  # noqa: E402

logger = logging.getLogger(__name__)


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    fmg_host = params.get("fmg_host")
    if not fmg_host:
        return {"success": False, "error": "Missing required parameter: fmg_host"}
    url = params.get("url")
    if not url:
        return {"success": False, "error": "Missing required parameter: url"}
    filter_ = params.get("filter")

    try:
        client = FortiManagerClient(host=fmg_host)
        resp = client.get(url, option=["count"], filter=filter_)
        result = resp.get("result", [{}])[0]
        status = result.get("status") or {}
        if status.get("code") != 0:
            return {"success": False, "url": url, "error": f"FMG {status}"}

        data = result.get("data")
        try:
            count = int(data) if data is not None else 0
        except (TypeError, ValueError):
            return {
                "success": False, "url": url,
                "error": f"Unexpected count response: {data!r}",
            }

        return {"success": True, "url": url, "count": count}

    except Exception as e:
        logger.exception("object-count failed")
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


def main(context) -> Dict[str, Any]:
    params = context.parameters if hasattr(context, "parameters") else context
    return asyncio.run(execute(params))


if __name__ == "__main__":
    import json
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.215.17"
    # Arg may be Git Bash mangled (C:/Program Files/Git/...); strip any prefix
    raw = sys.argv[2] if len(sys.argv) > 2 else "/pm/config/adom/root/obj/firewall/address"
    idx = raw.find("/pm/") if "/pm/" in raw else raw.find("/dvmdb/") if "/dvmdb/" in raw else 0
    url = raw[idx:] if idx > 0 else raw
    print(json.dumps(asyncio.run(execute({"fmg_host": host, "url": url})), indent=2))
