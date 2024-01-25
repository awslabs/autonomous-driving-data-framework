# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import subprocess
import tempfile
from threading import Timer
from typing import Any

from airflow_kubernetes_job_operator.kubernetes_job_operator import (
    KubernetesJobOperator
)

logging.basicConfig(level="DEBUG")
logger = logging.getLogger("airflow")


KUBECONFIG_REFRESH_RATE = 180


class EksJobOperator(KubernetesJobOperator):  # type: ignore
    def __init__(
        self,
        *args: Any,
        cluster_name: str,
        service_account_role_arn: str,
        **kwargs: Any,
    ) -> None:
        self.cluster_name = cluster_name
        self.service_account_role_arn = service_account_role_arn
        self.logger = logger

        super().__init__(*args, **kwargs)

    def update_kubeconfig(self, path: str) -> None:
        args = [
            "aws",
            "eks",
            "update-kubeconfig",
            "--name",
            self.cluster_name,
            "--role-arn",
            self.service_account_role_arn,
            "--kubeconfig",
            path,
        ]
        logger.info("command: %s", args)
        subprocess.check_call(args)

    def load_kubeconfig(self) -> None:
        logger.debug("Reloading kubeconfig")
        # Load the configuration.
        self.job_runner.client.load_kube_config(
            config_file=self.config_file,
            is_in_cluster=self.in_cluster,
            context=self.cluster_context,
        )
        Timer(KUBECONFIG_REFRESH_RATE, self.load_kubeconfig).start()

    def pre_execute(self, context: Any) -> Any:
        """Called before execution by the airflow system.
        Overriding this method without calling its super() will
        break the job operator.

        Arguments:
            context -- The airflow context
        """
        # Load the configuration.
        with tempfile.NamedTemporaryFile() as temp:
            kubeconfig_path = temp.name

        self.update_kubeconfig(path=kubeconfig_path)
        self.config_file = kubeconfig_path
        self.in_cluster = False
        self.cluster_context = None

        # This background thread refereshes the kubeconfig to eliminate
        # timeouts for long running jobs
        Timer(KUBECONFIG_REFRESH_RATE, self.load_kubeconfig).start()

        # call parent.
        return super().pre_execute(context)
