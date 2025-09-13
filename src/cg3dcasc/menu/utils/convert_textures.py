
#PARAMS = {
    #'label': 'Convert Textures'
#}


DIVIDER = ''

def command(*args, **kwargs):
    import cg3dcasc
    cg3dcasc.utils.convert_textures()