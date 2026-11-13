def command_name():
    return "Maya.Export Animation"


def name():
    return command_name()


def run(scene):
    import cg3dmaya
    cg3dmaya.export_maya_animation()