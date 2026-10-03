
PARAMS = {
    'label': 'Sync Cascadeur ID'
}


def command(*args, **kwargs):
    import cg3dcasc_v2
    cg3dcasc_v2.utils.sync_casc_id()
