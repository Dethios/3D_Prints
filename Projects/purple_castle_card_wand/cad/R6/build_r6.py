"""Build the 130 mm enclosed, bottom-loading castle wand in front XY millimeters."""
import argparse
import json
import sys
from pathlib import Path

import cadquery as cq
from shapely.geometry import LineString,Polygon,box,shape
from shapely.ops import unary_union

R6=Path(__file__).resolve().parent
CAD=R6.parent
sys.path.insert(0,str(CAD/"R3"))
from build_r3 import base,curved_region

ART=CAD.parent/"art/R6/castle_profiles.json"
MAP=ART.with_name("relief_map.json")
PARENT=CAD/"R5/purple_castle_card_wand_R5.step"
DONOR=base.DONOR
HASHES={ART:"ff1b7d81a01e941be9c393d3b716d585c54cd923cb2af1f61c3441d363779094",
        MAP:"0a73df176ea6965100df1e30e2ab8e6ef9c29b43f17cfa8f05a5e893c9331611",
        PARENT:"26e2623d9702eae12372d11a601f0097114c06a24ef7ae14edc99760a1952c0a",
        DONOR:base.DONOR_HASH}
SHIFT=-9.35
INNER=.90
FACE=2.90
BOW_BASE=6.90
BOW_BACKING=2.30
TOP=27.90
HALFW=27.50


def inputs():
    for path,h in HASHES.items():
        if base.digest(path)!=h:
            raise ValueError(f"Unexpected source revision {path.name}")
    packet=json.loads(ART.read_text())
    specs={name:s for s in json.loads(MAP.read_text())["profiles"] for name in s["ids"]}
    return packet,specs


def outlines(packet):
    star=base.clean2(shape(packet["footprints"]["head"]["geometry"]))
    # Complete both side rails around the rectangular card even where the
    # decorative star's lower notch leaves the central area empty.
    chin=base.rounded_box(-29.65,-59.35,29.65,-32.5,2.15)
    outer=base.clean2(star.union(chin))
    pocket=base.rounded_box(-HALFW,-117,HALFW,TOP,3.35)
    frame_geom=base.clean2(outer.difference(pocket))
    return star,outer,frame_geom


def half_hub(front,star):
    # The new fixed shoulder ends 0.67 mm before the rotating original cuff.
    # Its solid roots flare into the cover skin outside the card clearance.
    half_sign=1 if front else -1
    def wire(y,half_width,height):
        z0=half_sign*INNER
        z1=half_sign*height
        return cq.Wire.makePolygon([cq.Vector(x,y,z) for x,z in
            [(-half_width,z0),(half_width,z0),(half_width,z1),(-half_width,z1)]],close=True)
    web=cq.Solid.makeLoft([wire(y,w,h) for y,w,h in [
        (-68.25,6.65,5.60),(-65,8.8,6.30),(-58,12.2,6.10),
        (-52,15,4.65),(-46.5,16.5,2.90)]],ruled=True)
    hub=base.tube(8.55,-68.25,-57.30)
    clip=base.rect(-30,30,-85,-30,INNER,6.55) if front else base.rect(-30,30,-85,-30,-6.55,-INNER)
    root=web.fuse(hub.intersect(clip))
    if front:
        root=root.cut(base.prism(star,FACE,11))
    return root.cut(base.tube(5.99,-84,-57.82)).clean()


def shells(packet):
    star,outer,frame_geom=outlines(packet)
    donor=sorted(cq.importers.importStep(str(DONOR)).solids().vals(),key=lambda b:b.Volume(),reverse=True)
    extraction=base.tube(7.02,-69.10,-48.50)
    pair=[]
    for front,i in [(True,1),(False,0)]:
        # Widen the slot by shaving the mating inner face of each ORIGINAL
        # half. Their alignment, pitch and axial location stay coaxial.
        side=base.rect(-20,20,-81,-38,INNER,15) if front else base.rect(-20,20,-81,-38,-15,-INNER)
        half=donor[i].intersect(extraction).translate((0,SHIFT,0)).intersect(side)
        plate=base.prism(outer,INNER,FACE) if front else base.prism(outer,-FACE,-INNER)
        plate=plate.cut(base.tube(5.99,-84,-57.82))
        shell=base.combine([plate,half_hub(front,star),half])
        assert shell.isValid() and len(shell.Solids())==1
        pair.append(shell)
    return pair[0],pair[1],base.prism(frame_geom,-INNER,INNER)


def pads_and_ribs(packet):
    source={f["id"]:shape(f["geometry"]) for f in packet["features"]}
    star=source["carrier"]
    lands=[]
    ribs=[]
    for side,sign in [("left",-1),("right",1)]:
        loop=source[side+"-loop"].union(source[side+"-fold-floor"])
        land=loop.intersection(star).buffer(-1.35).simplify(.025,preserve_topology=True)
        rib=LineString([(sign*14,-43),(sign*20,-43)]).buffer(1.05,quad_segs=16)
        assert land.contains(rib.buffer(.20))
        lands.append(base.clean2(land))
        ribs.append(rib)
    return unary_union(lands),ribs


def regions(packet,part):
    rows=[(i,f) for i,f in enumerate(packet["features"]) if f["part"]==part]
    covered=Polygon()
    pad_mask=pads_and_ribs(packet)[0].buffer(.06)
    for _,f in sorted(rows,key=lambda r:(r[1]["relief_mm"],r[0]),reverse=True):
        g=base.clean2(shape(f["geometry"]))
        visible=g.difference(covered)
        covered=base.clean2(covered.union(g))
        if not f["relief_mm"] or visible.is_empty:
            continue
        if part=="head":
            visible=visible.difference(pad_mask)
        yield f,visible


def sculpt(packet,specs,part,datum):
    result={}
    regions_by_feature=list(regions(packet,part))
    house=next((g for f,g in regions_by_feature if f["id"]=="gatehouse"),None)
    for f,g in regions_by_feature:
        if f["id"] in ("left-tower","right-tower") and house is not None:
            g=g.difference(house.buffer(.009,quad_segs=4))
        shapes=[]
        for polygon in base.polygons(g):
            spec=specs.get(f["id"])
            b=curved_region(polygon,datum,spec) if spec else base.prism(polygon,datum,datum+f["relief_mm"])
            shapes.extend(b.Solids())
        if shapes:
            result.setdefault(f["color"],[]).extend(shapes)
    return result


def build(out):
    packet,specs=inputs()
    front,rear,frame=shells(packet)
    lands,ribs=pads_and_ribs(packet)
    purple=base.combine([front,base.prism(lands,FACE-.1,BOW_BASE)]+
                        [base.prism(rib,BOW_BASE-.1,BOW_BASE+.70) for rib in ribs])
    colors=sculpt(packet,specs,"head",FACE)
    # Capture the flags, twinkles and Mickey beneath the face with stepped
    # co-printed roots. A wider foot sits below each narrower central land.
    anchors={"left-flag","high-flag","right-flag","left-star","right-star","mickey"}
    for f,g in regions(packet,"head"):
        if f["id"] in anchors:
            foot=g.buffer(-.24,quad_segs=6).simplify(.018,preserve_topology=True)
            stem=g.buffer(-.56,quad_segs=6).simplify(.018,preserve_topology=True)
            key=base.combine([base.prism(foot,FACE-.80,FACE-.42),
                              base.prism(stem,FACE-.43,FACE+.04)])
            purple=purple.cut(key)
            colors[f["color"]].append(key)
    colors["purple"].append(purple.clean())
    bodies={"head_"+c:base.combine(parts) for c,parts in colors.items()}
    datum=BOW_BASE+BOW_BACKING
    bow_geom=base.clean2(shape(packet["footprints"]["bow"]["geometry"]))
    bow=base.combine([base.prism(bow_geom,BOW_BASE,datum)]+sculpt(packet,specs,"bow",datum)["pink"])
    for rib in ribs:
        bow=bow.cut(base.prism(rib.buffer(.20),BOW_BASE-.10,BOW_BASE+.93))
    bodies.update({"bow_pink":bow.clean(),"rear_purple":rear,"frame_purple":frame})
    previous=cq.Assembly.load(str(PARENT))
    for name in ("handle_purple","handle_gold"):
        bodies[name]=previous.objects[name].obj.translate((0,SHIFT,0))
    assembly=cq.Assembly(name="purple_castle_card_wand_R6")
    directory=out/"print_parts"
    directory.mkdir(parents=True,exist_ok=True)
    for name,body in bodies.items():
        assert body.isValid(),name
        mesh=base.save_stl(body,directory/(name+".stl"))
        print(name,"solids",len(body.Solids()),"watertight",mesh.is_volume,flush=True)
        assert mesh.is_volume,name
        assembly.add(body,name=name,color=cq.Color(base.COLORS[name.split("_")[-1]]))
    assembly.save(str(out/"purple_castle_card_wand_R6.step"))
    # Same lands, slot, positive upper stop, split neck and screw as production.
    # Windows expose the gauge card and reduce material in both skin coupons.
    envelope=base.rect(-30.8,30.8,-81,31.7,-11,11)
    window=base.prism(base.rounded_box(-21,-48,21,19,3.5),-12,12)
    coupon={"front_coupon_purple":front.intersect(envelope).cut(window).clean(),
            "rear_coupon_purple":rear.intersect(envelope).cut(window).clean(),
            "frame_coupon_purple":frame.intersect(envelope).clean(),
            "grip_stub_purple":bodies["handle_purple"].intersect(base.rect(-18,18,-94,-56,-12,12)).clean()}
    dest=out/"fit_coupon"
    dest.mkdir(exist_ok=True)
    for name,body in coupon.items():
        m=base.save_stl(body,dest/(name+".stl"))
        print(name,len(body.Solids()),m.is_volume,flush=True)
        assert body.isValid() and len(body.Solids())==1 and m.is_volume

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--out",type=Path,default=R6)
    build(cli.parse_args().out)
