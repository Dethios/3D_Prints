from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

out = Path(__file__).resolve().parent
root = out.parent
inner = Image.open(root / "ear-interior-alpha.png").convert("L")
outer = Image.open(root / "ear-outer-alpha.png").convert("L")
size, pad, center = (1248, 1248), 112, (624, 624)
bicubic = Image.Resampling.BICUBIC
opening_alpha = np.asarray(inner)


def read_layers(script, boundary, args=()):
    code, found, _ = script.read_text(encoding="utf-8-sig").partition(boundary)
    assert found, script
    before = sys.argv[:]
    try:
        sys.argv = [str(script), *map(str, args)]
        scope = {"__file__": str(script)}
        exec(compile(code, str(script), "exec"), scope)
        return scope
    finally:
        sys.argv = before


def trim(layer, mask):
    opacity = np.asarray(layer.getchannel("A")).astype(np.uint16)
    allowed = np.asarray(mask).astype(np.uint16)
    result = layer.copy()
    result.putalpha(Image.fromarray(((opacity * allowed + 127) // 255).astype(np.uint8)))
    return result


def mounted_mask(mask, angle):
    layer = Image.new("L", size)
    layer.paste(mask, (pad, pad))
    return layer.rotate(angle, bicubic, center=center)


def to_flat(mounted, angle):
    return mounted.rotate(-angle, bicubic, center=center).crop((pad, pad, pad + 1024, pad + 1024))


def decoration(path, angle, hard_clip=False):
    x, y, _, _ = mounted_mask(outer, angle).getbbox()
    native = Image.open(path).convert("RGBA")
    padded = Image.new("RGBA", size)
    padded.paste(native, (x - 35, y - 35))
    flat = to_flat(padded, angle)
    if hard_clip:
        alpha = np.where(opening_alpha == 255, np.asarray(flat.getchannel("A")), 0)
        flat.putalpha(Image.fromarray(alpha.astype(np.uint8)))
    return trim(flat, inner)


mickey_dir = root / "Mickey_Sticker_Base"
wisps = mickey_dir / "Wispy_Shift"
ornaments = mickey_dir / "Wispy_Ornaments"
mickey_layout = read_layers(wisps / "position-shifted-sticker.py", "\nfield=fill(opening,navy)",
                            (wisps / "isolated-sticker-wispy.png",))
mickey = trim(to_flat(mickey_layout["mounted_ink"], -40), inner)
mickey.alpha_composite(decoration(ornaments / "mounted-ornament-and-bridge-layer.png", -40, True))

broom_dir = root / "Broom_Pin_Match" / "New_Profile"
broom_start = read_layers(broom_dir / "fit-profile.py", "\nscene.alpha_composite(stars)",
                          (broom_dir / "reference-profile-cutout.png", "0", "selected-original-angle"))
broom_current = read_layers(broom_dir / "apply-matching-linework.py", "\nmounted_output=")
pair = trim(broom_current["after"], mounted_mask(inner, 40))
pair.alpha_composite(broom_start["stars"])
brooms = trim(to_flat(pair, 40), inner)
brooms.alpha_composite(decoration(broom_dir / "added-stars-matte.png", 40))
brooms.alpha_composite(decoration(broom_dir / "Marked_Stars" / "added-stars-matte.png", 40))


def verify_and_export(name, artwork, preview, navy):
    dest = out / f"{name}-flat-decorations-transparent.png"
    stored = np.asarray(artwork).copy()
    stored[stored[:,:,3] == 0] = 0
    Image.fromarray(stored).save(dest, dpi=(9.22 * 25.4, 9.22 * 25.4))
    saved = Image.open(dest)
    assert saved.size == (1024, 1024) and saved.mode == "RGBA"
    a = np.asarray(saved.getchannel("A"))
    assert not a[opening_alpha == 0].any()
    assert 0 < np.count_nonzero(a) < np.count_nonzero(opening_alpha) // 2
    # A normal navy backing reconstructs the approved flat view.
    ref = np.asarray(Image.open(preview).convert("RGB")).astype(int)
    rebuilt = Image.new("RGBA", saved.size, (*navy, 255))
    rebuilt.alpha_composite(saved)
    error = abs(np.asarray(rebuilt)[:,:,:3].astype(int) - ref).max(axis=2)
    different = error[(opening_alpha == 255)]
    assert (different > 2).sum() < 25, (name, different.max(), (different > 2).sum())
    return {"opaque_or_antialiased_art_pixels": int(np.count_nonzero(a)),
            "transparent_pixels": int(np.count_nonzero(a == 0)),
            "pixels_differing_over_two_levels_when_composited_over_navy": int((different > 2).sum()),
            "source_preview": str(preview.relative_to(root)),
            "sha256": sha256(dest.read_bytes()).hexdigest()}


report = {
    "mickey": verify_and_export("mickey", mickey, ornaments / "mickey-flat-wispy-original-ornaments-lithography.png", (28, 51, 99)),
    "brooms": verify_and_export("brooms", brooms, broom_dir / "Marked_Stars" / "brooms-flat-marked-stars-lithography.png", (35, 62, 114)),
}
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
