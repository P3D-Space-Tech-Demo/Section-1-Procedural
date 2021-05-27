# Author: Simulan

from direct.showbase.ShowBase import ShowBase
from panda3d.core import PerspectiveLens
from panda3d.core import loadPrcFileData
from panda3d.core import PointLight
from panda3d.core import Spotlight
from panda3d.core import AmbientLight
from panda3d.core import LPoint3f, Point3, Vec3, LVecBase3f
from panda3d.core import TransformState
from panda3d.core import TransparencyAttrib
from direct.showbase.DirectObject import DirectObject
from panda3d.bullet import BulletWorld
import random
import simplepbr
import gltf
import sys

class main(ShowBase):
     def __init__(self):
         # load data for self.render first
         loadPrcFileData('', 'framebuffer-srgb #t')
         loadPrcFileData('', 'fullscreen #f')
         loadPrcFileData('', 'win-size 1680 1050')
         loadPrcFileData('', 'clock-frame-rate 60')
         
         # new initialization routine for Panda3D
         # use super().__init__() instead of ShowBase
         # use simplepbr.init() to initialize pbr replacement of setShaderAuto
         # simplepbr works automatically
         # use gltf.patch_loader(self.loader) to use gltf exports from Blender
         super().__init__()
         pipeline = simplepbr.init()
         pipeline.enable_shadows = True
         pipeline.msaa_samples = 4
         gltf.patch_loader(self.loader)
         
         self.cam.set_pos(-150, -150, 30)
         self.cam.look_at(0, 0, 0)
         
         # Shortcut to view the wireframe mesh and quick exit
         self.accept("f3", self.toggleWireframe)
         self.accept("escape", sys.exit, [0])
         
         amb_light = AmbientLight('amblight')
         amb_light.setColor((0.2, 0.2, 0.2, 1))
         amb_light_node = self.render.attachNewNode(amb_light)
         self.render.setLight(amb_light_node)
         
         point_light_1 = PointLight('point_light_1')
         point_light_1.setColor((1, 1, 1, 1))
         point_light_1_node = self.render.attachNewNode(point_light_1)
         self.render.setLight(point_light_1_node)
         point_light_1_node.setPos(0, 0, 20)
         
         def reset_simulation():
             npc_vehicle_list = self.render.findAllMatches("**/npc_vehicle*")
             npc_v_pos_list = [(-6, 16.9847, 0.663382), 180, (-11, 16.9847, 0.663382), 180, (-6, 26, 0.663382), 180, (-11, 26, 0.663382), 180, (10, -18.1727, 0.663397), 0, (5, -18.1727, 0.663397), 0]
             
             for v in npc_vehicle_list:
                 v.setH(npc_v_pos_list.pop())
                 v.setPos(npc_v_pos_list.pop())
         
         reset_1 = DirectObject()
         reset_1.accept('f10', reset_simulation)

         # begin the BulletWorld
         from panda3d.bullet import BulletWorld
         from panda3d.bullet import BulletCharacterControllerNode
         from panda3d.bullet import BulletVehicle
         from panda3d.bullet import ZUp
         from panda3d.bullet import BulletCapsuleShape
         from panda3d.bullet import BulletRigidBodyNode
         from panda3d.bullet import BulletBoxShape
         from panda3d.bullet import BulletGhostNode
         from panda3d.bullet import BulletPlaneShape
         from panda3d.bullet import BulletTriangleMesh
         from panda3d.bullet import BulletTriangleMeshShape
         from panda3d.bullet import BulletSphereShape

         # infinite ground plane
         shape = BulletPlaneShape(Vec3(0, 0, 1), 0)
         node = BulletRigidBodyNode('Ground')
         node.addShape(shape)
         node.setFriction(0.1)
         np = self.render.attachNewNode(node)
         np.setPos(0, 0, 0)

         world = BulletWorld()
         world.setGravity(Vec3(0, 0, -9.81))  # standard is (Vec3(0, 0, -9.81)
         
         world.attachRigidBody(node)
         
         def make_vehicle_1(vehicle_label, start_pos, heading):
             # make first collision shape
             v_shape = BulletBoxShape(Vec3(1, 2.4, 0.5))
             transform_shape_space = TransformState.makePos(Point3(0, -0.65, 0.6))
             # attach universal vehicle node for automatic compound shape
             vehicle_node = render.attachNewNode(BulletRigidBodyNode(str(vehicle_label)))
             # second vehicle collision shape
             v_shape_2 = BulletBoxShape(Vec3(0.9, 1, 0.5))
             transform_shape_space_2 = TransformState.makePos(Point3(0, -0.4, 1))

             vehicle_node.node().setCcdMotionThreshold(0.000000007)
             vehicle_node.node().setCcdSweptSphereRadius(0.30)

             vehicle_node.node().addShape(v_shape, transform_shape_space)
             vehicle_node.node().addShape(v_shape_2, transform_shape_space_2)

             vehicle_node.setPos(start_pos)
             vehicle_node.setH(heading)
             vehicle_node.node().setMass(1000.0)  # mass in kilograms
             vehicle_node.node().setFriction(10.0)
             # vehicle_node.node().setLinearFactor(3)
             world.attachRigidBody(vehicle_node.node())
             vehicle_node.node().setDeactivationEnabled(False)

             # instantiate vehicle
             self.npc_vehicle_1 = BulletVehicle(world, vehicle_node.node())
             self.npc_vehicle_1.setCoordinateSystem(ZUp)
             print(self.npc_vehicle_1)
             world.attachVehicle(self.npc_vehicle_1)
             # pickup_truck_1 wheels begin
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_1 = self.npc_vehicle_1.createWheel()
             wheel_1.setNode(wheel_model.node())
             wheel_1.setChassisConnectionPointCs(Point3(0.75, 1.3, 0.2))
             wheel_1.setFrontWheel(True)
             wheel_1.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_1.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_1.setWheelRadius(0.5)
             wheel_1.setMaxSuspensionTravelCm(35.0)
             wheel_1.setSuspensionStiffness(70.0)
             wheel_1.setWheelsDampingRelaxation(2.0)
             wheel_1.setWheelsDampingCompression(4.0)
             wheel_1.setFrictionSlip(4)
             wheel_1.setRollInfluence(0.01)
             # wheel_2
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_2 = self.npc_vehicle_1.createWheel()
             wheel_2.setNode(wheel_model.node())
             wheel_2.setChassisConnectionPointCs(Point3(-0.75, 1.3, 0.2))
             wheel_2.setFrontWheel(True)
             wheel_2.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_2.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_2.setWheelRadius(0.5)
             wheel_2.setMaxSuspensionTravelCm(35.0)
             wheel_2.setSuspensionStiffness(70.0)
             wheel_2.setWheelsDampingRelaxation(2.0)
             wheel_2.setWheelsDampingCompression(4.0)
             wheel_2.setFrictionSlip(4)
             wheel_2.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # wheel_3
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_3 = self.npc_vehicle_1.createWheel()
             wheel_3.setNode(wheel_model.node())
             wheel_3.setChassisConnectionPointCs(Point3(0.75, -2, 0.2))
             wheel_3.setFrontWheel(False)
             wheel_3.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_3.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_3.setWheelRadius(0.5)
             wheel_3.setMaxSuspensionTravelCm(35.0)
             wheel_3.setSuspensionStiffness(70.0)
             wheel_3.setWheelsDampingRelaxation(2.0)
             wheel_3.setWheelsDampingCompression(4.0)
             wheel_3.setFrictionSlip(4)
             wheel_3.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # wheel_4
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_4 = self.npc_vehicle_1.createWheel()
             wheel_4.setNode(wheel_model.node())
             wheel_4.setChassisConnectionPointCs(Point3(-0.75, -2, 0.2))
             wheel_4.setFrontWheel(False)
             wheel_4.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_4.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_4.setWheelRadius(0.5)
             wheel_4.setMaxSuspensionTravelCm(35.0)
             wheel_4.setSuspensionStiffness(70.0)
             wheel_4.setWheelsDampingRelaxation(2.0)
             wheel_4.setWheelsDampingCompression(4.0)
             wheel_4.setFrictionSlip(4)
             wheel_4.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # vehicle_node geometry
             truck_1 = loader.loadModel('models/pickup_2.gltf')
             truck_1.setH(180)
             truck_1.setScale(0.6)
             truck_1.reparentTo(vehicle_node)
             truck_1_windows = truck_1.find("**/windows")
             truck_1_windows.setTransparency(TransparencyAttrib.M_multisample)
         
         make_vehicle_1('npc_vehicle_1', (-6, 16.9847, 0.663382), 180)
         
         def make_vehicle_2(vehicle_label, start_pos, heading):
             # make first collision shape
             v_shape = BulletBoxShape(Vec3(1, 2.4, 0.5))
             transform_shape_space = TransformState.makePos(Point3(0, -0.65, 0.6))
             # attach universal vehicle node for automatic compound shape
             vehicle_node = render.attachNewNode(BulletRigidBodyNode(str(vehicle_label)))
             # second vehicle collision shape
             v_shape_2 = BulletBoxShape(Vec3(0.9, 1, 0.5))
             transform_shape_space_2 = TransformState.makePos(Point3(0, -0.4, 1))

             vehicle_node.node().setCcdMotionThreshold(0.000000007)
             vehicle_node.node().setCcdSweptSphereRadius(0.30)

             vehicle_node.node().addShape(v_shape, transform_shape_space)
             vehicle_node.node().addShape(v_shape_2, transform_shape_space_2)

             vehicle_node.setPos(start_pos)
             vehicle_node.setH(heading)
             vehicle_node.node().setMass(1000.0)  # mass in kilograms
             vehicle_node.node().setFriction(10.0)
             # vehicle_node.node().setLinearFactor(3)
             world.attachRigidBody(vehicle_node.node())
             vehicle_node.node().setDeactivationEnabled(False)

             # instantiate vehicle
             self.npc_vehicle_2 = BulletVehicle(world, vehicle_node.node())
             self.npc_vehicle_2.setCoordinateSystem(ZUp)
             print(self.npc_vehicle_2)
             world.attachVehicle(self.npc_vehicle_2)
             # pickup_truck_1 wheels begin
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_1 = self.npc_vehicle_2.createWheel()
             wheel_1.setNode(wheel_model.node())
             wheel_1.setChassisConnectionPointCs(Point3(0.75, 1.3, 0.2))
             wheel_1.setFrontWheel(True)
             wheel_1.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_1.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_1.setWheelRadius(0.5)
             wheel_1.setMaxSuspensionTravelCm(35.0)
             wheel_1.setSuspensionStiffness(70.0)
             wheel_1.setWheelsDampingRelaxation(2.0)
             wheel_1.setWheelsDampingCompression(4.0)
             wheel_1.setFrictionSlip(4)
             wheel_1.setRollInfluence(0.01)
             # wheel_2
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_2 = self.npc_vehicle_2.createWheel()
             wheel_2.setNode(wheel_model.node())
             wheel_2.setChassisConnectionPointCs(Point3(-0.75, 1.3, 0.2))
             wheel_2.setFrontWheel(True)
             wheel_2.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_2.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_2.setWheelRadius(0.5)
             wheel_2.setMaxSuspensionTravelCm(35.0)
             wheel_2.setSuspensionStiffness(70.0)
             wheel_2.setWheelsDampingRelaxation(2.0)
             wheel_2.setWheelsDampingCompression(4.0)
             wheel_2.setFrictionSlip(4)
             wheel_2.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # wheel_3
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_3 = self.npc_vehicle_2.createWheel()
             wheel_3.setNode(wheel_model.node())
             wheel_3.setChassisConnectionPointCs(Point3(0.75, -2, 0.2))
             wheel_3.setFrontWheel(False)
             wheel_3.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_3.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_3.setWheelRadius(0.5)
             wheel_3.setMaxSuspensionTravelCm(35.0)
             wheel_3.setSuspensionStiffness(70.0)
             wheel_3.setWheelsDampingRelaxation(2.0)
             wheel_3.setWheelsDampingCompression(4.0)
             wheel_3.setFrictionSlip(4)
             wheel_3.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # wheel_4
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_4 = self.npc_vehicle_2.createWheel()
             wheel_4.setNode(wheel_model.node())
             wheel_4.setChassisConnectionPointCs(Point3(-0.75, -2, 0.2))
             wheel_4.setFrontWheel(False)
             wheel_4.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_4.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_4.setWheelRadius(0.5)
             wheel_4.setMaxSuspensionTravelCm(35.0)
             wheel_4.setSuspensionStiffness(70.0)
             wheel_4.setWheelsDampingRelaxation(2.0)
             wheel_4.setWheelsDampingCompression(4.0)
             wheel_4.setFrictionSlip(4)
             wheel_4.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # vehicle_node geometry
             truck_1 = loader.loadModel('models/pickup_2.gltf')
             truck_1.setH(180)
             truck_1.setScale(0.6)
             truck_1.reparentTo(vehicle_node)
             truck_1_windows = truck_1.find("**/windows")
             truck_1_windows.setTransparency(TransparencyAttrib.M_multisample)
         
         make_vehicle_2('npc_vehicle_2', (-20, 16.9847, 0.663382), 180)

         def make_vehicle_3(vehicle_label, start_pos, heading):
             # make first collision shape
             v_shape = BulletBoxShape(Vec3(1, 2.4, 0.5))
             transform_shape_space = TransformState.makePos(Point3(0, -0.65, 0.6))
             # attach universal vehicle node for automatic compound shape
             vehicle_node = render.attachNewNode(BulletRigidBodyNode(str(vehicle_label)))
             # second vehicle collision shape
             v_shape_2 = BulletBoxShape(Vec3(0.9, 1, 0.5))
             transform_shape_space_2 = TransformState.makePos(Point3(0, -0.4, 1))

             vehicle_node.node().setCcdMotionThreshold(0.000000007)
             vehicle_node.node().setCcdSweptSphereRadius(0.30)

             vehicle_node.node().addShape(v_shape, transform_shape_space)
             vehicle_node.node().addShape(v_shape_2, transform_shape_space_2)

             vehicle_node.setPos(start_pos)
             vehicle_node.setH(heading)
             vehicle_node.node().setMass(1000.0)  # mass in kilograms
             vehicle_node.node().setFriction(10.0)
             # vehicle_node.node().setLinearFactor(3)
             world.attachRigidBody(vehicle_node.node())
             vehicle_node.node().setDeactivationEnabled(False)

             # instantiate vehicle
             self.npc_vehicle_3 = BulletVehicle(world, vehicle_node.node())
             self.npc_vehicle_3.setCoordinateSystem(ZUp)
             print(self.npc_vehicle_3)
             world.attachVehicle(self.npc_vehicle_3)
             # pickup_truck_1 wheels begin
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_1 = self.npc_vehicle_3.createWheel()
             wheel_1.setNode(wheel_model.node())
             wheel_1.setChassisConnectionPointCs(Point3(0.75, 1.3, 0.2))
             wheel_1.setFrontWheel(True)
             wheel_1.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_1.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_1.setWheelRadius(0.5)
             wheel_1.setMaxSuspensionTravelCm(35.0)
             wheel_1.setSuspensionStiffness(70.0)
             wheel_1.setWheelsDampingRelaxation(2.0)
             wheel_1.setWheelsDampingCompression(4.0)
             wheel_1.setFrictionSlip(4)
             wheel_1.setRollInfluence(0.01)
             # wheel_2
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_2 = self.npc_vehicle_3.createWheel()
             wheel_2.setNode(wheel_model.node())
             wheel_2.setChassisConnectionPointCs(Point3(-0.75, 1.3, 0.2))
             wheel_2.setFrontWheel(True)
             wheel_2.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_2.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_2.setWheelRadius(0.5)
             wheel_2.setMaxSuspensionTravelCm(35.0)
             wheel_2.setSuspensionStiffness(70.0)
             wheel_2.setWheelsDampingRelaxation(2.0)
             wheel_2.setWheelsDampingCompression(4.0)
             wheel_2.setFrictionSlip(4)
             wheel_2.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # wheel_3
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_3 = self.npc_vehicle_3.createWheel()
             wheel_3.setNode(wheel_model.node())
             wheel_3.setChassisConnectionPointCs(Point3(0.75, -2, 0.2))
             wheel_3.setFrontWheel(False)
             wheel_3.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_3.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_3.setWheelRadius(0.5)
             wheel_3.setMaxSuspensionTravelCm(35.0)
             wheel_3.setSuspensionStiffness(70.0)
             wheel_3.setWheelsDampingRelaxation(2.0)
             wheel_3.setWheelsDampingCompression(4.0)
             wheel_3.setFrictionSlip(4)
             wheel_3.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # wheel_4
             wheel_model = loader.loadModel('models/wheel_1.gltf')
             wheel_model.reparentTo(render)
             wheel_4 = self.npc_vehicle_3.createWheel()
             wheel_4.setNode(wheel_model.node())
             wheel_4.setChassisConnectionPointCs(Point3(-0.75, -2, 0.2))
             wheel_4.setFrontWheel(False)
             wheel_4.setWheelDirectionCs(Vec3(0, 0, -1))
             wheel_4.setWheelAxleCs(Vec3(1, 0, 0))
             wheel_4.setWheelRadius(0.5)
             wheel_4.setMaxSuspensionTravelCm(35.0)
             wheel_4.setSuspensionStiffness(70.0)
             wheel_4.setWheelsDampingRelaxation(2.0)
             wheel_4.setWheelsDampingCompression(4.0)
             wheel_4.setFrictionSlip(4)
             wheel_4.setRollInfluence(0.01)
             # steering, engine control, and braking handled in Task section
             # vehicle_node geometry
             truck_1 = loader.loadModel('models/pickup_2.gltf')
             truck_1.setH(180)
             truck_1.setScale(0.6)
             truck_1.reparentTo(vehicle_node)
             truck_1_windows = truck_1.find("**/windows")
             truck_1_windows.setTransparency(TransparencyAttrib.M_multisample)
             
         make_vehicle_3('npc_vehicle_3', (-10, 26, 0.663382), 180)
         
         # debug toggle function
         def toggleDebug():
             if debugNP.isHidden():
                 debugNP.show()
             else:
                 debugNP.hide()

         o = DirectObject()
         o.accept('f1', toggleDebug)

         # load Bullet debugger
         from panda3d.bullet import BulletDebugNode

         debugNode = BulletDebugNode('Debug')
         debugNode.showWireframe(True)
         debugNode.showConstraints(True)
         debugNode.showBoundingBoxes(False)
         debugNode.showNormals(False)
         debugNP = self.render.attachNewNode(debugNode)
         # debugNP.show()
         world.setDebugNode(debugNP.node())
         # end debug
         
         # npc vehicle state handler begins
         self.vehicle_1_steer_inc = 5
         self.vehicle_1_engine_force = 200
         self.vehicle_1_brake_force = 0
         
         self.vehicle_2_steer_inc = 3
         self.vehicle_2_engine_force = 200
         self.vehicle_2_brake_force = 0
         
         self.vehicle_3_steer_inc = 6
         self.vehicle_3_engine_force = 200
         self.vehicle_3_brake_force = 0
         
         def dist_timing():
             # find the vehicle
             vehicle_1 = self.render.find('**/npc_vehicle_1')
             vehicle_2 = self.render.find('**/npc_vehicle_2')
             vehicle_3 = self.render.find('**/npc_vehicle_3')

             v_dist_1 = (vehicle_1.get_pos() - vehicle_2.get_pos(base.render)).length()
             print(v_dist_1)

             if v_dist_1 < 10:
                 print('Future collision detected between vehicle_1 and vehicle_2! Correcting course...')
                 self.vehicle_1_steer_inc = -5
                 self.vehicle_1_engine_force = 0
                 self.vehicle_1_brake_force = 200
                 
             if v_dist_1 > 11:
                 print('Course clear, driving...')
                 self.vehicle_1_steer_inc = 5
                 self.vehicle_1_engine_force = 100
                 self.vehicle_1_brake_force = 0
                 
             v_dist_2 = (vehicle_2.get_pos() - vehicle_3.get_pos(base.render)).length()
             print(v_dist_2)

             if v_dist_2 < 10:
                 print('Future collision detected between vehicle_2 and vehicle_3! Correcting course...')
                 self.vehicle_2_steer_inc = -3
                 self.vehicle_2_engine_force = 0
                 self.vehicle_2_brake_force = 200
                 
             if v_dist_2 > 11:
                 print('Course clear, driving...')
                 self.vehicle_2_steer_inc = 3
                 self.vehicle_2_engine_force = 100
                 self.vehicle_2_brake_force = 0
                 
             v_dist_3 = (vehicle_3.get_pos() - vehicle_1.get_pos(base.render)).length()
             print(v_dist_3)

             if v_dist_3 < 10:
                 print('Future collision detected between vehicle_1 and vehicle_3! Correcting course...')
                 self.vehicle_1_steer_inc = -6
                 self.vehicle_1_engine_force = 30
                 self.vehicle_1_brake_force = 0
                 
                 self.vehicle_3_steer_inc = -6
                 self.vehicle_3_engine_force = 0
                 self.vehicle_3_brake_force = 200
                 
             if v_dist_3 > 11:
                 print('Course clear, driving...')
                 self.vehicle_3_steer_inc = 6
                 self.vehicle_3_engine_force = 100
                 self.vehicle_3_brake_force = 0

         def pickup_physics_1(Task):
             # initialize global clock
             dt = globalClock.get_dt()
             
             dist_timing()

             # npc vehicle logic begins
             # first npc vehicle
             vehicle = self.npc_vehicle_1
             # activate npc front steering
             vehicle.setSteeringValue(self.vehicle_1_steer_inc, 0)
             vehicle.setSteeringValue(self.vehicle_1_steer_inc, 1)
             # activate npc rear power and braking
             vehicle.applyEngineForce(self.vehicle_1_engine_force, 2)
             vehicle.applyEngineForce(self.vehicle_1_engine_force, 3)
             vehicle.setBrake(self.vehicle_1_brake_force, 2)
             vehicle.setBrake(self.vehicle_1_brake_force, 3)
             
             # next npc vehicle
             vehicle = self.npc_vehicle_2
             # activate npc front steering
             vehicle.setSteeringValue(self.vehicle_2_steer_inc, 0)
             vehicle.setSteeringValue(self.vehicle_2_steer_inc, 1)
             # activate npc rear power and braking
             vehicle.applyEngineForce(self.vehicle_2_engine_force, 2)
             vehicle.applyEngineForce(self.vehicle_2_engine_force, 3)
             vehicle.setBrake(self.vehicle_2_brake_force, 2)
             vehicle.setBrake(self.vehicle_2_brake_force, 3)
             
             # next npc vehicle
             vehicle = self.npc_vehicle_3
             # activate npc front steering
             vehicle.setSteeringValue(self.vehicle_3_steer_inc, 0)
             vehicle.setSteeringValue(self.vehicle_3_steer_inc, 1)
             # activate npc rear power and braking
             vehicle.applyEngineForce(self.vehicle_3_engine_force, 2)
             vehicle.applyEngineForce(self.vehicle_3_engine_force, 3)
             vehicle.setBrake(self.vehicle_3_brake_force, 2)
             vehicle.setBrake(self.vehicle_3_brake_force, 3)

             return Task.cont
         
         def task_1(Task):    
             dt = globalClock.get_dt()
             world.do_physics(dt)
             return Task.cont
         
         self.taskMgr.add(pickup_physics_1)
         self.taskMgr.add(task_1)
         
app = main()
app.run()
