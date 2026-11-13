"""Verify the staging copy and organize it without writing to OneDrive."""

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(r"C:\Users\vic-l\OneDrive\.codex_sync\3D Prints")
STAGING = ROOT / "_incoming_sync_2026-11-10"
MANIFEST = Path(__file__).with_name("import-manifest.csv")

DIRS = {
    "A4T": "GitHub-Mods/A4T",
    "whopping_Voron_mods": "GitHub-Mods/whopping_Voron_mods",
    "Rewiring Prints": "Printer/rewiring",
    "modular-mini-figure-display-shelf-model_files": "Printables/modular-mini-figure-display-shelf",
    "stroller-ubmrella-holder-model_files": "Printables/stroller-umbrella-holder/Maker-package",
    "__pycache__": "Projects/sorcerer_hat/Recovery/__pycache__",
}

CHUBE = {
    "A4T Cowling - Chube [cw2-tap].3mf": "Prints",
    "A4T Cowling - Chube Air UHF [cw2-tap].step": "CAD",
    "A4T Cowling - Chube Air UHF [cw2-tap].stl": "STL",
    "Chube_hotend_integration_specifications.pdf": "Documentation",
    "CHUBE_INTEGRATION_REVA.step": "Reference",
}

FILES = {
    "1f04dd2813fa4d300f6973530a2c3036.jpg": "Projects/sorcerer_hat/Reference",
    "a4t_afc_cutter_arm_base_w_backers.stl": "Printer/mod-parts/a4t-afc-cutter",
    "Hexagons Chube Cowling.3mf": "Projects/Chube_Hotend_Integration/Prints",
    "Hexagons.3mf": "Printer/test-patterns",
    "polymaker-refill-spool-side-b-updated.stl": "Printables/polymaker-refill-spool",
    "replacement-battery-cap-for-ryobi-4v-lithium-tools-model_files.zip": "Printables/ryobi-4v-battery-cap",
    "ryobi-lithium-best-cover-240626-335mm-dia-x17hi.stl": "Printables/ryobi-4v-battery-cap",
    "sorcerer_hat_no_ears_hat.3mf": "Projects/sorcerer_hat/Prints",
    "sorcerer_hat_no_ears_hat.stl": "Projects/sorcerer_hat/STL",
    "sorcerer_hat_no_ears_stars_moon.stl": "Projects/sorcerer_hat/STL",
    "toolhead-board-h36-pug.step": "Printables/h36-wwg2-a4t-pug",
    "jedistitch.3mf": "Unverified-Downloads/star-wars/jedi-stitch",
    "Lightsaber_Birthday_Candle_Holder.stl": "Unverified-Downloads/star-wars/lightsaber-candle-holder",
    "May The Fourth Be With You Sign.stl": "Unverified-Downloads/star-wars/may-the-fourth-sign",
    "minivader.3mf": "Unverified-Downloads/star-wars/darth-vader",
    "vader-power-pose.3mf": "Unverified-Downloads/star-wars/darth-vader",
    "Vaders_and_Stich.3mf": "Unverified-Downloads/star-wars/combined-plates",
    "Vaders.3mf": "Unverified-Downloads/star-wars/darth-vader",
}

PREFIXES = {
    "Flow ": "Printer/calibration/flow",
    "Tripp Trapp Stokke Chair + IKEA Trofast ": "Printables/tripp-trapp-trofast",
    "Version 3 Stroller Umbrella Holder ": "Printables/stroller-umbrella-holder/Related-3MF",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def files(root):
    return {p.relative_to(root) for p in root.rglob("*") if p.is_file()}


def target(relative):
    name = relative.name
    first = relative.parts[0]
    if first in DIRS:
        return Path(DIRS[first]).joinpath(*relative.parts[1:])
    if first == "Chube_Hotend_Integration_Documentation" and len(relative.parts) == 2:
        return Path("Projects/Chube_Hotend_Integration") / CHUBE[name] / name
    if len(relative.parts) == 1:
        if name in FILES:
            return Path(FILES[name]) / name
        if name == "insert.stl":
            return Path("Printables/polymaker-refill-spool") / name
        for prefix, folder in PREFIXES.items():
            if name.startswith(prefix):
                return Path(folder) / name
    raise ValueError(f"Unclassified input: {relative}")


def main():
    if MANIFEST.exists():
        raise FileExistsError(MANIFEST)
    original = files(SOURCE)
    staged = files(STAGING)
    if original != staged:
        raise ValueError(f"Staging mismatch: missing {original - staged}; extra {staged - original}")
    rows = []
    seen = set()
    for relative in sorted(original):
        source = SOURCE / relative
        copy = STAGING / relative
        mapped = target(relative)
        final = ROOT / mapped
        final.resolve().relative_to(ROOT)
        if str(mapped).casefold() in seen:
            raise ValueError(f"Duplicate destination: {mapped}")
        seen.add(str(mapped).casefold())
        source_sha = digest(source)
        if source_sha != digest(copy):
            raise ValueError(f"Staging hash mismatch: {relative}")
        action = "moved-from-staging"
        if final.exists():
            if relative != Path("insert.stl") or digest(final) != source_sha:
                raise FileExistsError(final)
            action = "identical-existing-file"
        rows.append((relative, mapped, source.stat().st_size, source_sha, action))

    with MANIFEST.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("OriginalPath", "NewPath", "Bytes", "SHA256", "Action"))
        writer.writerows(rows)
    print(f"Verified {len(rows)} files against OneDrive; wrote {MANIFEST}", flush=True)
    # Whole repo directories retain empty folders, metadata, and the checkout layout.
    for name in ("A4T", "whopping_Voron_mods"):
        final = ROOT / DIRS[name]
        if final.exists():
            raise FileExistsError(final)
        final.parent.mkdir(parents=True, exist_ok=True)
        (STAGING / name).rename(final)
    for relative, mapped, _, _, action in rows:
        if relative.parts[0] in ("A4T", "whopping_Voron_mods"):
            continue
        final = ROOT / mapped
        if action == "identical-existing-file":
            (STAGING / relative).unlink()
        else:
            final.parent.mkdir(parents=True, exist_ok=True)
            if final.exists():
                raise FileExistsError(final)
            (STAGING / relative).rename(final)
    for relative, mapped, size, sha, _ in rows:
        final = ROOT / mapped
        if final.stat().st_size != size or digest(final) != sha:
            raise ValueError(f"Final verification failed: {relative}")
    for folder in sorted((p for p in STAGING.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        folder.rmdir()
    STAGING.rmdir()
    print(f"Organized and hash-verified {len(rows)} entries.", flush=True)


if __name__ == "__main__":
    main()
