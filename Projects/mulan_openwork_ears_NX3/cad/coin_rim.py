"""Coin-style square coils framed by stepped rails in the existing NX3 rim."""

import math

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import substring, unary_union

FLOOR_Z = 9.20
SHOULDER_Z = 9.48
KEY_Z = 9.72
GROOVE_RGB = (122, 88, 47)
KEY_RGB = (224, 180, 95)
KEY_STROKE = .42


def coin_rim(rim):
    """Return the occupied belt, floor and bent Greek-key tiles."""
    outline = orient(Polygon(rim.exterior), sign=1)
    inner = Polygon(rim.interiors[0])
    belt = outline.buffer(-.57).difference(inner.buffer(.57)).intersection(rim)
    field = outline.buffer(-.90).difference(inner.buffer(.90)).intersection(belt)
    loop = orient(outline.buffer(-2.527), sign=1).exterior
    length = loop.length
    count = round(length/9.65)
    pitch = length/count
    half = (pitch-.84)/2

    # A rectangular double turn, with roughly 0.4 mm between neighboring
    # strokes. Unwind each tile along the rim's arc length instead of laying
    # a straight stamp across the circular surface.
    key = np.array([
        [-half, -1.20], [half, -1.20], [half, 1.20], [-half, 1.20],
        [-half, -.40], [half-.82, -.40], [half-.82, .40], [-half+.82, .40],
    ])
    safe=field.buffer(-.075)

    def bent_stamp(guide,center):
        points=[]
        for start,end in zip(guide[:-1],guide[1:]):
            n=max(1,math.ceil(np.linalg.norm(end-start)/.18))
            points.extend(start+(end-start)*j/n for j in range(n))
        points.append(guide[-1])
        mapped=[]
        for along,across in points:
            d=(center+along)%length
            p=loop.interpolate(d)
            a,b=(loop.interpolate((d+offset)%length) for offset in (-.28,.28))
            dx,dy=b.x-a.x,b.y-a.y
            norm=math.hypot(dx,dy)
            mapped.append((p.x+dy/norm*across,p.y-dx/norm*across))
        center_path=LineString(mapped)
        stamp=center_path.buffer(KEY_STROKE/2,cap_style='square',join_style='mitre')
        # Leave a clean margin where the mount corners pinch a tile.
        if stamp.difference(safe).area < .075 and center_path.is_simple:
            return stamp.intersection(safe).simplify(.012)
        return None

    def corner_stamp(center, span, mirror):
        # Real inset curves track the sharp stock corner independently.
        # Connect the turns in alternating order for a wide nested key.
        lanes=[1.38,2.53,3.68]
        if mirror[1]<0:
            lanes.reverse()
        start,end=(loop.interpolate((center+step)%length) for step in (-span,span))
        coords=[]
        for i,depth in enumerate(lanes):
            edge=orient(outline.buffer(-depth),sign=1).exterior
            lo,hi=edge.project(start),edge.project(end)
            if lo>hi:
                first=list(substring(edge,lo,edge.length).coords)
                second=list(substring(edge,0,hi).coords)
                path=first+second[1:]
            else:
                path=list(substring(edge,lo,hi).coords)
            coords.extend(path if i%2==0 else path[::-1])
        line=LineString(coords)
        stamp=line.buffer(KEY_STROKE/2,cap_style='square',join_style='round')
        if line.is_simple and stamp.difference(safe).area<.035:
            return stamp.intersection(safe).simplify(.012)
        return None

    coils, corners = [], []
    for i in range(count):
        center = (i+.5)*pitch
        mirror=np.array([1,-1 if i%2 else 1])
        stamp=bent_stamp(key*mirror,center)
        if stamp is None:
            corners.append((center,mirror))
        else:
            coils.append(stamp)
    for center,mirror in corners:
        for span in (4.42,4.24,4.08,3.90,3.72,3.55):
            stamp=corner_stamp(center,span,mirror)
            if stamp is not None and stamp.distance(unary_union(coils))>.30:
                coils.append(stamp)
                break
        else:
            raise ValueError(f"Coin corner transition does not fit at {center:.2f} mm")
    stamps=unary_union(coils)
    assert len(coils)==count, (len(coils),count)
    assert stamps.area>120
    return belt,field,stamps,len(coils)
