from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from random import random
import array

load_prc_file_data("", "sync-video #f")


base = ShowBase()


Obstacles = []


class Obstacle:

    _inst = []

    def __init__(self, pos):

        self.model = base.loader.load_model("smiley")
        self.model.reparent_to(base.render)
        self.model.set_pos(pos)
        Obstacles.append(self)
        self.accel = 10.
        self.speed = 0.
        self.speed_max = 10.
        self.speed_unit_vec = Vec3.left()
        self.speed_vec = Vec3()
        base.task_mgr.add(self.move, "move_obstacle")

    def move(self, task):

        dt = globalClock.get_dt()

        if self.accel > 0.:
            if self.speed < self.speed_max:
                self.speed = min(self.speed_max, self.speed + self.accel * dt)
            else:
                self.accel *= -1.
        else:
            if self.speed > 0.:
                self.speed = max(0., self.speed + self.accel * dt)
            else:
                self.accel *= -1.

        if self.speed == 0.:
            self.accel *= -1.
            self.speed_unit_vec *= -1.

        self.speed_vec = self.speed_unit_vec * self.speed * dt
        pos = self.model.get_pos()
        pos += self.speed_vec
        pos.z = 0.
        self.model.set_pos(pos)

        return task.cont


class Bot:

    def __init__(self, pos, target_point, target_model):

        self.model = base.loader.load_model("smiley")
        self.model.reparent_to(base.render)
        self.radius = 5.
        self.buffer_area_model = self.model.copy_to(self.model)
        self.buffer_area_model.set_scale(-self.radius, self.radius, self.radius)
        self.model.set_pos(pos)
        self.accel = 15.
        self.speed = 5.
        self.speed_min = 5.
        self.speed_max = 20.
        self.target_point = target_point
        self.target_point_index = 0
        self.target_points = [target_point, pos]
        self.target_model = target_model
        target_vec = self.target_point - self.model.get_pos()
        self.start_dist = target_vec.length()
        self.speed_start_vec = Vec3.forward()
        self.speed_vec = Vec3.forward()
        base.task_mgr.add(self.move, "move_bot")

    def get_distance(self, obstacle):

        return self.model.get_distance(obstacle.model)

    def get_dir_vec(self, pos, obstacle, target_vec):
        """
        Compute a direction vector for the bot to make it move alongside the
        given obstacle.

        """

        from math import sqrt

        obst_pos = obstacle.model.get_pos()
        dist_vec = obst_pos - pos
        dist = dist_vec.length()
        dist_vec.normalize()

        if dist_vec.dot(target_vec) < 0:
            # if the bot is moving away from the obstacle, let it continue to
            # move along its speed vector
            return self.speed_vec * self.speed

        if dist <= self.radius:
            # the obstacle must lie outside of the "buffer circle"
            dist = self.radius + .1
            obst_pos = pos + dist_vec * dist

        tangent_len = sqrt(dist * dist - self.radius * self.radius)
        a = self.radius * self.radius / dist
        a_vec = dist_vec * a
        b = a * tangent_len / self.radius
        x, y, _ = dist_vec
        b_vec = Vec3(-y, x, 0.)
        # define the vectors pointing from the obstacle position in the
        # direction of the lines tangent from that point to the "buffer circle"
        tangent_vec1 = (obst_pos - (pos + a_vec + b_vec)).normalized()
        tangent_vec2 = (obst_pos - (pos + a_vec - b_vec)).normalized()
        dot1 = tangent_vec1.dot(target_vec)
        dot2 = tangent_vec2.dot(target_vec)

        if max(dot1, dot2) < 0.:
            # if the tangent vectors make too large an angle with the vector
            # pointing from the bot to its target, let the bot continue to move
            # along its speed vector
            return self.speed_vec * self.speed

        dir_vec = tangent_vec1 if dot1 > dot2 else tangent_vec2

        return dir_vec * self.speed

    def move(self, task):

        dt = globalClock.get_dt()
        target_vec = self.target_point - self.model.get_pos()
        dist = min(self.start_dist, target_vec.length())
        target_vec.normalize()
        dist_vec = Vec3(target_vec)
        target_vec *= self.start_dist - dist
        dot = self.speed_vec.dot(dist_vec)
        frac = min(1., (.35 + 6 * (1. - (dot + 1.) * .5)) * dt * self.start_dist / dist)

        if dot <= 0.:
            target_vec = dist_vec * 100.
#            print("Course corrected!")

        # to interpolate the speed vector, it is shortened by a small fraction,
        # while that same fraction of the target vector is added to it;
        # this generally changes the length of the speed vector, so to preserve
        # its length (the speed), it is normalized and then multiplied with the
        # current speed value
        self.speed_vec = self.speed_vec * self.speed * (1. - frac) + target_vec * frac
        self.speed_vec.normalize()

        pos = self.model.get_pos()
        old_pos = Point3(pos)
        pos += self.speed_vec * self.speed * dt
        pos.z = 0.
        self.model.set_pos(pos)

        pushed = False
        push_vec = Vec3()

        for obstacle in Obstacles:
            if self.get_distance(obstacle) < self.radius:
                pushed = True
                break

        if pushed:
            # accelerate the bot to avoid collisions
            self.speed = min(self.speed_max, self.speed + self.accel * dt)
        elif self.speed > self.speed_min:
            # decelerate to normal speed
            self.speed = max(self.speed_min, self.speed - self.accel * dt)
        else:
            # accelerate to normal speed
            self.speed = min(self.speed_min, self.speed + self.accel * dt)

        for obstacle in Obstacles:
            distance = self.get_distance(obstacle)
            if distance < self.radius:
                # set the bot back to its previous position and compute a
                # direction to move it alongside the obstacle
                pos = Point3(old_pos)
                pos += self.get_dir_vec(pos, obstacle, target_vec.normalized()) * dt
                pos.z = 0.
                self.model.set_pos(pos)

        target_vec = self.target_point - pos
        dist = target_vec.length()

        if dist <= self.speed * dt:
            self.speed = self.speed_min
            self.speed_start_vec *= -1.
            self.speed_vec = Vec3(self.speed_start_vec)
            self.target_point_index = 1 - self.target_point_index
            self.target_point = self.target_points[self.target_point_index]
            target_vec = self.target_point - self.model.get_pos()
            self.start_dist = target_vec.length()
            self.target_model.set_pos(self.target_point)
#            print("Switched target; self.start_dist:", self.start_dist)

        return task.cont


class Simulation:

    def __init__(self):

        base.disableMouse()
        base.camera.set_z(100.)
        base.camera.set_p(-90.)

        # set up a light source
        p_light = PointLight("point_light")
        p_light.set_color((1., 1., 1., 1.))
        self.light = base.camera.attach_new_node(p_light)
        self.light.set_pos(5., -100., 7.)
        base.render.set_light(self.light)

        Obstacle(Point3(0., -10., 0.))
        Obstacle(Point3(0., 0., 0.))
        Obstacle(Point3(0., 10., 0.))

        target_point = Point3(0., 20., 0.)
        target_model = base.loader.load_model("smiley")
        target_model.reparent_to(base.render)
        target_model.set_pos(target_point)
        target_model.set_color(1., 0., 0., 1.)
        Bot(Point3(-20., -15., 0.), target_point, target_model)


Simulation()
base.run()
