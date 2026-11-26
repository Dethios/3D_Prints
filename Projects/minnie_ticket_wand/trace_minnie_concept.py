"""Render the provisional Minnie CR80 wand concept from the supplied photo trace."""
from math import atan2, cos, degrees, radians, sin
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box


HEAD = (
    (560, 265),
    (
        (528, 268, 497, 248, 496, 216),
        (495, 184, 519, 157, 547, 153),
        (578, 147, 600, 166, 615, 191),
        (637, 209, 668, 207, 689, 187),
        (705, 157, 730, 142, 752, 144),
        (786, 144, 811, 170, 812, 202),
        (813, 232, 787, 256, 751, 260),
        (759, 282, 769, 306, 765, 333),
        (762, 386, 721, 425, 669, 431),
        (609, 440, 554, 395, 549, 337),
        (545, 308, 554, 286, 560, 265),
    ),
)
LEFT_BOW = (
    (641, 193),
    (
        (634, 178, 612, 147, 596, 144),
        (581, 139, 575, 154, 581, 172),
        (583, 182, 591, 190, 588, 199),
        (586, 209, 580, 221, 588, 230),
        (599, 241, 619, 230, 641, 220),
        (648, 213, 649, 203, 641, 193),
    ),
)
RIGHT_BOW = (
    (663, 191),
    (
        (669, 175, 688, 145, 701, 140),
        (717, 134, 723, 146, 718, 165),
        (717, 177, 710, 185, 713, 194),
        (716, 207, 723, 218, 716, 226),
        (708, 239, 687, 229, 664, 220),
        (656, 214, 656, 203, 663, 191),
    ),
)
KNOT = (
    (645, 191),
    (
        (650, 188, 658, 188, 662, 192),
        (667, 198, 667, 210, 664, 218),
        (661, 222, 647, 223, 642, 218),
        (639, 211, 639, 195, 645, 191),
    ),
)


def sample(path):
    origin, segments = path
    points = [origin]
    for ax, ay, bx, by, cx, cy in segments:
        ox, oy = origin
        for step in range(1, 41):
            t = step / 40
            u = 1 - t
            points.append((
                u**3 * ox + 3*u*u*t*ax + 3*u*t*t*bx + t**3*cx,
                u**3 * oy + 3*u*u*t*ay + 3*u*t*t*by + t**3*cy,
            ))
        origin = (cx, cy)
    return points


source = Image.open(sys.argv[1]).convert("RGB")
output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name("minnie-wand-upright.png")

# Image coordinates have positive y downward. Both the scanned ear crowns
# and the bow peaks rise to the right. Rotate their common front plane once.
reference_axis = (650.3, 141.5)
roll_degrees = 2.6
angle = radians(roll_degrees)


def rotate_about_axis(x, y, a):
    dx, dy = x-reference_axis[0], y-reference_axis[1]
    return (reference_axis[0] + cos(a)*dx - sin(a)*dy,
            reference_axis[1] + sin(a)*dx + cos(a)*dy)


def upright(x, y):
    return rotate_about_axis(x, y, angle)


def source_coordinates(x, y):
    return rotate_about_axis(x, y, -angle)


def upright_path(path):
    return [upright(x, y) for x, y in sample(path)]


ear_crowns = [(559.5, 153.0), (751.5, 144.0)]
bow_tips = [(594.0, 144.0), (706.5, 139.0)]
head = Polygon(upright_path(HEAD))
assert head.is_valid

# Dimension the open-top pocket from the nominal card, then fit the
# same scale to the entire image trace using the visible pocket width.
card_width, card_length = 53.98, 85.60
clearance = 0.25
wall = 1.50
reference_pocket_span = 142
reference_bottom = upright(664.0, 441.0)[1]
wand_center_x = reference_axis[0]
reference_left = wand_center_x - reference_pocket_span / 2
reference_right = wand_center_x + reference_pocket_span / 2
pocket_width = card_width + 2 * (clearance + wall)
pocket_length = card_length + 2 * clearance + wall
unit = pocket_width / reference_pocket_span
pocket_top = reference_bottom - pocket_length / unit
case = box(reference_left, pocket_top, reference_right, reference_bottom)
card_left = reference_left + (wall + clearance) / unit
card_top = pocket_top + clearance / unit
card_right = card_left + card_width / unit
card_bottom = card_top + card_length / unit
radius = 3.18 / unit
card = box(card_left+radius, card_top+radius,
           card_right-radius, card_bottom-radius).buffer(radius)
envelope = card.buffer(clearance / unit)
assert case.covers(envelope)
assert abs(card.centroid.x - wand_center_x) < 1e-8
assert abs(case.centroid.x - wand_center_x) < 1e-8
assert abs((card_right-card_left) * unit - card_width) < 1e-8
assert abs((card_bottom-card_top) * unit - card_length) < 1e-8
visible_case = case.difference(head)
assert not visible_case.is_empty
assert visible_case.bounds[1] > 385
width_mm = (head.bounds[2] - head.bounds[0]) * unit
for label, landmarks in (("Ear crowns", ear_crowns), ("Bow tips", bow_tips)):
    (lx, ly), (rx, ry) = [upright(*p) for p in landmarks]
    mismatch = abs(ry-ly) * unit
    assert mismatch < 0.12
    print(f"{label} residual {mismatch:.3f} mm; slope {degrees(atan2(ry-ly,rx-lx)):.3f} degrees.")
print(f"Head span {width_mm:.1f} mm. Card {card_width:.2f} x {card_length:.2f} mm. "
      f"Pocket exterior {pocket_width:.2f} x {pocket_length:.2f} mm. "
      "Card and pocket centerlines coincide with the handle axis.")

ss = 2
canvas = Image.new("RGB", (1310*ss, 970*ss), "#f6f2ee")
d = ImageDraw.Draw(canvas)
ink = "#252329"
muted = "#655760"
pink = "#f493b6"
deep_pink = "#a63d6a"


def scaled(points):
    return tuple(round(value*ss) for value in points)


def text(x, y, value, size, color=ink, bold=False, anchor="la"):
    font_file = "segoeuib.ttf" if bold else "segoeui.ttf"
    font = ImageFont.truetype(f"C:/Windows/Fonts/{font_file}", size*ss)
    d.text(scaled((x,y)), value, font=font, fill=color, anchor=anchor)


def rect(coords, radius, fill):
    d.rounded_rectangle(scaled(coords), radius*ss, fill=fill)


def ellipse(coords, fill):
    d.ellipse(scaled(coords), fill=fill)


def line(coords, fill, width):
    d.line([scaled(xy) for xy in coords], fill, width*ss, joint="curve")


def polygon(coords, fill):
    d.polygon([scaled(xy) for xy in coords], fill)


text(36, 29, "Minnie ticket wand", 39, bold=True)
text(36, 85, "Upright reference trace   /   portrait CR80 pocket", 23, muted)

for cx, label in [(224, "Source photograph"), (655, "Front"), (1086, "Back")]:
    rect((cx-205, 138, cx+205, 901), 22, "#fffdfa")
    text(cx, 162, label, 24, bold=True, anchor="ma")

crop_origin = (482, 127)
crop_box = (*crop_origin, 826, 475)
crop = source.crop(crop_box).resize((344*ss, 348*ss), Image.Resampling.LANCZOS)
canvas.paste(crop, scaled((52, 262)))
for path in (HEAD, LEFT_BOW, RIGHT_BOW, KNOT):
    points = sample(path)
    coordinates = [(52+x-crop_origin[0], 262+y-crop_origin[1]) for x, y in points]
    line(coordinates + [coordinates[0]], "#3bf1dd", 2)
for edge in visible_case.geoms if visible_case.geom_type == "MultiPolygon" else (visible_case,):
    points = [(52+x-crop_origin[0], 262+y-crop_origin[1])
              for x,y in [source_coordinates(x,y) for x,y in edge.exterior.coords]]
    line(points, "#ffc466", 2)
text(224, 633, "Cyan trace · amber pocket corners", 17, muted, anchor="ma")
line([(74, 700),(374, 700)], "#dfd5d2", 1)
text(224, 724, "Photo tilt", 19, bold=True, anchor="ma")
text(224, 764, "Ear crowns   2.68°", 17, muted, anchor="ma")
text(224, 790, "Bow peaks   2.54°", 17, muted, anchor="ma")
text(224, 837, "Corrected 2.60° clockwise", 18, deep_pink, bold=True, anchor="ma")

bow_dots = (
    (594, 155, 3.9), (601, 168, 4.1), (615, 180, 4.1),
    (596, 184, 4), (607, 198, 4.2), (597, 218, 4.1),
    (620, 213, 4.1), (701, 151, 3.9), (695, 164, 4.1),
    (682, 178, 4.1), (705, 181, 4.1), (691, 194, 4.2),
    (707, 213, 4.1), (684, 213, 4.1),
)
for cx, direction in [(655, 1), (1086, -1)]:
    def place(x, y):
        return cx + direction*(x-wand_center_x), 242 + y-127

    def place_trace(x, y):
        return place(*upright(x, y))

    grip_top = place(wand_center_x, reference_bottom)[1]
    grip_bottom = 844
    polygon([(cx-18,grip_top), (cx+18,grip_top),
             (cx+12,grip_bottom), (cx-12,grip_bottom)], pink)
    ellipse((cx-12,grip_bottom-12,cx+12,grip_bottom+12), pink)
    polygon([place(x,y) for x,y in case.exterior.coords], "#39343d")
    rect((cx-21,grip_top,cx+21,grip_top+27), 7, "#d66b96")
    rect((cx-20,grip_top,cx+20,grip_top+22), 7, pink)
    polygon([place(x, y) for x, y in head.exterior.coords], ink)

    if direction == 1:
        for path in (LEFT_BOW, RIGHT_BOW, KNOT):
            polygon([(x, y+4) for x, y in [place_trace(x,y) for x,y in sample(path)]], deep_pink)
        for path in (LEFT_BOW, RIGHT_BOW, KNOT):
            polygon([place_trace(x,y) for x,y in sample(path)], pink)
        for x, y, radius in bow_dots:
            a, b = place_trace(x,y)
            ellipse((a-radius,b-radius,a+radius,b+radius), "#fffaf5")
        for x0,y0,x1,y1 in [(625,201,640,205),(666,204,679,199)]:
            line([place_trace(x0,y0),place_trace(x1,y1)], "#ce618c", 2)
        knot_outline = [place_trace(x,y) for x,y in sample(KNOT)]
        polygon(knot_outline, "#f8a0c0")
        line(knot_outline + [knot_outline[0]], "#cb618b", 2)
        for x,y in [place_trace(*p) for p in ear_crowns]:
            line([(x-12,y-3),(x+12,y-3)], "#a79199", 1)
        text(cx, 866, "Level ear crowns", 16, muted, anchor="ma")
        continue

    polygon([place(x,y) for x,y in card.exterior.coords], "#e9dfd1")
    x0, y0, x1, y1 = card.bounds
    left, top = place(x1, y0)
    right, bottom = place(x0, y1)
    rail = "#514852"
    rect((left-4,top+9,left+5,bottom-6), 3, rail)
    rect((right-5,top+9,right+4,bottom-6), 3, rail)
    rect((left+10,bottom-3,right-10,bottom+5), 3, rail)
    card_center_x = (left + right) / 2
    rect((card_center_x-13,top-7,card_center_x+13,top+7), 5, deep_pink)
    for yy in range(round(top+14), int(grip_bottom+7), 11):
        line([(cx,yy),(cx,yy+5)], "#ad858b", 1)
    rect((cx-58,(top+bottom)/2-26,cx+58,(top+bottom)/2+26), 8, "#e9dfd1")
    text(card_center_x, (top+bottom)/2-24, "Disney ticket", 18, anchor="ma")
    text(card_center_x, (top+bottom)/2+4, "Tap this face", 15, muted, anchor="ma")
    text(card_center_x, 198, "Insert the short edge first", 17, deep_pink, anchor="ma")
    line([(card_center_x,225),(card_center_x,top-14)], deep_pink, 2)
    polygon([(card_center_x,top-11),(card_center_x-5,top-19),(card_center_x+5,top-19)], deep_pink)
    text(cx, 866, "Shared pocket and handle axis", 16, muted, anchor="ma")

text(35, 922, f"{width_mm:.0f} mm across ears   /   53.98 × 85.60 mm card   /   57.48 × 87.60 mm pocket exterior", 19, muted)
canvas.resize((1310,970),Image.Resampling.LANCZOS).save(output)
