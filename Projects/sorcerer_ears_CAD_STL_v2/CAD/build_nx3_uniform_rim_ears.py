"""Build NX3 ears with a continuous rim matched to the glue-on base."""

import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import cadquery as cq
import manifold3d as md
import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import unary_union
import trimesh

from build_reference_mounts import (
    BACKING, EAR_ANGLE, RELIEF, ROOT, circular_caps, fit_art, mesh_from_cq, outline,
    planar_solid, save_mesh, save_step,
)
from check_and_position import intersection_volume, transform


NX3 = ROOT / "STL" / "NX3"
VARIANT = "Uniform_Rim"
RIM_RESOLUTION = 32
ART_GAP = 0.8
POCKET_KEEPOUT_RADIUS = 3.13
RIM_RELIEF = 0.35


def rim_profile(blue, adapter):
    # Measure the adapter in the same XY front view used to size the rim.
    width = outline(adapter).intersection(LineString([(0, -100), (0, 100)])).length
    inner = outline(blue).buffer(-width, quad_segs=RIM_RESOLUTION)
    # Re-offset from the inner loop so convex joins have the same width.
    outer = inner.buffer(width, quad_segs=RIM_RESOLUTION)
    rim = outer.difference(inner)
    assert rim.geom_type == "Polygon" and len(rim.interiors) == 1
    return width, inner, rim


def manifold(mesh):
    return md.Manifold(md.Mesh64(mesh.vertices, mesh.faces.astype(np.uint64)))


def printable_mesh(solid):
    # Remove sub-micron boolean slivers before binary STL rounds vertices.
    data = solid.simplify(0.00004).to_mesh64()
    vertices = data.vert_properties[:, :3].astype(np.float32).astype(np.float64)
    mesh = trimesh.Trimesh(vertices, data.tri_verts, process=True)
    # Float32 rounding can collapse isolated triangles from coplanar joins.
    # Keep the watertight solid and require all discarded pieces to have zero volume.
    parts = mesh.split(only_watertight=False, repair=False)
    with np.errstate(divide="ignore", invalid="ignore"):
        volumes = [part.volume for part in parts]
    biggest = int(np.argmax(volumes))
    assert parts[biggest].is_volume
    assert all(abs(volume) < 1e-6 for index, volume in enumerate(volumes) if index != biggest)
    return parts[biggest]


def make_backing(original, mount, adapter, rim, mount_z):
    # Preserve the original part and subtract the adapter and bore keepouts
    # from the added material before joining it to the ear.
    rim_stock = planar_solid(rim, 0, mount_z)
    mesh_keepouts = [adapter]
    step_dir = ROOT / "CAD" / "NX3"
    cad_keepouts = [cq.importers.importStep(str(step_dir / "glue_on_base_SOURCE_GEOMETRY.step")).val()]
    for bore in circular_caps(mount):
        center = np.asarray(bore["center"])
        normal = np.asarray(bore["normal"])
        start = center - 0.02 * normal
        end = center + 5.0 * normal
        mesh_keepouts.append(trimesh.creation.cylinder(
            radius=POCKET_KEEPOUT_RADIUS, segment=[start, end], sections=64,
        ))
        cad_keepouts.append(cq.Solid.makeCylinder(
            POCKET_KEEPOUT_RADIUS, 5.02, cq.Vector(*start), cq.Vector(*normal),
        ))
    guarded_rim = md.Manifold.batch_boolean(
        [manifold(mesh_from_cq(rim_stock)), *map(manifold, mesh_keepouts)],
        md.OpType.Subtract,
    )
    blue = manifold(original) + guarded_rim
    # Keep the analytic STEP stock and use the manifold mesh boolean for STL.
    # The imported faceted STEP has tiny edges that are hard to re-tessellate.
    original_cad = cq.importers.importStep(str(step_dir / "ear_blue_base.step")).val()
    blue_cad = original_cad.fuse(rim_stock.cut(*cad_keepouts)).clean()
    assert len(blue_cad.Solids()) == 1 and blue_cad.isValid()
    assert abs(blue_cad.Volume() - blue.volume()) / blue.volume() < 0.001
    return blue, blue_cad


def width_range(rim):
    outer, inner = rim.exterior, rim.interiors[0]
    widths = [
        outer.distance(inner.interpolate(distance))
        for distance in np.linspace(0, inner.length, 1200)
    ]
    return [float(min(widths)), float(max(widths))]


def verify_geometry(folder, blue, original, mount, adapter, width, rim, variants):
    assert blue.is_volume and len(blue.split()) == 1
    old_caps, new_caps = circular_caps(original), circular_caps(blue)
    assert len(old_caps) == 5
    for old in old_caps:
        new = min(new_caps, key=lambda cap: np.linalg.norm(np.subtract(old["center"], cap["center"])))
        for key in ("center", "normal"):
            assert np.allclose(old[key], new[key], atol=0.005), (key, old, new)
        center, normal = np.asarray(old["center"]), np.asarray(old["normal"])
        probe = trimesh.creation.cylinder(
            radius=3.0, segment=[center + 0.05 * normal, center + 3.05 * normal], sections=96,
        )
        assert abs(intersection_volume(blue, probe) - intersection_volume(original, probe)) < 0.005
    baseline_overlap = intersection_volume(original, adapter)
    blue_overlap = intersection_volume(blue, adapter)
    assert blue_overlap <= baseline_overlap + 0.005, (baseline_overlap, blue_overlap)
    poses = json.loads((ROOT / "CAD" / "assembly_positions.json").read_text())["NX3"]
    center_base = trimesh.load_mesh(
        ROOT.parent / "magnetic_treasure_crab_ears_NX3" / "stl" / "center_hat_glue_base_3_of_5.stl"
    )
    hat = trimesh.load_mesh(
        NX3 / "Center_Hat_3D_Press_Fit_Centered" / "center_hat_3d_assembled.stl"
    )
    posed_base = transform(center_base, poses["center_hat"])
    hat.apply_translation((0, 0, center_base.bounds[1, 2] + 0.15))
    posed_hat = transform(hat, poses["center_hat"])
    placed = []
    for name, data in variants.items():
        ear = trimesh.load_mesh(folder / f"{name}_assembled.stl")
        gold = trimesh.load_mesh(folder / f"{name}_raised_gold.stl")
        flat_gold = trimesh.load_mesh(folder / f"{name}_gold_flat_print.stl")
        assert ear.is_volume and len(ear.split()) == 1, name
        assert gold.is_volume and len(gold.split()) == data["gold_solid_count"], name
        assert flat_gold.is_volume and len(flat_gold.split()) == data["gold_solid_count"], name
        assert all(abs(part.bounds[0, 2]) < 0.001 for part in flat_gold.split()), name
        assert abs(ear.volume - (blue.volume + gold.volume)) < 0.01, name
        missing = trimesh.boolean.difference([mount, ear], engine="manifold")
        assert missing.is_empty or abs(missing.volume) < 0.005, name
        overlap = intersection_volume(ear, adapter)
        assert overlap <= baseline_overlap + 0.005, (name, overlap)
        measured = width_range(outline_rim(gold, rim.area))
        assert np.max(np.abs(np.array(measured) - width)) < 0.025, (name, measured)
        posed = transform(ear, poses[name])
        placed.append(posed)
        hat_overlap = intersection_volume(posed, posed_hat)
        center_base_overlap = intersection_volume(posed, posed_base)
        assert max(hat_overlap, center_base_overlap) < 0.005, (name, hat_overlap, center_base_overlap)
        data.update(
            dimensions_xyz_mm=ear.extents.round(3).tolist(),
            exported_rim_width_range_mm=[round(value, 4) for value in measured],
            center_hat_overlap_mm3=hat_overlap,
            center_base_overlap_mm3=center_base_overlap,
            mating_base_overlap_mm3=overlap,
        )
    pair_overlap = intersection_volume(*placed)
    assert pair_overlap < 0.005
    return {
        "status": "PASS",
        "mount_centerline_face_width_mm": round(width, 4),
        "mating_base_sha256": hashlib.sha256((NX3 / "glue_on_base_SOURCE_GEOMETRY.stl").read_bytes()).hexdigest(),
        "baseline_mating_overlap_mm3": baseline_overlap,
        "five_bores_preserved": True,
        "ear_pair_overlap_mm3": pair_overlap,
        "ears": variants,
        "physical_fit": "Pending",
    }


def outline_rim(gold, rim_area):
    # The rim is the one component that encloses an opening in front view.
    rim = max(gold.split(), key=lambda part: part.bounds[1, 2])
    top = rim.triangles[np.all(np.isclose(rim.triangles[:, :, 2], rim.bounds[1, 2]), axis=1)]
    projection = unary_union([Polygon(face[:, :2]) for face in top])
    assert projection.geom_type == "Polygon" and len(projection.interiors) == 1
    assert abs(projection.area - rim_area) < 0.01
    return projection


def build():
    original = trimesh.load_mesh(NX3 / "ear_blue_base.stl")
    mount = trimesh.load_mesh(NX3 / "mount_test_strip.stl")
    adapter = trimesh.load_mesh(NX3 / "glue_on_base_SOURCE_GEOMETRY.stl")
    width, inner, rim = rim_profile(original, adapter)
    mount_z = float(mount.bounds[1, 2])
    blue, blue_cad = make_backing(original, mount, adapter, rim, mount_z)
    # The rim face stays below the adjacent center-hat adapter at Z=10.4.
    gold_rim = planar_solid(rim, mount_z, RIM_RELIEF)
    artwork = json.loads((ROOT / "CAD" / "artwork.json").read_text())
    safe_field = inner.buffer(-ART_GAP).intersection(box(-60, 15.3, 60, 120))
    variants = {}
    with TemporaryDirectory() as temporary:
        staging = Path(temporary)
        save_mesh(printable_mesh(blue), staging / "ear_blue_base.stl")
        save_step(blue_cad, staging / "ear_blue_base.step")
        for name, key, rotation in (
            ("left_brooms", "brooms", -EAR_ANGLE),
            ("right_mouse", "mouse", EAR_ANGLE),
        ):
            graphic = affinity.rotate(shape(artwork[key]), rotation, origin=(0, 0))
            fitted, placement = fit_art(graphic, safe_field, 0, 38.79776001)
            relief = planar_solid(fitted.simplify(0.025, preserve_topology=True), BACKING, RELIEF)
            gold = cq.Compound.makeCompound([relief, gold_rim])
            gold_mesh = mesh_from_cq(gold)
            # Preserve an installed copy for multipart slicing and space the
            # flat gold pieces apart for a separate, glue-on gold print.
            ring_on_bed = gold_rim.translate((0, 0, -mount_z))
            relief_on_bed = relief.translate((105, 0, -BACKING))
            flat_gold = mesh_from_cq(cq.Compound.makeCompound([ring_on_bed, relief_on_bed]))
            ear = printable_mesh(blue + manifold(gold_mesh))
            save_mesh(gold_mesh, staging / f"{name}_raised_gold.stl")
            save_mesh(flat_gold, staging / f"{name}_gold_flat_print.stl")
            save_mesh(ear, staging / f"{name}_assembled.stl")
            save_step(gold, staging / f"{name}_raised_gold.step")
            save_step(cq.Compound.makeCompound([blue_cad, gold]), staging / f"{name}_layer_assembly.step")
            variants[name] = {"artwork_placement": placement, "gold_solid_count": len(gold.Solids())}
        report = verify_geometry(staging, trimesh.load_mesh(staging / "ear_blue_base.stl"),
                                 original, mount, adapter, width, rim, variants)
        for step in staging.glob("*.step"):
            assert all(solid.isValid() for solid in cq.importers.importStep(str(step)).val().Solids()), step
        cad_dir = ROOT / "CAD" / "NX3" / VARIANT
        for folder, extension in ((cad_dir, "step"), (NX3 / VARIANT, "stl")):
            folder.mkdir(exist_ok=True)
            for path in staging.glob(f"*.{extension}"):
                shutil.copyfile(path, folder / path.name)
        (cad_dir / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    build()
