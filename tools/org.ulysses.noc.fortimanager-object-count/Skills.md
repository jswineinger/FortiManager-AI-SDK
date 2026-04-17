# FortiManager Object Count — Skills

## How to Call

Use this tool when:
- Dashboard widgets — "how many X does tenant Y have?"
- Pagination math — decide how many GET pages to fetch
- Tenant health metrics — "alert if address count > 10000"
- Before-and-after change counts
- Cheap answer — ONE integer versus thousands of full records

**Example prompts:**
- "How many firewall addresses in the root ADOM?"
- "Count the policies in package `default`"
- "How many devices does FMG manage in each ADOM?"

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `fmg_host` | string | Yes | — | FMG hostname/IP |
| `url` | string | Yes | — | Any table URL — see Common URLs below |
| `filter` | array | No | — | Server-side filter `[["attr","op","val"]]` |

## Common URLs

| URL | Counts |
|---|---|
| `/pm/config/adom/{adom}/obj/firewall/address` | Address objects |
| `/pm/config/adom/{adom}/obj/firewall/addrgrp` | Address groups |
| `/pm/config/adom/{adom}/obj/firewall/service/custom` | Custom services |
| `/pm/config/adom/{adom}/obj/firewall/vip` | VIPs |
| `/pm/config/adom/{adom}/pkg/{pkg}/firewall/policy` | Policies in a package |
| `/dvmdb/adom/{adom}/device` | Managed devices in ADOM |
| `/dvmdb/adom` | Total ADOM count |

## Interpreting Results

```json
{
  "success": true,
  "url": "/pm/config/adom/root/obj/firewall/address",
  "count": 22
}
```

## Example

**User:** "How many policies does `howard-sdwan-spoke-1` package have?"

**Tool call:**
```python
execute_certified_tool(
    canonical_id="org.ulysses.noc.fortimanager-object-count/1.0.0",
    parameters={
        "fmg_host": "192.168.215.17",
        "url": "/pm/config/adom/root/pkg/howard-sdwan-spoke-1/firewall/policy"
    }
)
```

## Error Handling

| Error | Meaning | Fix |
|---|---|---|
| `FMG {'code': -6, ...}` | Invalid URL | Check path + ADOM/package spelling |
| `FMG {'code': -3, ...}` | Resource does not exist | ADOM/package missing |
| `Unexpected count response` | FMG returned a non-integer for count | Usually means the URL is a single-entity, not a table — count not applicable |
