
import uuid

import cg3dguru.udata


class CascadeurTextures(cg3dguru.udata.BaseData):
    @staticmethod
    def get_attributes():
        attrs = [
            cg3dguru.udata.create_attr('textures', 'Int32Array'),
        ]
        
        return attrs


class ProxyData(cg3dguru.udata.BaseData):
    @staticmethod
    def get_attributes():
        attrs = [
            cg3dguru.udata.create_attr('proxySource', 'message'),
        ]
        
        return attrs
    
    
class ProxyRoot(cg3dguru.udata.BaseData):
    root = 'Root'
    joints = 'Joints'
    meshes = 'Meshes'
    skinned_meshes = 'Skin'
    
    @staticmethod
    def get_attributes():
        enum_names = f"{ProxyRoot.root}:{ProxyRoot.joints}:{ProxyRoot.meshes}:{ProxyRoot.skinned_meshes}"
        attrs = [
            cg3dguru.udata.create_attr('rootType', 'enum', enumName= enum_names),
        ]
        
        return attrs  


class QRigData(cg3dguru.udata.BaseData):
    """A block of data to help convert an HIK character to Cascaduer's quick rig"""

    @staticmethod
    def get_attributes():
        attrs = [
            cg3dguru.udata.create_attr('characterNode', 'message'),
            cg3dguru.udata.create_attr('chestJoint', 'message'),
            cg3dguru.udata.create_attr('leftWeapon', 'message'),
            cg3dguru.udata.create_attr('rightWeapon', 'message'),
            cg3dguru.udata.create_attr('alignPelvis', 'bool'),
            cg3dguru.udata.create_attr('createLayers', 'bool'),
            
            cg3dguru.udata.Attr('leftArmTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('leftForearmTwist', 'enum', enumName='X:Y:Z'),
            
            cg3dguru.udata.Attr('leftUpperLegTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('leftLegTwist', 'enum', enumName='X:Y:Z'),
            
            cg3dguru.udata.Attr('rightArmTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('rightForearmTwist', 'enum', enumName='X:Y:Z'),
            
            cg3dguru.udata.Attr('rightUpperLegTwist', 'enum', enumName='X:Y:Z'),
            cg3dguru.udata.Attr('rightLegTwist', 'enum', enumName='X:Y:Z'), 
            
            #cg3dguru.udata.Compound('twistAxes', 'compound', children =[
                #cg3dguru.udata.Attr('leftArm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('leftForearm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('leftUpLeg', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('leftLeg', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightArm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightForearm', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightUpLeg', 'enum', enumName='X:Y:Z'),
                #cg3dguru.udata.Attr('rightLeg', 'enum', enumName='X:Y:Z'), 
            #])
            
        ]
        
        return attrs
    
    @classmethod
    def post_create(cls, data):
        data.createLayers.set(1)
        
    
    
class CascExportData(cg3dguru.udata.BaseData):
    """A list for nodes that should always be sent to Cascadeur
    
    The CascExportData.exportNodes attribute can store meshes, joints, and
    skinClusters. Meshes, joints and skinClusters will be inspected to find
    all dependent joints and meshes. E.g. add a skinCluster and all joints
    will be exported (as well as the meshes they deform).
    """
    
    @classmethod
    def get_class_version(cls):
        return (0, 1, 0)    
    
    @staticmethod
    def get_attributes():
        attrs = [
            cg3dguru.udata.create_attr('cscDataId', 'string'),
            cg3dguru.udata.create_attr('dynamicSet', 'bool'),
             cg3dguru.udata.create_attr('textureLocation', 'string')
        ]
        
        return attrs
    
    @classmethod
    def post_create(cls, data):
        unique_id = uuid.uuid1()
        data.cscDataId.set(str(unique_id))
        data.cscDataId.lock()
        data.dynamicSet.set(1)
        
        
    @classmethod
    def pre_update_version(cls, old_data, old_version_number):
        pass
