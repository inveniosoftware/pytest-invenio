# SPDX-FileCopyrightText: 2026 TU Wien.
# SPDX-License-Identifier: MIT

"""Script for executing the tests."""

import argparse
import ast
import json
import os
import pathlib
import sys
from subprocess import CalledProcessError, run
from typing import Optional, Tuple

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import docker_services_cli.cli as dsc_cli
import docker_services_cli.env as dsc_env
from pytest import main as pytest_main

DEFAULT_CONFIG = {
    "services": {},
    "copy-env-to-from": {},
    "randomize_ports": True,
    "env_prefix": "",
    "project_name": None,
    "pre_test_scripts": [],
    "wait_for_services": True,
}


# similar to how isort fetches the config from pyproject.toml:
# https://github.com/PyCQA/isort/blob/8.0.0/isort/settings.py#L753
def _find_config_file(
    filename: str = "pyproject.toml",
    path: Optional[pathlib.Path] = None,
    max_depth: int = 10,
) -> Optional[pathlib.Path]:
    """Find the closest configuration file from the given directory.

    If the given directory doesn't contain a configuration file ("pyproject.toml"),
    keep checking higher up in the directory tree, up to the specified ``max_depth``.
    The first found configuration file's path will be returned.
    If none can be found, ``None`` will be returned.
    """
    if path is None:
        path = pathlib.Path().absolute()

    tries = 0
    while tries < max_depth:
        config_file_path = path / filename if path.is_dir() else path
        if config_file_path.exists():
            # note: we check 'exists()' rather than 'is_file()' to also support pipes
            return config_file_path

        if path.parent == path:
            # we're already at the root
            break
        else:
            tries += 1
            path = path.parent

    return None


def _read_pytest_invenio_config(
    filename: str = "pyproject.toml",
    path: Optional[pathlib.Path] = None,
) -> Tuple[dict, Optional[pathlib.Path]]:
    """Parse the tool's configuration from the closest configuration file.

    This will try to find the closest configuration file with the specified
    ``filename`` and read the configuration from a section ``[tool.pytest-invenio]``
    or equivalent, and some subsections.
    Supported formats are ``TOML`` and ``JSON`` (which will be used if ``TOML``
    parsing fails).

    If a configuration file could be found and successfully parsed, the parsed content
    will be returned along with the path of the configuration file.
    If no configuration file can be found, the tuple ``({}, None)`` will be returned.
    """
    config_file_path = _find_config_file(path)

    # note: we check 'exists()' rather than 'is_file()' to also support pipes
    if config_file_path and config_file_path.exists():
        # since we want to support files like pipes that aren't seekable, we only
        # read the text content once
        content = config_file_path.read_text()
        try:
            config_data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            config_data = json.loads(content)

        tool_config = config_data.get("tool", {}).get("pytest-invenio", {})
        return {**DEFAULT_CONFIG, **tool_config}, config_file_path

    return {}, None


def _fix_config_environment_variables(
    copy_to_from: dict[str, str], env_prefix: Optional[str] = None
) -> None:
    """Fix up the configuration environment variables.

    This is currently necessary because many of the cache-related connection strings
    in the various Invenio packages typically don't share a common base source.
    """
    env_prefix = env_prefix or ""

    for to_name, from_name in copy_to_from.items():
        os.environ[f"{env_prefix}{to_name}"] = os.environ[f"{env_prefix}{from_name}"]


def _start_docker_services_cli(
    services: dict[str, str],
    env_prefix=None,
    randomize_ports: bool = True,
    project_name: Optional[str] = None,
    wait: bool = True,
    retries: int = 6,
    verbose: bool = False,
) -> None:
    """Start ``docker-services-cli`` services.

    Run the commands in-process rather than shelling out, to prevent pain points
    related to the parsing of environment variables.
    """
    env_prefix = env_prefix or ""
    docker_compose_file = f"{dsc_cli._get_module_path()}/docker-services.yml"
    dsc_cli.populate_env_configuration()
    if randomize_ports:
        dsc_cli.randomize_service_ports_env(services.values())

    dsc_cli.override_default_versions_in_env(services.values())
    dsc_cli.services_up(
        services=services.values(),
        filepath=docker_compose_file,
        project_name=project_name,
        wait=wait,
        retries=retries,
        verbose=verbose,
    )

    for env_var_name, port in dsc_cli.get_public_service_ports(
        services=services.values(),
        filepath=docker_compose_file,
        project_name=project_name,
    ).items():
        os.environ[env_var_name] = port

    for svc_type, svc_name in services.items():
        for var_name, var_value in dsc_env.get_service_env_vars(svc_type, [svc_name]):
            try:
                var_value = ast.literal_eval(var_value)
            except (SyntaxError, ValueError):
                pass
            os.environ[f"{env_prefix}{var_name}"] = var_value


def _stop_docker_services_cli(project_name: Optional[str] = None) -> None:
    """Stop ``docker-services-cli`` services."""
    docker_compose_file = f"{dsc_cli._get_module_path()}/docker-services.yml"
    dsc_cli.services_down(filepath=docker_compose_file, project_name=project_name)


def _parse_args(
    args: Optional[list[str]] = None,
) -> Tuple[argparse.Namespace, list[str]]:
    """Parse the CLI arguments.

    Note: Argument names are chosen in a way to avoid collision with ``pytest``.
    """
    parser = argparse.ArgumentParser(
        epilog="Any other arguments will be passed to pytest; see `pytest --help` for more information."
    )
    parser.add_argument(
        "-K",
        "--keep-services",
        action="store_true",
        default=False,
        help="Keep the test services running after run completion.",
    )
    parser.add_argument(
        "-C",
        "--config",
        metavar="FILE",
        type=pathlib.Path,
        default=pathlib.Path("pyproject.toml"),
        help="Configuration file to use instead of 'pyproject.toml'",
    )
    parser.add_argument(
        "-P",
        "--print-config",
        action="store_true",
        default=False,
        help="Print the loaded configuration and exit.",
    )
    return parser.parse_known_args(args)


def run_tests(config: dict, pytest_args: list[str], keep_services: bool = False) -> int:
    """Run the tests with the given configuration."""
    services = config.get("services", {})
    env_prefix = config.get("env_prefix", "")
    randomize_ports = config.get("randomize_ports", True)
    project_name = config.get("project_name", None)
    pre_test_scripts = config.get("pre_test_scripts", [])
    wait = config.get("wait_for_services", True)

    try:
        scripts_done = 0
        for script in pre_test_scripts:
            run(script, shell=True, check=True)
            scripts_done += 1

        _start_docker_services_cli(
            services,
            env_prefix=env_prefix,
            randomize_ports=randomize_ports,
            project_name=project_name,
            wait=wait,
            retries=6,
            verbose=False,
        )

        _fix_config_environment_variables(
            config.get("env-copy-to-from", {}), env_prefix
        )
        return pytest_main(pytest_args)

    except CalledProcessError as e:
        if scripts_done < len(pre_test_scripts):
            print(f"Failed script with code {e.returncode}: {script}", file=sys.stderr)

        return e.returncode

    finally:
        if not keep_services and scripts_done >= len(pre_test_scripts):
            _stop_docker_services_cli(project_name)

    return 0


def run_tests_cli(args: Optional[list[str]] = None) -> int:
    """CLI command for running the tests.

    This function performs argument parsing and is intended to be run as a CLI command.
    If you are interested in calling this from within Python, consider using
    ``run_tests()`` instead.

    If ``args`` is not supplied, the arguments will be taken from ``sys.argv``.
    """
    parsed_args, remaining_args = _parse_args(args)
    config_filename, config_path = "pyproject.toml", parsed_args.config

    # note: we check 'exists()' rather than 'is_file()' to also support pipes
    if config_path and config_path.exists():
        config_filename = config_path.name

    config, _config_path = _read_pytest_invenio_config(
        filename=config_filename, path=config_path
    )

    # printing the configuration in conjunction with support for pipes as config
    # files enables config modifications via one-liners like:
    #
    # run-tests -C <(run-tests -P | jq '.tool["pytest-invenio"].services.mq="rabbitmq"')
    if parsed_args.print_config:
        print(json.dumps({"tool": {"pytest-invenio": config}}, indent=2))
        return 0

    return run_tests(config, remaining_args, keep_services=parsed_args.keep_services)


if __name__ == "__main__":
    run_tests_cli()
