#!/usr/bin/env python3
from __future__ import annotations
"""
FortiManager Object List

Generic GET for any FMG table with fields, filter, range, verbose, options,
and expand_datasrc support.

Author: Ulysses Project
Version: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    fields = params.get("fields")
    filter_ = params.get("filter")
    range_ = params.get("range")
    option = params.get("option")
    verbose = params.get("verbose")
    expand_datasrc = params.get("expand_datasrc")

    try:
        client = FortiManagerClient(host=fmg_host)
        # Ensure session for session auth
        if client.auth_method == "session" and not client.session:
            client.login()

        # Build the params dict — we need direct control for expand_datasrc
        req_params: Dict[str, Any] = {"url": url}
        if fields is not None:
            req_params["fields"] = list(fields)
        if filter_ is not None:
            req_params["filter"] = filter_
        if range_ is not None:
            req_params["range"] = list(range_)
        if option is not None:
            req_params["option"] = option if isinstance(option, list) else [option]
        if expand_datasrc is not None:
            req_params["expand datasrc"] = expand_datasrc

        payload: Dict[str, Any] = {
            "id": client._next_id(),
            "method": "get",
            "params": [req_params],
        }
        if client.session:
            payload["session"] = client.session
        if verbose is not None:
            payload["verbose"] = int(verbose)

        resp = client._request(payload)
        result = resp.get("result", [{}])[0]
        status = result.get("status") or {}
        if status.get("code") != 0:
            return {"success": False, "url": url, "error": f"FMG {status}"}

        data = result.get("data")
        count: Optional[int]
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict):
            count = 1
        elif isinstance(data, int):
            # Count option returns an int
            count = data
        else:
            count = None

        return {
            "success": True,
            "url": url,
            "count": count,
            "data": data,
        }

    except Exception as e:
        logger.exception("object-list failed")
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


def main(context) -> Dict[str, Any]:
    params = context.parameters if hasattr(context, "parameters") else context
    return asyncio.run(execute(params))


if __name__ == "__main__":
    import json
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.215.17"
    # Default smoke: list addresses with fields
    print(json.dumps(asyncio.run(execute({
        "fmg_host": host,
        "url": "/pm/config/adom/root/obj/firewall/address",
        "fields": ["name", "type"],
        "range": [0, 5],
    })), indent=2))
