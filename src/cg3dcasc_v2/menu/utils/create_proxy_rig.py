
PARAMS = {
    'label': 'Create Proxy From Selection'
}


DIVIDER = 'Proxy'

def command(*args, **kwargs):
    import cg3dcasc_v2
    cg3dcasc_v2.utils.derig_selection()
