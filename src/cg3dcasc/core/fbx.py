import pymel.core as pm
import os
import cg3dguru.utils

#http://tech-artists.org/forum/showthread.php?4988-Problem-doing-an-FBX-export-with-PyMEL
#http://download.autodesk.com/global/docs/maya2014/en_us/index.html?url=files/GUID-377B0ACE-CEC8-4D13-81E9-E8C9425A8B6E.htm,topicNumber=d30e145135

_EXPORT_NODES = None

EXPORT_ANIM = 0x01
EXPORT_RIG  = 0x01 << 1
EXPORT_ANIM_RIG = EXPORT_ANIM | EXPORT_RIG



def set_export_options(export_type, bake_animations=True, remove_namespaces=False):
    ##https://help.autodesk.com/view/MAYAUL/2022/ENU/index.html?guid=GUID-699CDF74-3D64-44B0-967E-7427DF800290
    start = int(pm.animation.playbackOptions(query=True, animationStartTime=True))
    end = int(pm.animation.playbackOptions(query=True, animationEndTime=True))
    _bake_anims = bool(export_type & EXPORT_ANIM)
    export_rig = bool(export_type & EXPORT_RIG)
    
    print('export animations:{0} export rig:{1}'.format(_bake_anims, export_rig))
    print('start:{0} end:{1}'.format(start, end))
    
    pm.mel.FBXResetExport()
    pm.mel.FBXExportUpAxis(v=pm.cmds.upAxis(q=True, axis=True))
    pm.mel.FBXExportBakeComplexStart(v=start)
    pm.mel.FBXExportBakeComplexEnd(v=end)
    pm.mel.FBXExportBakeComplexAnimation(v= _bake_anims and bake_animations)    
    pm.mel.FBXExportBakeResampleAnimation (v= True )
    pm.mel.FBXExportSkins(v=export_rig)
    
    pm.mel.FBXExportShapes(v=True)
    
    pm.mel.FBXExportConstraints(v=False)
    pm.mel.FBXExportInputConnections(v=False)
    #pm.mel.FBXExportUseSceneName(v=True)   //This uses the maya filename for the clip being exported
    pm.mel.FBXExportCameras(v=False)
    pm.mel.FBXExportLights(v=False)
    
    pm.mel.FBXExportInAscii(v=remove_namespaces)
    #pm.mel.FBXExportFileVersion(v='FBX201300')
    
    pm.mel.FBXExportAnimationOnly(v=not export_rig)
    


def export(filename, export_type=EXPORT_ANIM_RIG, bake_animations=True, remove_namespaces=False, include_children=True):
    ##https://help.autodesk.com/view/MAYAUL/2022/ENU/index.html?guid=GUID-699CDF74-3D64-44B0-967E-7427DF800290
    start = int(pm.animation.playbackOptions(query=True, animationStartTime=True))
    end = int(pm.animation.playbackOptions(query=True, animationEndTime=True))
    _bake_anims = bool(export_type & EXPORT_ANIM)
    export_rig = bool(export_type & EXPORT_RIG)
    
    print('export animations:{0} export rig:{1}'.format(_bake_anims, export_rig))
    print('start:{0} end:{1}'.format(start, end))
    
    pm.mel.FBXResetExport()
    pm.mel.FBXExportSkeletonDefinitions(v=True)
    pm.mel.FBXExportBakeComplexStart(v=start)
    pm.mel.FBXExportBakeComplexEnd(v=end)
    pm.mel.FBXExportBakeComplexAnimation(v= _bake_anims and bake_animations)    
    pm.mel.FBXExportBakeResampleAnimation (v= True )
    pm.mel.FBXExportSkins(v=export_rig )

    pm.mel.FBXExportUpAxis(pm.cmds.upAxis(q=True, axis=True))
    pm.mel.FBXExportShapes(v=True)
    
    pm.mel.FBXExportConstraints(v=False)
    
    pm.mel.FBXExportIncludeChildren(v=include_children)
    pm.mel.FBXExportInputConnections(v=False)
    #pm.mel.FBXExportUseSceneName(v=True)   //This uses the maya filename for the clip being exported
    pm.mel.FBXExportCameras(v=False)
    pm.mel.FBXExportLights(v=False)
    
    pm.mel.FBXExportInAscii(v=remove_namespaces)
    #pm.mel.FBXExportFileVersion(v='FBX201300')
    
    pm.mel.FBXExportAnimationOnly(v=not export_rig)
    

    pm.mel.FBXExport(s=True, f=filename)
    if os.path.exists(filename) and remove_namespaces:
        cg3dguru.utils.remove_namespaces(filename)  
    

def export_anim(filename, *args, **kwargs):
    export(filename, export_type = EXPORT_ANIM_RIG, *args, **kwargs)
    
def export_rig(filename, *args, **kwargs):
    export(filename, export_type=EXPORT_RIG, *args, **kwargs)
    

def import_fbx(filepath):
    ##https://help.autodesk.com/view/MAYAUL/2022/ENU/index.html?guid=GUID-699CDF74-3D64-44B0-967E-7427DF800290
    pm.mel.FBXImportMode(v='merge')
    pm.mel.FBXImportFillTimeline(v=True)
    pm.mel.FBXImportSkins(v=True)
    pm.mel.FBXImport(f=filepath)


    