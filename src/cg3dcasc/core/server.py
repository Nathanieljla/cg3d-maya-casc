
import socket
import json
import struct
import pymel.core as pm
from . import command_port

from cg3dcasc import preferences

HOST = '127.0.0.1'
PORT = 0 #this makes the port dynamic
TIMEOUT_SECONDS = 0.2

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


def send_to_casc(cmd):
    import wingcarrier.pigeons

    success = False
    if command_port.open():
        cmd = f"import cg3dmaya; cg3dmaya.set_active_port({command_port.port_number}); {cmd}"
        casc = wingcarrier.pigeons.CascadeurPigeon()

        if not casc.send_python_command(cmd):
            #pm.confirmDialog(message="Please make sure Cascadeur is running and try again.", button=['Okay'])
            pm.displayError("Please make sure Cascadeur is running and try again.")
        else:
            success = True

    return success

        
def send_and_listen(cmd):
    """Sends a command to Casc and listens for any return data"""

    data = None
    success = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        s.settimeout(TIMEOUT_SECONDS)

        server_port = s.getsockname()[1]
        cmd = f"cg3dmaya.client.set_port({server_port}); {cmd};"
        send_to_casc(cmd)

        try:
            conn, addr = s.accept()
            with conn:
                success, data = handle_client(conn, addr)
        except socket.timeout:
            pm.warning(f"No connection received within {TIMEOUT_SECONDS} seconds. Shutting down.")
        except Exception as e:
            pm.error(f"An unexpected error occurred: {e}")

    return (success, data)