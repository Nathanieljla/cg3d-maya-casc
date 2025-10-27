def command_name():
    return "Maya.Export Sets.Select Set Members"


def run(scene):
    import cg3dmaya
    cg3dmaya.select_set_members()