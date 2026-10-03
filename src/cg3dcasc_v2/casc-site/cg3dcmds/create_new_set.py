def command_name():
    return "Maya.Export Sets.Create New Set"


def name():
    return command_name()

def run(scene):
    import cg3dmaya
    cg3dmaya.add_selection_to(True)