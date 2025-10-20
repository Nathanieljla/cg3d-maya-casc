import maya.cmds as cmds
import maya.utils


command_port = 6000 #':6000'


def _get_unique_port_number():
    global command_port
    target_number = command_port
    max_count = 100
    idx = 0

    while cmds.commandPort(f":{target_number}", q=True) or idx >= max_count:
        idx += 1
        target_number += idx

    return -1 if idx >= max_count else target_number


def open_maya_port():
    global command_port
    
    try:
        target_number = _get_unique_port_number()
        if target_number == -1:
            raise ValueError

        port_string = f":{target_number}"
        if not cmds.commandPort(port_string, q=True):
            cmds.commandPort(n=port_string, sourceType='python') #, noreturn=True) no returns is just for debugging
            command_port = target_number
            
            print("Cascadeur Bridge opened Command Port:{0}".format(command_port))
    except:
        print('couldnt open command port')


def casc_setup():
    try:
        open_maya_port()
        
        import cg3dcasc
        import cg3dcasc.core
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
