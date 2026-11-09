#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Mapping, Any, Iterable, Dict, List, Optional

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

# XIQ announces only the remaining quota ("RateLimit: "tenant-hour";r=...").
# If the agent did not get a quota (RateLimit-Policy: q=...), this value is
# used to calculate "used". Adjust here if your XIQ tenant has another quota.
DEFAULT_QUOTA = 7500
DEFAULT_WINDOW_S = 3600


# ---------------------------------------------------------------------------
# Check 1: XIQ API Rate Limits  (quota of the tenant, from RateLimit header)
# ---------------------------------------------------------------------------
def discover_rate_limits(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()


def check_xiq_rate_limits(section: Mapping[str, Any]) -> Iterable[CheckResult]:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No API rate limit data")
        return

    s = section.get("state")
    if s == "UNLIMITED":
        yield Result(state=State.OK, summary="API has no rate limit headers")
        return

    if s == "NO_RESPONSE":
        yield Result(state=State.CRIT, summary="No HTTP response from XIQ API")
        return

    rem = section.get("remaining")
    if rem is None:
        yield Result(state=State.UNKNOWN, summary="No 'remaining' value in rate limit headers")
        return

    limit = section.get("limit")
    assumed = not limit
    if assumed:
        limit = DEFAULT_QUOTA
    window_s = section.get("window_s") or DEFAULT_WINDOW_S
    reset = section.get("reset_in_seconds")

    used = max(int(limit) - int(rem), 0)

    state = State.OK
    ratio = float(rem) / float(limit) if limit else 1.0
    if ratio < 0.05:
        state = State.CRIT
    elif ratio < 0.10:
        state = State.WARN

    yield Result(
        state=state,
        summary=(
            f"Remaining {rem} of {limit}{' (assumed quota)' if assumed else ''}, "
            f"used {used} ({used * 100.0 / limit:.0f}%) in window {window_s}s"
        ),
    )
    if reset is not None:
        yield Result(state=State.OK, notice=f"Window resets in {reset}s")

    yield Metric("xiq_api_remaining", rem)
    yield Metric("xiq_api_limit", limit)
    yield Metric("xiq_api_used", used)


check_plugin_xiq_rate_limits = CheckPlugin(
    name="xiq_rate_limits",
    sections=["extreme_cloud_iq_rate_limits"],
    service_name="XIQ API Rate Limits",
    discovery_function=discover_rate_limits,
    check_function=check_xiq_rate_limits,
)


# ---------------------------------------------------------------------------
# Check 2: XIQ API Usage  (what *this agent run* consumed)
# ---------------------------------------------------------------------------
def _to_int(val: str) -> Optional[int]:
    try:
        return int(val)
    except ValueError:
        try:
            return int(float(val))
        except ValueError:
            return None


def parse_xiq_api_usage(string_table: StringTable) -> Optional[Mapping[str, Any]]:
    res: Dict[str, Any] = {}
    endpoints: List[tuple] = []
    for line in string_table:
        if not line:
            continue
        key = line[0].strip()
        if key == "endpoint" and len(line) >= 3:
            cnt = _to_int(line[2].strip())
            if cnt is not None:
                endpoints.append((line[1].strip(), cnt))
        elif len(line) >= 2:
            val = line[1].strip()
            res[key] = val if key == "policy" else _to_int(val)
    if not res:
        return None
    res["endpoints"] = endpoints
    return res


agent_section_xiq_api_usage = AgentSection(
    name="extreme_cloud_iq_api_usage",
    parse_function=parse_xiq_api_usage,
)


def discover_api_usage(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()


def check_xiq_api_usage(section: Mapping[str, Any]) -> Iterable[CheckResult]:
    calls = section.get("calls_total") or 0
    c429 = section.get("calls_429") or 0
    cerr = section.get("calls_error") or 0
    duration = section.get("duration_s") or 0

    state = State.WARN if c429 else State.OK
    yield Result(
        state=state,
        summary=(
            f"{calls} API calls in last agent run ({duration}s), "
            f"{c429} throttled (429), {cerr} errors"
        ),
    )

    first = section.get("remaining_first")
    last = section.get("remaining_last")
    if first is not None and last is not None:
        if first >= last:
            consumed = first - last
            note = f"Quota consumed during run: {consumed}"
            if consumed > calls:
                note += f" (agent made {calls}, {consumed - calls} from other consumers of the tenant)"
            yield Result(state=State.OK, notice=note)
            yield Metric("xiq_api_quota_consumed_run", consumed)
        else:
            yield Result(state=State.OK, notice="Quota window reset during run, consumption not comparable")

    policy = section.get("policy")
    if policy:
        yield Result(state=State.OK, notice=f"Rate limit policy: {policy}")

    for ep, cnt in section.get("endpoints", [])[:10]:
        yield Result(state=State.OK, notice=f"{ep}: {cnt}")

    yield Metric("xiq_api_calls_run", calls)
    yield Metric("xiq_api_calls_429", c429)
    yield Metric("xiq_api_calls_error", cerr)
    yield Metric("xiq_api_run_duration", duration)


check_plugin_xiq_api_usage = CheckPlugin(
    name="xiq_api_usage",
    sections=["extreme_cloud_iq_api_usage"],
    service_name="XIQ API Usage",
    discovery_function=discover_api_usage,
    check_function=check_xiq_api_usage,
)
