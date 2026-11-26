"""Compare the source photos with rendered, reloaded print geometry."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, shift

from build_ears import BG, NAMES, ROOT, crab
from coin_rim import FLOOR_Z, GROOVE_RGB, KEY_RGB, KEY_Z

FONT_DIR = Path("C:/Windows/Fonts")
TITLE = ImageFont.truetype(str(FONT_DIR / "georgia.ttf"), 38)
LABEL = ImageFont.truetype(str(FONT_DIR / "segoeui.ttf"), 22)
CAPTION = ImageFont.truetype(str(FONT_DIR / "segoeui.ttf"), 17)
BASES = {"back": (38, 54, 118), "rim": (177, 133, 63)}
INK = "#f3d59a"
MUTED = "#cec0cb"


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def render_mesh(entry, angle=0, use_paint=False):
    body, paint, pose, illustration = entry
    mesh = crab.mesh(crab.transformed(body, pose))
    theta = np.radians(angle)
    camera = np.array([[1,0,0], [0,np.cos(theta),-np.sin(theta)],
                      [0,np.sin(theta),np.cos(theta)]])
    screen = mesh.vertices @ camera.T
    low, high = screen[:, :2].min(axis=0), screen[:, :2].max(axis=0)
    units = 7.
    pad = 8.
    width, height = (np.ceil((high-low+2*pad)*units)).astype(int)
    screen[:,0] = (screen[:,0]-low[0]+pad)*units
    screen[:,1] = (high[1]+pad-screen[:,1])*units
    zbuffer = np.full((height,width), -np.inf, dtype=np.float32)
    normalmap = np.zeros((height,width,3), dtype=np.float32)
    world = np.zeros((height,width,3), dtype=np.float32)
    normals = mesh.face_normals @ camera.T
    for idx in np.flatnonzero(normals[:,2] > 1e-8):
        ids = mesh.faces[idx]
        t = screen[ids]
        lo = np.floor(t[:,:2].min(axis=0)).astype(int)
        hi = np.ceil(t[:,:2].max(axis=0)).astype(int)
        yy, xx = np.ogrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        p, q = t[1]-t[0], t[2]-t[0]
        det = p[0]*q[1]-p[1]*q[0]
        u = ((xx+.5-t[0,0])*q[1]-(yy+.5-t[0,1])*q[0])/det
        v = (p[0]*(yy+.5-t[0,1])-p[1]*(xx+.5-t[0,0]))/det
        depth = t[0,2]+u*p[2]+v*q[2]
        region = np.s_[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        hit = (u >= -1e-7)&(v >= -1e-7)&(u+v <= 1.0000001)&(depth >= zbuffer[region])
        if not hit.any():
            continue
        zbuffer[region][hit] = depth[hit]
        normalmap[region][hit] = normals[idx]
        a, b, c = mesh.vertices[ids]
        world[region][hit] = a+u[hit,None]*(b-a)+v[hit,None]*(c-a)
    used = np.isfinite(zbuffer)
    x, y, z = world[used].T
    depth = np.where(used, zbuffer, -90.)
    # Stepped edges cast short directional shadows even in an orthographic
    # front view. Use only the mesh depth and normals for the unpainted image.
    shadows = np.zeros_like(depth)
    for distance in (1,2,3,5,8,12):
        light_depth = shift(depth, (distance, distance), order=0, mode="constant", cval=-90)
        occlusion = np.clip((light_depth-depth)*.85-distance*.065, 0., .58)
        shadows = np.maximum(shadows, occlusion)
    shadow = gaussian_filter(shadows, .57)[used]
    light_dir = np.array([-.46, .45, .76])
    light = .76 + .31*np.clip(normalmap[used]@light_dir,0,1) - shadow*.50

    if use_paint:
        colors = np.tile(BASES["back"], (len(x),1)).astype(float)
        colors[z > 6] = BASES["rim"]
        colors[np.abs(z-FLOOR_Z)<.042] = GROOVE_RGB
        colors[np.abs(z-KEY_Z)<.042] = KEY_RGB
        area = z < 6
        inverse = np.linalg.inv(pose[:2,:2])
        loc = (np.column_stack((x[area],y[area])) - pose[:2,3]) @ inverse.T
        colors[area] = paint.color_at(*loc.T)
    else:
        colors = np.tile((210, 201, 181), (len(x),1)).astype(float)
        # Render with a warmer, brighter top and darker tonal recesses.
        relief_area = (z > 1.97) & (z < 6.0)
        light[relief_area] *= .58 + .49*np.clip((z[relief_area]-2.)/2.9, 0, 1)
    out = np.empty((height,width,3), dtype=np.uint8)
    out[:,:,:] = rgb(BG)
    out[used] = np.clip(colors*light[:,None],0,255)
    return Image.fromarray(out)


def paste_fit(page, picture, x, y, width, height):
    picture = picture.copy()
    picture.thumbnail((width,height),Image.Resampling.LANCZOS)
    position = (x+(width-picture.width)//2,y+(height-picture.height)//2)
    page.paste(picture, position, picture if picture.mode == "RGBA" else None)


def render(inputs, band):
    out = ROOT / "previews"
    scene = [(band, "band")]
    sheet = Image.new("RGB", (1590, 1075), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((37,22), "Mulan NX3  |  Fitted artwork and printable relief", font=TITLE, fill=INK)
    for x, text in ((32,"FOREGROUND SOURCE"), (415,"CROPPED COMPOSITION"), (802,"UNPAINTED STL"), (1192,"PAINT GUIDE")):
        draw.text((x+13,91), text, font=LABEL, fill=MUTED)
    for i, entry in enumerate(inputs):
        body, paint, pose, illustration = entry
        scene.append((crab.transformed(body, pose), "gold_light"))
        composition = paint.placed_image()
        composition.save(out/f"{NAMES[i]}_fitted_composition.png")
        raw = render_mesh(entry)
        color = render_mesh(entry, use_paint=True)
        raw.save(out/f"{NAMES[i]}_unpainted_CAD.png")
        color.save(out/f"{NAMES[i]}_paint_reference.png")
        top = 130+i*433
        for x, picture in zip((25,406,789,1176),(illustration, composition, raw, color)):
            paste_fit(sheet,picture,x,top,375,408)
    draw.text((42,1032), "Left ear above · Right ear below   /   All CAD images use the exported STL geometry",
              fill=MUTED, font=CAPTION)
    sheet.save(out/"reference_comparison.png")
    detail = Image.new("RGB", (1210, 600), BG)
    d = ImageDraw.Draw(detail)
    d.text((38,20), "Illustration relief and full-depth rims", font=TITLE, fill=INK)
    for i, entry in enumerate(inputs):
        paste_fit(detail,render_mesh(entry, angle=23), 590*i+20, 71, 580, 507)
    detail.save(out/"relief_only.png")
    crab.rendered(scene, out/"mounted_angle.png", angled=True)
    rear = [(entry[0].rotate((-66, 0, 0)).translate((110*i, 0, 0)), "gold_light")
            for i, entry in enumerate(inputs)]
    crab.rendered(rear, out/"integrated_magnet_pockets.png")
