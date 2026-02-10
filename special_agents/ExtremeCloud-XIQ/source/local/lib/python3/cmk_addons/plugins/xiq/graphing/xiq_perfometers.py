#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : xiq_perfometers.py
#
# Description:
#   Perf-o-meters for ExtremeCloudIQ (XIQ) metrics.
#   These definitions are used in Checkmk dashboards and graphs to visualize
#   AP counts, client counts, uptime, SSID distribution, and radio activity
#   using Graphing API v1.
#
#   All perf-o-meters reference metrics defined in:
#       graphing/xiq_metrics.py
# =============================================================================

from cmk.graphing.v1 import perfometers


# ---------------------------------------------------------------------
# COMMON FOCUS RANGES – define typical display scales
# ---------------------------------------------------------------------
RANGE_APS = perfometers.FocusRange(
    perfometers.Closed(0),
    perfometers.Closed(100),
)

RANGE_CLIENTS = perfometers.FocusRange(
    perfometers.Closed(0),
    perfometers.Closed(600),
)


# ---------------------------------------------------------------------
# SUMMARY: Stacked Perf-o-meter
#   LOWER: total APs
#   UPPER: clients per band (2.4 / 5 / 6 GHz)
# ---------------------------------------------------------------------
perfometer_xiq_summary = perfometers.Stacked(
    name="xiq_summary",
    lower=perfometers.Perfometer(
        name="xiq_summary_lower",
        focus_range=RANGE_APS,
        segments=["xiq_aps_total"],
    ),
    upper=perfometers.Perfometer(
        name="xiq_summary_upper",
        focus_range=RANGE_CLIENTS,
        segments=[
            "xiq_clients_24",
            "xiq_clients_5",
            "xiq_clients_6",
        ],
    ),
)


# ---------------------------------------------------------------------
# AP STATUS: Stacked Perf-o-meter
#   UPPER: uptime (seconds; CMK auto-formats to d/h/m)
#   LOWER: total clients
# ---------------------------------------------------------------------

perfometer_xiq_ap_status = perfometers.Stacked(
    name="xiq_ap_status",
    upper=perfometers.Perfometer(
        name="perfometer_xiq_ap_uptime_days",
        segments=["xiq_uptime_days"],    
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(365),      
        ),
    ),
    lower=perfometers.Perfometer(
        name="perfometer_xiq_ap_clients",
        segments=["xiq_clients_total"],
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(100),
        ),
    ),
)


# ---------------------------------------------------------------------
# SSID CLIENTS – standalone perf-o-meter
# ---------------------------------------------------------------------
perfometer_xiq_ssid_clients = perfometers.Perfometer(
    name="xiq_ssid_clients",
    segments=["xiq_ssid_clients_total"],
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(100),
    ),
)


# ---------------------------------------------------------------------
# ALTERNATIVE PERF-O-METERS
# ---------------------------------------------------------------------
perfometer_xiq_aps_only = perfometers.Perfometer(
    name="xiq_aps_only",
    focus_range=RANGE_APS,
    segments=["xiq_aps_total"],
)

perfometer_xiq_clients_only = perfometers.Perfometer(
    name="xiq_clients_only",
    focus_range=RANGE_CLIENTS,
    segments=["xiq_clients_total"],
)

perfometer_xiq_clients_by_frequency = perfometers.Perfometer(
    name="xiq_clients_by_frequency",
    focus_range=RANGE_CLIENTS,
    segments=[
        "xiq_clients_24",
        "xiq_clients_5",
        "xiq_clients_6",
    ],
)

perfometer_xiq_radios = perfometers.Perfometer(
    name="xiq_radios",
    segments=["xiq_radio_clients_total"],
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(200),
    ),
)