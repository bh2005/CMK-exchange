# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : xiq.py
#
# Description:
#   Server-side call configuration for the ExtremeCloudIQ (XIQ) Special Agent.
#   Defines the Pydantic parameter model and translates rule parameters into
#   agent command-line arguments for Checkmk's server-side execution.
# =============================================================================

from typing import Iterator
from pydantic import BaseModel, Field
from cmk.server_side_calls.v1 import (
    SpecialAgentConfig,
    SpecialAgentCommand,
    HostConfig,
    Secret,
)

# ---------------------------------------------------------------------
# PARAMETER MODEL – validated rule parameters for the XIQ agent
# ---------------------------------------------------------------------
class XIQParams(BaseModel):
    url: str = Field(default="https://api.extremecloudiq.com")
    username: str
    password: Secret
    verify_tls: bool = True
    timeout: int = 30
    proxy_url: str | None = None


# ---------------------------------------------------------------------
# COMMAND TRANSLATION – map rule params to agent CLI arguments
# ---------------------------------------------------------------------
def _commands(params: XIQParams, host_config: HostConfig) -> Iterator[SpecialAgentCommand]:
    """
    Build the special agent command-line argument list. The password is passed
    as plain text using Secret.unsafe() to the agent process (as per Checkmk's
    server-side call convention).
    """
    args: list[str] = [
        "--url", params.url,
        "--username", params.username,
        "--password", params.password.unsafe(),  # pass secret in plain text to the agent
        "--timeout", str(params.timeout),
        "--host", host_config.name,
    ]

    if not params.verify_tls:
        args.append("--no-cert-check")

    if params.proxy_url:
        args += ["--proxy", params.proxy_url]

    yield SpecialAgentCommand(command_arguments=args)


# ---------------------------------------------------------------------
# REGISTRATION – expose the special agent "xiq" to Checkmk
# ---------------------------------------------------------------------
special_agent_xiq = SpecialAgentConfig(
    name="xiq",
    parameter_parser=XIQParams.model_validate,
    commands_function=_commands,
)