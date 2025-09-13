import math
import enum
import maya.cmds
import pymel.core as pm


class Axis(enum.Flag):
    X = enum.auto()
    Y = enum.auto()
    Z = enum.auto()
    ALL = X | Y | Z
    REVERSE = enum.auto()
    NEG_X = X | REVERSE
    NEG_Y = Y | REVERSE
    NEG_Z = Z | REVERSE
 
 
class Space(enum.Enum):
    OBJECT = 0
    WORLD = 1
    PARENT = 2
    CAMERA = 3
    TANGENT = 4
    UV = 5
    
    
class Direction(enum.Flag):
    FORWARD = enum.auto()
    UP = enum.auto()
    RIGHT = enum.auto()
    REVERSE = enum.auto()
    BACKWARDS = FORWARD | REVERSE
    DOWN = UP | REVERSE
    LEFT = RIGHT | REVERSE
    
    
class Flip(enum.Enum):
    FORWARD = 0
    UP = 1
    RIGHT = 2
    
    
class MatrixUtils(object):
    """
    Allows users to get and set transforms in the generic terms of forward, up, and right (fur).
    Users define the mapping of a axis to a direction.
    """
    def __init__(self, transform_node = None, *args, **kwargs):  
        super().__init__(*args, **kwargs)
            
        self._transform_node = None
        self.transform_node = transform_node
        
        self._right_axis = Axis.X
        self._up_axis = Axis.Y
        self._forward_axis = Axis.Z
        
        self._flip = Flip.RIGHT
        
        #what space the matrix operations take place in
        self._space = Space.WORLD
        

##--properties----------------------------------------------------


    @property
    def transform_node(self) -> pm.nodetypes.Transform:
        return self._transform_node
    
    @transform_node.setter
    def transform_node(self, node: pm.nodetypes.Transform):
        if node is not None and not isinstance( node, pm.nodetypes.Transform ):
            pm.system.error('Type Error')
            
        self._transform_node = node        
    
    @property
    def space(self) -> Space:
        return self._space
    
    @space.setter
    def space(self, value: Space):
        if not isinstance(value, Space):
            pm.system.error('Type Error')
        
        self._space = value;
        
    @property
    def Flip(self) -> Flip:
        return self._flip
    
    @Flip.setter
    def Flip(self, value: Flip):
        if not isinstance(value, Flip):
            pm.system.error('Type Error')
            
        self._flip = value
    
    @property
    def forward(self) -> pm.datatypes.Vector:
        return MatrixUtils.get_axis_vector( self.get_matrix(), self._forward_axis)
     
    @property
    def up(self) -> pm.datatypes.Vector:
        return MatrixUtils.get_axis_vector( self.get_matrix(), self._up_axis)
    
    @property
    def right(self) -> pm.datatypes.Vector:
        return MatrixUtils.get_axis_vector( self.get_matrix(), self._right_axis)    
    
 
##--static methods----------------------------------------------------------------------------
     
    @staticmethod
    def get_world_pos( obj_name ):
        x_list = pm.xform( obj_name, query = True, matrix = True, worldSpace = True )
        return pm.datatypes.Vector( *x_list[12:15] )    

    @staticmethod
    def get_matrix_position(matrix: pm.datatypes.Matrix):
        return pm.datatypes.Vector(matrix.a30, matrix.a31, matrix.a32)
    
    
    @staticmethod
    def set_matrix_translation(matrix: pm.datatypes.Matrix,
                        position: pm.datatypes.Vector):
        matrix.a30 = position.x
        matrix.a31 = position.y
        matrix.a32 = position.z
    
    
    @staticmethod
    def get_axis_vector(matrix: pm.datatypes.Matrix,
                        axis: Axis):
        
        vector = None
        if Axis.X in axis:
            vector = pm.datatypes.Vector(matrix.a00, matrix.a01, matrix.a02)
        elif Axis.Y in axis:
            vector = pm.datatypes.Vector(matrix.a10, matrix.a11, matrix.a12)
        elif Axis.Z in axis:
            vector = pm.datatypes.Vector(matrix.a20, matrix.a21, matrix.a22)
            
        if Axis.REVERSE in axis:
            vector = -vector
            
        return vector
        
        
    @staticmethod
    def set_axis_vector(matrix: pm.datatypes.Matrix,
                        vector: pm.datatypes.Vector,
                        axis: Axis):
        if axis == Axis.X:
            matrix.a00 = vector.x
            matrix.a01 = vector.y
            matrix.a02 = vector.z
        if axis == Axis.Y:
            matrix.a10 = vector.x
            matrix.a11 = vector.y
            matrix.a12 = vector.z
        if axis == Axis.Z:
            matrix.a20 = vector.x
            matrix.a21 = vector.y
            matrix.a22 = vector.z
            
            
    @staticmethod
    def ensure_right_handedness( forward, up, right, handedness_rule: Flip):
        if not (right.cross( up ) * forward > 0 and up.cross( forward ) * right > 0):
            if handedness_rule == Flip.RIGHT:
                right.x = -right.x
                right.y = -right.y
                right.z = -right.z
            elif handedness_rule == Flip.UP:
                up.x = -up.x
                up.y = -up.y
                up.z = -up.z
            elif handedness_rule == Flip.FORWARD:
                forward.x = -forward.x
                forward.y = -forward.y
                forward.z = -forward.z    
            
            
    @staticmethod
    def set_matrix_vectors(matrix: pm.datatypes.Matrix, 
                           x: pm.datatypes.Vector,
                           y: pm.datatypes.Vector,
                           z: pm.datatypes.Vector,
                           position: pm.datatypes.Vector, 
                           flip: Flip,
                           ignore_scale: bool):
        """
        Set's the transform_node's f, u, r to the input while ensuring proper right handedness.
        """
        
        MatrixUtils.ensure_right_handedness(z, y, x, flip)
        
        if ignore_scale:
            z.normalize()
            y.normalize()
            x.normalize()
        
        MatrixUtils.set_axis_vector(matrix, x, Axis.X)
        MatrixUtils.set_axis_vector(matrix, y, Axis.Y)
        MatrixUtils.set_axis_vector(matrix, z, Axis.Z)
        MatrixUtils.set_matrix_translation(matrix, position)
        
        
    @staticmethod    
    def get_three_point_matrix( p1, p2, p3, u_dir = None ):
        f_vec = p3 - p1
        f_vec.normalize()
        
        r_vec = p2 - p1
        r_vec.normalize()

        if math.fabs( f_vec * r_vec ) > .999:
            maya.OpenMaya.MGlobal.displayError( "Your three points are too in line with one another!" )
            return None

        r_vec, u_vec = MatrixUtils.get_orthogonal_vectors( f_vec, r_vec, v3_dir = u_dir )
        #self.ensure_right_handedness( r_vec, u_vec, f_vec )

        matrix = pm.datatypes.Matrix()
        MatrixUtils.set_matrix_vectors(matrix, f_vec, u_vec, r_vec, p1, Flip.RIGHT, True)

        #pos = cgkit.cgtypes.vec4( p1 )
        #pos.w = 1

        #three_point_matrix = cgkit.cgtypes.mat4( )
        #three_point_matrix.setColumn( 3, pos )

        #orient = cgkit.cgtypes.mat3( r_vec, u_vec, f_vec )
        #three_point_matrix.setMat3( orient )

        return matrix
        
       
    @staticmethod
    def get_world_matrix( obj_name ):
        """

        """
        matrix_list = pm.xform( obj_name, query = True, matrix = True, worldSpace = True )
        rotatePivot = pm.xform( obj_name, query = True, ws = True, rotatePivot = True )

        matrix_list[ 12 ] = rotatePivot[ 0 ]
        matrix_list[ 13 ] = rotatePivot[ 1 ]
        matrix_list[ 14 ] = rotatePivot[ 2 ]

        return pm.datatypes.Matrix( matrix_list)    
        
        
    @staticmethod
    def set_world_matrix( obj_name, matrix, no_scale = False ):
        """

        """
        if no_scale:
            matrix.scale = pm.datatypes.Vector.one

        pm.xform( obj_name, matrix = matrix, worldSpace = True )
        
        
    @staticmethod
    def get_third_axis(a1: Axis, a2: Axis):
        a3 = (a1 | a2) & ~Axis.REVERSE
        return Axis.ALL & ~a3
    
    
    @staticmethod
    def get_orthogonal_vectors( v1, v2, v3_dir = None ):
        """
        Given two vectors (v1 and v2) return two vectors (v2 and v3) that are orthogonal to v1.
        v3_dir can be used to ensure that v3 matches a desired direction
        """
        v3 = v1.cross( v2 ) #.normalize( )
        v3.normalize()
        
        #Make sure the up dir is aiming towards the desired up dir
        if v3_dir:
            if v3 * v3_dir < 0:
                v3 = -v3

        #Do a final adjustment of the r_vec to account for orthogonal consideration and a flipped Up vec
        scale = v2.length()
        v2 = v3.cross( v1 )
        v2.normalize( )
        v2 *= scale

        return (v2, v3)
 
##--methods-----------------------------------------------------------------------------------
                
                
    def set_forward_up_coordinates(self, forward: Axis,
                                   up: Axis):
        self._forward_axis = forward
        self._up_axis = up
        self._right_axis = self.get_third_axis(forward, up)
                
                
    def set_coordinates(self, foward: Axis,
                        up: Axis,
                        right: Axis):
        self._forward_axis = foward
        self._up_axis = up
        self._right_axis = right
        
    
    def get_matrix(self):
        return self.transform_node.getMatrix(worldSpace = self._space == Space.WORLD)
    
    
    def get_translation(self):
        if self.space == Space.WORLD:
            return self.transform_node.getTranslation('world')
        else:
            return self.transform_node.getTranslation('object')


    def _set_forward_up_right(self,
                               forward: pm.datatypes.Vector,
                               up: pm.datatypes.Vector,
                               right: pm.datatypes.Vector,
                               flip: Flip,
                               ignore_scale: bool):
        """
        Set's the transform_node's f, u, r to the input while ensuring proper right handedness.
        """
        
        MatrixUtils.ensure_right_handedness(forward, up, right, flip)
        
        if ignore_scale:
            forward.normalize()
            up.normalize()
            right.normalize()
        
        matrix = self.get_matrix()
        MatrixUtils.set_axis_vector(matrix, forward, self._forward_axis)
        MatrixUtils.set_axis_vector(matrix, up, self._up_axis)
        MatrixUtils.set_axis_vector(matrix, right, self._right_axis)
        
        self.transform_node.setMatrix(matrix, worldSpace = self.space == Space.WORLD)        
    
    
    def set_forward_up(self,
                       forward: pm.datatypes.Vector,
                       up: pm.datatypes.Vector,
                       priority: Direction = Direction.FORWARD, 
                       ignore_scale: bool = True):
        
        if (Direction.FORWARD in priority):
            up, right = self.get_orthogonal_vectors(forward, up)
            
        elif (Direction.UP in priority):
            forward, right = self.get_orthogonal_vectors(up, forward)
            
        else:
            pm.system.error('Type Error')
            
        self._set_forward_up_right(forward, up, right, Flip.RIGHT, ignore_scale)
        
        
    def set_forward_right(self,
                       forward: pm.datatypes.Vector,
                       right: pm.datatypes.Vector,
                       priority: Direction = Direction.FORWARD,
                       ignore_scale: bool = True):
        
        if (Direction.FORWARD in priority):
            right, up = self.get_orthogonal_vectors(forward, right)
            
        elif (Direction.RIGHT in priority):
            forward, up = self.get_orthogonal_vectors(right, forward)

        else:
            pm.system.error('Type Error')
            
        self._set_forward_up_right(forward, up, right, Flip.UP, ignore_scale)
        
        
    def set_up_right(self,
                       up: pm.datatypes.Vector,
                       right: pm.datatypes.Vector,
                       priority: Direction = Direction.UP,
                       ignore_scale: bool = True):
        
        if (Direction.UP in priority):
            right, forward = self.get_orthogonal_vectors(up, right)
            
        elif (Direction.RIGHT in priority):
            up, forward = self.get_orthogonal_vectors(right, up)
            
        else:
            pm.system.error('Type Error')
            
        self._set_forward_up_right(forward, up, right, Flip.FORWARD, ignore_scale)    
    
        
    