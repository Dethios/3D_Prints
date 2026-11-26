"""Rebuild the native, flush CW2/Tap hex inlays in the custom CHUBE STEP."""

from collections import defaultdict
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import cadquery as cq
import numpy as np
import trimesh
from PIL import Image, ImageDraw


OUT = Path(__file__).resolve().parent
PROJECT = OUT.parent
ROOT = PROJECT.parent.parent
BODY = PROJECT / "CAD" / "A4T Cowling - Chube Air UHF [cw2-tap].step"
DONOR = (ROOT / "GitHub-Mods" / "A4T" / "CAD" / "Cowlings [Hexagon multi-colour]"
         / "Hex A4T Cowling - Dragon-Rapido UHF [cw2-tap].step")
NAME = "CHUBE Air UHF CW2-Tap - Hexagons"
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PART_NAMES = ("CHUBE cowl", "Outline hexagons", "Filled hexagons")
COLORS = ("#AC253D", "#F5F5F3", "#222326")
TOOLS = (1, 3, 4)  # Prusa extruders are one-based: T0 red, T2 white, T3 black.


def native_art():
    solids = cq.importers.importStep(str(DONOR)).solids().vals()
    labels = re.findall(r"MANIFOLD_SOLID_BREP\('([^']+)'", DONOR.read_text())
    groups = [(1 if label == "outline hexagons" else 2, solid)
              for label, solid in zip(labels, solids, strict=True)
              if label in ("outline hexagons", "solid hexagons")]
    if [sum(group == n for group, _ in groups) for n in (1, 2)] != [2, 8]:
        raise ValueError("Unexpected native artwork groups")
    for _, solid in groups:
        bounds = solid.BoundingBox()
        if abs(bounds.zmin) > 0.00001 or abs(bounds.zmax - 0.4) > 0.00001:
            raise ValueError("Native art registration or thickness changed")
    return groups


def partition(body, artwork):
    # Splitting once makes the boundary of each color a shared CAD face.
    shape = body.split(*(solid for _, solid in artwork))
    solids = sorted(shape.Solids(), key=lambda s: -s.Volume())
    if len(solids) != len(artwork) + 1:
        raise ValueError(f"Unexpected partition count {len(solids)}")
    groups = defaultdict(list)
    groups[0].append(solids[0])
    remaining = solids[1:]
    for group, tool in artwork:
        part = min(remaining, key=lambda s: (s.Center() - tool.Center()).Length)
        if ((part.Center() - tool.Center()).Length > 0.00001
                or abs(part.Volume() - tool.Volume()) > 0.00001):
            raise ValueError("An inlay falls outside the custom cowl")
        groups[group].append(part)
        remaining.remove(part)
    if not shape.isValid() or body.cut(shape).Solids() or shape.cut(body).Solids():
        raise ValueError("CAD symmetric difference contains material")
    shape.mesh(0.006, 0.09)
    return groups


def make_mesh(solid):
    vertices, faces = solid.tessellate(0.006, 0.09)
    vertices = np.round([v.toTuple() for v in vertices], 5)
    unique, indices = np.unique(vertices, axis=0, return_inverse=True)
    mesh = trimesh.Trimesh(vertices=unique, faces=indices[np.asarray(faces)], process=False)
    mesh.update_faces(mesh.nondegenerate_faces(height=1e-10))
    mesh.remove_unreferenced_vertices()
    if not mesh.is_watertight:
        # OCC occasionally omits seam slivers in this imported STEP. Only
        # accept triangular closures of negligible area on the tessellation.
        counts = np.bincount(mesh.edges_unique_inverse)
        boundary = mesh.edges[counts[mesh.edges_unique_inverse] == 1]
        next_point = dict(boundary.tolist())
        triangles = []
        while next_point:
            a, b = next_point.popitem()
            c = next_point.pop(b)
            if next_point.pop(c) != a:
                raise ValueError("Non-triangular mesh seam")
            triangles.append((a, c, b))
        mesh.faces = np.vstack((mesh.faces, triangles))
        patch_area = mesh.area_faces[-len(triangles):].sum()
        print(f"Closed {len(triangles)} mesh seam triangles "
              f"covering {patch_area:.8f} mm2", flush=True)
        if patch_area > 0.05:
            raise ValueError("Excessive seam repair in the tessellation")
    if not mesh.is_volume or not mesh.is_winding_consistent:
        raise ValueError("Generated mesh is open or incorrectly oriented")
    return mesh


def write_model(path, parts):
    ET.register_namespace("", CORE)
    root = ET.Element(f"{{{CORE}}}model", unit="millimeter",
                      attrib={"xmlns:slic3rpe": "http://schemas.slic3r.org/3mf/2017/06"})
    ET.SubElement(root, "metadata", name="slic3rpe:Version3mf").text = "1"
    resources = ET.SubElement(root, "resources")
    colors = ET.SubElement(resources, "basematerials", id="1")
    for name, color in zip(PART_NAMES, COLORS):
        ET.SubElement(colors, "base", name=name, displaycolor=color)
    obj = ET.SubElement(resources, "object", id="2", type="model", name=path.stem,
                        pid="1", pindex="0")
    geom = ET.SubElement(obj, "mesh")
    points = ET.SubElement(geom, "vertices")
    faces = ET.SubElement(geom, "triangles")
    config = ET.Element("config")
    settings = ET.SubElement(config, "object", id="2", instances_count="1")
    ET.SubElement(settings, "metadata", type="object", key="name", value=path.stem)
    first_face = 0
    first_vertex = 0
    for i, (name, mesh) in enumerate(zip(PART_NAMES, parts)):
        for x, y, z in mesh.vertices:
            ET.SubElement(points, "vertex", x=f"{x:.6f}", y=f"{y:.6f}", z=f"{z:.6f}")
        props = {"pid": "1", "p1": str(i)} if i else {}
        for a, b, c in mesh.faces + first_vertex:
            ET.SubElement(faces, "triangle", v1=str(a), v2=str(b), v3=str(c), **props)
        end_face = first_face + len(mesh.faces)
        volume = ET.SubElement(settings, "volume", firstid=str(first_face), lastid=str(end_face - 1))
        for key, value in (("name", name), ("volume_type", "ModelPart"), ("extruder", str(TOOLS[i]))):
            ET.SubElement(volume, "metadata", type="volume", key=key, value=value)
        first_face = end_face
        first_vertex += len(mesh.vertices)
    ET.SubElement(ET.SubElement(root, "build"), "item", objectid="2")
    content_types = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                     '<Default Extension="config" ContentType="application/xml"/>'
                     '</Types>')
    relationships = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Target="/3D/3dmodel.model" Id="model" '
                     'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("3D/3dmodel.model", ET.tostring(root, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/Slic3r_PE_model.config", ET.tostring(config, encoding="utf-8", xml_declaration=True))


def render_front(path):
    """Read the delivered mesh; look from -Z with +X right and +Y down."""
    with zipfile.ZipFile(path) as archive:
        core = ET.fromstring(archive.read("3D/3dmodel.model"))
        settings = ET.fromstring(archive.read("Metadata/Slic3r_PE_model.config"))
    vertices = np.array([[float(v.get(k)) for k in "xyz"]
                         for v in core.findall(".//{*}vertex")])
    indices = np.array([[int(f.get(k)) for k in ("v1", "v2", "v3")]
                        for f in core.findall(".//{*}triangle")])
    palette = np.array([tuple(bytes.fromhex(c[1:])) for c in COLORS])
    part = np.zeros(len(indices), dtype=int)
    for i, volume in enumerate(settings.findall(".//volume")):
        part[int(volume.get("firstid")):int(volume.get("lastid")) + 1] = i
    triangles = vertices[indices]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-20)
    light = np.array([-0.42, -0.34, -0.84])
    intensity = 0.47 + 0.58 * np.clip(normals @ light, 0, 1)
    rgb = np.clip(palette[part] * intensity[:, None], 0, 255).astype(int)
    scale, margin = 26, 90
    xy = vertices[:, :2]
    pixels = np.rint((xy - xy.min(axis=0)) * scale + margin).astype(int)
    image = Image.new("RGB", tuple(pixels.max(axis=0) + margin), "#e0dfde")
    drawing = ImageDraw.Draw(image)
    visible = np.nonzero(normals[:, 2] < -1e-8)[0]
    for i in visible[np.argsort(triangles[visible, :, 2].mean(axis=1))[::-1]]:
        drawing.polygon([tuple(p) for p in pixels[indices[i]]], fill=tuple(rgb[i]))
    image.thumbnail((820, 820), Image.Resampling.LANCZOS)
    image.save(path.with_name(path.stem + " - front.png"))


def build(name, artwork):
    body, = cq.importers.importStep(str(BODY)).solids().vals()
    groups = partition(body, artwork)
    assembly = cq.Assembly(name=name)
    parts = []
    for i, name_part in enumerate(PART_NAMES):
        solids = groups[i]
        assembly.add(cq.Compound.makeCompound(solids), name=name_part, color=cq.Color(COLORS[i]))
        meshes = [make_mesh(solid) for solid in solids]
        mesh = trimesh.util.concatenate(meshes)
        print(f"{name_part}: {len(solids)} solids; CAD {sum(s.Volume() for s in solids):.6f} mm3; "
              f"mesh {mesh.volume:.6f} mm3; {len(mesh.faces)} triangles", flush=True)
        parts.append(mesh)
    write_model(OUT / (name + ".3mf"), parts)
    assembly.export(str(OUT / (name + ".step")))
    render_front(OUT / (name + ".3mf"))


if __name__ == "__main__":
    build(NAME, native_art())
