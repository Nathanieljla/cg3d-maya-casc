import maya.cmds as cmds
import maya.utils


COMMAND_PORT = ':6000'

def open_maya_port():
    try:   
        if not cmds.commandPort(COMMAND_PORT, q = True):
            cmds.commandPort(n = COMMAND_PORT, sourceType='python')
            print( "Opened Command Port:{0}".format(COMMAND_PORT) )
    except:
        print('couldnt open command port')


def casc_setup():
    try:
        open_maya_port()
        
        import cg3dcasc
        print("Cascadeur: building Menu!")
        from cg3dguru.utils import menu_maker
        menu_maker.run(menu_namespace='cg3dcasc.menu')
    except Exception as e:
        import traceback
        from pathlib import Path        
        import maya.cmds as cmds
        module_path = cmds.moduleInfo(path=True, moduleName='cascadeur')
        print("\n\n")
        print("--------------------------------------------------------")
        print(e)
        log = Path(module_path).parent.joinpath('cascadeur', 'scripts', 'error.log')
        print(log)
        callstack = traceback.format_exc()
        print(callstack)
        print("--------------------------------------------------------")
        print("\n\n")
        
        with open(log, 'w') as f:
            f.write(callstack)



maya.utils.executeDeferred(casc_setup)
