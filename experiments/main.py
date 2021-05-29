from direct.showbase.ShowBase import ShowBase
from panda3d.core import *
from random import random
import array
import gltf


load_prc_file_data("", "sync-video #f")


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

    idle_units = {"bot": [], "drone": []}

    def __init__(self, worker_type, model, beam):

        self.type = worker_type
        self.model = model
        self.beam = beam.copy_to(self.model)
        self.ready = False
        self.idle_units[worker_type].append(self)

    def do_job(self, job, finalizer, start=False):

        part = job.generate_part()

        def do_job():

            dist = (part.center - self.beam.get_pos(base.render)).length()
            self.beam.set_sy(dist)
            self.beam.look_at(base.render, part.center)
            part.model.reparent_to(base.render)
            solidify_task = lambda task: part.solidify(task, 1.5, finalizer)
            base.task_mgr.add(solidify_task, "solidify")
            deactivation_task = lambda task: self.set_part(None)
            base.task_mgr.add(deactivation_task, "deactivate_beam", delay=1.5)

            def move_to_elevator(task):

                elevator = self.get_nearest_elevator(self.model.get_y())

                if elevator.ready:
                    pos = elevator.model.get_pos()
                    self.target_point = pos + (self.model.get_pos() - pos).normalized() * .8875
                    target_vec = self.target_point - self.model.get_pos()
                    self.start_dist = target_vec.length()
                    base.task_mgr.add(self.move, "move_bot")
                    self._do_job = lambda: elevator.add_request(lambda: elevator.lower_bot(self))
                    elevator.ready = False
#                    print("Job done, returning!")
                    return

                return task.cont

            if job:
                delay = 1.6 + random()
                continue_job = lambda task: self.do_job(job, finalizer)
                base.task_mgr.add(continue_job, "continue_job", delay=delay)
            elif self.type == "bot":
                elevator = self.get_nearest_elevator(self.model.get_y())
                elevator.add_request(lambda: base.task_mgr.add(elevator.open_iris, "open_iris"))
                delay = 1.6 + random()
                self.final_task = base.task_mgr.add(move_to_elevator, "move_to_elevator", delay=delay)

        self._do_job = do_job

        if start and self.type == "bot":
            self.start_job = lambda: self.set_part(part)
            elevator = self.get_nearest_elevator(part.center.y)
            elevator.add_request(lambda: elevator.raise_bot(self))
        else:
            self.set_part(part)

    def get_nearest_elevator(self, start_y):

        shortest_dist = 1000000.

        for elevator in Elevator.instances:

            dist = abs(elevator.start_y - start_y)

            if dist < shortest_dist:
                shortest_dist = dist
                nearest_elevator = elevator

        return nearest_elevator


class WorkerBot(Worker):

    def __init__(self, model, beam):

        Worker.__init__(self, "bot", model, beam)

        self.beam.set_pos(0., 1.325, 1.92)
        self.beam.set_sy(.1)
        self.turn_speed = 300.
        self.accel = 15.
        self.speed = 0.
        self.speed_max = 5.
        self.speed_vec = Vec3.forward()
        self.target_point = None
        self._do_job = lambda: None

    def set_part(self, part):

        if part:
            x, y, z = part.center
            self.target_point = Point3(x, y, 0.)
            target_vec = self.target_point - self.model.get_pos()
            self.start_dist = target_vec.length()
            base.task_mgr.add(self.move, "move_bot")
        else:
            self.beam.set_sy(.1)

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

        # accelerate to normal speed
        self.speed = min(self.speed_max, self.speed + self.accel * dt)

        target_vec = self.target_point - pos
        dist = target_vec.length()

        if dist <= self.speed * dt:
            self.speed = 0.
            self._do_job()
            self._do_job = lambda: None
            self.target_point = None

            return task.done

        return task.cont


class WorkerDrone(Worker):

    def __init__(self, model, beam):

        Worker.__init__(self, "drone", model, beam)

        self.beam.set_sy(.1)

    def set_part(self, part):

        if part:
            x, y, z = part.center
            self.model.set_pos(x, y, z + 10.)
            self._do_job()
        else:
            self.beam.set_sy(.1)


class Job:

    def __init__(self, primitives, vertex_data, worker_type, next_jobs):

        self.primitives = primitives
        self.vertex_data = vertex_data
        self.length = len(primitives)
        self.worker_type = worker_type
        self.next_jobs = {}
        self.is_assigned = False

        for next_job in next_jobs:
            self.next_jobs[next_job["delay"]] = next_job["rel_index"]

        self.parts_done = 0

    def __bool__(self):

        return True if self.primitives else False

    def __len__(self):

        return len(self.primitives)

    @property
    def done(self):

        return self.parts_done == self.length

    @property
    def next_job_index(self):

        return self.next_jobs.get(self.parts_done, -1)

    def notify_part_done(self):

        self.parts_done += 1

    def generate_part(self):

        if not self.primitives:
            return

        prim = self.primitives.pop(0)

        return Part(self, self.vertex_data, prim)


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


class Elevator:

    instances = []

    def __init__(self, start_y):

        self.instances.append(self)
        self.model = base.loader.load_model("models/builder_bot_elevator.gltf")
        self.model.reparent_to(base.render)
        self.model.set_y(start_y)
        self.start_y = start_y
        self.ready = False
        self.idle = True
        self.requests = []
        self.bot = None
        self.platform = self.model.find("**/platform")
        # create a node to attach a bot to, such that the latter ends up
        # being centered on the platform
        self.platform_connector = self.platform.attach_new_node("bot_connector")
        self.platform_connector.set_x(-.8875)
        self.platform_connector.set_h(-90.)
        self.platform_z_min = self.platform.get_z()
        self.platform_speed = 5.
        self.blade_angle = 44.8  # controls aperture of shutter
        self.blade_speed = 40.
        self.blades = []

        for blade in self.model.find_all_matches("**/blade.*"):
            blade.set_h(self.blade_angle)
            self.blades.append(blade)

    def raise_platform(self, task):

        dt = globalClock.get_dt()
        z = self.platform.get_z()
        z += self.platform_speed * dt
        r = task.cont

        if z >= 0.:

            z = 0.
            r = task.done

            def set_ready(task=None):

                self.ready = True
                self.idle = True

            if self.bot:
                self.bot.model.wrt_reparent_to(base.render)
                self.bot.start_job()
                self.bot = None
                base.task_mgr.add(set_ready, "set_ready", delay=1.5)
            else:
                set_ready()

        self.platform.set_z(z)

        return r

    def lower_platform(self, task):

        self.ready = False
        self.idle = False
        dt = globalClock.get_dt()
        z = self.platform.get_z()
        z -= self.platform_speed * dt
        r = task.cont

        if z <= self.platform_z_min:
            z = self.platform_z_min
            r = task.done
            base.task_mgr.add(self.close_iris, "close_iris")

        self.platform.set_z(z)

        return r

    def open_iris(self, task):

        self.idle = False
        dt = globalClock.get_dt()
        self.blade_angle -= self.blade_speed * dt
        r = task.cont

        if self.blade_angle <= 0.:
            self.blade_angle = 0.
            r = task.done
            base.task_mgr.add(self.raise_platform, "raise_platform")

        for blade in self.blades:
            blade.set_h(self.blade_angle)

        return r

    def close_iris(self, task):

        dt = globalClock.get_dt()
        self.blade_angle += self.blade_speed * dt
        r = task.cont

        if self.blade_angle >= 44.8:

            self.blade_angle = 44.8
            r = task.done
            self.idle = True

            if self.bot:
                Worker.idle_units[self.bot.type].insert(0, self.bot)
                self.bot.model.detach_node()
                self.bot = None

        for blade in self.blades:
            blade.set_h(self.blade_angle)

        return r

    def raise_bot(self, bot):

        if self.platform.get_z() < 0.:
            self.bot = bot
            bot.model.set_pos_hpr(0., 0., 0., 0., 0., 0.)
            bot.model.reparent_to(self.platform_connector)
            base.task_mgr.add(self.open_iris, "open_iris")
        else:
            self.add_request(lambda: self.raise_bot(bot), index=0)
            request = lambda: base.task_mgr.add(self.lower_platform, "lower_platform")
            self.add_request(request, index=0)

        self.cam_target.reparent_to(self.model)

    def lower_bot(self, bot):

        self.bot = bot
        bot.model.wrt_reparent_to(self.platform_connector)
        base.task_mgr.add(self.lower_platform, "lower_platform")

    def add_request(self, request, index=None):

        if index is None:
            self.requests.append(request)
        else:
            self.requests.insert(index, request)

    def handle_next_request(self):

        if self.idle and self.requests:
            self.requests.pop(0)()

    @classmethod
    def handle_requests(cls, task):

        for inst in cls.instances:
            inst.handle_next_request()

        return task.cont


class Demo:

    def __init__(self):

        base.disableMouse()

        # set up light sources
        p_light = PointLight("point_light")
        p_light.set_color((.5, .5, .5, 1.))
        self.light = base.camera.attach_new_node(p_light)
        self.light.set_pos(5., -100., 7.)
        base.render.set_light(self.light)
        p_light2 = PointLight("point_light2")
        p_light2.set_color((.5, .5, .5, 1.))
        self.light2 = base.render.attach_new_node(p_light2)
        self.light2.set_pos(10., 0., 50.)
        base.render.set_light(self.light2)

        base.set_background_color(0.3, 0.3, 0.3)
        self.setup_elevator_camera()

        for i in range(20):
            elevator = Elevator(-90. + i * 10.)
            elevator.cam_target = self.elevator_cam_target

        base.task_mgr.add(Elevator.handle_requests, "handle_elevator_requests")

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
        offset = (p_max - p_min).y / 10.

        for i in range(6):
            model = base.loader.load_model("models/builder_bot.gltf")
            bot = WorkerBot(model, beam)
            model = base.loader.load_model("models/builder_copter.fbx")
            model.reparent_to(base.render)
            model.set_pos(0., p_max.y - offset * i, 20.)
            drone = WorkerDrone(model, beam)

        bounds = self.model.node().get_bounds()
        geom = self.model.node().modify_geom(0)
        self.vertex_data = geom.get_vertex_data()
        new_prim = GeomTriangles(GeomEnums.UH_static)
        new_prim.set_index_type(GeomEnums.NT_uint32)

        primitives = [prim for prim in geom.primitives]

        self.parse_job_schedule()
        self.jobs = []

        for job_data in self.job_schedule:
            part_count = job_data["part_count"]
            job_data_ = job_data.copy()
            del job_data_["part_count"]
            job = Job(primitives[:part_count], self.vertex_data, **job_data_)
            self.jobs.append(job)
            del primitives[:part_count]

        job = self.jobs[0]
        worker = Worker.idle_units[job.worker_type].pop(0)

        geom.clear_primitives()
        geom.add_primitive(new_prim)
        self.model.node().set_bounds(bounds)
        self.model.node().set_final(True)
        base.task_mgr.add(self.move_camera, "move_camera")
        task = lambda t: self.check_job(t, job, worker)
        base.task_mgr.add(task, "check_job")
        worker.do_job(job, self.add_primitive, start=True)
        job.is_assigned = True

    def parse_job_schedule(self):

        self.job_schedule = []
        read_next_jobs = False

        with open("jobs.txt") as job_file:

            for line in job_file:

                line = line.strip("\n")

                if line.startswith("#"):
                    continue
                elif not line:
                    job_data = {}
                    self.job_schedule.append(job_data)
                    continue
                elif line.startswith("next_jobs"):
                    read_next_jobs = True
                    next_jobs_data = []
                    job_data["next_jobs"] = next_jobs_data
                    continue
                elif not line.startswith(" "):
                    read_next_jobs = False

                prop, val = [x.strip() for x in line.split()]

                if prop == "part_count":
                    val = int(val)

                if read_next_jobs:
                    val = int(val)
                    if prop == "rel_index":
                        next_job_data = {prop: val}
                        next_jobs_data.append(next_job_data)
                    else:
                        next_job_data[prop] = val
                else:
                    job_data[prop] = val

    def move_camera(self, task):

        self.cam_heading -= 1.75 * globalClock.get_dt()
        self.cam_target.set_h(self.cam_heading)

        return task.cont

    def setup_elevator_camera(self):

        self.elevator_display_region = dr = base.win.make_display_region(.05, .45, .05, .45)
        dr.sort = 10
        dr.set_clear_color_active(True)
        dr.set_clear_depth_active(True)
        cam_node = Camera("elevator_cam")
        self.elevator_cam_target = target = base.render.attach_new_node("elevator_cam_target")
        target.set_hpr(120., -30., 0.)
        self.elevator_cam = cam = target.attach_new_node(cam_node)
        cam.set_y(-10.)
        dr.camera = cam

    def add_primitive(self, prim):

        prim_array = prim.get_vertices()
        prim_view = memoryview(prim_array).cast("B").cast("I")
        geom = self.model.node().modify_geom(0)
        new_prim = geom.modify_primitive(0)
        new_prim_array = new_prim.modify_vertices()
        old_size = new_prim_array.get_num_rows()
        new_prim_array.set_num_rows(old_size + len(prim_view))
        new_prim_view = memoryview(new_prim_array).cast("B").cast("I")
        new_prim_view[old_size:] = prim_view[:]

    def check_job(self, task, job, worker):

        next_job_index = job.next_job_index

        if next_job_index > 0:

            index = self.jobs.index(job)
            next_job = self.jobs[index + next_job_index]

            if not next_job.is_assigned:
                next_worker = Worker.idle_units[next_job.worker_type].pop(0)
                next_worker.do_job(next_job, self.add_primitive, start=True)
                next_job.is_assigned = True
                next_check = lambda task: self.check_job(task, next_job, next_worker)
                base.task_mgr.add(next_check, "check_job")

        if not job.done:
            return task.cont

        if worker.type == "drone":
            Worker.idle_units[worker.type].insert(0, worker)


Demo()
base.run()
