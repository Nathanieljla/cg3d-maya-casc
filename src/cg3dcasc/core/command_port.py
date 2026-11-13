import maya.cmds as cmds

port_number = None

def open():
    """Attempt to open a port if one's not already opened"""
    global port_number
    
    if port_number is not None:
        if cmds.commandPort(f':{port_number}', q=True):
            return True
        else:
            port_number = None

    #We must not have an open port, so let's open one.
    start_port = 6000
    end_port = start_port + 50

    for i in range(start_port, end_port + 1):
        try:
            # Try to open a port with the specific number.
            cmds.commandPort(n=f':{i}', sourceType='python') #, noreturn=True) no returns is just for debugging
            port_number = i
            break
        except RuntimeError:
            # If opening the port fails, it's likely already in use.
            continue

    if port_number is not None:
        print("Cascadeur Bridge opened Command Port:{0}".format(port_number))
        return True
    else:
        print("Couldn't open command port")
        return False
    
