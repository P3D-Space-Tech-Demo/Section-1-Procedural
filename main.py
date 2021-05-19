'''
BSD 3-Clause License

Copyright (c) 2021, "The Panda3D Community".
All rights reserved.

Authors: Simulan, Epihaius, Thaumaturge

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

from direct.showbase.ShowBase import ShowBase
from direct.stdpy import threading2
from direct.filter.CommonFilters import CommonFilters
from panda3d.core import load_prc_file_data
from panda3d.core import BitMask32
from panda3d.core import Shader, ShaderAttrib
from panda3d.core import TransformState
from panda3d.core import PointLight
from panda3d.core import Spotlight
from panda3d.core import PerspectiveLens
from panda3d.core import ConfigVariableManager
from panda3d.core import FrameBufferProperties
from panda3d.core import AntialiasAttrib
from panda3d.core import TransparencyAttrib
from panda3d.core import Fog
import sys
import random
import time
from panda3d.core import LPoint3f, Point3, Vec3, LVecBase3f, VBase4
from panda3d.core import WindowProperties
from direct.showbase.DirectObject import DirectObject
from direct.interval.IntervalGlobal import *
# gui imports
from direct.gui.DirectGui import *
from panda3d.core import TextNode
# new pbr imports
import gltf
# local imports
# import actor_data


class app(ShowBase):
    def __init__(self):
        load_prc_file_data("", """
            win-size 1680 1050
            window-title Collaborative Sci-Fantasy Tech Demo
            show-frame-rate-meter #t
            framebuffer-srgb #t
            framebuffer-multisample 1
            multisamples 4
            view-frustum-cull 0
            textures-power-2 none
            hardware-animated-vertices #t
            gl-depth-zero-to-one true
            clock-frame-rate 60
            interpolate-frames 1
            fullscreen #f
        """)

        # Initialize the showbase
        super().__init__()
        gltf.patch_loader(self.loader)
        
        props = WindowProperties()
        props.set_mouse_mode(WindowProperties.M_relative)
        base.win.request_properties(props)
        
        # the following setup routines are based on the Arena FPS Sample Program 
        # by Simulan with customized simplepbr shaders
        self.camLens.set_fov(80)
        self.camLens.set_near_far(0.01, 90000)
        self.camLens.set_focal_length(7)
        # self.camera.set_pos(0, 0, 2)
        
        # ConfigVariableManager.getGlobalPtr().listVariables()
        
        # point light generator
        for x in range(0, 1):
            plight_1 = PointLight('plight')
            # add plight props here
            plight_1_node = self.render.attach_new_node(plight_1)
            # plight_1.set_attenuation((0.5, 0, 0.0000005))
            # group the lights close to each other to create a sun effect
            plight_1_node.set_pos(random.uniform(-21, -20), random.uniform(-21, -20), random.uniform(100, 102))
            self.render.set_light(plight_1_node)
        
        self.sunlight = Spotlight('sunlight')
        self.sunlight.set_shadow_caster(True, 1024, 1024)
        self.sunlight.set_color(VBase4(0.7, 0.2, 0.3, 1))  # reddish
        lens = PerspectiveLens()
        lens.set_near_far(0.05, 5000)
        self.sunlight.set_lens(lens)
        self.sunlight.set_attenuation((0.5, 0, 0.0000005))
        self.sunlight = self.render.attach_new_node(self.sunlight)
        self.sunlight.set_pos(100, 100, 40)
        self.sunlight.look_at(-21, -21, 1)
        self.render.set_light(self.sunlight)
        
        # point light for volumetric lighting filter
        plight_1 = PointLight('plight')
        # add plight props here
        plight_1_node = self.render.attach_new_node(plight_1)
        # group the lights close to each other to create a sun effect
        plight_1_node.set_pos(random.uniform(-21, -20), random.uniform(-21, -20), random.uniform(20, 21))
        self.render.set_light(plight_1_node)
            
        scene_filters = CommonFilters(base.win, base.cam)
        scene_filters.set_bloom()
        scene_filters.set_high_dynamic_range()
        scene_filters.set_exposure_adjust(0.8)
        scene_filters.set_gamma_adjust(1.1)
        # scene_filters.set_volumetric_lighting(plight_1_node, 64, 0.5, 0.7, 0.1)
        # scene_filters.set_blur_sharpen(0.1)
        # scene_filters.set_ambient_occlusion(64, 0.05, 2.0, 0.01, 0.000002)

        self.accept("f3", self.toggle_wireframe)
        self.accept("escape", sys.exit, [0])
        
        exponential_fog = Fog('world_fog')
        exponential_fog.set_color(0.6, 0.7, 0.7)
        exponential_fog.set_exp_density(0.0009)
        self.render.set_fog(exponential_fog)
        
        self.accept("f3", self.toggle_wireframe)
        self.accept("escape", sys.exit, [0])
        
        self.game_start = 0
        
        from panda3d.bullet import BulletWorld
        from panda3d.bullet import BulletCharacterControllerNode
        from panda3d.bullet import ZUp
        from panda3d.bullet import BulletCapsuleShape
        from panda3d.bullet import BulletTriangleMesh
        from panda3d.bullet import BulletTriangleMeshShape
        from panda3d.bullet import BulletBoxShape
        from panda3d.bullet import BulletGhostNode
        from panda3d.bullet import BulletRigidBodyNode
        from panda3d.bullet import BulletPlaneShape

        self.world = BulletWorld()
        self.world.set_gravity(Vec3(0, 0, -9.81))
        
        hangar_1 = self.loader.load_model('models/hangar_1.gltf')
        hangar_1.reparent_to(self.render)
        hangar_1.set_pos(0, 0, 0)
        hangar_windows = hangar_1.find('**/clear_arches')
        hangar_windows.set_transparency(TransparencyAttrib.M_multisample)
        hangar_windows.hide()
        skybox = hangar_1.find('**/skybox')
        skybox.set_two_sided(True)
        '''
        # starship instantiation begins here
        self.starship_model = self.loader.load_model("procedural/starship.bam")
        self.starship_model.reparent_to(self.render)
        # perform procedural model adjustments here
        # self.starship_model.set_hpr(0, 90, 0)
        # self.starship_model.set_pos(0, 0, 11)
        # self.starship_model.set_color(0.9, 0.5, 0.5, 1)
        # self.starship_model.set_two_sided(True)
        # self.starship_model.set_scale(10)
        bounds = self.starship_model.node().get_bounds()
        geom = self.starship_model.node().modify_geom(0)
        prim = geom.get_primitive(0)
        self.prim_view = memoryview(prim.get_vertices()).cast("B").cast("I")
        new_prim = GeomTriangles(GeomEnums.UH_static)
        new_prim.set_index_type(GeomEnums.NT_uint32)
        geom.set_primitive(0, new_prim)
        self.starship_model.node().set_bounds(bounds)
        self.starship_model.node().set_final(True)
        self.prim_row_index = 0
        self.task_mgr.add(self.__build_starship, "build_starship", delay=0.)
        '''
        def make_collision_from_model(input_model, node_number, mass, world, target_pos):
            # tristrip generation from static models
            # generic tri-strip collision generator begins
            geom_nodes = input_model.find_all_matches('**/+GeomNode')
            geom_nodes = geom_nodes.get_path(node_number).node()
            # print(geom_nodes)
            geom_target = geom_nodes.get_geom(0)
            # print(geom_target)
            output_bullet_mesh = BulletTriangleMesh()
            output_bullet_mesh.add_geom(geom_target)
            tri_shape = BulletTriangleMeshShape(output_bullet_mesh, dynamic=False)
            print(output_bullet_mesh)

            body = BulletRigidBodyNode('input_model_tri_mesh')
            np = self.render.attach_new_node(body)
            np.node().add_shape(tri_shape)
            np.node().set_mass(mass)
            np.node().set_friction(0.01)
            np.set_pos(target_pos)
            np.set_scale(1)
            # np.set_h(180)
            # np.set_p(180)
            # np.set_r(180)
            np.set_collide_mask(BitMask32.allOn())
            world.attach_rigid_body(np.node())
        
        # make_collision_from_model(hangar_1, 0, 0, self.world, (hangar_1.get_pos()))

        # prototype hardware shader for Actor nodes
        actor_shader = Shader.load(Shader.SL_GLSL, "shaders/simplepbr_vert_mod_1.vert", "shaders/simplepbr_frag_mod_1.frag")
        actor_shader = ShaderAttrib.make(actor_shader)
        actor_shader = actor_shader.setFlag(ShaderAttrib.F_hardware_skinning, True)
        '''
        # initialize player character physics the Bullet way
        shape_1 = BulletCapsuleShape(0.75, 0.5, ZUp)
        player_node = BulletCharacterControllerNode(shape_1, 5, 'Player')  # (shape, mass, player name)
        player_np = self.render.attach_new_node(player_node)
        player_np.set_pos(-20, -10, 30)
        player_np.set_collide_mask(BitMask32.allOn())
        self.world.attach_character(player_np.node())
        # cast player_np to self.player
        self.player = player_np

        # reparent player character to render node
        fp_character = actor_data.player_character
        fp_character.reparent_to(self.render)
        fp_character.set_scale(1)
        # set the actor skinning hardware shader
        fp_character.set_attrib(actor_shader)

        self.camera.reparent_to(self.player)
        # reparent character to FPS cam
        fp_character.reparent_to(self.player)
        fp_character.set_pos(0, 0, -0.95)
        # self.camera.set_x(self.player, 1)
        self.camera.set_y(self.player, 0.03)
        self.camera.set_z(self.player, 0.5)

        # player gun begins
        self.player_gun = self.loader.load_model('models/handgun_1.gltf')
        self.player_gun.reparent_to(self.render)
        self.player_gun.reparent_to(self.camera)
        self.player_gun.set_x(self.camera, 0.1)
        self.player_gun.set_y(self.camera, 0.4)
        self.player_gun.set_z(self.camera, -0.1)
        '''
        # directly make a text node to display text
        text_1 = TextNode('text_1_node')
        text_1.set_text("")
        text_1_node = self.aspect2d.attach_new_node(text_1)
        text_1_node.set_scale(0.05)
        text_1_node.set_pos(-1.4, 0, 0.92)
        # import font and set pixels per unit font quality
        nunito_font = loader.load_font('fonts/Nunito/Nunito-Light.ttf')
        nunito_font.set_pixels_per_unit(100)
        nunito_font.set_page_size(512, 512)
        # apply font
        text_1.set_font(nunito_font)
        # small caps
        # text_1.set_small_caps(True)

        # on-screen target dot for aiming
        target_dot = TextNode('target_dot_node')
        target_dot.set_text(".")
        target_dot_node = self.aspect2d.attach_new_node(target_dot)
        target_dot_node.set_scale(0.075)
        target_dot_node.set_pos(0, 0, 0)
        # target_dot_node.hide()
        # apply font
        target_dot.set_font(nunito_font)
        target_dot.set_align(TextNode.ACenter)
        # see the Task section for relevant dot update logic
        
        # directly make a text node to display text
        text_2 = TextNode('text_2_node')
        text_2.set_text("Cycle the camera view by pressing Arrow Right." + '\n' + "Press 'f' to toggle the flashlight." + '\n' + "Currently viewing: Camera " + str(1))
        text_2_node = self.aspect2d.attach_new_node(text_2)
        text_2_node.set_scale(0.04)
        text_2_node.set_pos(-1.4, 0, 0.8)
        # import font and set pixels per unit font quality
        nunito_font = self.loader.load_font('fonts/Nunito/Nunito-Bold.ttf')
        nunito_font.set_pixels_per_unit(100)
        nunito_font.set_page_size(512, 512)
        # apply font
        text_2.set_font(nunito_font)
        text_2.set_text_color(0.7, 0.7, 0.7, 0.8)
        text_2.set_shadow(0.05, 0.05)

        self.flashlight_state = 0

        def toggle_flashlight():
            current_flashlight = self.render.find_all_matches("**/flashlight")

            if self.flashlight_state == 0:
                if len(current_flashlight) == 0:
                    self.slight = 0
                    self.slight = Spotlight('flashlight')
                    # self.slight.set_shadow_caster(True, 512, 512)
                    self.slight.set_color(VBase4(0.5, 0.6, 0.6, 1))  # slightly bluish
                    lens = PerspectiveLens()
                    lens.set_near_far(0.05, 5000)
                    self.slight.set_lens(lens)
                    self.slight.set_attenuation((0.5, 0, 0.0000005))
                    self.slight = self.render.attach_new_node(self.slight)
                    self.slight.set_pos(-0.1, 0.2, -0.4)
                    self.slight.reparent_to(self.camera)
                    self.flashlight_state = 1
                    self.render.set_light(self.slight)

                elif len(current_flashlight) > 0:
                    self.render.set_light(self.slight)
                    self.flashlight_state = 1

            elif self.flashlight_state > 0:
                self.render.set_light_off(self.slight)
                self.flashlight_state = 0

        self.accept('f', toggle_flashlight)
        
        # Section 1 Camera Positions
        # LPoint3f(-4.83092, -73.4093, 15)
        # LPoint3f(72.7162, -71.9642, 15)
        # LPoint3f(72.135, 72.5487, 15)
        # LPoint3f(6.86335, 72.8645, 15)
        # LPoint3f(-72.0691, 71.6962, 15)
        
        self.sec_1_cam_pos_list = [(-4.83092, -73.4093, 15), (72.7162, -71.9642, 15), (72.135, 72.5487, 15), (6.86335, 72.8645, 15), (-72.0691, 71.6962, 15)]
        self.camera.set_pos(self.sec_1_cam_pos_list[0])
        self.camera.look_at(0, 0, 0)
        self.sec_1_cam_inc = 1
        
        def cycle_right_security_cameras_sec_1():
        
            self.camera.set_pos(self.sec_1_cam_pos_list[self.sec_1_cam_inc])
            self.camera.look_at(0, 0, 0)
            
            text_2.set_text("Cycle the camera view by pressing Arrow Right." + '\n' + "Press 'f' to toggle the flashlight." + '\n' + "Currently viewing: Camera " + str(self.sec_1_cam_inc + 1))
            
            if self.sec_1_cam_inc < 4:
                self.sec_1_cam_inc += 1
            elif self.sec_1_cam_inc == 4:
                self.sec_1_cam_inc = 0
                
        self.accept('arrow_right', cycle_right_security_cameras_sec_1)               
        
        # 3D player movement system begins
        self.keyMap = {"left": 0, "right": 0, "forward": 0, "backward": 0, "run": 0, "jump": 0}

        def setKey(key, value):
            self.keyMap[key] = value

        # define button map
        self.accept("a", setKey, ["left", 1])
        self.accept("a-up", setKey, ["left", 0])
        self.accept("d", setKey, ["right", 1])
        self.accept("d-up", setKey, ["right", 0])
        self.accept("w", setKey, ["forward", 1])
        self.accept("w-up", setKey, ["forward", 0])
        self.accept("s", setKey, ["backward", 1])
        self.accept("s-up", setKey, ["backward", 0])
        self.accept("shift", setKey, ["run", 1])
        self.accept("shift-up", setKey, ["run", 0])
        self.accept("space", setKey, ["jump", 1])
        self.accept("space-up", setKey, ["jump", 0])
        # disable mouse
        self.disable_mouse()

        # the player movement speed
        self.movementSpeedForward = 7
        self.movementSpeedBackward = 7
        self.striveSpeed = 10
        self.ease = -10.0

        def move(Task):
            if self.game_start > 0:
                '''
                # first-person camera controller can be used from the following code:
                # get mouse data
                mouse_watch = base.mouseWatcherNode
                if mouse_watch.has_mouse():
                    pointer = base.win.get_pointer(0)
                    mouseX = pointer.get_x()
                    mouseY = pointer.get_y()
                    
                # screen sizes
                window_Xcoord_halved = base.win.get_x_size() // 2
                window_Ycoord_halved = base.win.get_y_size() // 2
                # mouse speed
                mouseSpeedX = 0.2
                mouseSpeedY = 0.2
                # maximum and minimum pitch
                maxPitch = 90
                minPitch = -50
                # cam view target initialization
                camViewTarget = LVecBase3f()

                if base.win.movePointer(0, window_Xcoord_halved, window_Ycoord_halved):
                    p = 0

                    if mouse_watch.has_mouse():
                        # calculate the pitch of camera
                        p = self.camera.get_p() - (mouseY - window_Ycoord_halved) * mouseSpeedY

                    # sanity checking
                    if p < minPitch:
                        p = minPitch
                    elif p > maxPitch:
                        p = maxPitch

                    if mouse_watch.has_mouse():
                        # directly set the camera pitch
                        self.camera.set_p(p)
                        camViewTarget.set_y(p)

                    # rotate the self.player's heading according to the mouse x-axis movement
                    if mouse_watch.has_mouse():
                        h = self.player.get_h() - (mouseX - window_Xcoord_halved) * mouseSpeedX

                    if mouse_watch.has_mouse():
                        # sanity checking
                        if h < -360:
                            h += 360

                        elif h > 360:
                            h -= 360

                        self.player.set_h(h)
                        camViewTarget.set_x(h)
                        
                    # hide the gun if looking straight down
                    if p < -30:
                        self.player_gun.hide()
                    if p > -30:
                        self.player_gun.show()

                if self.keyMap["left"]:
                    self.player.set_x(self.player, -self.striveSpeed * globalClock.get_dt())
                    
                    myAnimControl = actor_data.player_character.get_anim_control('walking')
                    if not myAnimControl.isPlaying():
                        actor_data.player_character.play("walking")
                        actor_data.player_character.set_play_rate(4.0, 'walking')
                        
                if not self.keyMap["left"]:
                    pass

                if self.keyMap["right"]:
                    self.player.set_x(self.player, self.striveSpeed * globalClock.get_dt())
                    
                    myAnimControl = actor_data.player_character.get_anim_control('walking')
                    if not myAnimControl.isPlaying():
                        actor_data.player_character.play("walking")
                        actor_data.player_character.set_play_rate(4.0, 'walking')
                        
                if not self.keyMap["right"]:
                    pass

                if self.keyMap["forward"]:
                    self.player.set_y(self.player, self.movementSpeedForward * globalClock.get_dt())
                    
                    myAnimControl = actor_data.player_character.get_anim_control('walking')
                    if not myAnimControl.isPlaying():
                        actor_data.player_character.play("walking")
                        actor_data.player_character.set_play_rate(4.0, 'walking')
                    
                if self.keyMap["forward"] != 1:
                    pass
                    
                if self.keyMap["backward"]:
                    self.player.set_y(self.player, -self.movementSpeedBackward * globalClock.get_dt())
                    
                    myBackControl = actor_data.player_character.get_anim_control('walking')
                    if not myBackControl.isPlaying():
                        myBackControl.stop()
                        actor_data.player_character.play('walking')
                        actor_data.player_character.set_play_rate(-4.0, 'walking')
                    
                if self.keyMap["backward"] != 1:
                    pass
                '''
                    
            return Task.cont

        # infinite ground plane
        # the effective world Z limit
        ground_plane = BulletPlaneShape(Vec3(0, 0, 1), 0)
        node = BulletRigidBodyNode('ground')
        node.add_shape(ground_plane)
        node.set_friction(0.1)
        np = self.render.attach_new_node(node)
        np.set_pos(0, 0, 1)
        self.world.attach_rigid_body(node)

        # Bullet debugger
        from panda3d.bullet import BulletDebugNode
        debugNode = BulletDebugNode('Debug')
        debugNode.show_wireframe(True)
        debugNode.show_constraints(True)
        debugNode.show_bounding_boxes(False)
        debugNode.show_normals(False)
        debugNP = self.render.attach_new_node(debugNode)
        self.world.set_debug_node(debugNP.node())

        # debug toggle function
        def toggle_debug():
            if debugNP.is_hidden():
                debugNP.show()
            else:
                debugNP.hide()

        self.accept('f1', toggle_debug)

        def update(Task):
            if self.game_start < 1:
                self.game_start = 1
            return Task.cont

        def physics_update(Task):
            dt = globalClock.get_dt()
            self.world.do_physics(dt)
            return Task.cont

        self.task_mgr.add(move)
        self.task_mgr.add(update)
        self.task_mgr.add(physics_update)
    '''
    # Epihaius starship build gets called here
    def __build_starship(self, task):
        start = self.prim_row_index
        end = start + 3
        geom = self.starship_model.node().modify_geom(0)
        prim = geom.modify_primitive(0)
        prim_array = prim.modify_vertices()
        prim_array.set_num_rows(end)
        prim_view = memoryview(prim_array).cast("B").cast("I")
        prim_view[start:end] = self.prim_view[start:end]
        self.prim_row_index += 3

        if self.prim_row_index != len(self.prim_view):
            return task.again
   '''
app().run()

