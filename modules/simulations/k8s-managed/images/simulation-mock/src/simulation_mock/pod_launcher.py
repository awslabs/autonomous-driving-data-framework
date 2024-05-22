#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
import logging
import os
import subprocess
from typing import Any, Dict

import kopf
from kubernetes import config as k8_config
from kubernetes import dynamic
from kubernetes.client import api_client

NAMESPACE = os.environ.get("NAMESPACE")
POD_LAUNCHER_NAME = os.environ.get("POD_LAUNCHER_NAME")
POD_LAUNCHER_UID = os.environ.get("POD_LAUNCHER_UID")
JOB_NAME = os.environ.get("JOB_NAME")
JOB_UID = os.environ.get("JOB_UID")
POD_LAUNCHER_BODY = None
COMPLETIONS = 0
FAILURES = 0


def load_config(in_cluster: bool = True) -> None:
    in_cluster_env = os.environ.get("IN_CLUSTER_DEPLOYMENT", None)
    in_cluster = in_cluster_env.lower() in ["yes", "true", "1"] if in_cluster_env is not None else in_cluster
    if in_cluster:
        k8_config.load_incluster_config()
    else:
        k8_config.load_kube_config()


def dynamic_client() -> dynamic.DynamicClient:
    load_config()
    return dynamic.DynamicClient(client=api_client.ApiClient())


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, memo: kopf.Memo, logger: kopf.Logger, **_: Any) -> None:
    settings.persistence.progress_storage = kopf.MultiProgressStorage(
        [
            kopf.AnnotationsProgressStorage(prefix="simulation-pod-launcher.addf.aws"),
            kopf.StatusProgressStorage(field="simulation-pod-launcher.addf.aws"),
        ]
    )
    settings.persistence.finalizer = "simulation-pod-launcher.addf.aws/kopf-finalizer"
    settings.posting.level = logging.getLevelName(os.environ.get("EVENT_LOG_LEVEL", "INFO"))

    memo.namespace = os.environ.get("NAMESPACE")
    memo.pod_launcher_name = os.environ.get("POD_LAUNCHER_NAME")
    memo.pod_launcher_uid = os.environ.get("POD_LAUNCHER_UID")
    memo.worker_body = os.environ.get("WORKER_POD_BODY")
    memo.queue_url = os.environ.get("QUEUE_URL")
    memo.default_region = os.environ.get("AWS_DEFAULT_REGION")
    memo.account_id = os.environ.get("AWS_ACCOUNT_ID")
    memo.parallelism = int(os.environ.get("PARALLELISM"))
    memo.completions = int(os.environ.get("COMPLETIONS"))
    memo.max_failures = int(os.environ.get("MAX_FAILURES"))

    logger.info("memo.namespace: %s", memo.namespace)
    logger.info("memo.pod_launcher_name: %s", memo.pod_launcher_name)
    logger.info("memo.pod_launcher_uid: %s", memo.pod_launcher_uid)
    logger.info("memo.worker_body: %s", memo.worker_body)
    logger.info("memo.queue_url: %s", memo.queue_url)
    logger.info("memo.default_region: %s", memo.default_region)
    logger.info("memo.account_id: %s", memo.account_id)
    logger.info("memo.parallelism: %s", memo.parallelism)

    logger.info("JOB_NAME: %s", JOB_NAME)
    logger.info("JOB_UID: %s", JOB_UID)


def _should_index_pod(meta: kopf.Meta, **_: Any) -> bool:
    return (
        "ownerReferences" in meta
        and len(meta["ownerReferences"]) > 0
        and meta["ownerReferences"][0]["uid"] == POD_LAUNCHER_UID
    )


@kopf.index("pods", when=_should_index_pod)
def worker_pods_idx(name: str, status: kopf.Status, **_: Any) -> Dict[str, str]:
    status = status.get("phase")
    if status not in ["Succeeded", "Failed"]:
        return {"Running": name}
    elif status == "Succeeded":
        global COMPLETIONS
        COMPLETIONS += 1
        return {"Completed": name}
    elif status == "Failed":
        global FAILURES
        FAILURES += 1
        return {"Failed": name}
    else:
        return {"Unknown": name}


def _should_update_job_metadata(meta: kopf.Meta, **_: Any) -> bool:
    return meta["uid"] == POD_LAUNCHER_UID


@kopf.on.resume("pods", when=_should_update_job_metadata)
@kopf.on.create("pods", when=_should_update_job_metadata)
def update_job_metadata(meta: kopf.Meta, body: kopf.Body, memo: kopf.Memo, logger: kopf.Logger, **_: Any) -> str:
    global POD_LAUNCHER_BODY
    POD_LAUNCHER_BODY = body

    logger.debug("POD_LAUNCHER_BODY: %s", POD_LAUNCHER_BODY)

    return "METADATA_UPDATED"


def _should_monitor_job(meta: kopf.Meta, **_: Any) -> bool:
    return meta["uid"] == JOB_UID


@kopf.daemon("batch", "v1", "jobs", when=_should_monitor_job, initial_delay=30)
def monitor_job(
    name: str,
    patch: kopf.Patch,
    stopped: kopf.DaemonStopped,
    memo: kopf.Memo,
    logger: kopf.Logger,
    worker_pods_idx: kopf.Index,
    **_: Any,
) -> str:
    logger.info("JOB: %s", name)
    worker_spec = json.loads(memo.worker_body)
    for container in worker_spec["spec"]["containers"]:
        env = container["env"] if "env" in container else []
        env.extend(
            [
                {"name": "NAMESPACE", "value": memo.namespace},
                {"name": "JOB_NAME", "value": JOB_NAME},
                {"name": "JOB_UID", "value": JOB_UID},
                {"name": "POD_LAUNCHER_NAME", "value": memo.pod_launcher_name},
                {"name": "AWS_DEFAULT_REGION", "value": memo.default_region},
                {"name": "AWS_ACCOUNT_ID", "value": memo.account_id},
                {"name": "QUEUE_URL", "value": memo.queue_url},
            ]
        )

    kopf.append_owner_reference(objs=[worker_spec], owner=POD_LAUNCHER_BODY)
    kopf.harmonize_naming(objs=[worker_spec], name=POD_LAUNCHER_BODY["metadata"]["name"], forced=True)
    kopf.adjust_namespace(objs=[worker_spec], namespace=NAMESPACE, forced=True)
    logger.debug("WORKER_BODY: %s", worker_spec)

    running_pod_count = 0

    while not stopped and COMPLETIONS < memo.completions and FAILURES < memo.max_failures:
        running_pod_count = len(list(worker_pods_idx.get("Running"))) if "Running" in worker_pods_idx else 0
        launch_count = min(
            memo.parallelism - running_pod_count,
            memo.completions - (COMPLETIONS + running_pod_count),
        )

        logger.info(
            "RUNNING_POD_COUNT: %s  COMPLETIONS: %s  FAILURES: %s  LAUNCHING: %s",
            running_pod_count,
            COMPLETIONS,
            FAILURES,
            launch_count,
        )

        client = dynamic_client()
        api = client.resources.get(kind="Pod")

        counter = 0
        for _ in range(0, launch_count):
            counter += 1
            try:
                api.create(namespace=NAMESPACE, body=worker_spec)
            except Exception as e:
                logger.exception("LAUNCH_ERROR", e)
            if counter % 10 == 0:
                stopped.wait(0.5)

        stopped.wait(10)

    if COMPLETIONS < memo.completions and FAILURES >= memo.max_failures:
        logger.info("FAILED")
        patch["metadata"] = {
            "annotations": {
                "simulation-pod-launcher.addf.aws/status": "Failed",
                "simulation-pod-launcher.addf.aws/completions": f"{COMPLETIONS}",
                "simulation-pod-launcher.addf.aws/failures": f"{FAILURES}",
            }
        }
        patch["status"] = {"phase": "Failed"}

        status = "JOB_FAILED"
    else:
        logger.info("COMPLETE")
        patch["metadata"] = {
            "annotations": {
                "simulation-pod-launcher.addf.aws/status": "Succeeded",
                "simulation-pod-launcher.addf.aws/completions": f"{COMPLETIONS}",
                "simulation-pod-launcher.addf.aws/failures": f"{FAILURES}",
            }
        }

        status = "JOB_COMPLETED"

    json_status = json.dumps({"status": status})

    logger.info("WILL_EXIT_IN_30")
    # Write status out so that it can be picked up by the XCom Value Parser
    # And fork a subprocess to send a SIGTERM and initiate graceful shutdown
    subprocess.Popen(
        f"sleep 30; echo '::kube_api:xcom={json_status}'; echo 'Sending SIGTERM'; kill -15 {os.getpid()}",
        shell=True,
    )
    return status
