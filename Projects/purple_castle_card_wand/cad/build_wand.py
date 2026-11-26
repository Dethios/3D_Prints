"""Build the R2 castle wand in front XY, millimeters. Assembly Z points forward."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import trimesh
from shapely import set_precision
from shapely.geometry import LineString, Point, Polygon, box, shape

CAD = Path(__file__).resolve().parent
ART = CAD.parent / "art/R2/castle_profiles.json"
DONOR = CAD.parents[1] / "minnie_ticket_wand/asa_cad/minnie_card_wand.step"
ART_HASH = "157e4526ce2e8a31cf1bcfd0d903d3c1fd56db4d6431e11811acd003a2974cfa"
DONOR_HASH = "fd40571d938553f20a34d1777a30869eaa36b0a24a456f3d2d79b8a8a344b86d"
COLORS = {"purple": "#8343a4", "gold": "#f4be4e", "cream": "#ffefd5", "blue": "#55a6de", "pink": "#e75d91"}
FLOOR = 4.6
BOND = 7.4
FACE = 9.8
BOW_BASE = 13.2
BOW_MOUNTS = [(-20, -53), (20, -53)]
REGISTERS = [(-36, 22), (33, 24)]
PIVOT = (16, 16)
OPEN = -80
ORIGIN = (0, 0, 0)
YAXIS = (0, 1, 0)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_art():
    if digest(ART) != ART_HASH or digest(DONOR) != DONOR_HASH:
        raise ValueError("Artwork or source STEP revision mismatch")
    return json.loads(ART.read_text())


def clean2(geom):
    return set_precision(geom, 0.001)


def ring(coords, z):
    return cq.Wire.makePolygon([cq.Vector(x, y, z) for x, y in list(coords)[:-1]], close=True)


def polygons(geom):
    if geom.geom_type == "Polygon":
        if geom.area > 0.003:
            yield geom
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from polygons(part)


def prism(geom, lo, hi):
    solids = []
    for p in polygons(geom):
        solids.append(cq.Solid.extrudeLinear(ring(p.exterior.coords, lo),
                    [ring(h.coords, lo) for h in p.interiors], (0, 0, hi-lo)))
    if len(solids) == 1:
        return solids[0]
    return cq.Compound.makeCompound(solids)


def rect(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1-x0, y1-y0, z1-z0, (x0,y0,z0))


def circle(x,y,r,lo,hi):
    return cq.Solid.makeCylinder(r, hi-lo, (x,y,lo))


def tube(r,lo,hi):
    return cq.Solid.makeCylinder(r, hi-lo, (0,lo,0), YAXIS)


def combine(bodies):
    return bodies[0].fuse(*bodies[1:]).clean() if len(bodies)>1 else bodies[0]


def relief(packet, part, datum):
    """Project the height-winning region at each XY point down to solid backing."""
    features = [(i,f) for i,f in enumerate(packet["features"]) if f["part"] == part]
    covered = Polygon()
    by_color = {}
    for _, f in sorted(features, key=lambda it:(it[1]["relief_mm"],it[0]), reverse=True):
        label = f["id"]
        g = clean2(shape(f["geometry"]))
        visible = g.difference(covered)
        covered = clean2(covered.union(g))
        height = f["relief_mm"]
        if height == 0 or visible.is_empty:
            continue
        if part == "head":
            for x,y in BOW_MOUNTS:
                visible = visible.difference(Point(x,y).buffer(3.65,quad_segs=24))
        body = prism(visible, datum, datum+height)
        by_color.setdefault(f["color"], []).extend(body.Solids())
    return by_color


def art_parts(packet):
    head = clean2(shape(packet["footprints"]["head"]["geometry"]))
    colors = relief(packet,"head",FACE)
    base = prism(head, BOND, FACE)
    for x,y in REGISTERS:
        base = base.cut(circle(x,y,1.77,BOND-.1,BOND+1.52))
    for x,y in BOW_MOUNTS:
        pad = circle(x,y,3.54,FACE-.12,BOW_BASE)
        key = cq.Solid.makeCone(1.40,1.26,1.2,(x,y,BOW_BASE))
        base = base.fuse(pad,key)
    colors["purple"].append(base)
    result = {"head_"+color:combine(parts) for color,parts in colors.items()}
    bow_g = clean2(shape(packet["footprints"]["bow"]["geometry"]))
    backing = prism(bow_g,BOW_BASE,BOW_BASE+1.8)
    bow_relief = relief(packet,"bow",BOW_BASE+1.8)
    bow = combine([backing]+bow_relief["pink"])
    for x,y in BOW_MOUNTS:
        bow = bow.cut(circle(x,y,1.65,BOW_BASE-.1,BOW_BASE+1.45))
    result["bow_pink"] = bow.clean()
    return result


def extract_thread():
    donor = sorted(cq.importers.importStep(str(DONOR)).solids().vals(),key=lambda s:s.Volume(),reverse=True)
    source = tube(7.02,-69.1,-48.5)
    annulus = tube(6,-69,-48.5).cut(tube(5.06,-70,-48))
    female = combine([donor[0].intersect(source),donor[1].intersect(source),annulus])
    male = donor[2].intersect(rect(-12,12,-72,-48.5,-12,12)).clean()
    return female, male


def rear_to_world(part):
    # Local d points out of the back. X and Y stay in artwork registration.
    return part.mirror("XY").translate((0,0,FLOOR))


def rounded_box(x0,y0,x1,y1,r):
    return box(x0+r,y0+r,x1-r,y1-r).buffer(r,quad_segs=12)


def turn(x,y,angle):
    a = math.radians(angle)
    dx,dy = x-PIVOT[0], y-PIVOT[1]
    return (PIVOT[0]+dx*math.cos(a)-dy*math.sin(a),
            PIVOT[1]+dx*math.sin(a)+dy*math.cos(a))


def mechanism(packet, female):
    head = clean2(shape(packet["footprints"]["head"]["geometry"]))
    # Main deck with 2.80 mm solid card floor and flat bed/bond plane.
    pocket = rounded_box(-43.30,-43.25,43.30,12.25,3.25)
    scoop = Point(0,12.25).buffer(8,quad_segs=48)
    plate = prism(head,FLOOR-BOND,2.30)
    plate = plate.cut(prism(pocket,-.00001,4),prism(scoop,-1.90,4))
    # Narrow lower toes each cantilever 2.19 mm over the bottom of the pocket.
    for x in (-26,26):
        tab = prism(rounded_box(x-5,-45.55,x+5,-41.06,0.8),2.30,3.75)
        plate = plate.fuse(tab)
    # Bonded pin has an indexing shoulder stop; pilot ends 1.5 mm before glue face.
    plate = plate.cut(circle(*PIVOT,1.83,-1.30,2.45))
    # Keeper spring noses seat in either of two shallow stations on the deck.
    closed_nose = (16,26.1)
    for x,y in (closed_nose, turn(*closed_nose,OPEN)):
        seat = cq.Solid.makeCone(.73,1.55,.56,(x,y,1.75))
        plate = plate.cut(seat)
    # Raised stops on either side of the permitted 80-degree sector.
    for x,y in [(12.80,24.4),(24.36,14.34)]:
        plate = plate.fuse(circle(x,y,1.16,2.28,3.80))
    for x,y in REGISTERS:
        plate = plate.cut(circle(x,y,1.77,FLOOR-BOND-.1,FLOOR-BOND+1.75))
    plate = rear_to_world(plate)
    # Sleeve interfaces the original cuff only through the donor thread.
    # A broad, flat-fronted web joins the full sleeve to the back of the star.
    hub = tube(9.7,-58.95,-45.25).intersect(rect(-12,12,-59,-45,-10,BOND))
    hub = hub.cut(tube(5.99,-70,-48.47))
    web = prism(Polygon([(-7.1,-58.95),(7.1,-58.95),(12.8,-48.2),
                         (15.6,-44.8),(-15.6,-44.8),(-12.8,-48.2)]),0.2,BOND)
    web = web.cut(tube(5.99,-70,-48.47))
    plate = plate.cut(tube(5.99,-70,-48.47)).fuse(female,hub,web).clean()
    # Rigid hub and tongue, narrow flexure to a manually lifted finger pad.
    arm_g = LineString([(16,12.2),(16,16)]).buffer(2.55,quad_segs=24)
    hub_g = Point(*PIVOT).buffer(3.25,quad_segs=28)
    flex_g = LineString([(16,17.6),(16,26.1)]).buffer(1.54,quad_segs=20)
    pad_g = Point(*closed_nose).buffer(2.35,quad_segs=24)
    keeper = prism(arm_g.union(hub_g),2.52,4.30)
    keeper = keeper.fuse(prism(flex_g,3.28,4.30),prism(pad_g,2.52,4.30))
    keeper = keeper.fuse(cq.Solid.makeCone(.68,1.39,.65,(16,26.1,1.88)))
    keeper = keeper.cut(circle(*PIVOT,2.45,1.7,4.40)).clean()
    # Pin prints head-down. Solvent/cement only at the blind end of its stem.
    pin = combine([circle(*PIVOT,1.67,-1.05,2.31),circle(*PIVOT,2.15,2.30,4.56),
                   circle(*PIVOT,3.14,4.55,5.82)])
    rear = {"rear_purple":plate,"keeper_purple":rear_to_world(keeper),
            "pivot_pin_purple":rear_to_world(pin)}
    for i,(x,y) in enumerate(REGISTERS):
        rear["shell_key_"+str(i+1)+"_purple"]=circle(x,y,1.57,BOND-1.61,BOND+1.40)
    return rear


def section(y, radius, depth):
    # Elliptical grip with left/right symmetry and a broad rear printing chord.
    return cq.Wire.makeEllipse(radius,depth,(0,y,0),(0,1,0),(1,0,0))


def handle(male):
    # Stations follow the R2 band and grip extents. Gold sleeves surround an
    # unbroken purple core. Loft caps between stations are deliberately ruled.
    stations = [
        (-302.57, .85,.85),(-302,3.7,2.6),(-300.3,6.5,5),(-297.2,9.2,7.5),
        (-293,11.0,9.0),(-288,11.85,9.45),(-284.56,11.91,9.45),
        (-282.9,14.8,10.05),(-281.6,15.48,10.12),(-277.0,15.48,10.12),
        (-275.2,14.3,9.9),(-274.17,11.92,9.45),(-121,11.65,9.4),
        (-107.03,11.7,9.45),(-105.0,13.70,9.90),(-100.9,13.74,10.0),
        (-98.8,12.28,9.60),(-97.3,14.24,10.08),(-92.7,14.30,10.12),
        (-90.29,12.75,9.65),(-87,12.5,9.4),(-82,12.35,9.15),
        (-76,10.1,8.45),(-73,8.5,8.00),(-71.4,7.88,7.86),(-69.45,7.8,7.8)]
    grip = cq.Solid.makeLoft([section(*station) for station in stations],ruled=True)
    grip = grip.intersect(rect(-20,20,-305,-68,-7.8,20))
    # Preserve both original mating surfaces and the cuff rim through the
    # initial twist. Only the donor grip below its collar overlaps the loft.
    complete = combine([grip,male])
    bands = [(-284.56,-274.17),(-107.03,-100.0),(-98.8,-90.29)]
    outer = []
    for lo,hi in bands:
        band = complete.intersect(rect(-18,18,lo,hi,-15,15))
        outer.append(band.cut(tube(7.05,lo-.02,hi+.02)))
    gold = combine(outer)
    return {"handle_purple":complete.cut(gold).clean(),"handle_gold":gold}


def save_stl(body,path):
    cq.exporters.export(body,str(path),tolerance=.028,angularTolerance=.075)
    mesh = trimesh.load_mesh(path)
    f = mesh.faces
    keep = (f[:,0]!=f[:,1]) & (f[:,0]!=f[:,2]) & (f[:,1]!=f[:,2])
    if not keep.all():
        mesh.update_faces(keep)
        mesh.remove_unreferenced_vertices()
        mesh.export(path)
    return mesh


def save(parts,out):
    (out/"print_parts").mkdir(parents=True,exist_ok=True)
    assembly = cq.Assembly(name="purple_castle_card_wand_R2")
    report = {}
    for name,body in parts.items():
        color = name.split("_")[-1]
        assert body.isValid(), f"Invalid CAD {name}"
        path = out/"print_parts"/(name+".stl")
        mesh = save_stl(body,path)
        discrete = mesh.split(only_watertight=False)
        info = {"sha256":digest(path),"bbox_mm":mesh.bounds.round(4).tolist(),
                "cad_solids":len(body.Solids()),"mesh_shells":len(discrete),
                "watertight":bool(mesh.is_watertight),"winding_consistent":bool(mesh.is_winding_consistent),
                "positive_volume":all(s.volume>0 for s in discrete)}
        print(name,info,flush=True)
        report[name] = info
        assembly.add(body,name=name,color=cq.Color(COLORS[color]))
    assembly.save(str(out/"purple_castle_card_wand.step"))
    return report


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--out",type=Path,default=CAD)
    arg.add_argument("--only",choices=["art","mechanism","handle"])
    args=arg.parse_args()
    packet=load_art()
    parts={}
    if args.only in (None,"art"):
        print("Building face and bow",flush=True)
        parts.update(art_parts(packet))
    if args.only in (None,"mechanism","handle"):
        female,male=extract_thread()
        if args.only in (None,"mechanism"):
            print("Building rear and keeper",flush=True)
            parts.update(mechanism(packet,female))
        if args.only in (None,"handle"):
            print("Building grip",flush=True)
            parts.update(handle(male))
    report=save(parts,args.out)
    (args.out/"exports.json").write_text(json.dumps(report,indent=2)+"\n")
    if args.only is None:
        coupon = parts["rear_purple"].intersect(rect(-46.6,46.6,-47,31,-20,12))
        weight_cut = prism(rounded_box(-38,-38,38,6,3),-12,12)
        coupon = coupon.cut(weight_cut).clean()
        fit = args.out/"fit_coupon"
        fit.mkdir(exist_ok=True)
        save_stl(coupon,fit/"rear_card_frame_purple.stl")
        socket = parts["rear_purple"].intersect(rect(-12,12,-70,-45,-12,9))
        stud = parts["handle_purple"].intersect(rect(-15,15,-85,-48,-12,12))
        save_stl(socket,fit/"socket_purple.stl")
        save_stl(stud,fit/"grip_stub_purple.stl")

if __name__ == "__main__":
    main()
