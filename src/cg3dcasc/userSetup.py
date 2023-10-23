import maya.utils



def casc_setup():
    try: 
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
