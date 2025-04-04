def command_name():
    return "Maya.Export Animation"


def run(scene):
    import cg3dmaya
    cg3dmaya.export_maya_animation()
    
    
#import cg3dcmds
#import cg3dmaya
#cg3dmaya.export_maya_animation()