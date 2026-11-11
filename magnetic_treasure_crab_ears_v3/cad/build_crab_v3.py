"""Image-led treasure crab ears, rear magnet carriers and store-headband saddles.
Units mm; CadQuery 2.7. New version, preserving previous files.
"""
from pathlib import Path
import math,json
import cadquery as cq
import numpy as np
from scipy.interpolate import CubicSpline

ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'cad';STL=ROOT/'stl';PREV=ROOT/'previews'
for p in [CAD,STL,STL/'adapters',PREV]:p.mkdir(exist_ok=True)
FACE=1.8;RELIEF=.6
STALK_WIDTH=6.5;EYE_BASE=3.0
EAR_CY=-5.726;ARC_CY=-122.00625
SEAT_R=84.1448;TOP_R=90.9948;BACK_R=87.24425
BORE_D=6.2;ANGLES=[-.30,-.15,0,.15,.30]
DEFAULT_RADIUS=65;DEFAULT_WIDTH=10;TILT=50
PAD_RADIAL_HEIGHT=6.0
COLORS={'purple':(.19,.035,.34),'violet':(.44,.095,.61),'blue':(.08,.18,.54),
        'gold':(.91,.56,.10),'white':(.95,.92,.80),'black':(.025,.015,.055),
        'band_reference':(.055,.04,.085)}

def cyl(r,h,p=(0,0,0),u=(0,0,1)):
    return cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*u))
def fuse(items):
    a=list(items)
    if not a:raise ValueError('Empty shape list')
    return a[0].fuse(*a[1:]).clean() if len(a)>1 else a[0]
def disk(x,y,r,h,z=0):return cyl(r,h,(x,y,z))
def poly(p,h,z=0):return cq.Workplane('XY').polyline([tuple(v) for v in p]).close().extrude(h).val().translate((0,0,z))
def box(x,y,w,d,h,z=0):return cq.Solid.makeBox(w,d,h,cq.Vector(x,y,z))
def cap(ax,ay,bx,by,r,h,z=0):
    dx,dy=bx-ax,by-ay;l=math.hypot(dx,dy)
    if l<1e-8:return disk(ax,ay,r,h,z)
    nx,ny=-dy/l*r,dx/l*r
    return fuse([disk(ax,ay,r,h,z),disk(bx,by,r,h,z),poly([(ax+nx,ay+ny),(bx+nx,by+ny),(bx-nx,by-ny),(ax-nx,ay-ny)],h,z)])
def ellipse(x,y,rx,ry,rot,h,z=0):
    return cq.Workplane('XY').ellipse(rx,ry).extrude(h).val().rotate((0,0,0),(0,0,1),rot).translate((x,y,z))
def ring(x,y,ro,ri,h,z=0):return disk(x,y,ro,h,z).cut(disk(x,y,ri,h+2,z-1))
def sparkle(x,y,h,z=0):
    pts=[]
    for i in range(8):
        a=math.pi/2+i*math.pi/4;r=11 if i%2==0 else 2.3
        pts.append((x+r*math.cos(a),y+r*math.sin(a)))
    return poly(pts,h,z)
def local(shape,side='left'):
    return shape.rotate((0,0,0),(0,0,1),-TILT if side=='left' else TILT).translate((0,EAR_CY,0))
def ear_limit(h,z=0):
    return disk(0,EAR_CY,50,h,z).cut(disk(0,ARC_CY,SEAT_R,h+2,z-1))
def foot(h,z=0):
    return disk(0,EAR_CY,50,h,z).intersect(disk(0,ARC_CY,TOP_R,h,z)).cut(disk(0,ARC_CY,SEAT_R,h+2,z-1)).clean()
def holes_carrier(shape):
    cuts=[]
    for a in ANGLES:
        u=(math.sin(a),math.cos(a),0);start=82
        cuts.append(cyl(BORE_D/2,BACK_R-start,(start*u[0],ARC_CY+start*u[1],5),u))
    return shape.cut(fuse(cuts)).clean()
PEGS=[(-15,ARC_CY+math.sqrt(88.5**2-15**2)),(15,ARC_CY+math.sqrt(88.5**2-15**2))]
def carrier():
    p=holes_carrier(foot(10))
    p=fuse([p]+[disk(x,y,1.6,.8,10) for x,y in PEGS])
    return p.clean()

# Claw outline traced manually from the supplied image, expressed about the
# left ear's circle center. Rounded closed spline interpolation preserves the
# crescent pincer instead of the previous sideways hand silhouette.
CLAW_PX=np.array([(94,291),(86,273),(81,249),(80,222),(82,190),(91,153),
 (109,119),(137,94),(169,78),(203,70),(235,72),(261,82),(279,94),
 (283,102),(268,105),(251,112),(237,121),(231,132),(221,137),
 (216,149),(205,154),(199,164),(185,174),(184,180),(199,180),
 (216,174),(233,167),(237,168),(232,180),(221,198),(207,214),
 (188,225),(165,232),(145,241),(128,255),(116,274),(108,289)],float)
CLAW=(CLAW_PX-np.array([207,234]))*np.array([50/184,-50/184])
def claw(h,z=0,side='left'):
    p=np.vstack([CLAW,CLAW[0]])
    t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    curve=CubicSpline(t,p,bc_type='periodic')
    points=curve(np.linspace(0,t[-1],170,endpoint=False))
    if side=='right':points[:,0]*=-1
    return poly(points,h,z)

COINS=[(-37,-15,7,3.7,-25),(-42,-25,6,4.2,-55),(-33,-30,7.6,4.3,10),
 (-24,-25,8,4.5,10),(-15,-29,7,4.5,-20),(-5,-31,8,4.2,5),
 (7,-26,7,4.0,15),(20,-22,7,4.1,-5),(29,-16,6,3.8,35),
 (37,-6,6.4,3.5,35),(27,-9,6.7,3.7,8),(38,-23,6.2,3.8,-10),
 (33,-31,7,4.2,-22),(21,-34,7.7,4.1,5),(10,-38,7.2,4.1,-15),
 (-3,-42,8,4.6,-4),(-16,-41,7.1,4.1,6),(-28,-38,7.1,4.2,20),
 (-35,-35,7,4,35),(27,-40,6.7,4,10),(14,-44,7,4.3,5),(0,-47,7,3.7,0),
 (-26,-19,6.8,3.8,-18),(-13,-21,6.6,3.8,12),(0,-23,6.2,3.7,-8),
 (14,-17,6.5,3.6,22),(25,-25,6.4,3.7,-12),(-6,-35,6.7,3.8,10)]
PILE=[(-44,-20),(-35,-14),(-25,-18),(-16,-22),(-7,-20),(5,-18),
      (16,-13),(26,-9),(39,-4),(44,-14),(44,-28),(30,-41),(15,-48),
      (0,-50),(-20,-47),(-38,-36)]
GEM_LEFT=[(3,4.5),(14,-.5),(17,-18.5),(7,-30.5),(-8,-24),(-16,-16),(-14,-4)]
GEM_RIGHT=[(-5,-8),(-15,-12),(-18,-23),(-12,-32),(1,-29),(8,-18),(3,-10)]
def ear_face(side):
    s=1 if side=='left' else -1
    def coinshape(c,h,z=0,shrink=0):
        x,y,rx,ry,r=c
        return ellipse(s*x,y,rx-shrink,ry-shrink,s*r,h,z)
    pile_pts=[(s*x,y) for x,y in PILE]
    pile_base=fuse([poly(pile_pts,FACE)]+[coinshape(c,FACE) for c in COINS])
    claw_base=claw(FACE,side=side)
    gem_pts=GEM_LEFT if side=='left' else GEM_RIGHT
    gem_base=poly(gem_pts,FACE)
    star_base=sparkle(s*27,10,FACE)
    connectors=[cap(s*27,1,s*28,-14,1.65,FACE),cap(s*-29,-15,s*-31,-25,3,FACE)]
    art=fuse([pile_base,claw_base,gem_base,star_base]+connectors)
    body=fuse([ring(0,EAR_CY,50,45.8,FACE),local(art,side),foot(FACE)]).intersect(ear_limit(FACE))
    for x,y in PEGS:body=body.cut(disk(x,y,1.75,.9))
    # Top relief uses only one additional height; grooves sit inside that relief.
    pile_mask=fuse([poly(pile_pts,RELIEF,FACE)]+[coinshape(c,RELIEF,FACE) for c in COINS])
    # All coin tops share the upper relief height. Their 0.2-mm groove floors
    # stay above the lower gold foundation, avoiding coincident cut surfaces.
    coin_heights=[RELIEF for _ in COINS]
    pile=fuse([poly(pile_pts,.2,FACE)]+[coinshape(c,h,FACE) for c,h in zip(COINS,coin_heights)])
    grooves=[]
    for c,h in zip(COINS,coin_heights):
        outer=coinshape(c,.21,FACE+h-.2,.55)
        inner=coinshape(c,.40,FACE+h-.3,1.10)
        grooves.append(outer.cut(inner))
    pile=pile.cut(fuse(grooves))
    gem=poly(gem_pts,RELIEF,FACE)
    # Gold border is a thin inset band; facet lines remain robust at 0.4-mm nozzle.
    center=np.mean(np.array(gem_pts),axis=0)
    inner=[tuple(center+.87*(np.array(p)-center)) for p in gem_pts]
    border=gem.cut(poly(inner,RELIEF+1,FACE-.2))
    if side=='left':
        facet=[((3,4.5),(1,-6)),((1,-6),(-14,-4)),((1,-6),(14,-.5)),
               ((1,-6),(7,-30.5)),((-16,-16),(-4,-12)),((-4,-12),(7,-30.5))]
        fillcolor='violet'
    else:
        facet=[((-5,-8),(-7,-17)),((-7,-17),(-18,-23)),((-7,-17),(3,-10)),
               ((-7,-17),(1,-29)),((-15,-12),(-10,-24)),((-10,-24),(1,-29))]
        fillcolor='blue'
    lines=fuse([cap(*a,*b,.48,RELIEF,FACE) for a,b in facet]).intersect(gem)
    gold_gem=fuse([border,lines]);fill=gem.cut(gold_gem)
    pile=pile.cut(gem)
    ct=claw(RELIEF,FACE,side).cut(pile_mask).cut(gem)
    # Tiny image-like gold speckles are supported inlays in the claw surface.
    dots=[]
    for x,y,r in [(-29,27,.6),(-22,33,.7),(-14,38,.6),(-6,39,.65),
                   (-30,20,.55),(-24,25,.6),(-18,29,.6),(-11,33,.5),
                   (-28,14,.6),(-22,18,.55),(-16,22,.55),(-26,31,.5)]:
        dots.append(disk(s*x,y,r,RELIEF,FACE))
    dots=fuse(dots).intersect(ct)
    ct=ct.cut(dots)
    blue=ct.intersect(ellipse(s*-31,8,19,30,s*-15,RELIEF,FACE))
    violet=ct.cut(blue)
    star_stem=cap(s*27,0,s*28,-10,1.1,RELIEF,FACE)
    gold=fuse([pile,gold_gem,sparkle(s*27,10,RELIEF,FACE),star_stem,dots])
    colors={'gold':local(gold,side),'blue':local(blue,side),'violet':local(violet,side)}
    if fillcolor in colors:colors[fillcolor]=fuse([colors[fillcolor],local(fill,side)])
    else:colors[fillcolor]=local(fill,side)
    rim=ring(0,EAR_CY,50,45.8,RELIEF,FACE).intersect(ear_limit(RELIEF,FACE))
    # Ensure nonoverlapping top color bodies and clip everything to backed areas.
    backing=body.translate((0,0,RELIEF))
    for name in list(colors):
        colors[name]=colors[name].intersect(ear_limit(RELIEF,FACE)).intersect(backing).clean()
    colors['purple']=fuse([body,rim.cut(fuse(colors.values()))])
    full=fuse(colors.values())
    return colors,full

def eye_unit():
    # Eyes retain tall curved stalks from the supplied image. Width increased to
    # 6.5 mm, with 3-mm structural thickness and radiused roots.
    anchor=box(-13,65.5,26,8,4.2)
    pieces=[anchor]
    for sign in [-1,1]:
        pts=[(sign*11,72),(sign*11.2,79),(sign*12.8,86),(sign*17,94),(sign*20.5,98)]
        pieces += [cap(*a,*b,STALK_WIDTH/2,EYE_BASE) for a,b in zip(pts[:-1],pts[1:])]
        pieces.append(disk(sign*22,107.5,12.5,EYE_BASE))
    base=fuse(pieces)
    for x in [-7,7]:base=base.cut(cyl(BORE_D/2,3.2,(x,69.5,-.1),(0,0,1)))
    white=[];black=[];lids=[]
    for sign in [-1,1]:
        x=sign*22
        inside=disk(x,107.5,10.5,RELIEF,EYE_BASE)
        lower=inside.intersect(box(x-13,94,26,14,RELIEF+2,EYE_BASE-.5))
        pupil=disk(x-sign*3.4,106.3,5.2,RELIEF,EYE_BASE).intersect(lower)
        shine=fuse([disk(x-sign*4.1,108,.95,RELIEF,EYE_BASE),disk(x-sign*2.1,107.6,.50,RELIEF,EYE_BASE)]).intersect(pupil)
        black.append(pupil.cut(shine));white += [lower.cut(pupil),shine]
        lids.append(inside.cut(lower))
    regions={'purple':fuse([base]+lids),'white':fuse(white),'black':fuse(black)}
    return regions,fuse(regions.values())

def ear_adapter(width=10,radius=65):
    # Top radius follows the five-magnet ear system; underside follows a real
    # headband's outside curve. Width is the front-to-back bonding dimension.
    center_y=84-PAD_RADIAL_HEIGHT-radius
    body=disk(0,0,84,width).cut(disk(0,center_y,radius+.10,width+2,-1))
    body=body.intersect(box(-34,60,68,30,width))
    bores=[]
    for a in ANGLES:
        u=(math.sin(a),math.cos(a),0);r=80.9
        bores.append(cyl(BORE_D/2,6,(r*u[0],r*u[1],width-5),u))
    return body.cut(fuse(bores)).clean()

def center_adapter(width=10,radius=65):
    # Glue the concave underside to the headband; front-facing disc magnets
    # allow the tall eye unit to sit close to the crown without a tall pedestal.
    center_y=DEFAULT_RADIUS-radius
    p=box(-13,DEFAULT_RADIUS-3,26,11.5,width)
    p=p.cut(disk(0,center_y,radius+.1,width+2,-1))
    for x in [-7,7]:p=p.cut(cyl(BORE_D/2,3.2,(x,69.5,width+.1),(0,0,-1)))
    return p.clean()

def magnet_coupon():
    p=box(-15,0,30,7,10)
    for i,(x,d) in enumerate(zip([-10,0,10],[6,6.1,6.2]),1):
        p=p.cut(cyl(d/2,3.2,(x,-.1,5),(0,1,0)))
        for j in range(i):p=p.cut(box(x-1.5+j*1.2,4,.7,1.8,.5,9.5))
    return p.clean()

def radius_coupon(radius):
    # Lightweight concave-edge gauge for choosing a saddle before printing one.
    p=ring(0,0,radius+1.8,radius,1.8).intersect(box(-34,radius-15,68,20,1.8))
    count={55:1,65:2,75:3}[radius]
    for j in range(count):p=p.cut(box(-2+j*1.5,radius+.6,.65,.8,.35,1.5))
    return p.clean()

def ear_place(shape,side='left',z=0):
    angle=TILT if side=='left' else -TILT
    a=math.radians(angle);u=np.array([-math.sin(a),math.cos(a)])
    target=(DEFAULT_RADIUS+PAD_RADIAL_HEIGHT-84)*u
    old=np.array([-ARC_CY*math.sin(a),ARC_CY*math.cos(a)])
    delta=target-old
    return shape.rotate((0,0,0),(0,0,1),angle).translate((float(delta[0]),float(delta[1]),z))

def adapter_place(shape,side='left',width=10):
    angle=TILT if side=='left' else -TILT;a=math.radians(angle)
    u=np.array([-math.sin(a),math.cos(a)])
    target=(DEFAULT_RADIUS+PAD_RADIAL_HEIGHT-84)*u
    return shape.rotate((0,0,0),(0,0,1),angle).translate((float(target[0]),float(target[1]),-width))

def headband_proxy(width=10):
    ann=ring(0,0,65,62.5,width)
    # The proxy is a partial circular store-headband envelope, never a print file.
    a1,a2=math.radians(-32),math.radians(212)
    points=[(0,0)]+[(90*math.cos(a),90*math.sin(a)) for a in np.linspace(a1,a2,90)]
    return ann.intersect(poly(points,width)).translate((0,0,-width))

def export_stl(p,path):p.exportStl(str(path),tolerance=.025,angularTolerance=.07,ascii=False)
def main():
    print('Building image-led left face',flush=True);lc,left=ear_face('left')
    print('Building image-led right face',flush=True);rc,right=ear_face('right')
    print('Building tall eyes and rear carriers',flush=True);ec,eyes=eye_unit();boot=carrier()
    parts={'left_face':left,'right_face':right,'rear_magnet_carrier_print_two':boot,
           'tall_eyes':eyes,'magnet_fit_coupon':magnet_coupon()}
    parts.update({f'radius_fit_R{r}':radius_coupon(r) for r in [55,65,75]})
    variants={}
    for radius in [55,65,75]:
        for width in [10,15,20]:
            name=f'ear_adapter_W{width}_R{radius}_print_two'
            variants[name]=ear_adapter(width,radius)
            name=f'eye_adapter_W{width}_R{radius}'
            variants[name]=center_adapter(width,radius)
    metrics={}
    for n,p in {**parts,**variants}.items():
        print('Export',n,flush=True)
        if not p.isValid() or len(p.Solids())!=1:raise ValueError(f'Invalid/disconnected {n}: {len(p.Solids())}')
        folder=STL/'adapters' if n in variants else STL
        export_stl(p,folder/(n+'.stl'))
        if n in parts or ('W10_R65' in n):cq.exporters.export(p,str(CAD/(n+'.step')))
        b=p.BoundingBox();metrics[n]={'volume_mm3':p.Volume(),'valid':True,'solids':1,
           'bounds_mm':[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]}
    for n,regions in [('left_face',lc),('right_face',rc),('tall_eyes',ec)]:
        for color,p in regions.items():export_stl(p,STL/(n+'_'+color+'.stl'))
    render=[];assembly=cq.Assembly(name='Image_based_crab_ears_and_glue_on_adapters')
    def add(n,p,color):
        if not p.isValid():raise ValueError('Invalid assembly '+n)
        assembly.add(p,name=n,color=cq.Color(*COLORS[color]))
        export_stl(p,PREV/(n+'.stl'));render.append({'name':n,'color':color,'path':n+'.stl'})
    for side,colors in [('left',lc),('right',rc)]:
        for color,p in colors.items():add(side+'_'+color,ear_place(p,side,.1),color)
        add(side+'_rear_carrier',ear_place(boot,side,-10),'purple')
        add(side+'_glue_on_adapter',adapter_place(variants['ear_adapter_W10_R65_print_two'],side,10),'purple')
    for color,p in ec.items():add('eyes_'+color,p.translate((0,0,.1)),color)
    add('eye_glue_on_adapter',variants['eye_adapter_W10_R65'].translate((0,0,-10)),'purple')
    add('headband_reference_ONLY',headband_proxy(),'band_reference')
    assembly.save(str(CAD/'crab_v3_assembly.step'))
    # Fit jig: the plain rear carrier is already the exact five-pocket test piece.
    export_stl(cq.Compound.makeCompound([left.translate((-56,0,0)),right.translate((56,0,0))]),STL/'both_faces.stl')
    meta={'units':'mm','parameters':{'face_base':FACE,'face_relief':RELIEF,'stalk_width':STALK_WIDTH,
        'eye_base':EYE_BASE,'bore_diameter':BORE_D,'magnet_nominal':[6,3],'adapter_widths':[10,15,20],
        'adapter_underside_radii':[55,65,75],'default_radius':65,'ear_tilt_degrees':TILT},
        'parts':metrics,'render':render}
    (ROOT/'model_metrics.json').write_text(json.dumps(meta,indent=2))
    print('DONE',json.dumps({n:round(p['volume_mm3'],1) for n,p in metrics.items()}),flush=True)
if __name__=='__main__':main()
