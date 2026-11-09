#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : xiq_metrics.py
#
# Description:
#   Metrics definitions for ExtremeCloudIQ (XIQ) within Checkmk 2.5.
#   Provides all metrics used by XIQ checks, graphs, dashboards and
#   perf-o-meters. Fully compatible with Graphing API v1.
#
#   CMK 2.5 change: color module removed from cmk.graphing.v1.
#   Colors are now metrics.Color.<NAME> instead of color.<NAME>.
#   Also: GREY was renamed to GRAY.
# =============================================================================

from cmk.graphing.v1 import metrics, unit

# ---------------------------------------------------------------------
# UNIT DEFINITIONS — integer counters, time units, dBm units
# ---------------------------------------------------------------------
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.AutoPrecision(0))
UNIT_TIME    = metrics.Unit(metrics.TimeNotation())
UNIT_DBM     = metrics.Unit(metrics.DecimalNotation("dBm"), metrics.AutoPrecision(0))

# ---------------------------------------------------------------------
# ACCESS POINT COUNTS
# ---------------------------------------------------------------------

metric_xiq_aps_total = metrics.Metric(
    name="xiq_aps_total",
    title=metrics.Title("Access Points (total)"),
    unit=metrics.Unit(metrics.DecimalNotation("APs"), metrics.AutoPrecision(0)),
    color=metrics.Color.BLUE,
)


metric_xiq_aps_connected = metrics.Metric(
    name="xiq_aps_connected",
    title=metrics.Title("Access Points (connected)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_xiq_aps_disconnected = metrics.Metric(
    name="xiq_aps_disconnected",
    title=metrics.Title("Access Points (disconnected)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_RED,
)

# ---------------------------------------------------------------------
# CLIENT COUNTS (GLOBAL + PER BAND)
# ---------------------------------------------------------------------

metric_xiq_clients_total = metrics.Metric(
    name="xiq_clients_total",
    title=metrics.Title("Clients (total)"),
    unit=metrics.Unit(metrics.DecimalNotation("Clients"), metrics.AutoPrecision(0)),
    color=metrics.Color.GREEN,
)


metric_xiq_clients_24 = metrics.Metric(
    name="xiq_clients_24",
    title=metrics.Title("Clients (2.4 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_xiq_clients_5 = metrics.Metric(
    name="xiq_clients_5",
    title=metrics.Title("Clients (5 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

metric_xiq_clients_6 = metrics.Metric(
    name="xiq_clients_6",
    title=metrics.Title("Clients (6 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.RED,
)

# ---------------------------------------------------------------------
# API RATE LIMIT / REMAINING QUOTA
# ---------------------------------------------------------------------
metric_xiq_api_remaining = metrics.Metric(
    name="xiq_api_remaining",
    title=metrics.Title("API remaining quota"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)

# ---------------------------------------------------------------------
# API USAGE METRICS
# ---------------------------------------------------------------------
metric_xiq_api_limit = metrics.Metric(
    name="xiq_api_limit",
    title=metrics.Title("API Requests Kontingent"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GRAY,
)

metric_xiq_api_used = metrics.Metric(
    name="xiq_api_used",
    title=metrics.Title("API Requests verbraucht (Zeitfenster)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

metric_xiq_api_calls_run = metrics.Metric(
    name="xiq_api_calls_run",
    title=metrics.Title("API Calls des Agent-Laufs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

metric_xiq_api_calls_429 = metrics.Metric(
    name="xiq_api_calls_429",
    title=metrics.Title("API Calls gedrosselt (429)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.RED,
)

metric_xiq_api_calls_error = metrics.Metric(
    name="xiq_api_calls_error",
    title=metrics.Title("API Calls mit Fehler (HTTP >= 400)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)

metric_xiq_api_quota_consumed_run = metrics.Metric(
    name="xiq_api_quota_consumed_run",
    title=metrics.Title("Kontingent verbraucht waehrend Lauf"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

metric_xiq_api_run_duration = metrics.Metric(
    name="xiq_api_run_duration",
    title=metrics.Title("Dauer des Agent-Laufs"),
    unit=unit.SECOND,
    color=metrics.Color.GRAY,
)

# ---------------------------------------------------------------------
# UPTIME METRICS
# ---------------------------------------------------------------------
metric_xiq_uptime_seconds = metrics.Metric(
    name="xiq_uptime_seconds",
    title=metrics.Title("Uptime"),
    unit=unit.SECOND,
    color=metrics.Color.BLUE,
)

metric_xiq_uptime_days = metrics.Metric(
    name="xiq_uptime_days",
    title=metrics.Title("Uptime (days)"),
    unit=metrics.Unit(metrics.DecimalNotation("d"), metrics.AutoPrecision(0)),
    color=metrics.Color.BLUE,
)

# ---------------------------------------------------------------------
# SSID CLIENT COUNTS
# ---------------------------------------------------------------------
metric_xiq_ssid_clients_total = metrics.Metric(
    name="xiq_ssid_clients_total",
    title=metrics.Title("SSID clients (total)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

metric_xiq_ssid_clients_24 = metrics.Metric(
    name="xiq_ssid_clients_24",
    title=metrics.Title("SSID clients (2.4 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_xiq_ssid_clients_5 = metrics.Metric(
    name="xiq_ssid_clients_5",
    title=metrics.Title("SSID clients (5 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

metric_xiq_ssid_clients_6 = metrics.Metric(
    name="xiq_ssid_clients_6",
    title=metrics.Title("SSID clients (6 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.RED,
)

# ---------------------------------------------------------------------
# RADIO CLIENT COUNTS
# ---------------------------------------------------------------------
metric_xiq_radio_clients_24 = metrics.Metric(
    name="xiq_radio_clients_24",
    title=metrics.Title("Radio clients (2.4 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_xiq_radio_clients_5 = metrics.Metric(
    name="xiq_radio_clients_5",
    title=metrics.Title("Radio clients (5 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

metric_xiq_radio_clients_6 = metrics.Metric(
    name="xiq_radio_clients_6",
    title=metrics.Title("Radio clients (6 GHz)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.RED,
)

metric_xiq_radio_clients_total = metrics.Metric(
    name="xiq_radio_clients_total",
    title=metrics.Title("Radio clients (total)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

# ---------------------------------------------------------------------
# RADIO POWER (dBm) & CHANNEL COUNT
# ---------------------------------------------------------------------
metric_xiq_radio_power_avg_dbm = metrics.Metric(
    name="xiq_radio_power_avg_dbm",
    title=metrics.Title("Radio power (avg, dBm)"),
    unit=UNIT_DBM,
    color=metrics.Color.PURPLE,
)

metric_xiq_radio_power_min_dbm = metrics.Metric(
    name="xiq_radio_power_min_dbm",
    title=metrics.Title("Radio power (min, dBm)"),
    unit=UNIT_DBM,
    color=metrics.Color.DARK_PURPLE,
)

metric_xiq_radio_channels_count = metrics.Metric(
    name="xiq_radio_channels_count",
    title=metrics.Title("Radio channels (distinct)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GRAY,
)
