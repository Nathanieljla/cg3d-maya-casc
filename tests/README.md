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
