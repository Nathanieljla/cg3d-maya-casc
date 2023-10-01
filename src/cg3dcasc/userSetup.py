import maya.utils

def casc_setup():
    import cg3dcasc
    print("Cascadeur: building Menu!")
    from cg3dguru.utils import menu_maker
    menu_maker.run(menu_namespace='cg3dcasc.menu')


maya.utils.executeDeferred(casc_setup)
