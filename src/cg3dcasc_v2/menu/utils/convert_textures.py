
#PARAMS = {
    #'label': 'Convert Textures'
#}


DIVIDER = ''

def command(*args, **kwargs):
    import cg3dcasc_v2
    cg3dcasc_v2.utils.convert_textures()
