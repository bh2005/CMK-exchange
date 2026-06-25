from typing import Iterator

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class LoginCheckParams(BaseModel):
    url: str
    username: str
    password: Secret
    verify_tls: bool = True
    proxy_url: str | None = None


def _commands(params: LoginCheckParams, host_config: HostConfig) -> Iterator[SpecialAgentCommand]:
    args: list[str] = [
        "--url",      params.url,
        "--username", params.username,
        "--password", params.password.unsafe(),
    ]
    if not params.verify_tls:
        args.append("--insecure")
    if params.proxy_url:
        args += ["--proxy", params.proxy_url]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_logincheck = SpecialAgentConfig(
    name="logincheck",
    parameter_parser=LoginCheckParams.model_validate,
    commands_function=_commands,
)
