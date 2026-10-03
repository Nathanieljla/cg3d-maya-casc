def command_name():
    return "Maya.Export Sets.Remove Selected"

def name():
    return command_name()

def run(scene):
    import cg3dmaya
    cg3dmaya.remove_selection_from()