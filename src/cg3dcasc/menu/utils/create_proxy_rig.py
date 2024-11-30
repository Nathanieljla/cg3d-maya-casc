
PARAMS = {
    'label': 'Create Proxy From Selection'
}


DIVIDER = 'Proxy'

def command(*args, **kwargs):
    import cg3dcasc 
    cg3dcasc.utils.derig_selection()