# Playbook: SD-WAN Health Check

## Goal

Answer the question: **"Is my SD-WAN healthy right now AND over the last window?"**

Produces a traffic-light (green / yellow / red) per device plus per-interface detail on SLA violations, flapping links, and saturated overlays.

## When to Run

- Daily morning check across all MSSP tenants
- Before a scheduled change
- After a site report of degraded performance
- On demand when user asks "how's SD-WAN?"

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `fmg_host` | Yes | — | FortiManager IP/hostname |
| `adom` | No | `root` | ADOM to scope |
| `device` | No | all SD-WAN devices | Single device, or omit to loop all |
| `time_window_sec` | No | `3600` | History trend window (default last hour) |
| `sla_threshold_ms` | No | `100` | Latency threshold for "SLA violation" flag |
| `packetloss_threshold_pct` | No | `0.02` | Packet-loss threshold (0.02 = 2%) |
| `link_flap_threshold_pct` | No | `0.99` | Below this link-up % = flap |

## Prerequisites

- FMG RTM enabled — see `tools/org.ulysses.noc.fortimanager-sdwan-history/Skills.md` for how to enable (`config system admin setting / set sdwan-monitor-history enable`). If not enabled, skip historical steps and note it in the output.

## Procedure

### Step 1 — Discover SD-WAN devices

```python
r = device-list({"fmg_host": fmg_host, "adom": adom,
                 "platform_like": ""})  # no filter — grab all, then filter local
sdwan_devices = [d for d in r["devices"] if d["conn_status"] == 1]  # only online
```

Narrow to `device` input if provided.

### Step 2 — Live health snapshot (per device, parallel if possible)

```python
live = device-monitor-proxy({
    "fmg_host": fmg_host,
    "resource": "/api/v2/monitor/virtual-wan/health-check",
    "targets": [f"/adom/{adom}/device/{d['name']}"]
})
```

Parse `results[0].response.results` — dict of `{sla_name: {interface: {status, latency, packet-loss, jitter, ...}}}`

### Step 3 — Historical SLA trend (if RTM enabled)

```python
trend_sla = sdwan-history({
    "fmg_host": fmg_host,
    "device": d["name"],
    "metric": "sla",
    "time_window_sec": time_window_sec
})
```

Skip if `entry_count == 0` and `note` indicates RTM not enabled.

### Step 4 — Historical bandwidth trend

```python
trend_if = sdwan-history({
    "fmg_host": fmg_host,
    "device": d["name"],
    "metric": "interface",
    "time_window_sec": time_window_sec
})
```

### Step 5 — Synthesize per-device verdict

Apply these rules:

| Condition | Flag |
|---|---|
| Any live SLA status != `up` | RED — link down NOW |
| Any trend `summary.link_up_pct < link_flap_threshold_pct` | RED — flap detected |
| Any trend `summary.max_latency_ms > sla_threshold_ms` | YELLOW — SLA breach in window |
| Any trend `summary.max_packetloss_pct > packetloss_threshold_pct` | YELLOW — packet loss spike |
| Any interface sustained > 80% of nominal bandwidth | YELLOW — saturated |
| All checks clean | GREEN |

### Step 6 — Output

Return a structured object AND a narrative summary:

```json
{
  "overall_verdict": "YELLOW",
  "devices": [
    {
      "name": "howard-sdwan-spoke-1",
      "verdict": "YELLOW",
      "live_sla_monitors": 3,
      "findings": [
        {"severity": "YELLOW", "kind": "latency", "interface": "wan",
         "sla_name": "Public_SLA", "detail": "max 148ms exceeded 100ms threshold at 14:32"}
      ],
      "recommendations": [
        "Tune Public_SLA latency threshold or investigate ISP queue during 14:30-14:40 window."
      ]
    }
  ],
  "summary_text": "1 of 1 device YELLOW. 1 SLA breach on howard-sdwan-spoke-1/Public_SLA..."
}
```

## Example AI Dialogue

**User:** "How's my SD-WAN looking?"

**AI:**
> Checking howard-sdwan-spoke-1 (the 1 SD-WAN device in root ADOM).
>
> **Live:** All 3 SLA monitors (Default_DNS, HUB_Health, Public_SLA) show interfaces up. Latencies look clean.
>
> **Last hour:** 1 SLA latency breach — `Public_SLA` on `wan` hit 148ms at 14:32 (threshold is 100ms). No packet loss, no flaps, no saturation.
>
> **Verdict: YELLOW** — recommend checking ISP queue behavior around that spike, or relaxing the threshold if 148ms is acceptable.

## Tools Used

- `device-list` — find SD-WAN devices
- `device-monitor-proxy` — live state via FortiOS REST
- `sdwan-history` — RTM historical trend (SLA + interface)

## Variations

- **"Quick check"** — skip Step 3/4, just run Steps 1-2-5
- **"Deep dive"** — add `device-monitor-proxy` calls for `/api/v2/monitor/router/bgp/neighbors` and `/api/v2/monitor/vpn/ipsec` to correlate routing events
- **"Fleet-wide"** — loop over all ADOMs via `adom-list` first

## Failure Modes

| Symptom | What to tell the user |
|---|---|
| `device-list` returns 0 SD-WAN devices | "No managed SD-WAN devices found in this ADOM. Check inventory." |
| `device-monitor-proxy` returns `http_status: 403` per device | "FortiGate API user perms too restrictive. Need `read-only-monitor` perm." |
| `sdwan-history` returns `entry_count: 0` across devices | "FMG RTM not populated yet — proceed with live-only check. Enable RTM via `config system admin setting / set sdwan-monitor-history enable`." |
| Live status shows `up` but trend shows breaches | Real issue — trends are more accurate than current snapshot. Surface the trend findings. |
