
def command_name():
    return "Guru.Connect to Wing"


def name():
    return command_name()


def run(scene):
    try:
        import wingcarrier.wingdbstub
        wingcarrier.wingdbstub.Ensure()
    except Exception as e:
        print('Connection to Wing-IDE failed: %s' % e)
        scene.error('Connection to Wing-IDE failed.') 