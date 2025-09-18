import os
import enum
import cg3dguru.ui as ui
import pymel.core as pm
import cg3dguru.utils.modeling as mu


class Finger(enum.Enum):
    THUMB = 0,
    INDEX = 1,
    MIDDLE = 2,
    RING = 3,
    PINKY = 4,
    
    
class Joint(enum.Enum):
    METACARPAL = 0,
    PROXIMAL = 1,
    MEDIAL = 2,
    DISTAL = 3
    
    
JOINT_PERCENTS = {
    Finger.THUMB : {
        Joint.METACARPAL : -0.44,
        Joint.PROXIMAL : 0,
        Joint.DISTAL : 0.54
    }, 
    Finger.INDEX : {
        Joint.METACARPAL : -0.45,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.49,
        Joint.DISTAL : 0.76
    },
    Finger.MIDDLE : {
        Joint.METACARPAL : -0.41,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.48,
        Joint.DISTAL : 0.77
    },
    Finger.RING : {
        Joint.METACARPAL : -0.40,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.47,
        Joint.DISTAL : 0.76
    },
    Finger.PINKY : {
        Joint.METACARPAL : -0.43,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.46,
        Joint.DISTAL : 0.72
    }  
}



WINDOW_NAME = 'Plot Finger Percents'

class Fingers_Window(ui.Window):
    
    def __init__(self, windowKey, uiFilepath, *args, **kwargs):
        super(Fingers_Window, self).__init__(windowKey, uiFilepath)
        
        self.ui.thumb.pressed.connect( lambda: self.plot_joint(Finger.THUMB) )
        self.ui.index.pressed.connect( lambda: self.plot_joint(Finger.INDEX) )
        self.ui.middle.pressed.connect( lambda: self.plot_joint(Finger.MIDDLE) )
        self.ui.ring.pressed.connect( lambda: self.plot_joint(Finger.RING) )
        self.ui.pinky.pressed.connect( lambda: self.plot_joint(Finger.PINKY) )
        
        #I don't have support in for metacarpals
        self.ui.createMeta.setVisible(False)
        
                
        
    def plot_joint(self, finger : Finger):
        sel = pm.ls(sl = True)

        if len(sel) != 1:
            pm.system.displayError( 'One nurbsCurve transform must be selected.' )
            return

        shapes = pm.listRelatives(sel[0], shapes=True)
        if not shapes or not isinstance(shapes[0], pm.nodetypes.NurbsCurve):
            return
         
        curve = shapes[0]
        percents = JOINT_PERCENTS[finger]   
        for id in Joint:
            if id is Joint.METACARPAL and not self.ui.createMeta.isChecked():
                continue
            
            if id in percents:
                #create locator
                locator = pm.createNode('locator')
                marker = pm.listRelatives(locator, parent=True)[0] #get the shape's Transform
                
                name =  (finger.name + '_' + id.name).lower()
                pm.rename(marker, name)
                
                if id is Joint.METACARPAL:
                    mu.plot_percent_on_curve(curve, percents[id], marker)
                else:
                    mu.plot_percent_on_curve(curve, percents[id], marker)
                    
                    
        
        
def run():
    filepath = os.path.join( os.path.dirname(__file__), r'fingers.ui' )
    joint_utils_window = Fingers_Window(WINDOW_NAME, filepath)
    joint_utils_window.ui.show()