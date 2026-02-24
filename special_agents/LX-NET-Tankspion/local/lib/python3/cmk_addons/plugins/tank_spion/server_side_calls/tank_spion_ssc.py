#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CheckMK 2.4 – Server-Side-Call: Tank-Spion Special Agent
# ==========================================================
#
# uebersetzt die Ruleset-Parameter in den Kommandozeilen-Aufruf
# des Special Agents (agent_tank_spion).
#
# Kette:
#   Ruleset (tank_spion_datasource_programs)
#     → server_side_calls/tank_spion_cmc.py    ← diese Datei
#       → special_agent_tank_spion
#         → local/share/check_mk/agents/special/agent_tank_spion
#           → HTTP-Abruf Tank-Spion Webinterface
#             → <<<tank_spion>>> Section
#               → agent_based/tank_spion.py (Parse + Check)
#
# Installation:
#   local/lib/python3/cmk_addons/plugins/tank_spion/server_side_calls/tank_spion_cmc.py

from __future__ import annotations

from collections.abc import Iterator

from cmk.server_side_calls.v1 import (
    HostConfig,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def generate_tank_spion_command(
    params: dict,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    """
    Erzeugt den Kommandozeilen-Aufruf fuer agent_tank_spion.

    Verwendet immer die primaere IP-Adresse des CMK-Hosts
    (Host = Tank-Spion-Geraet direkt).
    """
    yield SpecialAgentCommand(
        command_arguments=[
            "--host", host_config.primary_ip_config.address,
        ],
    )


# Variablenname MUSS mit "special_agent_" beginnen → CMK 2.4 Entry-Point
special_agent_tank_spion = SpecialAgentConfig(
    name="tank_spion",
    parameter_parser=lambda p: p,
    commands_function=generate_tank_spion_command,
)
