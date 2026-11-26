"""Fit original illustrations to the NX3 interiors and emboss their tones."""

import math

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, map_coordinates
from scipy.optimize import linprog
from shapely import affinity, contains_xy
from shapely.geometry import MultiPoint, box
from shapely.geometry.polygon import orient
import trimesh

from build_ears import crab


GRID_MM = .215
HEIGHT_MM = 2.90


def fit_outline(alpha, safe, angle):
    """Choose the largest undistorted scale that fits the whole silhouette."""
    rows, cols = np.where(alpha > .16)
    hull = MultiPoint(np.column_stack((cols, -rows))).convex_hull
    hull = affinity.rotate(hull, angle, origin=(0,0))
    vertices = np.asarray(hull.exterior.coords)[:-1]
    contour = np.asarray(orient(safe.convex_hull.buffer(-.035), sign=1).exterior.coords)
    edges = np.diff(contour, axis=0)
    normals = np.column_stack((edges[:,1], -edges[:,0]))
    reach = np.max(normals @ vertices.T, axis=1)
    limits = (normals*contour[:-1]).sum(axis=1)
    fit = linprog([0,0,-1], A_ub=np.column_stack((normals,reach)), b_ub=limits,
                  bounds=[(None,None),(None,None),(0,None)], method="highs")
    if not fit.success:
        raise ValueError(f"Illustration does not fit the NX3 recess: {fit.message}")
    x, y, scale = fit.x
    placed = affinity.translate(affinity.scale(hull, scale, scale, origin=(0,0)), x, y)
    assert placed.difference(safe.buffer(.025)).area < .02
    return x, y, scale


def source_layers(picture):
    rgba = np.asarray(picture.convert("RGBA"), dtype=float)/255
    rgb, original_alpha = rgba[:,:,:3], rgba[:,:,3]
    labels, _ = label(original_alpha > .40, structure=np.ones((3,3)))
    sizes = np.bincount(labels.ravel())
    matte = (labels > 0) & (sizes[labels] > rgba.shape[0]*rgba.shape[1]*.00012)
    if not np.any(matte) or matte.mean() > .95:
        raise ValueError("Provide an isolated transparent illustration for each ear.")
    alpha = np.minimum(original_alpha, np.clip(gaussian_filter(matte.astype(float),.7)*1.55,0,1))

    # Convert clean color blocks into paintable height changes. Keep an
    # elevated silhouette even for the black outlines, hair and brows.
    luma = rgb @ np.array([.25,.58,.17])
    r,g,b = np.moveaxis(rgb,-1,0)
    tone = np.clip((luma-.04)/.87 + .16*np.maximum(b-r,0) + .07*np.maximum(r-g,0),0,1)
    tone = np.clip(gaussian_filter(tone,.65),0,1)**.84
    depth = alpha*(.48 + (HEIGHT_MM-.48)*tone)
    return rgb, alpha, depth


class Artwork:
    def __init__(self, image, interior, index):
        prepared = image.copy()
        prepared.thumbnail((750,750), Image.Resampling.LANCZOS)
        self.color, self.alpha, self.depth = source_layers(prepared)
        self.safe = interior.buffer(-.44).intersection(box(-56,14.76,56,90))
        placement = self.safe.buffer(-.52)
        angle = -40 if index == 0 else 40
        self.x,self.y,self.scale = fit_outline(self.alpha, placement, angle)
        self.cos = math.cos(math.radians(angle))
        self.sin = math.sin(math.radians(angle))
        self.background_rgb = np.array([.13,.18,.43])

    def photo_coordinates(self, x, y):
        x,y = (x-self.x)/self.scale,(y-self.y)/self.scale
        return self.cos*x+self.sin*y,self.sin*x-self.cos*y

    def color_at(self, x, y):
        u,v = self.photo_coordinates(x,y)
        a = map_coordinates(self.alpha,[v,u],order=1,mode="constant")
        rgb = np.column_stack([map_coordinates(self.color[:,:,i],[v,u],order=1,
                                               mode="nearest") for i in range(3)])
        return (255*(self.background_rgb*(1-a[:,None])+rgb*a[:,None])).clip(0,255)

    def mesh(self):
        xmin,ymin,xmax,ymax = self.safe.bounds
        row,col = np.meshgrid(np.arange(ymin-GRID_MM, ymax+2*GRID_MM, GRID_MM),
                              np.arange(xmin-GRID_MM, xmax+2*GRID_MM, GRID_MM), indexing="ij")
        u,v = self.photo_coordinates(col,row)
        relief = map_coordinates(self.depth,[v,u],order=1,mode="constant")
        inside = contains_xy(self.safe,col,row)
        taper = np.minimum(distance_transform_edt(inside)*GRID_MM/.52,1.)
        relief *= taper
        return height_mesh(col,row,relief), relief


def height_mesh(x,y,values):
    valid = values > .001
    # Leave a margin beyond the relief. Every
    # exterior edge of the active mesh is already below the backing plane.
    nonzero_rows, nonzero_cols = np.where(valid)
    row_slice = slice(nonzero_rows.min()-1, nonzero_rows.max()+2)
    col_slice = slice(nonzero_cols.min()-1, nonzero_cols.max()+2)
    x, y, values = (a[row_slice,col_slice] for a in (x,y,values))
    rows, cols = x.shape
    active = np.ones((rows-1,cols-1),dtype=bool)
    indices = np.arange(rows*cols).reshape(rows,cols)
    ids = np.column_stack((indices[:-1,:-1][active],indices[:-1,1:][active],
                           indices[1:,1:][active],indices[1:,:-1][active]))
    top = np.r_[ids[:,[0,1,2]],ids[:,[0,2,3]]]
    edges = np.concatenate([ids[:,[0,1]],ids[:,[1,2]],ids[:,[2,3]],ids[:,[3,0]]])
    undirected = np.sort(edges,axis=1)
    _, inverse, counts = np.unique(undirected,axis=0,return_inverse=True,return_counts=True)
    edges = edges[counts[inverse] == 1]
    size = rows*cols
    a,b = edges.T
    sides = np.r_[np.column_stack((b,a,a+size)),np.column_stack((b,a+size,b+size))]
    faces = np.r_[top,top[:,::-1]+size,sides]
    bottom_z = np.full(size,1.72)
    top_z = 1.94+values.ravel()
    verts = np.column_stack((np.tile(x.ravel(),2),np.tile(y.ravel(),2),np.r_[top_z,bottom_z]))
    # Simplify only the relief before fusing. The approved carrier's bore
    # facets and engraving are kept out of the relief simplification.
    model = trimesh.Trimesh(vertices=verts,faces=faces,process=True)
    model.remove_unreferenced_vertices()
    return crab.solid(model).simplify(.022)
