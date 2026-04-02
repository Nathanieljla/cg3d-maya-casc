# How to Set Up Global debugpy Attach in VS Code

This guide explains how to configure VS Code so you can press **F5** to attach to a running `debugpy` instance from **any workspace** — no per-project `launch.json` required.

## Why?

By default, debug configurations live in `.vscode/launch.json` inside each workspace. If you want an **"Attach to debugpy"** option available globally (e.g., to connect to Maya, Cascadeur, or any DCC app running `debugpy`), you can add it to your **user-level settings** instead.

---

## Steps

### 1. Open User Settings (JSON)

1. Open VS Code
2. Press `Ctrl+Shift+P` to open the **Command Palette**
3. Type **"Preferences: Open User Settings (JSON)"** and select it

This opens your global `settings.json` file, typically located at:

```
%APPDATA%\Code\User\settings.json
```

### 2. Add the `launch` Configuration

Add the following `launch` key at the **top level** of your `settings.json` (alongside your other settings):

```json
{
    "launch": {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Attach to debugpy",
                "type": "debugpy",
                "request": "attach",
                "connect": {
                    "host": "localhost",
                    "port": 5678
                }
            }
        ]
    }
}
```

> **Note:** Make sure the `"launch"` block is placed as a sibling to your other top-level settings — not nested inside another key. If your `settings.json` already has content, just add the `"launch": { ... }` block with a comma after the preceding entry.

### 3. Press F5 to Connect

With a DCC application (e.g., Maya) running `debugpy` and listening on port `5678`, simply press **F5** in any workspace to attach the debugger.

---

## Good to Know

- **Merging with workspace configs** — If a workspace also has its own `.vscode/launch.json`, both the global and workspace configurations will appear in the debug dropdown. They don't overwrite each other.

- **Path mappings** — The global config above omits `pathMappings` since it's workspace-agnostic. If breakpoints aren't being hit, you can add a workspace-level `.vscode/launch.json` with the appropriate mappings:

    ```json
    {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Python: Maya Debugger",
                "type": "debugpy",
                "request": "attach",
                "connect": {
                    "host": "localhost",
                    "port": 5678
                },
                "pathMappings": [
                    {
                        "localRoot": "${workspaceFolder}",
                        "remoteRoot": "${workspaceFolder}"
                    }
                ]
            }
        ]
    }
    ```

- **Prerequisites** — Make sure you have the [Python Debugger extension](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy) (`ms-python.debugpy`) installed in VS Code.
