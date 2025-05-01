
import pymel.core as pm
#iter = 10

def create_stretchy_spline():
    #make sure we have an ik handle in our selection
    selection = pm.general.ls(sl = True, type = 'ikHandle' )
    
    dm = pm.createNode('decomposeMatrix')
    npc = pm.createNode('nearestPointOnCurve')
    dm.outputTranslate >> npc.inPosition
    
    for handle in selection:
        inputCurve = pm.listConnections(handle.inCurve)
        if not inputCurve:
            continue
        
        inputCurve = inputCurve[0]
            
        #find the start and end joint
        startJoint = handle.getStartJoint()
        endEffector = handle.getEndEffector()

        endJoint = pm.listConnections(endEffector.tx)
        if endJoint:
            endJoint = endJoint[0]
        else:
            continue

        #build the network               
        inputCurve.worldSpace[0] >> npc.inputCurve
        currentJoint = endJoint          
        lastDistanceNode = None
        #count = 0
        
        while currentJoint != startJoint:
            currentJoint = currentJoint.getParent()
            #count += 0
            #if count > iter:
                #break
                
            #print(currentJoint)

            currentJoint.worldMatrix[0] >> dm.inputMatrix
            poc = pm.createNode('pointOnCurveInfo')
            inputCurve.worldSpace[0] >> poc.inputCurve
            
            #store the default parameter value for the joint
            #a quick connect then disconnect gets us what we need.
            npc.parameter >> poc.parameter
            npc.parameter // poc.parameter
            
            db = pm.createNode('distanceBetween')
            poc.position >> db.point1
            if lastDistanceNode:
                poc.position >> lastDistanceNode.point2
                divide = pm.createNode('multiplyDivide')

                lastDistanceNode.distance >> divide.input1X
                divide.input2X.set( lastDistanceNode.distance.get() )
                divide.operation.set(2)
                
                divide.outputX >> currentJoint.scaleX
                
            lastDistanceNode = db
             
    pm.delete(dm)
    pm.delete(npc)
    
    pm.select(selection, replace = True)
        
    
    

def run():
    create_stretchy_spline()