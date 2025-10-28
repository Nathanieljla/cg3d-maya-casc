import socket
import json
import struct


import pycsc

HOST = '127.0.0.1'
PORT = 0 #this makes the port dynamic
TIMEOUT_SECONDS = 0.5
SCRIPT_DELAY_TIME = 0.05


def is_port_open(host, port, timeout=0.5):
    """
    Checks if a given port on a host is open.

    Args:
        host (str): The IP address or hostname of the target.
        port (int): The port number to check.
        timeout (int): The timeout in seconds for the connection attempt.

    Returns:
        bool: True if the port is open, False otherwise.
    """
    try:
        # Create a new socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set a timeout for the connection attempt
        s.settimeout(timeout)
        # Attempt to connect to the host and port
        result = s.connect_ex((host, port))
        # If connect_ex returns 0, the connection was successful, meaning the port is open
        if result == 0:
            return True
        else:
            return False
    except socket.error as e:
        # Handle potential socket errors (e.g., host not found)
        print(f"Socket error: {e}")
        return False
    finally:
        # Close the socket in all cases
        s.close()



def receive_all(sock, n):
    """Helper function to ensure all 'n' bytes are received."""
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


def handle_client(conn, addr):
    """Handles a single client connection."""

    data = None
    success = False
    try:
        # 1. Read the 4-byte header indicating the message length.
        raw_msg_len = receive_all(conn, 4)
        if not raw_msg_len:
            print("Client disconnected unexpectedly.")
            return
        msg_len = struct.unpack('>I', raw_msg_len)[0]

        # 2. Read the full JSON message using the length.
        json_data = receive_all(conn, msg_len)
        if not json_data:
            print("Client disconnected while sending data.")
            return

        # 3. Decode the JSON message.
        #    Note: The decode('utf-8') is crucial for converting bytes to string.
        data = json.loads(json_data.decode('utf-8'))
        print("Received JSON data:")
        print(data)
        success = True

    except (socket.error, json.JSONDecodeError) as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()

    return (success, data)
        

def send_to_maya(maya_command_port, cmd):
    """Send a command to maya using wingcarrier
    
    import cg3dcasc.core is added to all commands
    """
    global HOST
    import wingcarrier.pigeons

    if not is_port_open(HOST, maya_command_port):
        scene = pycsc.get_current_scene().ds
        scene.error("Couldn't find Maya.  Please Connect to Cascadeur from Maya.")
        return False
         
    cmd = f"import cg3dcasc.core; {cmd};"
    maya = wingcarrier.pigeons.MayaPigeon()
    maya.command_port = maya_command_port
    maya.send_python_command(cmd)

    return True
    
    
def send_and_listen(maya_command_port, cmd):
    data = None
    success = False

    if maya_command_port == -1:
        return (success, data)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        s.settimeout(TIMEOUT_SECONDS)

        server_port = s.getsockname()[1]
        print(f"Server listening on {HOST}:{server_port} for {TIMEOUT_SECONDS} seconds...")
        cmd = f"import time; time.sleep({SCRIPT_DELAY_TIME}); cg3dcasc.core.client.set_port({server_port}); {cmd}"
        if not send_to_maya(maya_command_port, cmd):
            return (success, None)

        try:
            conn, addr = s.accept()
            with conn:
                success, data = handle_client(conn, addr)
        except socket.timeout:
            print(f"No connection received within {TIMEOUT_SECONDS} seconds. Shutting down.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


    return (success, data)