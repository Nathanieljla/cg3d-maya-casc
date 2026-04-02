


def command_name():
    return "Guru.Connect to Wing"


def run(scene):
    try:
        import sys
        import os
        _3rdparty_path = os.path.join(os.path.dirname(__file__), '..', '..')
        _3rdparty_path = os.path.normpath(_3rdparty_path)
        if _3rdparty_path not in sys.path:
            sys.path.insert(0, _3rdparty_path)
        import wing.wingdbstub
        wing.wingdbstub.Ensure()
    except:
        scene.error('Connection to Wing-IDE failed.') 