from pathlib import Path
from PIL import Image
import sys
p = Path(sys.argv[1])
original = Image.open(p.parent/"Mickey_Qwen_Targeted_Hands/qwen-full-art-registered.png").convert("RGB")
edited = Image.open(p/"qwen-four-digit-registered-crop.png").convert("RGB")
# The new Qwen pass affects only the lower glove. Preserve the accepted upper glove donor.
original.paste(edited,(321,493))
original.save(p/"qwen-registered-selected-hands.png")
