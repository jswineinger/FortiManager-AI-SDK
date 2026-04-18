# Playbook: SD-WAN Spoke Onboarding

## Goal

Build a complete SD-WAN configuration on a managed FortiGate spoke from scratch — zones, members, health-checks, services, ADVPN neighbor — following the SDWAN corpus 3-layer pattern (underlay assumed already in place: WAN interface, IPsec phase1/phase2, BGP). This playbook focuses on **layer 3** (the SD-WAN object stack itself).

## When to Run

- New site provisioning after IPsec tunnels are up + BGP peering is established
- Re-bootstrap after `sdwan-config-audit` flagged a mostly-empty / corrupt config
- Bulk MSSP rollout — one playbook run per spoke from a metadata variable set

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `fmg_host` | Yes | — | FMG IP/hostname |
| `adom` | No | `root` | ADOM containing the device |
| `device` | Yes | — | Spoke device name |
| `vdom` | No | `root` | VDOM for SD-WAN |
| `site_id` | Yes | — | Numeric site ID — drives seq-num convention (site_id × 100, +1) |
| `loopback_ip` | Yes | — | Spoke identity IP (corpus: `172.16.0.{site_id}`) — used as `source` on overlay members |
| `hub_loopback_ip` | Yes | — | Hub's primary loopback (corpus example: `172.16.255.253`) — probed by HUB_Health |
| `overlay_interfaces` | Yes | — | Tunnel interface names already configured, e.g. `["HUB1-VPN1", "HUB2-VPN2"]` |
| `wan_interface` | No | `wan` | Direct internet breakout interface |
| `wan_seq_num` | No | `2` | seq-num for the wan member (per corpus) |
| `zone_name` | No | `SDWAN-HUB` | Name for the hub-overlay zone |
| `enable_advpn` | No | `true` | Set ADVPN on the zone for spoke-to-spoke shortcuts |
| `dry_run` | No | `false` | If true, preview the operations without applying |

## Prerequisites

Before running this playbook, verify (manually or with `sdwan-config-audit`):

- [ ] Tunnel interfaces named in `overlay_interfaces` exist (created by IPsec phase1)
- [ ] Loopback interface with `loopback_ip` exists on device
- [ ] BGP neighbor to hub (`hub_loopback_ip`) is configured + UP
- [ ] WAN interface has IP + default gateway

If any prerequisite missing → STOP and tell the user. Do not partial-build.

## Procedure

### Step 0 — Pre-flight checks

```python
# Verify the device exists and is online
devs = device-list({"fmg_host": fmg_host, "adom": adom})
device_record = next((d for d in devs["devices"] if d["name"] == device), None)
if not device_record:
    return {"error": f"Device {device} not found in ADOM {adom}"}
if device_record["conn_status"] != 1:
    return {"error": f"Device {device} is not online (conn_status={device_record['conn_status']})"}

# Verify SD-WAN config doesn't already exist (avoid clobber)
existing = object-list({
    "fmg_host": fmg_host,
    "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan/zone"
})
if existing["count"] > 1:   # virtual-wan-link is the default zone, count=1 means empty
    return {"error": "SD-WAN already configured. Run sdwan-config-audit first; use sdwan-spoke-update for incremental changes."}
```

### Step 1 — Create the SD-WAN zone

```python
object-create({
    "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan/zone",
    "data": {
        "name": zone_name,
        "advpn-select": 1 if enable_advpn else 0,
        "advpn-health-check": ["HUB_Health"] if enable_advpn else [],
        "service-sla-tie-break": 1,        # cfg-order — corpus default
        "minimum-sla-meet-members": 1
    }
})
```

### Step 2 — Add members (overlays first, then wan)

For each overlay interface, allocate a seq-num: `site_id * 100 + index` (HUB1=100, HUB2=101 for site 1; HUB1=200 for site 2).

```python
for idx, iface in enumerate(overlay_interfaces):
    seq = site_id * 100 + idx
    object-create({
        "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan/members",
        "data": {
            "seq-num": seq,
            "interface": [iface],
            "source": loopback_ip,    # CORPUS CONVENTION
            "zone": [zone_name],
            "priority-in-sla": 10,
            "priority-out-sla": 20,
            "status": 1
        }
    })

# Direct internet member (wan)
object-create({
    "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan/members",
    "data": {
        "seq-num": wan_seq_num,
        "interface": [wan_interface],
        "zone": [zone_name],
        "status": 1
    }
})
```

### Step 3 — Create health-checks

Two minimum: HUB_Health (probes hub loopback over overlays) and Public_SLA (probes 8.8.8.8 / 4.2.2.2 over wan).

```python
overlay_seqs = [site_id * 100 + i for i in range(len(overlay_interfaces))]

object-create({
    "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan/health-check",
    "data": {
        "name": "HUB_Health",
        "server": [hub_loopback_ip],
        "members": [str(s) for s in overlay_seqs],
        "protocol": 1,                # ping
        "interval": 500,
        "probe-timeout": 500,
        "failtime": 5,
        "recoverytime": 5,
        "embed-measured-health": 1,
        "sla": [{
            "id": 1,
            "latency-threshold": 200,
            "jitter-threshold": 50,
            "packetloss-threshold": 5
        }]
    }
})

object-create({
    "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan/health-check",
    "data": {
        "name": "Public_SLA",
        "server": ["8.8.8.8", "4.2.2.2"],
        "members": [str(wan_seq_num)],
        "protocol": 1,
        "interval": 500,
        "probe-timeout": 500,
        "sla": [{
            "id": 1,
            "latency-threshold": 5,
            "jitter-threshold": 5,
            "packetloss-threshold": 0
        }]
    }
})
```

### Step 4 — Add ADVPN neighbor (if enable_advpn)

```python
if enable_advpn:
    object-create({
        "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan/neighbor",
        "data": {
            "ip": [hub_loopback_ip],
            "member": [str(s) for s in overlay_seqs],
            "health-check": ["HUB_Health"],
            "minimum-sla-meet-members": 1,
            "mode": 1,        # sla
            "role": 3
        }
    })
```

### Step 5 — Push device settings to live FortiGate

```python
device-settings-install({
    "fmg_host": fmg_host,
    "scope": [{"name": device, "vdom": vdom}],
    "wait": True,
    "max_wait_sec": 180,
    "dev_rev_comments": f"SD-WAN spoke onboard for site {site_id} via SDK playbook"
})
```

If `task.num_err > 0` → roll back (delete the zone, members, health-checks, neighbor we just created via `object-delete`).

### Step 6 — Verify post-install

```python
# Re-run the audit playbook
audit_result = run_playbook("sdwan-config-audit", {device, adom, vdom})

# Live verify SLA monitors are reporting
live = device-monitor-proxy({
    "fmg_host": fmg_host,
    "resource": "/api/v2/monitor/virtual-wan/health-check",
    "targets": [f"/adom/{adom}/device/{device}"]
})
```

Both should pass before declaring success.

## Output

```json
{
  "success": true,
  "device": "spoke-03",
  "site_id": 3,
  "objects_created": {
    "zones": 1,
    "members": 3,
    "health_checks": 2,
    "neighbors": 1
  },
  "install_task_id": 42,
  "audit_after": {"grade": "A", "findings": []},
  "live_verify": {"sla_monitors_up": 2, "all_links_up": true}
}
```

## Dry-Run Mode

When `dry_run: true`:
- Skip Steps 1-4 calls
- Print what WOULD be created (full data payloads)
- Skip Step 5 (no install)
- Skip Step 6 (nothing to verify)
- Return preview structure showing all planned operations

## Failure Modes

| Symptom | Action |
|---|---|
| Step 0 finds existing SD-WAN config | STOP. Use `sdwan-config-audit` to inspect, then `sdwan-spoke-update` (planned) for changes. |
| Step 2 add member fails (interface doesn't exist) | Roll back zone (Step 1). Tell user IPsec tunnel not yet up. |
| Step 5 install task `num_err > 0` | Read `task.lines[*].detail`. Common: "device disconnected" → wait + retry, "config conflict" → diff + report. Roll back FMG-side objects only if live-side install fully failed. |
| Step 6 audit grade is C/F after install | Don't roll back automatically — surface findings to user. The install succeeded, the audit is informational. |

## Tools Used

- `device-list` (Step 0)
- `object-list` (Step 0, Step 6)
- `object-create` (Steps 1-4)
- `object-delete` (rollback)
- `device-settings-install` (Step 5)
- `device-monitor-proxy` (Step 6)

Zero new tools required. The 26 primitives + session pool support this end-to-end.

## Example AI Dialogue

**User:** "Build SD-WAN on the new spoke at site 5. Two HUB tunnels already up: HUB1-VPN1 and HUB2-VPN2. Loopback is 172.16.0.5, hub is 172.16.255.253."

**AI:**
> Pre-flight check: Found `new-spoke-5`, online, conn_status=1. SD-WAN currently empty (only default `virtual-wan-link` zone). Good to proceed.
>
> Plan (dry-run preview):
> - Create zone `SDWAN-HUB` (ADVPN enabled, health-check HUB_Health)
> - Add 3 members: HUB1-VPN1 seq=500, HUB2-VPN2 seq=501, wan seq=2 (all source=172.16.0.5)
> - Create 2 health-checks: HUB_Health (probes 172.16.255.253), Public_SLA (probes 8.8.8.8)
> - Add 1 ADVPN neighbor at 172.16.255.253
> - Install device settings
>
> Confirm to apply?

(User confirms → AI runs Steps 1-6 and reports outcome.)

## Related Playbooks

- `sdwan-config-audit.md` — read-only audit, run before AND after this playbook
- `sdwan-health-check.md` — runtime health post-onboard
- `sdwan-spoke-update.md` (planned) — incremental changes to existing config
