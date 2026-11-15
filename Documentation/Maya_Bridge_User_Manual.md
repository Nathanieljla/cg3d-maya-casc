# Maya Bridge User Manual

**Maya and Cascadeur workflow guide**  
Current development build - November 2026

## 1. What the bridge does

The Maya Bridge moves characters, animation, models, rigs, and material texture references between Autodesk Maya and Cascadeur. It uses FBX for scene data and a small amount of bridge metadata to recognize the same character on later transfers.

The most common loop is:

1. Prepare a character in Maya.
2. Send it to Cascadeur with **Cascadeur > Quick Export**.
3. Animate or edit the character in Cascadeur.
4. Send the animation back with **Maya > Export Animation** in Cascadeur.
5. Repeat without creating duplicate characters.

The bridge is designed around persistent **export sets**. An export set says what belongs to a character and stores an ID that lets Maya and Cascadeur match the same data on later transfers.

## 2. Before you begin

- Start Maya and Cascadeur.
- Confirm that Maya has a top-level **Cascadeur** menu.
- Confirm that Cascadeur has commands under **Maya**.
- Save both scenes before the first transfer.
- For automatic transfers, both applications must be running and connected.

Maya normally opens its bridge command port during startup. If the applications do not recognize each other, run **Cascadeur > Connect** in Maya. A successful connection reports a completion message in Maya and a connected port in Cascadeur.

The bridge uses a temporary `mayacasc` folder while transferring files. Those files are working data, not a replacement for saving either scene.

## 3. Export sets and matching IDs

### Export sets in Maya

A Maya export set is an `objectSet` with `CascExportData`. It usually has a name ending in `_CSC_EXPORT`. The set stores:

- the objects that seed the export;
- a persistent Cascadeur ID;
- whether the set is dynamic;
- the Texture Export mode and optional texture location;
- optional HIK and quick-rig settings.

With **Dynamic Set** enabled, the bridge expands the listed content through skinning and HIK relationships. A mesh can bring its skinCluster and influences, and a joint or skinCluster can bring the required meshes and skeleton. The current exporter trims unrelated branches rather than exporting every child under a top-level group.

With **Dynamic Set** disabled, the set behaves more literally and exports only its explicit joints, meshes, transforms, and skinClusters.

### Export sets in Cascadeur

A Cascadeur export set is a scene object with **Maya Data** and **Maya Roots** behaviours. Maya Roots contains the root objects assigned to the set. Maya Data stores the matching Maya ID and export settings such as Bake Animation.

### Why the ID matters

The ID is the bridge's identity card. When both sides contain the same ID, a transfer updates the existing character. When Cascadeur sends an ID Maya has never seen, Maya imports new data and creates a matching export set.

Do not edit or synchronize IDs during normal work. Use a Sync ID command only to repair a relationship you understand. Assigning the wrong ID can update the wrong character.

## 4. First transfer: Maya to Cascadeur

### Fast path with Quick Export

1. If the scene has no export set yet, select the character root, important meshes, or joints you want to seed the first set.
2. Choose **Cascadeur > Quick Export**.
3. If the Maya scene already contains export sets, the bridge exports all of those sets; the ordinary Maya selection does not narrow that list.
4. If no export set exists, the bridge creates `CACS_EXPORT`:
   - from the current selection, if there is one;
   - otherwise from top-level scene assemblies, excluding cameras.
5. Cascadeur imports the FBX and creates matching Maya Data and Maya Roots behaviours.

Quick Export uses automatic import behavior in Cascadeur:

- A new ID imports the scene data and creates a new Cascadeur export set.
- A known ID updates the existing character, normally as animation.
- If quick-rig data is included for an existing character, Cascadeur can apply the rig data without importing a duplicate FBX hierarchy.

### Send to the current or a new Cascadeur scene

Use these Maya commands when you want explicit scene placement:

- **Cascadeur > Add To > Current Scene** imports the Maya data into the open Cascadeur scene.
- **Cascadeur > Add To > New Scene** creates a Cascadeur scene and imports the Maya data there.

### Choosing what belongs in a set

For a skinned character, a useful starting set contains the skinned meshes, a relevant joint or the skinCluster, and any additional transform that must travel with the character. Dynamic Set usually finds the rest. Use the Maya Bridge editor to add or remove exceptions.

## 5. Updating Cascadeur from Maya

After the first transfer, use the matching update command instead of creating another set:

- **Update Animation(s)** exports and imports animation data for matching characters.
- **Update Model(s)** exports current model data for the set.
- **Update Textures** rebuilds the Reference-mode material sidecar and reapplies the latest texture mapping without exporting another FBX.
- **Quick Export** remains the convenient general-purpose option and decides how Cascadeur should import based on the existing ID and available data.

An update is matched by ID, not merely by object name. Renaming an export set does not intentionally create a new character as long as its ID remains intact.

## 6. Sending animation from Cascadeur to Maya

1. Make sure the intended Cascadeur export set exists.
2. To export only particular sets, select those export set objects. With none selected, the command considers all scene export sets.
3. Choose **Maya > Export Animation**.
4. Cascadeur compares its set IDs with the IDs currently available in Maya.
5. Existing IDs update their matching Maya characters. Unknown IDs are imported as new data after confirmation.

If there are no Cascadeur export sets, the command can offer to create one containing the available scene roots. If only some selected sets match Maya, the bridge asks whether to export only matching sets or all selected/scene sets.

The **Bake Animation** value on each Cascadeur Maya Data behaviour controls whether animation is baked into the outgoing FBX.

On Maya import, a matching HIK character is switched to no active source so the imported animation can be seen. New data receives a Maya export set with the Cascadeur ID.

## 7. Export Character and Rig

Use **Maya > Export Character and Rig** in Cascadeur when the goal is to recreate a Cascadeur character in Maya with an HIK definition.

Current requirements:

- The Cascadeur scene must contain exactly one Rig Info behaviour.
- Rig Info must define valid `qrt_json` data.
- Rig Info must contain related joints.

The command exports the Rig Info skeleton plus meshes influenced by that skeleton. It also writes mapping information used by Maya to create an HIK character definition. SplineIK chains are included so multi-joint spines can be assigned correctly. Twist joints are mapped to the available HIK roll slots.

The command does not build the Maya HIK control rig. After import, open Maya's HumanIK tools, review the definition, and create the control rig when desired.

If the same character content already has a matching Cascadeur export set, the command reuses it and preserves its ID. Repeated exports therefore update the same Maya-side relationship instead of creating a fresh set every time.

## 8. Texture modes

Select a Maya export set and edit its **Texture Export** attribute. New export sets default to **Reference**:

### Embed

- FBX Embed Media is enabled.
- The bridge does not write its custom material sidecar.
- Cascadeur does not run bridge texture-remapping logic.

Use Embed for a self-contained FBX transfer when FBX media embedding is the desired behavior.

### Reference

- FBX media embedding is disabled.
- Maya writes a material sidecar that maps meshes, material instances, properties, texture files, and supported packed-map channels.
- Project-relative Maya paths are resolved to absolute paths before export.
- Cascadeur applies the mapping to official material instances created by FBX import.

If **Texture Location** is empty, Cascadeur references the source texture at its resolved absolute location.

If Texture Location is set, the bridge creates that directory when possible. JPG, JPEG, and PNG images are copied there if missing. Other readable image types are converted to PNG. Existing destination files are left in place.

Packed image channels are supported for roughness, metallic, reflectance, and ambient occlusion. The sidecar records R, G, B, or A channel selection when an individual channel is connected. Whole-color connections fall back to the expected default channel behavior.

After changing Maya material connections or texture paths, run **Cascadeur > Update > Update Textures** to rebuild and reload the complete mapping. Removed mappings are cleared rather than leaving stale Cascadeur paths behind.

## 9. Maya command reference

| Command | Purpose |
|---|---|
| Quick Export | Export known sets, or create a default set when none exists, then auto-import in Cascadeur. |
| Update > Update Animation(s) | Send animation updates to matching Cascadeur sets. |
| Update > Update Model(s) | Send model updates to matching Cascadeur sets. |
| Update > Update Textures | Rebuild and apply Reference-mode material mappings only. |
| Add To > Current Scene | Import Maya data into the open Cascadeur scene. |
| Add To > New Scene | Create a Cascadeur scene and import Maya data. |
| Connect | Refresh the Maya/Cascadeur command-port connection. |
| Import | Ask Cascadeur to export animation and import the result into Maya. |
| Editor | Open the Maya Bridge export-set and HIK editor. |
| Preferences | Configure baking and proxy-rig utility behavior. |

### Maya utility commands

| Command | Purpose |
|---|---|
| Create Proxy From Selection | Clone selected skinned content into a proxy skeleton and mesh hierarchy, then create an export set. |
| Constrain Proxy | Parent-constrain proxy joints to their recorded source joints. |
| HIK Character from Proxy | Build a new HIK definition for the original joints by reading the active proxy HIK definition. |
| Convert Textures | Convert unsupported textures under the selected roots to Cascadeur-supported images. |
| Sync Cascadeur ID | Replace one selected Maya export set ID with one selected Cascadeur set ID. Use only for deliberate repair. |

## 10. Cascadeur command reference

| Command | Purpose |
|---|---|
| Maya > Export Animation | Export selected export sets, or all sets, and send them to Maya. |
| Maya > Export Character and Rig | Export one Rig Info character, influenced meshes, and HIK mapping data to Maya. |
| Maya > Export Sets > Create New Set | Create a set from selected roots, or available scene roots when appropriate. |
| Maya > Export Sets > Add Selected | Add selected root objects to an existing or chosen set. |
| Maya > Export Sets > Remove Selected | Remove selected roots from their assigned sets. |
| Maya > Export Sets > Select Set Members | Select the Maya Roots assigned to a chosen set. |
| Maya > Export Sets > Sync Maya ID | Replace one Cascadeur set ID with the ID of one selected Maya set. Use only for repair. |

## 11. The Maya Bridge editor

The editor is the easiest place to manage Maya export sets without editing objectSet membership manually.

Use the selection-set tab to:

- create or delete an export set;
- add the Maya selection;
- remove listed members;
- enable or disable Dynamic Set.

Use the rig tab after associating an HIK character to:

- choose the chest/spine joint used by quick rig;
- set optional left and right weapon joints;
- control pelvis alignment and layer creation;
- choose global or per-limb twist axes;
- export the rig to the current or a new Cascadeur scene.

The editor stores these choices on the export set, so they travel with the Maya scene.

## 12. Troubleshooting

### The applications are not connected

- Confirm both applications are running.
- Run **Cascadeur > Connect** in Maya.
- Check Maya's Script Editor and Cascadeur's command output for a port or connection error.
- Restart the application that was opened first if its command server was not available during the other application's startup.

### Too much scene data is exported

- Open the Maya Bridge editor and inspect each export set.
- Remove unrelated roots or disable Dynamic Set for a literal selection.
- Confirm the character is not being seeded by an overly broad top-level transform.
- In Cascadeur, select only the export sets intended for **Export Animation**.

### A duplicate character is created

- Compare the export set IDs on both sides.
- Do not create a new set for routine updates.
- If a set was rebuilt and its relationship was intentionally lost, select exactly one set in each application and use Sync ID after saving backups.

### Animation updates but the model does not

Use **Update Model(s)** for geometry changes. The automatic existing-character path normally favors animation updates.

### Textures do not appear

- Confirm the Maya export set uses Reference mode if you expect sidecar mapping.
- Confirm the source image exists and Maya can resolve its project-relative path.
- Check Texture Location permissions when a custom folder is used.
- Run **Update Textures** after changing material connections.
- Confirm Cascadeur supports the targeted material property and channel.

### Export Character and Rig is unavailable or fails

- Confirm there is exactly one Rig Info behaviour.
- Confirm Rig Info contains related joints and valid `qrt_json`.
- Remember that the command creates an HIK definition, not an HIK control rig.

## 13. Recommended habits

- Save both applications before transferring.
- Keep one export set per logical character or independent asset.
- Reuse export sets instead of recreating them.
- Treat set IDs as persistent data.
- Use Dynamic Set for normal skinned-character workflows and inspect the result when a hierarchy contains unrelated branches.
- Use Reference texture mode when you need explicit material-instance mapping or packed-map channel control.
- Use Sync ID only as a repair tool and only after making backups.

