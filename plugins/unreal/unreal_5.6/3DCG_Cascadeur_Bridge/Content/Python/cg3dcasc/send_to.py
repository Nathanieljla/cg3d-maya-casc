import unreal
import uuid

def get_selected():
    """
    Get the currently selected asset in the Content Browser.
    Must be exactly 1 SkeletalMesh or 1 PDA_CascadeurBridgeConfig.
    """
    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    
    if len(selected_assets) != 1:
        unreal.EditorDialog.show_message("Invalid Selection", "Please select exactly one Skeletal Mesh or Config asset.", unreal.AppMsgType.OK)
        return None
        
    asset = selected_assets[0]
    
    # Check if SkeletalMesh
    if isinstance(asset, unreal.SkeletalMesh):
        return asset
        
    # Check if instance of PDA_CascadeurBridgeConfig
    if asset.get_class().get_name().startswith("PDA_CascadeurBridgeConfig"):
        return asset
        
    unreal.EditorDialog.show_message("Invalid Selection", "Please select either a Skeletal Mesh or a Cascadeur Bridge Config.", unreal.AppMsgType.OK)
    return None

def create_new_config(selected_asset):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    mesh_path = selected_asset.get_path_name()
    package_path = unreal.Paths.get_path(mesh_path)
    base_name = f"{selected_asset.get_name()}_CascConfig"
    
    # Ensure unique name to avoid errors if one already exists
    unique_package_path, unique_asset_name = asset_tools.create_unique_asset_name(f"{package_path}/{base_name}", "")
    
    config_path = "/3DCG_Cascadeur_Bridge/Data/PDA_CascadeurBridgeConfig"
    
    # load_blueprint_class handles fetching the _C class under the hood given the standard asset path
    config_class = unreal.EditorAssetLibrary.load_blueprint_class(config_path)
    
    if not config_class:
        unreal.log_error(f"Could not load Blueprint class at {config_path}")
        return None
        
    factory = unreal.DataAssetFactory()
    
    # NOTE: A known quirk when using AssetTools in python with BP Data Assets is that 
    # sometimes you might need to set the factory property or just let Unreal infer it.
    new_asset = asset_tools.create_asset(unique_asset_name, package_path, config_class, factory)
    
    if new_asset:
        # Set properties on the new instance
        new_asset.set_editor_property("character", selected_asset)
        
        # Construct an Unreal Guid struct automatically
        new_guid = unreal.Guid()
        new_asset.set_editor_property("bridge_id", new_guid)
        
        # Save the new asset
        unreal.EditorAssetLibrary.save_loaded_asset(new_asset)
        return new_asset
        
    return None

def get_config(selected_skeletal_mesh):
    existing_config = None
    
    mesh_path = selected_skeletal_mesh.get_path_name()
    package_path = unreal.Paths.get_path(mesh_path)
    asset_name = f"{selected_skeletal_mesh.get_name()}_CascConfig"
    expected_path = f"{package_path}/{asset_name}.{asset_name}"
    
    # Check the exact expected path first
    if unreal.EditorAssetLibrary.does_asset_exist(expected_path):
        loaded_asset = unreal.EditorAssetLibrary.load_asset(expected_path)
        if loaded_asset and loaded_asset.get_class().get_name().startswith("PDA_CascadeurBridgeConfig"):
            if loaded_asset.get_editor_property("character") == selected_skeletal_mesh:
                existing_config = loaded_asset

    # If not found, look for referencers
    if not existing_config:
        try:
            referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(mesh_path)
            for ref_pkg in referencers:
                base_name = unreal.Paths.get_base_filename(ref_pkg)
                asset_path = f"{ref_pkg}.{base_name}"
                
                if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                    loaded_asset = unreal.EditorAssetLibrary.load_asset(asset_path)
                    if loaded_asset and loaded_asset.get_class().get_name().startswith("PDA_CascadeurBridgeConfig"):
                        if loaded_asset.get_editor_property("character") == selected_skeletal_mesh:
                            existing_config = loaded_asset
                            break
        except Exception:
            pass
            
    if existing_config:
        result = unreal.EditorDialog.show_message(
            "Existing Config Found", 
            f"An existing config '{existing_config.get_name()}' was found for this mesh.\nDo you want to use it? (No will create a new one)", 
            unreal.AppMsgType.YES_NO
        )
        if result == unreal.AppReturnType.YES:
            return existing_config
        else:
            return create_new_config(selected_skeletal_mesh)
            
    return create_new_config(selected_skeletal_mesh)

def process_selection(selected_asset):
    """
    Process the selection. If config, return it.
    If Skeletal Mesh, fetch or create a config for it.
    """
    if not selected_asset:
        return None
        
    # If it's already a config, return it
    if selected_asset.get_class().get_name().startswith("PDA_CascadeurBridgeConfig"):
        return selected_asset
        
    # If it's a skeletal mesh, get or create its config
    if isinstance(selected_asset, unreal.SkeletalMesh):
        return get_config(selected_asset)
            
    return None

def run():
    selected = get_selected()
    if selected is None:
        return

    bridge_config = process_selection(selected)
    if bridge_config is None:
        return
    
    print(bridge_config.get_path_name())
    
    character = bridge_config.get_editor_property("character")
    if character:
        import os
        import sys
        import subprocess
        try:
            from cg3dcasc import core
        except ImportError:
            import core
            
        mat_data = core.MaterialData.from_skel_mesh(character)
        if mat_data:
            save_loc = core.get_save_location()
            guid = bridge_config.get_editor_property("bridge_id")
            if not guid:
                guid_str = "unknown"
            else:
                try:
                    guid_str = guid.to_string()
                except Exception:
                    guid_str = "unknown"
                    
            file_name = f"material_data.{guid_str}.json"
            full_path = os.path.join(save_loc, file_name)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(mat_data.to_json())
                
            print(f"Saved material data to: {full_path}")
            
            # Open OS window to this location
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{os.path.normpath(full_path)}"')
            elif sys.platform == "darwin":
                subprocess.Popen(['open', '-R', full_path])
                
    return True