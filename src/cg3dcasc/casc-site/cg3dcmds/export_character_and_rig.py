def command_name():
    return "Maya.Export Character and Rig"


def name():
    return command_name()


def run(scene):
    import cg3dmaya

    return cg3dmaya.export_character_and_rig()
