import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

out = Path(__file__).resolve().parent
guide = Image.open(out / "exact-broom-pin-contour-guide.png").convert("RGB")
pixels = np.asarray(guide).astype(float)
background = np.median(pixels[:80, :80], axis=(0, 1))
distance = np.linalg.norm(pixels - background, axis=2)
alpha = np.clip((distance - 10) / 40, 0, 1)
Y, X = np.indices(distance.shape)
# The neighboring red cape crosses beneath the lower left bucket.
# Follow the surviving red stave and the ivory bottom hoop at the join.
bucket_edge = np.interp(Y, [498, 514, 529, 543, 553, 560], [225, 230, 244, 259, 277, 323])
fragment = (Y >= 498) & (Y <= 583) & (X < 323) & (X < bucket_edge)
alpha[fragment] = 0
labels, _ = ndimage.label(alpha > .18)
counts = np.bincount(labels.ravel())
counts[0] = 0
alpha[labels != counts.argmax()] = 0
source = guide.filter(ImageFilter.UnsharpMask(radius=2, percent=130, threshold=3)).convert("RGBA")
source.putalpha(Image.fromarray(np.rint(alpha * 255).astype(np.uint8)))
source.crop(source.getbbox()).save(out / "pin-cleanup-fallback.png")
