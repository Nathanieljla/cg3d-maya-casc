def command_name():
    return "Maya.Export Sets.Add Selected"


def name():
    return command_name()


def run(scene):
    import cg3dmaya
    cg3dmaya.add_selection_to(False)