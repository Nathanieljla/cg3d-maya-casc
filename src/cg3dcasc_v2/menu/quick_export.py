
DIVIDER = 'Export'

PARAMS = {
    'label': 'Quick Export'
}


def command(*args, **kwargs):
    import cg3dcasc_v2
    cg3dcasc_v2.smart_export()
