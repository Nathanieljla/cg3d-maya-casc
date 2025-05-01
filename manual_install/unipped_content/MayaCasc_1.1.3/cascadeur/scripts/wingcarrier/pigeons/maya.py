from .pigeon import *
import socket


#import below are used maya side to receive commands
import sys
import __main__
import importlib
_MAYA_ACTIVE = False
try:
    import maya.OpenMaya as om
    _MAYA_ACTIVE = False
except:
    pass



class MayaPigeon(Pigeon):
    commandPort = 6000

    
    def __init__(self, *args, **kwargs):
        super(MayaPigeon, self).__init__(*args, **kwargs)

        
    @classmethod
    def get_temp_filename(cls):
        return('wing_maya_temp.txt')


    def get_socket(self):
        
        # The commandPort you opened in userSetup.py Make sure this matches!
        m_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        # Now ping Maya over the command-port
        try:
            # Make our socket-> Maya connection: There are different connection ways
            # which vary between machines, so sometimes you need to try different
            # solutions to get it to work... :-S
            #mSocket.connect(("127.0.0.1", commandPort))
            #mSocket.connect(("::1",commandPort)) #works!
            m_socket.connect(("127.0.0.1", MayaPigeon.commandPort))

        except Exception as e:
            print('Connection to Maya failed: {}'.format(e))
            m_socket.close()
            m_socket = None

        finally:
            return m_socket


    def can_dispatch(self):
        """Check if conditions are right to send code to application
        
        can_dispatch() is used to determine what dispatcher wing will use
        with when there's no active dispatcher found.
        """
        
        m_socket = self.get_socket()
        if m_socket is not None:
            m_socket.close()
            return True
        else:
            return False
        

    def owns_process(self, process):
        """Returns true if the process is the pigeons target application
        
        This is used when an external application is connects to wing. When True
        is returned the Dispatcher becomes the active dispatcher to send commands
        to.
        
        Args:
            process (psutils.Process) : The node to remove the data from.  
        """
        return 'maya' in process.name()
      

    @classmethod
    def read_file(cls, file_path, doc_type=''):
        """
        Evaluate the temp file on disk, made by Wing, in Maya.
    
        Args:
            file_path (str) : The absolute path to the file to load
            doc_type (str) : Supports either 'python' or 'mel'
        """
        
        print_lines = False
        if not doc_type:
            doc_type = 'python'
            
        if doc_type == 'python':
            super(MayaPigeon, cls).read_file(file_path)
            #Pigeon.read_file(file_path)
        else:
            print("MayaPigeon : Running MEL code from file {}\n".format(file_path))
            if os.access(file_path, os.F_OK):
                if print_lines:
                    #temp data is likely highlighted code from Wing
                    #so let's print it for review.
                    with open(file_path, "rb") as f:
                        for line in f.readlines():
                            print(line.rstrip())
                    print("\n"),

                melCmd = 'source "%s"' % file_path
                # This causes the "// Result: " line to show up in the Script Editor:
                om.MGlobal.executeCommand(melCmd, True, True)
            else:
                print("No Wing-generated temp file exists: " + file_path)
            

    @classmethod
    def receive(cls, module_path, doc_type, file_path):
        print("{} {} {}".format(module_path, doc_type, file_path))
        if not module_path:
            cls.read_file(file_path, doc_type=doc_type)

        elif 'python' in doc_type:
            cls.import_module(module_path, file_path)


    def send(self, highlighted_text, module_path, file_path, doc_type):
        """The main entry point for sending content from wing to an external app"""
        m_socket = self.get_socket()
        if m_socket is None:
            print("Can't communicate with Maya!")
            return
        
        if 'python' not in doc_type and file_path.endswith('mel'):
            doc_type = 'mel'
            module_path = ''        
        
        if highlighted_text:
            module_path = ''
            if doc_type == 'mel' and not highlighted_text.endswith(';'):
                highlighted_text += ';'
            
            file_path = self.write_temp_file(highlighted_text)

        try:
            command = u"import wingcarrier.pigeons; wingcarrier.pigeons.MayaPigeon.receive(\'{}\',\'{}\',\'{}\')".format(module_path, doc_type, file_path)
            print(command)
            m_socket.send(command.encode())
        except Exception as e:
            print("Maya socket errored:{}".format(e))
            
        finally:
            m_socket.close()
            
            
    def send_python_command(self, command_string):
        m_socket = self.get_socket()
        if m_socket is None:
            print("Can't connect to Maya!")
            return False
        
        success = False
        try:
            #command = u'python("{}")'.format(command_string)
            m_socket.send(command_string.encode())
            success = True
        except Exception as e:
            print("Maya socket errored:{}".format(e))
        finally:
            m_socket.close()
              
        return success

