from __future__ import annotations

import json
import struct
import sys
import types
import unittest

from tests._support import (
    CASCADEUR_SITE_ROOT,
    SRC_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class FakeConnection:
    def __init__(self, incoming=b""):
        self.incoming = incoming
        self.sent = b""
        self.closed = False

    def recv(self, size):
        chunk = self.incoming[:size]
        self.incoming = self.incoming[size:]
        return chunk

    def sendall(self, data):
        self.sent += data

    def close(self):
        self.closed = True


class FakeSocket(FakeConnection):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.connected_to = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def connect(self, address):
        self.connected_to = address


class FakeCommandPort(types.ModuleType):
    def __init__(self):
        super().__init__("maya.cmds")
        self.open_ports = set()
        self.fail_ports = set()
        self.calls = []

    def commandPort(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if kwargs.get("q"):
            return int(args[0][1:]) in self.open_ports
        port = int(kwargs["n"][1:])
        if port in self.fail_ports:
            raise RuntimeError("port in use")
        self.open_ports.add(port)
        return True


class CommandPortTests(unittest.TestCase):
    def _load(self, cmds):
        maya = make_package("maya", cmds=cmds)
        with installed_modules({"maya": maya, "maya.cmds": cmds}):
            return load_module(
                "_transport_command_port", SRC_ROOT / "core" / "command_port.py"
            )

    def tearDown(self):
        sys.modules.pop("_transport_command_port", None)

    def test_reuses_a_still_open_port(self):
        cmds = FakeCommandPort()
        cmds.open_ports.add(6007)
        module = self._load(cmds)
        module.port_number = 6007

        self.assertTrue(module.open())

        self.assertEqual([((":6007",), {"q": True})], cmds.calls)

    def test_scans_past_occupied_ports(self):
        cmds = FakeCommandPort()
        cmds.fail_ports.update({6000, 6001})
        module = self._load(cmds)

        self.assertTrue(module.open())

        self.assertEqual(6002, module.port_number)

    def test_reports_failure_when_every_candidate_is_occupied(self):
        cmds = FakeCommandPort()
        cmds.fail_ports.update(range(6000, 6051))
        module = self._load(cmds)

        self.assertFalse(module.open())

        self.assertIsNone(module.port_number)


class MayaServerTests(unittest.TestCase):
    def _load(self, port_opens=True, send_result=True):
        cmds = make_module("maya.cmds", error=CallRecorder(), warning=CallRecorder())
        maya = make_package("maya", cmds=cmds)
        port = make_module(
            "_transport_maya_host.command_port",
            open=CallRecorder(port_opens),
            port_number=6020,
        )
        prefs = make_module("cg3dcasc.preferences")
        package = make_package("_transport_maya_host")
        pigeon = types.SimpleNamespace(send_python_command=CallRecorder(send_result))
        pigeons = make_module(
            "wingcarrier.pigeons", CascadeurPigeon=lambda: pigeon
        )
        wingcarrier = make_package("wingcarrier", pigeons=pigeons)
        cg3dcasc = make_package("cg3dcasc", preferences=prefs)
        modules = {
            "maya": maya,
            "maya.cmds": cmds,
            "cg3dcasc": cg3dcasc,
            "cg3dcasc.preferences": prefs,
            "wingcarrier": wingcarrier,
            "wingcarrier.pigeons": pigeons,
            "_transport_maya_host": package,
            "_transport_maya_host.command_port": port,
        }
        with installed_modules(modules):
            module = load_module(
                "_transport_maya_host.server", SRC_ROOT / "core" / "server.py"
            )
        return module, port, pigeon, cmds, wingcarrier, pigeons

    def tearDown(self):
        sys.modules.pop("_transport_maya_host.server", None)

    def test_wraps_command_with_active_maya_port(self):
        module, unused_port, pigeon, unused_cmds, wingcarrier, pigeons = self._load()

        with installed_modules(
            {"wingcarrier": wingcarrier, "wingcarrier.pigeons": pigeons}
        ):
            self.assertTrue(module.send_to_casc("cg3dmaya.smart_import()"))

        self.assertEqual(
            [
                ((
                    "import cg3dmaya; cg3dmaya.set_active_port(6020); "
                    "cg3dmaya.smart_import()",
                ), {})
            ],
            pigeon.send_python_command.calls,
        )

    def test_does_not_dispatch_when_command_port_cannot_open(self):
        module, unused_port, pigeon, unused_cmds, wingcarrier, pigeons = self._load(
            port_opens=False
        )

        with installed_modules(
            {"wingcarrier": wingcarrier, "wingcarrier.pigeons": pigeons}
        ):
            self.assertFalse(module.send_to_casc("ignored()"))

        self.assertEqual([], pigeon.send_python_command.calls)


class ProtocolTests(unittest.TestCase):
    def tearDown(self):
        for name in (
            "_transport_maya_client",
            "_transport_casc_client",
            "_transport_casc_server",
        ):
            sys.modules.pop(name, None)

    def test_maya_client_sends_length_prefixed_json(self):
        cmds = make_module("maya.cmds", warning=CallRecorder())
        maya = make_package("maya", cmds=cmds)
        sock = FakeSocket()
        socket_module = make_module(
            "socket",
            AF_INET=2,
            SOCK_STREAM=1,
            socket=lambda *args, **kwargs: sock,
        )
        with installed_modules(
            {"maya": maya, "maya.cmds": cmds, "socket": socket_module}
        ):
            module = load_module(
                "_transport_maya_client", SRC_ROOT / "core" / "client.py"
            )
            module.set_port(7411)
            module.data_to_casc({"answer": 42})

        size = struct.unpack(">I", sock.sent[:4])[0]
        self.assertEqual(size, len(sock.sent[4:]))
        self.assertEqual({"answer": 42}, json.loads(sock.sent[4:].decode("utf-8")))
        self.assertEqual(("127.0.0.1", 7411), sock.connected_to)

    def test_cascadeur_client_sends_length_prefixed_json(self):
        sock = FakeSocket()
        socket_module = make_module(
            "socket",
            AF_INET=2,
            SOCK_STREAM=1,
            socket=lambda *args, **kwargs: sock,
        )
        scene = types.SimpleNamespace(warning=CallRecorder(), error=CallRecorder())
        with installed_modules({"socket": socket_module}):
            module = load_module(
                "_transport_casc_client",
                CASCADEUR_SITE_ROOT / "cg3dmaya" / "client.py",
            )
            module.set_port(7412)
            module.data_to_maya(scene, ["one", "two"])

        size = struct.unpack(">I", sock.sent[:4])[0]
        self.assertEqual(size, len(sock.sent[4:]))
        self.assertEqual(["one", "two"], json.loads(sock.sent[4:].decode("utf-8")))
        self.assertEqual(("127.0.0.1", 7412), sock.connected_to)

    def test_server_handler_reassembles_fragmented_json_and_closes(self):
        pycsc = make_module("pycsc")
        with installed_modules({"pycsc": pycsc}):
            module = load_module(
                "_transport_casc_server",
                CASCADEUR_SITE_ROOT / "cg3dmaya" / "server.py",
            )
        payload = json.dumps({"ids": ["a", "b"]}).encode("utf-8")
        connection = FakeConnection(struct.pack(">I", len(payload)) + payload)

        success, data = module.handle_client(connection, ("local", 1))

        self.assertTrue(success)
        self.assertEqual({"ids": ["a", "b"]}, data)
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
