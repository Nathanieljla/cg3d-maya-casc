import unreal

def register_my_tool():
    # This registers the widget so it appears on the Main Toolbar
    tool_menus = unreal.ToolMenus.get()
    
    # Look for the UE5 Assets ToolBar first, fallback to UE4 MainToolBar if not found
    toolbar = tool_menus.find_menu("LevelEditor.LevelEditorToolBar.AssetsToolBar")
    if not toolbar:
        toolbar = tool_menus.find_menu("LevelEditor.LevelEditorToolBar.MainToolBar")
    
    if not toolbar:
        unreal.log_error("Could not find the Main Toolbar to add the Cascadeur Bridge button.")
        return
        
    entry = unreal.ToolMenuEntry(
        name="CascadeurBridge_ToolbarButton",
        type=unreal.MultiBlockType.TOOL_BAR_BUTTON
    )
    entry.set_label("Cascadeur Bridge")
    entry.set_tool_tip("Open the Cascadeur Bridge Widget")
    
    # You can optionally add an icon here. For example:
    # entry.set_icon("EditorStyle", "ClassIcon.SkeletalMesh")
    
    exec_string = (
        'import unreal; '
        'subsystem = unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem); '
        'euw = unreal.EditorAssetLibrary.load_asset("/3DCG_Cascadeur_Bridge/Widgets/EUW_CascBridgeDashboard"); '
        'subsystem.spawn_and_register_tab(euw) if euw else unreal.log_error("Could not load widget")'
    )
    
    entry.set_string_command(
        type=unreal.ToolMenuStringCommandType.PYTHON,
        custom_type=unreal.Name(""),
        string=exec_string
    )
    
    # Add a section just for this plugin so we don't need to guess existing section names
    toolbar.add_section("CascadeurPlugin", "Cascadeur")
    toolbar.add_menu_entry("CascadeurPlugin", entry)
    
    # Refresh the UI so the button shows up immediately
    tool_menus.refresh_all_widgets()

register_my_tool()