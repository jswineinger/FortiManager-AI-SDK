# FortiManager Object List — Skills

## How to Call

Use this tool when:
- Listing ANY FortiManager table — webfilter profiles, DLP sensors, applications, VIPs, custom services, etc.
- Auditing with readable symbolic names via `expand_datasrc` (see category names not just IDs)
- Reading reserved/reference tables via `option: ["get reserved"]`
- Server-side filtering + pagination for large datasets
- Cutting payload via `fields`

**Example prompts:**
- "List all webfilter profile filters with readable category names"
- "Show me DLP sensors in root ADOM"
- "Enumerate all application signatures"
- "Get webfilter categories"

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `fmg_host` | string | Yes | — | FMG hostname/IP |
| `url` | string | Yes | — | Any FMG table URL |
| `fields` | array | No | — | Return only these fields |
| `filter` | array | No | — | Server-side filter, e.g. `[["id","in",33,34]]` |
| `range` | array | No | — | `[offset, limit]` pagination |
| `option` | array | No | — | FMG options: `get reserved`, `extra info`, `no loadsub`, `scope member` |
| `verbose` | integer | No | — | Set `1` for symbolic (string) enum values |
| `expand_datasrc` | array | No | — | Expand name refs to full object data |

## Common Use Cases

### Webfilter filters with readable category names
```python
{
  "url": "/pm/config/adom/root/obj/webfilter/profile/wfp_001/ftgd-wf/filters",
  "expand_datasrc": [
    {"name": "category",
     "datasrc": [{"obj type": "webfilter categories"}]}
  ],
  "verbose": 1
}
# Returns: [{action: "block", category: [{id: "84", obj description: "Web-based Applications"}], ...}]
```

### Reserved reference tables (webfilter categories)
```python
{
  "url": "/pm/config/adom/root/obj/webfilter/categories",
  "option": ["get reserved"]
}
```

### FortiGuard-backed tables (DLP sensors)
```python
{"url": "/pm/config/adom/root/_fdsdb/dlp/sensor", "verbose": 1}
```

### Applications catalog
```python
{"url": "/pm/config/adom/root/_application/list",
 "fields": ["id", "name", "category", "risk", "popularity"],
 "range": [0, 50]}
```

### Filtered policy list
```python
{"url": "/pm/config/adom/root/pkg/default/firewall/policy",
 "filter": [["action", "==", 0]],      # deny rules only
 "verbose": 1}
```

### Custom services
```python
{"url": "/pm/config/adom/root/obj/firewall/service/custom",
 "fields": ["name", "protocol", "tcp-portrange", "udp-portrange"],
 "verbose": 1}
```

## Interpreting Results

```json
{
  "success": true,
  "url": "/pm/config/adom/root/obj/firewall/address",
  "count": 22,
  "data": [ {"name": "addr1", "type": 0}, ... ]
}
```

`data` shape varies by URL:
- Tables → `data` is a list, `count` = array length
- Single entity → `data` is an object, `count` = 1
- Count option → `data` is an integer, `count` = that number

## Example

**User:** "List all webfilter profile filters in `wfp_001` with readable category names"

**Tool call:**
```python
execute_certified_tool(
    canonical_id="org.ulysses.noc.fortimanager-object-list/1.0.0",
    parameters={
        "fmg_host": "192.168.215.17",
        "url": "/pm/config/adom/root/obj/webfilter/profile/wfp_001/ftgd-wf/filters",
        "expand_datasrc": [
            {"name": "category", "datasrc": [{"obj type": "webfilter categories"}]}
        ],
        "verbose": 1
    }
)
# Returns each filter with category expanded to {id, obj description}
```

## Error Handling

| Error | Meaning | Fix |
|---|---|---|
| `FMG {'code': -6, ...}` | Invalid URL or permission | Check path + rpc-permit |
| `FMG {'code': -3, ...}` | Resource doesn't exist | Verify ADOM / parent names |
| `FMG {'code': -11, ...}` | No permission | Admin profile needs rpc-permit read-write |

## Pairs With

- `fortimanager-object-count` — just the count without entries (cheaper)
- `fortimanager-object-schema` — discover valid fields before listing
- `fortimanager-field-datasrc` — alternative way to discover valid name refs
- `fortimanager-object-create/update/delete` — the other CRUD primitives
