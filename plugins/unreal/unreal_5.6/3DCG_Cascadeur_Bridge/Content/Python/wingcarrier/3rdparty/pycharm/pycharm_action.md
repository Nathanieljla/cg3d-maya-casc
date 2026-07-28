# Wing Carrier – PyCharm Action Setup

This guide shows you how to add a keyboard shortcut in **PyCharm** (or any JetBrains IDE) that sends the currently active file to a DCC application (Maya, Cascadeur, etc.) via Wing Carrier's pigeon system. The tool is registered as a **PyCharm External Tool** (global), so it works across all projects.

---

## How It Works

Because PyCharm has no Python API for reading the active editor from an external script, the active file path is passed to `dispatcher.py` via the PyCharm External Tool macro `$FilePath$`. The script then:

1. Resolves the Python **module namespace** (by walking parent `__init__.py` files).
2. Finds a running DCC application that can receive the dispatch (e.g. Maya with its command port open).
3. Calls `carrier.send(...)` — which triggers an import/reload of the module in the target app and runs its `run()` function if one exists.

> **Note on selected text:** PyCharm External Tools have no built-in macro for the editor's selected text. The dispatcher will always operate in *import/reload mode*.

---

## Step 1 – Add an External Tool

1. Open **Settings** → **Tools** → **External Tools** → click `+`
2. Fill in the fields:

| Field | Value |
|---|---|
| **Name** | `Wing Carrier: Dispatch Active File` |
| **Program** | `python` (or full path to your venv interpreter, e.g. `C:/path/to/.venv/Scripts/python.exe`) |
| **Arguments** | `D:/Users/Anderson/Documents/github/wing-carrier/src/wingcarrier/3rdparty/pycharm/dispatcher.py $FilePath$` |
| **Working directory** | `$ProjectFileDir$` |

> **Important:** The path to `dispatcher.py` in **Arguments** must be an **absolute path**. Update it to match wherever `wing-carrier` lives on your machine.

---

## Step 2 – Bind a Keyboard Shortcut

1. Open **Settings** → **Keymap**
2. Search for `External Tools` → expand to find `Wing Carrier: Dispatch Active File`
3. Right-click → **Add Keyboard Shortcut** → press your preferred key combo (e.g. `Ctrl+Shift+E`)

---

## Step 3 – Make Sure the Target DCC Is Ready

**Maya:**
- Ensure Maya has its command port open. Add the following to your `userSetup.py` (or run it manually in Maya's Script Editor before dispatching):

```python
import maya.cmds as cmds
if not cmds.commandPort(':6000', query=True):
    cmds.commandPort(name=':6000', sourceType='python')
```

**Cascadeur:**
- Follow the Cascadeur-specific Wing Carrier setup in `3rdparty/cascadeur/`.

---

## File Reference

| File | Purpose |
|---|---|
| `3rdparty/pycharm/dispatcher.py` | The script that resolves the module and dispatches to the pigeon |
| `3rdparty/pycharm/pycharm_action.md` | This setup guide |
| `3rdparty/antigravity/dispatcher.py` | The VS Code / Antigravity equivalent for reference |
| `3rdparty/wing/wing_ide_hotkeys/dispatcher.py` | The original Wing IDE equivalent for reference |
