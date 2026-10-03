print("this worked")

print("highlighted text")
import sys
import pathlib

def run():
    mypath = pathlib.Path(__file__)
    site_package = mypath.parent.parent.parent
    sys.path.append(str(site_package))
    import wingcarrier.pigeons.cascadeur as casc
    pigeon = casc.CascadeurPigeon()
    path = pigeon.get_running_path()

    
run()