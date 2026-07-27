
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

        ]
        
        return attrs
    
    @classmethod
    def post_create(cls, data):
        data.alignPelvis.set(1)
        data.createLayers.set(1)
        
    
    
class CascExportData(cg3dguru.udata.BaseData):
    """A list for nodes that should always be sent to Cascadeur
    
    The CascExportData.exportNodes attribute can store meshes, joints, and
    skinClusters. Meshes, joints and skinClusters will be inspected to find
    all dependent joints and meshes. E.g. add a skinCluster and all joints
    will be exported (as well as the meshes they deform).
    """

    LEGACY_0_1_0 = 0
    LATEST       = 1
    """export_version enum values.

    Every format gets an explicit index in the enum string, so adding a new
    format later can't change the meaning of a value that's already been
    written into a scene file. The legacy format is index 0 -- the value an
    enum falls back to -- so data that somehow misses being stamped keeps
    using the old export logic instead of silently opting into the new one.
    """

    @classmethod
    def get_class_version(cls):
        return (0, 2, 0)

    @classmethod
    def get_attributes(cls):
        attrs = [
            cg3dguru.udata.create_attr('cscDataId', 'string'),
            cg3dguru.udata.create_attr('dynamicSet', 'bool'),
            cg3dguru.udata.create_attr('textureLocation', 'string'),
            cg3dguru.udata.create_attr('export_version', 'enum',
                                       enumName = '0_1_0={0}:Latest={1}'.format(
                                           cls.LEGACY_0_1_0, cls.LATEST),
                                       defaultValue = cls.LEGACY_0_1_0,
                                       keyable = False),
        ]

        return attrs

    @classmethod
    def post_create(cls, data):
        unique_id = uuid.uuid1()
        data.cscDataId.set(str(unique_id))
        data.cscDataId.lock()
        data.dynamicSet.set(1)
        data.export_version.set(cls.LATEST)


    @classmethod
    def pre_update_version(cls, old_data, old_version_number):
        #Updating is additive and non-destructive: nothing gets dropped, and
        #anything older than 0.2.0 gets flagged so it keeps exporting exactly
        #the way it did before. So always update.
        return True


    @classmethod
    def post_update_version(cls, data, update_successful, old_version_number = None):
        #export_version is new in 0.2.0, so it isn't part of the copyAttr
        #transfer and is sitting at its default value. Data made before
        #0.2.0 has to keep using the old export logic.
        if update_successful and old_version_number and old_version_number < (0, 2, 0):
            data.export_version.set(cls.LEGACY_0_1_0)
