

import maya.cmds as cmds
import socket
import json
import struct


HOST = '127.0.0.1'
port = 7258 #dynamically changed by the cg3dmaya.server.send_to_maya



def set_port(number):
    print(f"new port number = {number}{number.__class__}")
    global port
    port = number


def send_to_casc(data):
    """Encodes and sends JSON data to the external server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        try:
            print(f"cascadeur port:{port}")
            client.connect((HOST, port))
            
            json_string = json.dumps(data)
            json_bytes = json_string.encode('utf-8')

            # 3. Prepend a 4-byte length-prefix.
            length_prefix = struct.pack('>I', len(json_bytes))
            
            # 4. Send the length-prefix followed by the JSON data.
            client.sendall(length_prefix + json_bytes)
            
            print(f"Sent {len(json_bytes)} bytes of JSON data to the server. Data is:{data}")
        
        except ConnectionRefusedError:
            cmds.warning(f"Failed to connect to server at {HOST}:{port}. Is the server running?")
        except Exception as e:
            cmds.warning(f"An error occurred: {e}")