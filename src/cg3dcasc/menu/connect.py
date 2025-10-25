

DIVIDER = ''


def command(*args, **kwargs):
    import cg3dcasc
    cg3dcasc.server.send_to_casc("cg3dmaya.report_port_number()")