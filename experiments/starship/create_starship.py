#!/usr/bin/env python

from panda3d.core import *
import os
import array


loader = Loader.get_global_ptr()
loader_options = LoaderOptions(LoaderOptions.LF_no_cache)

models = []
model_names = []

original_format = GeomVertexFormat.get_v3n3t2()

# define custom vertex format with float color column
vertex_format = GeomVertexFormat()
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.get_vertex(), 3, GeomEnums.NT_float32, GeomEnums.C_point)
array_format.add_column(InternalName.get_normal(), 3, GeomEnums.NT_float32, GeomEnums.C_normal)
array_format.add_column(InternalName.get_texcoord(), 2, GeomEnums.NT_float32, GeomEnums.C_texcoord)
array_format.add_column(InternalName.get_color(), 4, GeomEnums.NT_float32, GeomEnums.C_color)
vertex_format.add_array(array_format)
float_color_format = GeomVertexFormat.register_format(vertex_format)

# define custom vertex format with a separate int color column
vertex_format = GeomVertexFormat()
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.get_vertex(), 3, GeomEnums.NT_float32, GeomEnums.C_point)
array_format.add_column(InternalName.get_normal(), 3, GeomEnums.NT_float32, GeomEnums.C_normal)
array_format.add_column(InternalName.get_texcoord(), 2, GeomEnums.NT_float32, GeomEnums.C_texcoord)
vertex_format.add_array(array_format)
array_format = GeomVertexArrayFormat()
array_format.add_column(InternalName.get_color(), 4, GeomEnums.NT_uint8, GeomEnums.C_color)
vertex_format.add_array(array_format)
int_color_format = GeomVertexFormat.register_format(vertex_format)

# collect all model names
for name in os.listdir("models"):
    if os.path.splitext(name)[1].lower() in (".bam", ".egg", ".fbx", ".gltf"):
        model_names.append(name)

# load all models
for name in model_names:
    n = Filename.from_os_specific(name)
    print("name:", name)
    model = NodePath(loader.load_sync(f"models/{name}", loader_options))
    for node in model.find_all_matches("**/+GeomNode"):
        node.node().modify_geom(0).modify_vertex_data().format = float_color_format
    model.flatten_strong()  # bake the transforms into the vertices
    for node in model.find_all_matches("**/+GeomNode"):
        models.append(node)

tmp_data_views = []
tmp_prim_views = []
sorted_indices = []
vert_count = 0
prim_vert_count = 0

# process all models
for model in models:

    geom = model.node().modify_geom(0)
    v_data = geom.get_vertex_data()
    tmp_v_data = GeomVertexData(v_data)
    tmp_v_data.format = float_color_format
    data_size = tmp_v_data.get_num_rows()
    tmp_data_view = memoryview(tmp_v_data.arrays[0]).cast("B").cast("f")
    tmp_data_views.append(tmp_data_view)
    tmp_v_data.format = int_color_format
    color_array = tmp_v_data.arrays[1]
    color_view = memoryview(color_array).cast("B")
    prim = geom.modify_primitive(0)
    prim.set_index_type(GeomEnums.NT_uint32)
    prim_size = prim.get_num_vertices()
    prim.offset_vertices(vert_count, 0, prim_size)
    prim_view = memoryview(prim.get_vertices()).cast("B").cast("I")
    tmp_prim_views.append(prim_view)

    for j, color in enumerate(color_view[i:i+4] for i in range(0, len(color_view), 4)):
        r, g, b, a = color
        sort = r << 16 | g << 8 | b
        sorted_indices.append((sort, vert_count + j))

    vert_count += data_size
    prim_vert_count += prim_size

sorted_indices.sort()
sort_values = [i[0] for i in sorted_indices]
sorted_indices = [i[1] for i in sorted_indices]

new_data = GeomVertexData("data", float_color_format, GeomEnums.UH_static)
data_array = new_data.modify_array(0)
data_array.set_num_rows(vert_count)
new_data_view = memoryview(data_array).cast("B").cast("f")
start = 0

for tmp_data_view in tmp_data_views:
    end = start + len(tmp_data_view)
    new_data_view[start:end] = tmp_data_view
    start = end

new_data.format = original_format

tmp_prim = GeomTriangles(GeomEnums.UH_static)
tmp_prim.set_index_type(GeomEnums.NT_uint32)
prim_array = tmp_prim.modify_vertices()
prim_array.set_num_rows(prim_vert_count)
prim_view = memoryview(prim_array).cast("B").cast("I")
start = 0

for tmp_prim_view in tmp_prim_views:
    end = start + len(tmp_prim_view)
    prim_view[start:end] = tmp_prim_view
    start = end

sorted_tris = []

for tri in (prim_view[i:i+3] for i in range(0, len(prim_view), 3)):
    tri_indices = [sorted_indices.index(i) for i in tri]
    sorted_tris.append((min(tri_indices), tri.tolist()))

sorted_tris.sort(reverse=True)
index, tri = sorted_tris.pop()
sort_val = sort_values[index]
tris = [tri]
tris_by_sort = [tris]

while sorted_tris:

    index, tri = sorted_tris.pop()
    next_sort_val = sort_values[index]

    if next_sort_val == sort_val:
        tris.append(tri)
    else:
        tris = [tri]
        tris_by_sort.append(tris)
        sort_val = next_sort_val

geom = Geom(new_data)

for tris in tris_by_sort:
    new_prim = GeomTriangles(GeomEnums.UH_static)
    new_prim.set_index_type(GeomEnums.NT_uint32)
    prim_array = new_prim.modify_vertices()
    tri_rows = sum(tris, [])
    prim_array.set_num_rows(len(tri_rows))
    new_prim_view = memoryview(prim_array).cast("B").cast("I")
    new_prim_view[:] = array.array("I", tri_rows)
    geom.add_primitive(new_prim)

geom_node = GeomNode("starship")
geom_node.add_geom(geom)
NodePath(geom_node).write_bam_file("../models/starship.bam")
