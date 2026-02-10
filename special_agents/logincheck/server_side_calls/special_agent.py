# Dateipfad: ~/local/lib/python3/cmk_addons/plugins/logincheck/server_side_calls/special_agent.py

from cmk.server_side_calls.v1 import (
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)


def _agent_arguments(params, host_config):
    args = []

    args.extend(["--url", params["url"]])
    args.extend(["--username", params["username"]])
    args.extend(["--password", params["password"].unsafe()])

    yield SpecialAgentCommand(command_arguments=args)


special_agent_logincheck = SpecialAgentConfig(
    name="logincheck",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)