import json
import os
import subprocess
import sys
import urllib.request
from typing import Optional, List, Tuple

import ray
import psutil


RAY_OPEN_PORT_CHECKER_SERVICE_URL = (
    "https://ray-open-port-checker.uc.r.appspot.com/open-port-check"
)


def main():
    if not user_confirm(
        "Do you want to check the local Ray cluster for any nodes with ports accessible to the internet?"
    ):
        print("Exiting without checking as instructed")
        return

    cluster_open_ports = check_ray_cluster()

    public_nodes = []
    for node_id, (open_ports, checked_ports) in cluster_open_ports:
        if open_ports:
            print(
                f"[🛑] open ports detected open_ports={open_ports!r} node={node_id!r}"
            )
            public_nodes.append((node_id, open_ports, checked_ports))
        else:
            print(
                f"[🟢] No open ports detected checked_ports={checked_ports!r} node={node_id!r}"
            )

    print("Check complete, results:")

    if public_nodes:
        print(
            """
[🛑] An server on the internet was able to open a connection to one of this Ray
cluster's public IP on one of Ray's internal ports. If this is not a false
positive, this is an extremely unsafe configuration for Ray to be running in.
Ray is not meant to be exposed to untrusted clients and will allow them to run
arbitrary code on your machine.

You should take immediate action to validate this result and if confirmed shut
down your Ray cluster immediately and take appropriate action to remediate its
exposure. Anything either running on this Ray cluster or that this cluster has
had access to could be at risk.

For guidance on how to operate Ray safely, please review [Ray's security
documentation](https://docs.ray.io/en/master/ray-security/index.html).
""".strip()
        )
    else:
        print("[🟢] No open ports detected from any Ray nodes")


def user_confirm(question):
    reply = str(input(question + " (y/n): ")).lower().strip()
    if not reply:
        return user_confirm(question)
    elif reply[0] == "y":
        return True
    elif reply[0] == "n":
        return False
    else:
        return user_confirm(question)


def check_ray_cluster(
    ports: Optional[List[int]] = None,
) -> List[Tuple[str, Tuple[List[int], List[int]]]]:
    ray.init(ignore_reinit_error=True)

    @ray.remote(num_cpus=0)
    def check(node_id, ports):
        return node_id, check_if_exposed_to_internet(ports)

    ray_node_ids = [node["NodeID"] for node in ray.nodes() if node["Alive"]]
    print(
        f"Cluster has {len(ray_node_ids)} node(s). Scheduling tasks on each to check for exposed ports",
    )

    per_node_tasks = {
        node_id: (
            check.options(
                scheduling_strategy=ray.util.scheduling_strategies.NodeAffinitySchedulingStrategy(
                    node_id=node_id, soft=False
                )
            ).remote(node_id, ports)
        )
        for node_id in ray_node_ids
    }

    results = []
    for node_id, per_node_task in per_node_tasks.items():
        try:
            results.append(ray.get(per_node_task))
        except Exception as e:
            print(f"Failed to check on node {node_id}: {e}")
    return results


def check_if_exposed_to_internet(
    ports: Optional[List[int]] = None,
) -> Tuple[List[int], List[int]]:
    if ports is None:
        ports = get_ray_ports()

    return check_for_open_ports_from_internet(ports)


# Sourced from `python/ray/autoscaler/_private/constants.py``
RAY_PROCESSES = [
    # The first element is the substring to filter.
    # The second element, if True, is to filter ps results by command name
    # (only the first 15 charactors of the executable name on Linux);
    # if False, is to filter ps results by command with all its arguments.
    # See STANDARD FORMAT SPECIFIERS section of
    # http://man7.org/linux/man-pages/man1/ps.1.html
    # about comm and args. This can help avoid killing non-ray processes.
    # Format:
    # Keyword to filter, filter by command (True)/filter by args (False)
    ["raylet", True],
    ["plasma_store", True],
    ["monitor.py", False],
    ["ray.util.client.server", False],
    ["default_worker.py", False],  # Python worker.
    ["setup_worker.py", False],  # Python environment setup worker.
    # For mac osx, setproctitle doesn't change the process name returned
    # by psutil but only cmdline.
    [
        "ray::",
        sys.platform != "darwin",
    ],  # Python worker. TODO(mehrdadn): Fix for Windows
    ["io.ray.runtime.runner.worker.DefaultWorker", False],  # Java worker.
    ["log_monitor.py", False],
    ["reporter.py", False],
    [os.path.join("dashboard", "agent.py"), False],
    [os.path.join("dashboard", "dashboard.py"), False],
    [os.path.join("runtime_env", "agent", "main.py"), False],
    ["ray_process_reaper.py", False],
    ["gcs_server", True],
]


def get_ray_ports() -> List[int]:
    unique_ports = set()

    process_infos = []
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            process_infos.append((proc, proc.name(), proc.cmdline()))
        except psutil.Error:
            pass

    for keyword, filter_by_cmd in RAY_PROCESSES:
        for candidate in process_infos:
            proc, proc_cmd, proc_args = candidate
            corpus = proc_cmd if filter_by_cmd else subprocess.list2cmdline(proc_args)
            if keyword in corpus:
                try:
                    for connection in proc.connections():
                        if connection.status == psutil.CONN_LISTEN:
                            unique_ports.add(connection.laddr.port)
                except psutil.AccessDenied:
                    print(
                        "Access denied to process connections for process, worker process probably restarted",
                        proc,
                    )

    return sorted(unique_ports)


def check_for_open_ports_from_internet(ports: List[int]) -> Tuple[List[int], List[int]]:
    request = urllib.request.Request(
        method="POST",
        url=RAY_OPEN_PORT_CHECKER_SERVICE_URL,
        headers={
            "Content-Type": "application/json",
            "X-Ray-Open-Port-Check": "1",
        },
        data=json.dumps({"ports": ports}).encode("utf-8"),
    )

    response = urllib.request.urlopen(request)
    if response.status != 200:
        raise RuntimeError(
            f"Failed to check with Ray Open Port Service: {response.status}"
        )
    response_body = json.load(response)

    publicly_open_ports = response_body.get("open_ports", [])
    checked_ports = response_body.get("checked_ports", [])

    return publicly_open_ports, checked_ports


if __name__ == "__main__":
    main()
