


def command_name():
    return "Guru.Connect to Wing"


def run(scene):
    try:
        import wingcarrier.wingdbstub
        wingcarrier.wingdbstub.Ensure()
    except:
        scene.error('Connection to wing failed.') 