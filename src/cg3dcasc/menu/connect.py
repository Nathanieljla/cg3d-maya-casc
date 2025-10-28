

DIVIDER = ''


def command(*args, **kwargs):
    import cg3dcasc
    import pymel.core as pm
    if cg3dcasc.server.send_to_casc("cg3dmaya.report_port_number()"):
        pm.displayInfo("Connection complete.")