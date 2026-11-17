# Test suite

The default suite uses only Python's standard library. It replaces the Maya and
Cascadeur APIs with small host fakes, so it can run quickly without starting
either application:

```powershell
python -m unittest discover -s tests -t . -v
```

The command inventory tests intentionally fail when a new Maya menu command or
Cascadeur command is added without an explicit routing expectation. Add the new
entry point to `test_command_entrypoints.py`, then add behavior coverage in the
closest workflow test module.

The suite covers:

- every Maya and Cascadeur command entry point;
- export-set selection, creation, membership, and ID synchronization;
- Maya and Cascadeur FBX adapters;
- Maya-to-Cascadeur and Cascadeur-to-Maya import/export decisions;
- material sidecars, relative paths, packed texture channels, and refreshes;
- proxy skin wiring and texture conversion;
- temporary file and `.fbm` directory cleanup;
- command ports, command dispatch, and length-prefixed JSON transport;
- migration guards for PyMel and the temporary `_v2` package names.

Host-isolated tests are the required fast gate. Scene-level smoke tests should
also be run in clean Maya and Cascadeur processes before publishing, because
their proprietary APIs are not importable in ordinary Python and can change
between host versions.

## Clean-process release smoke tests

Close Maya and Cascadeur, then run:

```powershell
python tests/integration/run_clean_process_tests.py
```

The runner starts Maya 2027's `mayapy` and the development Cascadeur build,
verifies that both load this checkout, and closes the Cascadeur process it
started. It never reads or writes the published `cascadeur_pub_163` package.

The Maya process tests UUID-backed nodes with duplicate short names, uData
defaults, a real selection-only FBX round trip, packed-channel Reference
materials, and proxy-skeleton deformation. The Cascadeur process tests command
registration, export-set creation/membership/ID synchronization, selection,
recursive `.fbm` cleanup, and the Embed/no-sidecar texture path.

Override host locations when necessary:

```powershell
python tests/integration/run_clean_process_tests.py `
  --mayapy "C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe" `
  --cascadeur "D:\path\to\cascadeur.exe"
```
