

DIVIDER = ''


def command(*args, **kwargs):
    import cg3dcasc_v2
    from maya.api import OpenMaya as om

    if cg3dcasc_v2.server.send_to_casc("cg3dmaya.report_port_number()"):
        om.MGlobal.displayInfo("Connection complete.")
