# Wing Carrier – Antigravity IDE Action Setup

This guide shows you how to add a keyboard shortcut in Antigravity IDE (VS Code) that sends the currently active file to a DCC application (Maya, Cascadeur, etc.) via Wing Carrier's pigeon system. The task is registered as a **User Task** (global), so it works in every workspace — not just this one.

---

## How It Works

Because Antigravity / VS Code has no Python API for reading the active editor, the active file path is passed to `dispatcher.py` via the VS Code task variable `${file}`. The script then:

1. Resolves the Python **module namespace** (by walking parent `__init__.py` files).
2. Finds a running DCC application that can receive the dispatch (e.g. Maya with its command port open).
3. Calls `carrier.send(...)` — which triggers an import/reload of the module in the target app and runs its `run()` function if one exists.

> **Note on selected text:** VS Code tasks have no built-in variable for the editor's selected text. The dispatcher will always operate in *import/reload mode*. If you need selected-text support in the future, a VS Code extension would be required.

---

## Step 1 – Add the task to User Tasks

User Tasks are global and apply to every workspace, unlike `.vscode/tasks.json`.

1. Open the Command Palette: `Ctrl+Shift+P`
2. Run **Tasks: Open User Tasks**
3. VS Code will open your global `tasks.json`. Add the following entry inside the `"tasks"` array:

```json
{
    "label": "Wing Carrier: Dispatch Active File",
    "type": "shell",
    "command": "python",
    "args": [
        "D:/Users/Anderson/Documents/github/wing-carrier/src/wingcarrier/3rdparty/antigravity/dispatcher.py",
        "${file}"
    ],
    "presentation": {
        "reveal": "always",
        "panel": "shared",
        "clear": false
    },
    "problemMatcher": []
}
```

> **Important:** Because this is a User Task (not workspace-relative), the path to `dispatcher.py` must be an **absolute path**. Update the path in `"args"` to match wherever `wing-carrier` lives on your machine.

> **Tip:** If `wingcarrier` is installed into a specific virtual environment, replace `"python"` with the full path to that environment's interpreter, e.g. `"C:/path/to/.venv/Scripts/python.exe"`.

---

## Step 2 – Bind the task to a keyboard shortcut

Open the **user** keybindings file:
- `Ctrl+Shift+P` → *Preferences: Open Keyboard Shortcuts (JSON)*

Add an entry like the one below. Change the `"key"` to whatever hotkey you prefer.

```json
[
    {
        "key": "ctrl+shift+e",
        "command": "workbench.action.tasks.runTask",
        "args": "Wing Carrier: Dispatch Active File"
    }
]
```

---

## Step 3 – Make sure the target DCC is ready

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
| `3rdparty/antigravity/dispatcher.py` | The script that resolves the module and dispatches to the pigeon |
| `3rdparty/antigravity/antigravity_action.md` | This setup guide |
| `3rdparty/wing/wing_ide_hotkeys/dispatcher.py` | The original Wing IDE equivalent for reference |
