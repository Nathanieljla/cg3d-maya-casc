def command_name():
    return "Maya.Export Sets.Sync Maya ID"

def name():
    return command_name()

def run(scene):
    import cg3dmaya
    cg3dmaya.sync_selected_set_ids()