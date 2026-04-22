#!/usr/bin/env python3
from __future__ import annotations
"""
FortiManager Object Checksum

Return chksum (table version int) or devinfo (ADOM UUID) for change detection.

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
    mode = (params.get("mode") or "chksum").lower()
    if mode not in {"chksum", "devinfo"}:
        return {"success": False, "error": f"Invalid mode {mode!r}. Use: chksum | devinfo"}

    try:
        client = FortiManagerClient(host=fmg_host)
        resp = client.get(url, option=[mode])
        result = resp.get("result", [{}])[0]
        status = result.get("status") or {}
        if status.get("code") != 0:
            return {"success": False, "url": url, "mode": mode, "error": f"FMG {status}"}

        data = result.get("data")
        # chksum returns an int; devinfo returns {"uuid": "..."}
        if mode == "devinfo":
            if isinstance(data, dict) and data.get("uuid"):
                value = data["uuid"]
            else:
                return {"success": False, "url": url, "mode": mode,
                        "error": f"Unexpected devinfo response: {data!r}"}
        else:
            try:
                value = str(int(data))
            except (TypeError, ValueError):
                return {"success": False, "url": url, "mode": mode,
                        "error": f"Unexpected chksum response: {data!r}"}

        return {"success": True, "url": url, "mode": mode, "value": value}

    except Exception as e:
        logger.exception("object-checksum failed")
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
    mode = sys.argv[3] if len(sys.argv) > 3 else "chksum"
    print(json.dumps(asyncio.run(execute({"fmg_host": host, "url": url, "mode": mode})), indent=2))
