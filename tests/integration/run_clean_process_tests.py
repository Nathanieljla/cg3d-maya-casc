"""Launch and verify the bridge in clean Maya and Cascadeur processes."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
INTEGRATION_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_MAYAPY = pathlib.Path(r"C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe")
DEFAULT_CASCADEUR = pathlib.Path(
    r"D:\Users\Anderson\Documents\github\Cascadeur-build-win\cascadeur.exe"
)
DEFAULT_CORE_SRC = REPO_ROOT.parent / "cg3d-maya-core" / "src"
CASCADEUR_SITE = REPO_ROOT / "src" / "cg3dcasc" / "casc-site"


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _json_request(url, payload=None, timeout=5.0):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_cascadeur(base_url, process, timeout):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError("Cascadeur exited during startup with code {}".format(process.returncode))
        try:
            health = _json_request(base_url + "/health", timeout=2.0)
            if health.get("ok"):
                return health
        except (OSError, urllib.error.URLError, ValueError) as error:
            last_error = error
        time.sleep(0.25)
    raise RuntimeError("Cascadeur script server did not start: {}".format(last_error))


def run_maya(mayapy, core_src, timeout):
    if not mayapy.is_file():
        raise FileNotFoundError("mayapy was not found: {}".format(mayapy))
    environment = os.environ.copy()
    environment["CG3D_MAYA_CORE_SRC"] = str(core_src)
    command = [str(mayapy), str(INTEGRATION_ROOT / "maya_host_smoke.py")]
    print("\n=== Clean Maya process ===")
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    print(completed.stdout)
    if completed.returncode:
        raise RuntimeError("Maya smoke tests failed with code {}".format(completed.returncode))


def run_cascadeur(executable, port, timeout, connect_existing=False, leave_open=False):
    base_url = "http://127.0.0.1:{}".format(port)
    process = None
    log_handle = None
    log_path = pathlib.Path(tempfile.gettempdir()) / "cg3dcasc-clean-cascadeur.log"
    try:
        if not connect_existing:
            if not executable.is_file():
                raise FileNotFoundError("Cascadeur was not found: {}".format(executable))
            environment = os.environ.copy()
            environment["CASCADEUR_MCP_AUTOSTART"] = "1"
            environment["CASCADEUR_MCP_PORT"] = str(port)
            log_handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(
                [str(executable)],
                cwd=str(executable.parent),
                env=environment,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )

        print("\n=== Clean Cascadeur process ===")
        health = _wait_for_cascadeur(base_url, process, timeout)
        print("Connected to Cascadeur process {}".format(health.get("process", health.get("pid", "unknown"))))
        code = (INTEGRATION_ROOT / "cascadeur_host_smoke.py").read_text(encoding="utf-8")
        response = _json_request(
            base_url + "/run",
            {
                "code": code,
                "args": {
                    "site_root": str(CASCADEUR_SITE),
                    "unreal_scene": str(
                        executable.parent
                        / "samples"
                        / "UE5_Manny.casc"
                    ),
                },
                "timeout": min(timeout, 120),
            },
            timeout=timeout + 5,
        )
        if not response.get("ok"):
            raise RuntimeError(
                "Cascadeur smoke tests failed:\n{}".format(
                    response.get("error") or response.get("errors") or response
                )
            )
        result = response.get("result") or {}
        print(json.dumps(result, indent=2))
        if not result.get("count"):
            raise RuntimeError("Cascadeur smoke script returned no checks")
    finally:
        if process is not None and not leave_open:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if log_handle is not None:
            log_handle.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mayapy", type=pathlib.Path, default=DEFAULT_MAYAPY)
    parser.add_argument("--cascadeur", type=pathlib.Path, default=DEFAULT_CASCADEUR)
    parser.add_argument("--core-src", type=pathlib.Path, default=DEFAULT_CORE_SRC)
    parser.add_argument("--cascadeur-port", type=int)
    parser.add_argument("--connect-existing-cascadeur", action="store_true")
    parser.add_argument("--leave-cascadeur-open", action="store_true")
    parser.add_argument("--maya-only", action="store_true")
    parser.add_argument("--cascadeur-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.maya_only and args.cascadeur_only:
        raise ValueError("Choose at most one of --maya-only and --cascadeur-only")
    if not args.cascadeur_only:
        run_maya(args.mayapy.resolve(), args.core_src.resolve(), args.timeout)
    if not args.maya_only:
        port = args.cascadeur_port or (8765 if args.connect_existing_cascadeur else _free_port())
        run_cascadeur(
            args.cascadeur.resolve(),
            port,
            args.timeout,
            connect_existing=args.connect_existing_cascadeur,
            leave_open=args.leave_cascadeur_open,
        )
    print("\nAll clean-process smoke tests passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("\nCLEAN PROCESS TEST FAILURE: {}".format(error), file=sys.stderr)
        raise
