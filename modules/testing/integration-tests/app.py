#!/usr/bin/env python3
import os
import json
from typing import Optional

import aws_cdk as cdk

from integration_tests_infra import IntegrationTestsInfrastructure

app = cdk.App()

project_name = os.getenv("SEEDFARMER_PROJECT_NAME")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME")
module_name = os.getenv("SEEDFARMER_MODULE_NAME")
hash = os.getenv("SEEDFARMER_HASH", "")

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError(
        "This module cannot support a project+deployment name character length greater than 35"
    )


def get_arg_value(
    name: str, default: Optional[str] = None, required: Optional[bool] = True
) -> str:
    value = (
        os.getenv(f"SEEDFARMER_PARAMETER_{name}", default)
        if default
        else os.getenv(f"SEEDFARMER_PARAMETER_{name}", "")
    )
    if not value and not required:
        return None
    elif value == "":
        raise ValueError(
            f"required argument {name.replace('_', '-').lower()} is missing"
        )
    else:
        return value


manifests = get_arg_value("MANIFEST_PATHS")
repo_owner = get_arg_value("REPO_OWNER")
repo_name = get_arg_value("REPO_NAME")
oauth_token_secret_name = get_arg_value("OAUTH_TOKEN_SECRET_NAME")
branch = get_arg_value("BRANCH", required=False)


stack = IntegrationTestsInfrastructure(
    app,
    f"{project_name}-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    manifests=manifests,
    repo_owner=repo_owner,
    repo_name=repo_name,
    oauth_token_secret_name=oauth_token_secret_name,
    seedfarmer_project_name=project_name,
    branch=branch,
)

app.synth()
