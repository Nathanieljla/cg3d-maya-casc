
import re


def remove_namespaces(filename, remove_subdeformer_namespaces=False):
    """FBX must be saved in ACSII format otherwise the parser will error."""
    
    fbx = open(filename)
    file_string = fbx.read()
    fbx.close()
    
    #don't use \s in this otherwise it will wrap past the return character and cause issues
    expression_str = "(?P<start>::)(?P<namespace>([ \d\w]*:)*)(?P<name>[ \d\w]*)"
    result = re.sub(expression_str, "\g<start>\g<name>", file_string)

    if remove_subdeformer_namespaces:
        expression_str = "(?P<start>SubDeformer::)(?P<namespace>([ \d\w]*\.)*)(?P<name>[ \d\w]*)"
        result = re.sub(expression_str, "\g<start>\g<name>", result)
        
    new_file = open(filename, 'w')
    new_file.write(result)
    new_file.close()
    
    
    
def fbx_ascii_to_binary(filename):
    #"c:\program files\autodesk\maya2023\bin\mayapy.exe" "d:/fixIt.py"

    # Gain access to maya.cmds
    import pymel
    import os

    try:
        import maya.standalone 			
        maya.standalone.initialize() 		
    except: 			
        return False

    success = False
    try:
        from maya import cmds
        cmds.file(filename, i=True)

        ##https://help.autodesk.com/view/MAYAUL/2022/ENU/index.html?guid=GUID-699CDF74-3D64-44B0-967E-7427DF800290
        start = int(pymel.core.animation.playbackOptions(query=True, animationStartTime=True))
        end = int(pymel.core.animation.playbackOptions(query=True, animationEndTime=True))
        
        pymel.core.mel.FBXResetExport()
        pymel.core.mel.FBXExportBakeComplexStart(v=start)
        pymel.core.mel.FBXExportBakeComplexEnd(v=end)
        pymel.core.mel.FBXExportSkeletonDefinitions(v=True)
        pymel.core.mel.FBXExportBakeComplexAnimation(v=False)
        pymel.core.mel.FBXExportBakeResampleAnimation(v=True)
        pymel.core.mel.FBXExportSkins(v=True)
        pymel.core.mel.FBXExportShapes(v=True)
        pymel.core.mel.FBXExportConstraints(v=False)
        pymel.core.mel.FBXExportInputConnections(v=False)
        pymel.core.mel.FBXExportCameras(v=False)
        pymel.core.mel.FBXExportLights(v=False)
        pymel.core.mel.FBXExportInAscii(False)
        pymel.core.mel.FBXExportAnimationOnly(v=False)
        pymel.core.mel.FBXExport(s=True, f=filename)

        success = True
    except:
        success = False
    finally:
        try:
            maya.standalone.uninitialize() 		
        except: 			
            pass

    return success

    


