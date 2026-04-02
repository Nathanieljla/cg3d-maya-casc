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

def process_selection(selected_asset):
    """
    Process the selection. If config, return it.
    If Skeletal Mesh, create a new config next to it, set variables, and return it.
    """
    if not selected_asset:
        return None
        
    # If it's already a config, return it
    if selected_asset.get_class().get_name().startswith("PDA_CascadeurBridgeConfig"):
        return selected_asset
        
    # If it's a skeletal mesh, create a new config instance
    if isinstance(selected_asset, unreal.SkeletalMesh):
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        
        mesh_path = selected_asset.get_path_name()
        package_path = unreal.Paths.get_path(mesh_path)
        asset_name = f"{selected_asset.get_name()}_CascConfig"
        
        config_path = "/3DCG_Cascadeur_Bridge/Data/PDA_CascadeurBridgeConfig"
        
        # load_blueprint_class handles fetching the _C class under the hood given the standard asset path
        config_class = unreal.EditorAssetLibrary.load_blueprint_class(config_path)
        
        if not config_class:
            unreal.log_error(f"Could not load Blueprint class at {config_path}")
            return None
            
        factory = unreal.DataAssetFactory()
        
        # NOTE: A known quirk when using AssetTools in python with BP Data Assets is that 
        # sometimes you might need to set the factory property or just let Unreal infer it.
        new_asset = asset_tools.create_asset(asset_name, package_path, config_class, factory)
        
        if new_asset:
            # Set properties on the new instance
            new_asset.set_editor_property("character", selected_asset)
            new_uuid = uuid.uuid4().hex  # Generate string without dashes
            new_asset.set_editor_property("bridge_id", new_uuid)
            
            # Save the new asset
            unreal.EditorAssetLibrary.save_loaded_asset(new_asset)
            return new_asset
            
    return None

def run():
    selected = get_selected()
    if selected is None:
        return False

    bridge_config = process_selection(selected)
    if bridge_config is None:
        return False
    
    return True