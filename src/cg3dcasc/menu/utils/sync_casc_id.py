
PARAMS = {
    'label': 'Sync Cascadeur ID'
}


def command(*args, **kwargs):
    import cg3dcasc
    cg3dcasc.utils.sync_casc_id()