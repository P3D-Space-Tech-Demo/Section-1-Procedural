from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from random import random
import array
import gltf


base = ShowBase()


def create_beam():

    from math import pi, sin, cos

    data = array.array("f", [])
    segs = 6
    vert_count = 0

    for i in range(segs + 1):
        angle = pi * 2 / segs * i
        x = sin(angle)
        z = -cos(angle)
        data.extend((x, 0., z, x, 1., z))
        vert_count += 2

    vertex_format = GeomVertexFormat.get_v3()
    v_data = GeomVertexData("data", vertex_format, GeomEnums.UH_static)
    data_array = v_data.modify_array(0)
    data_array.unclean_set_num_rows(vert_count)
    view = memoryview(data_array).cast("B").cast("f")
    view[:] = data

    prim = GeomTriangles(GeomEnums.UH_static)

    for i in range(segs):
        i1 = i * 2
        i2 = i1 + 1
        i3 = i2 + 1
        i4 = i3 + 1
        prim.add_vertices(i1, i2, i3)
        prim.add_vertices(i2, i4, i3)

    geom = Geom(v_data)
    geom.add_primitive(prim)

    node = GeomNode("beam")
    node.add_geom(geom)
    beam = NodePath(node)
    beam.set_light_off()
    beam.set_color(1., 0., 0., 1.)

    return beam


class Worker:

    def __do_job(self, task, job, vertex_data, finalizer):

        part = job.generate_part(vertex_data)

        def do_job():

            dist = (part.center - self.beam.get_pos(base.render)).length()
            self.beam.set_sy(dist)
            self.beam.look_at(base.render, part.center)
            part.model.reparent_to(base.render)
            solidify_task = lambda task: part.solidify(task, 1.5, finalizer)
            base.task_mgr.add(solidify_task, "solidify")
            deactivation_task = lambda task: self.set_part(None)
            base.task_mgr.add(deactivation_task, "deactivate_beam", delay=1.5)

        self._do_job = do_job
        self.set_part(part)

    def start_job(self, job, vertex_data, finalizer):

        if not job:
            return

        part = job.generate_part(vertex_data)

        def do_job():

            dist = (part.center - self.beam.get_pos(base.render)).length()
            self.beam.set_sy(dist)
            self.beam.look_at(base.render, part.center)
            part.model.reparent_to(base.render)
            solidify_task = lambda task: part.solidify(task, 1.5, finalizer)
            base.task_mgr.add(solidify_task, "solidify")
            deactivation_task = lambda task: self.set_part(None)
            base.task_mgr.add(deactivation_task, "deactivate_beam", delay=1.5)

            if job:
                delay = 1.6 + random()
                continue_job = lambda task: self.start_job(job, vertex_data, finalizer)
                base.task_mgr.add(continue_job, "continue_job", delay=delay)

        self._do_job = do_job
        self.set_part(part)


class WorkerBot(Worker):

    instances = []

    def __init__(self, model, beam):

        self.type = "bot"
        self.model = model
        self.beam = beam.copy_to(self.model)
        self.beam.set_pos(0., 1.325, 1.92)
        self.beam.set_sy(.1)
        self.radius = 3.
        self.turn_speed = 500.
        self.accel = 15.
        self.speed = 5.
        self.speed_min = 5.
        self.speed_max = 20.
        self.speed_vec = Vec3.forward()
        self.target_point = Point3()
        self.instances.append(self)

    def set_part(self, part):

        if part:
            x, y, z = part.center
            self.target_point = Point3(x, y, 0.)
            target_vec = self.target_point - self.model.get_pos()
            self.start_dist = target_vec.length()
            base.task_mgr.add(self.move, "move_bot")
        else:
            self.beam.set_sy(.1)

    def get_distance(self, obstacle):

        return self.model.get_distance(obstacle.model)

    def get_dir_vec(self, pos, obstacle, target_vec):

        from math import sqrt

        obst_pos = obstacle.model.get_pos()
        dist_vec = obst_pos - pos
        dist = dist_vec.length()
        dist_vec.normalize()

        if dist_vec.dot(target_vec) < 0:
            return self.speed_vec * self.speed

        if dist <= self.radius:
            dist = self.radius + .1
            obst_pos = pos + dist_vec * dist

        tangent_len = sqrt(dist * dist - self.radius * self.radius)
        a = self.radius * self.radius / dist
        a_vec = dist_vec * a
        b = a * tangent_len / self.radius
        x, y, _ = dist_vec
        b_vec = Vec3(-y, x, 0.)
        tangent_vec1 = (obst_pos - (pos + a_vec + b_vec)).normalized()
        tangent_vec2 = (obst_pos - (pos + a_vec - b_vec)).normalized()
        dot1 = tangent_vec1.dot(target_vec)
        dot2 = tangent_vec2.dot(target_vec)

        if max(dot1, dot2) < 0.:
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
        frac = min(1., (.35 + 100 * (1. - (dot + 1.) * .5)) * dt * self.start_dist / dist)

        if dot <= 0.:
            target_vec = dist_vec * 100.
#            print("Course corrected!")

        # to interpolate the speed vector, it is shortened by a small fraction,
        # while that same fraction of the target vector is added to it;
        # this generally changes the length of the speed vector, so to preserve
        # its length (the speed), it is normalized and then multiplied with the
        # current speed value
        speed_vec = self.speed_vec * self.speed * (1. - frac) + target_vec * frac

        if speed_vec.normalize():
            self.speed_vec = speed_vec

        pos = self.model.get_pos()
        old_pos = Point3(pos)
        pos += self.speed_vec * self.speed * dt
        pos.z = 0.
        self.model.set_pos(pos)
        old_h = self.model.get_h()
        quat = Quat()
        look_at(quat, self.speed_vec, Vec3.up())
        h, p, r = quat.get_hpr()
        d_h = h - old_h

        if abs(d_h) > self.turn_speed * dt:
            turn_speed = self.turn_speed * (-1. if d_h < 0. else 1.)
            self.model.set_h(old_h + turn_speed * dt)
        else:
            self.model.set_h(h)

        pushed = False
        push_vec = Vec3()
        instances = self.instances[:]
        instances.remove(self)

        '''for inst in instances:
            if self.get_distance(inst) < self.radius:
                pushed = True
                break'''

        if pushed:
            # accelerate the bot to avoid collisions
            self.speed = min(self.speed_max, self.speed + self.accel * dt)
        elif self.speed > self.speed_min:
            # decelerate to normal speed
            self.speed = max(self.speed_min, self.speed - self.accel * dt)
        else:
            # accelerate to normal speed
            self.speed = min(self.speed_min, self.speed + self.accel * dt)

        '''for inst in instances:
            distance = self.get_distance(inst)
            if distance < self.radius:
                pos = Point3(old_pos)
                pos += self.get_dir_vec(pos, inst, target_vec.normalized()) * dt
                pos.z = 0.
                self.model.set_pos(pos)'''

        target_vec = self.target_point - pos
        dist = target_vec.length()

        if dist <= self.speed * dt:
            self.speed = self.speed_min
            self._do_job()
            self._do_job = lambda: None

            return task.done

        return task.cont


class WorkerDrone(Worker):

    def __init__(self, model, beam):

        self.type = "drone"
        self.model = model
        self.beam = beam.copy_to(self.model)
#        self.beam.set_pos(0., 0., 0.)
        self.beam.set_sy(.1)

    def set_part(self, part):

        if part:
            x, y, z = part.center
            self.model.set_pos(x, y, z + 10.)
            self._do_job()
        else:
            self.beam.set_sy(.1)


class Job:

    def __init__(self, primitives, worker_type, next_jobs):

        self.primitives = primitives
        self.worker_type = worker_type
        self.next_jobs = {}
        self.is_assigned = False

        for next_job in next_jobs:
            self.next_jobs[next_job["delay"]] = next_job["index"]

        self.parts_done = 0

    def __bool__(self):

        return True if self.primitives else False

    def __len__(self):

        return len(self.primitives)

    @property
    def next_job_index(self):

        return self.next_jobs.get(self.parts_done, -1)

    def notify_part_done(self):

        self.parts_done += 1
        self.primitives.pop(0)

    def generate_part(self, vertex_data):

        if not self.primitives:
            return

        prim = self.primitives[0]

        return Part(self, vertex_data, prim)


class Part:

    def __init__(self, job, vertex_data, primitive):

        self.job = job
        geom = Geom(vertex_data)
        geom.add_primitive(primitive)
        self.primitive = primitive
        node = GeomNode("part")
        node.add_geom(geom)
        self.model = NodePath(node)
        self.model.set_transparency(TransparencyAttrib.M_alpha)
        self.model.set_color(1., 1., 0., 1.)
        self.model.set_alpha_scale(0.)
        p_min, p_max = self.model.get_tight_bounds()
        self.center = p_min + (p_max - p_min) * .5

    def destroy(self):

        self.model.detach_node()
        self.model = None
        self.job.notify_part_done()
        self.job = None

    def solidify(self, task, duration, finalizer):

        self.model.set_alpha_scale(task.time / duration)

        if task.time < duration:
            return task.cont

        finalizer(self.primitive)
        self.destroy()


class Demo:

    def __init__(self):

        base.disableMouse()

        # set up a light source
        p_light = PointLight("point_light")
        p_light.set_color((1., 1., 1., 1.))
        self.light = base.camera.attach_new_node(p_light)
        self.light.set_pos(5., -100., 7.)
        base.render.set_light(self.light)

        # the `starship.bam` model needs to be created using the `create_starship.py`
        # script in the `starship` folder
        self.model = base.loader.load_model("models/starship.bam")
        self.model.reparent_to(base.render)

        p_min, p_max = self.model.get_tight_bounds()
        ship_size = (p_max - p_min).length()
        self.cam_dist = ship_size
        self.cam_heading = 180.
        self.cam_target = base.render.attach_new_node("cam_target")
        x, y, z = self.model.get_pos()
        self.cam_target.set_pos(x, y, 10.)
        self.cam_target.set_h(self.cam_heading)
        base.camera.reparent_to(self.cam_target)
        base.camera.set_y(-self.cam_dist)

        beam = create_beam()
        beam.set_scale(.1)
        self.workers = {"bot": [], "drone": []}
        self.active_workers = {"bot": [], "drone": []}
        offset = (p_max - p_min).y / 10.

        for i in range(6):
            model = base.loader.load_model("models/builder_bot.gltf")
            model.reparent_to(base.render)
            model.set_pos(0., p_max.y - offset * i, 0.)
            bot = WorkerBot(model, beam)
            self.workers["bot"].append(bot)
            model = base.loader.load_model("models/builder_copter.fbx")
            model.reparent_to(base.render)
            model.set_pos(0., p_max.y - offset * i, 20.)
            drone = WorkerDrone(model, beam)
            self.workers["drone"].append(drone)

        bounds = self.model.node().get_bounds()
        geom = self.model.node().modify_geom(0)
        self.vertex_data = geom.get_vertex_data()
        new_prim = GeomTriangles(GeomEnums.UH_static)
        new_prim.set_index_type(GeomEnums.NT_uint32)

        primitives = [prim for prim in geom.primitives]

        # Divide the hull into (predefined) sections.
        # Each section will be generated with one bot for the bottom half and
        # one drone for the upper half.

        self.job_schedule = [
            # 0
            {
                "part_count": 1,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 1, "delay": 1}
                ]
            },
            # 1
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 3, "delay": 2},
                    {"index": 2, "delay": 5}
                ]
            },
            # 2
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 3
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 5, "delay": 2},
                    {"index": 4, "delay": 5}
                ]
            },
            # 4
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 5
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 7, "delay": 2},
                    {"index": 6, "delay": 5}
                ]
            },
            # 6
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 7
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 9, "delay": 2},
                    {"index": 8, "delay": 5}
                ]
            },
            # 8
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 9
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 11, "delay": 2},
                    {"index": 10, "delay": 5}
                ]
            },
            # 10
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 11
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 13, "delay": 2},
                    {"index": 12, "delay": 5}
                ]
            },
            # 12
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },  
            # 13
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 15, "delay": 2},
                    {"index": 14, "delay": 5}
                ]
            },
            # 14
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 15
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 17, "delay": 2},
                    {"index": 16, "delay": 5}
                ]
            },
            # 16
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 17
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 19, "delay": 2},
                    {"index": 18, "delay": 5}
                ]
            },
            # 18
            {
                "part_count": 2,
                "worker_type": "drone",
                "next_jobs": []
            },
            # 19
            {
                "part_count": 5,
                "worker_type": "bot",
                "next_jobs": [
                    {"index": 20, "delay": 5}
                ]
            },
            # 20
            {
                "part_count": 5,
                "worker_type": "drone",
                "next_jobs": []
            },
        ]
        self.jobs = []

        for job_data in self.job_schedule:
            part_count = job_data["part_count"]
            job_data_ = job_data.copy()
            del job_data_["part_count"]
            job = Job(primitives[:part_count], **job_data_)
            self.jobs.append(job)
            del primitives[:part_count]

        # prune any invalid jobs
        self.jobs = [j for j in self.jobs if j]

        job = self.jobs[0]
        worker = self.workers[job.worker_type].pop(0)
        self.active_workers[job.worker_type].append(worker)

        geom.clear_primitives()
        geom.add_primitive(new_prim)
        self.model.node().set_bounds(bounds)
        self.model.node().set_final(True)
        base.task_mgr.add(self.__move_camera, "move_camera")
        task = lambda t: self.__check_job(t, job, worker)
        base.task_mgr.add(task, "check_job")
        worker.start_job(job, self.vertex_data, self.__add_primitive)
        job.is_assigned = True

    def __move_camera(self, task):

        self.cam_heading -= 1.75 * globalClock.get_dt()
        self.cam_target.set_h(self.cam_heading)

        return task.cont

    def __add_primitive(self, prim):

        prim_array = prim.get_vertices()
        prim_view = memoryview(prim_array).cast("B").cast("I")
        geom = self.model.node().modify_geom(0)
        new_prim = geom.modify_primitive(0)
        new_prim_array = new_prim.modify_vertices()
        old_size = new_prim_array.get_num_rows()
        new_prim_array.set_num_rows(old_size + len(prim_view))
        new_prim_view = memoryview(new_prim_array).cast("B").cast("I")
        new_prim_view[old_size:] = prim_view[:]

    def __check_job(self, task, job, worker):

        next_job_index = job.next_job_index

        if next_job_index > 0:

            next_job = self.jobs[next_job_index]

            if not next_job.is_assigned:
                next_worker = self.workers[next_job.worker_type].pop(0)
                self.active_workers[next_job.worker_type].append(next_worker)
                next_worker.start_job(next_job, self.vertex_data, self.__add_primitive)
                next_job.is_assigned = True
                next_check = lambda task: self.__check_job(task, next_job, next_worker)
                base.task_mgr.add(next_check, "check_job")

        if job:
            return task.cont

        self.active_workers[worker.type].remove(worker)
        self.workers[worker.type].insert(0, worker)


Demo()
base.run()

