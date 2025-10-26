def command_name():
    return "Maya.Export Sets.Sync Maya ID"


def run(scene):
    import cg3dmaya
    cg3dmaya.sync_selected_set_ids()