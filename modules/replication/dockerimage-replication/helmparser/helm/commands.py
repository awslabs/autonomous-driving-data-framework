"""Helm commands"""
import os
import shlex
import shutil
import subprocess  # nosec B404

import yaml


def _execute_command(command: str) -> str:
    """Executes arbitrary command

    Args:
        command (str): Command to execute

    Returns:
        str: Command execution result
    """
    cmd = shlex.split(command)
    with subprocess.Popen(
        cmd,
        shell=False,
        text=True,
        universal_newlines=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as executed_command:
        stdout, _ = executed_command.communicate()
        return stdout


def _unarchive_repo(project_path: str, repo: str, chart: str, version: str) -> None:
    """Pulls and unarchives helm repository locally


    Args:
        project_path (str): Path where to unarchive the helm repository
        repo (str): Helm repository name
        chart (str): Helm chart name
        version (str): Helm chart version
    """
    _execute_command(
        f"helm pull {repo}/{chart} --version {version} --untar --untardir {project_path}"
    )


def show(subcommand: str, chart: str, version: str) -> dict:
    """Shows helm values

    Args:
        subcommand (str): Helm show subcommand. Can be one of: all, chart, crds, readme, values
        chart (str): Helm chart name
        version (str): Helm chart version

    Returns:
        dict: Parsed helm show output
    """
    return yaml.safe_load(
        _execute_command(f"helm show {subcommand} {chart} --version {version}")
    )


def show_subchart(
    project_path: str, repo: str, chart: str, subchart: str, version: str
) -> dict:
    """Shows helm values for subchart

    Args:
        project_path (str): Path where to unarchive the helm repository
        repo (str): Helm repository name
        chart (str): Helm subchart name
        subchart (str): Helm subchart name
        version (str): Helm subchart version

    Returns:
        dict: Parsed helm show output
    """
    _unarchive_repo(project_path, repo, chart, version)

    result = {}
    result["chart"] = yaml.safe_load(
        _execute_command(
            f"helm show chart {os.path.join(project_path, chart, 'charts', subchart)}"
        )
    )

    result["values"] = yaml.safe_load(
        _execute_command(
            f"helm show values {os.path.join(project_path, chart, 'charts', subchart)}"
        )
    )

    shutil.rmtree(f"{project_path}/{chart}")

    return result


def add_repo(name: str, repo: str) -> None:
    """Adds a chart repository locally

    Args:
        name (str): Helm chart name
        repo (str): Helm repository name
    """
    _execute_command(f"helm repo add {name} {repo}")


def update_repos() -> None:
    """Updates information of available charts locally from chart repositories"""
    _execute_command("helm repo update")
