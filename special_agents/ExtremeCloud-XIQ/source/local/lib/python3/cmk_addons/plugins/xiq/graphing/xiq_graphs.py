#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : xiq_graphs.py
#
# Description:
#   Graph definitions for ExtremeCloudIQ (XIQ) using Checkmk Graphing API v1.
#   Provides graphs for AP counts, client distribution, per-band client totals,
#   and API remaining quota. Used in dashboards and detailed service graphs.
# =============================================================================

from cmk.graphing.v1 import graphs, metrics


# ---------------------------------------------------------------------
# GRAPH 1 – Access Points (total)
# ---------------------------------------------------------------------
graph_xiq_aps = graphs.Graph(
    name="xiq_aps",
    title=metrics.Title("XIQ: Access Points"),
    minimal_range=graphs.MinimalRange(0, 10),
    simple_lines=["xiq_aps_total"],
)


# ---------------------------------------------------------------------
# GRAPH 2 – Clients: Combined (total + per band)
# ---------------------------------------------------------------------
graph_xiq_clients_combined = graphs.Graph(
    name="xiq_clients_combined",
    title=metrics.Title("XIQ: Clients (total and by frequency)"),
    minimal_range=graphs.MinimalRange(0, 10),
    compound_lines=[
        "xiq_clients_24",
        "xiq_clients_5",
        "xiq_clients_6",
    ],
    simple_lines=["xiq_clients_total"],
)


# ---------------------------------------------------------------------
# GRAPH 3 – API remaining quota
# ---------------------------------------------------------------------
graph_xiq_api_remaining = graphs.Graph(
    name="xiq_api_remaining",
    title=metrics.Title("XIQ: API Calls Remaining"),
    minimal_range=graphs.MinimalRange(0, 1000),
    simple_lines=["xiq_api_remaining"],
)