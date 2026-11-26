from pathlib import Path
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

out = Path(sys.argv[1])
source = Image.open(out / "broom-comfy-render.png").convert("RGBA")
r, g, b, a = np.moveaxis(np.asarray(source).astype(float), -1, 0)
level = np.maximum((r - 19) / 37, (g - 71) / 57)
labels, _ = ndimage.label(level > .04)
count = np.bincount(labels.ravel())
count[0] = 0
alpha = np.where(labels == count.argmax(), np.clip(level, 0, 1), 0)
source.putalpha(Image.fromarray(np.rint(alpha * 255).astype(np.uint8)))
source = source.crop(source.getbbox())
source.save(out / "broom-comfy-cutout.png")
print("motif dimensions", source.size, "width over height", round(source.width/source.height, 3))
