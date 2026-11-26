"""Apply the K2's four Moonraker lane assignments to a PrusaSlicer 2.9 project copy."""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.request import urlopen
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
MOONRAKER = "http://192.168.1.246:4409"
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PrusaSlicer"
INSTALL = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Prusa3D" / "PrusaSlicer"
CONSOLE = INSTALL / "prusa-slicer-console.exe"
GUI = INSTALL / "prusa-slicer.exe"
PROJECT_CONFIG = "Metadata/Slic3r_PE.config"
K2_PRESET = re.compile(r"Creality K2 \(0\.[2468] mm\)\Z")
COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")
PRESET_ONLY_KEYS = {
    "inherits", "compatible_printers", "compatible_printers_condition",
    "compatible_prints", "compatible_prints_condition",
}


class SyncError(Exception):
    pass


@dataclass(frozen=True)
class Slot:
    index: int
    spool_id: int
    name: str
    material: str
    vendor: str
    color: str

    @property
    def label(self):
        return f"1{'ABCD'[self.index]}"


def api(base, path):
    with urlopen(base.rstrip("/") + path, timeout=8) as reply:
        return json.load(reply)["result"]


def read_slots(base):
    box = api(base, "/printer/objects/query?box=state,map")["status"]["box"]
    if box.get("state") != "connect":
        raise SyncError("Moonraker reports that the CFS is disconnected.")
    mapping = box.get("map", {})
    if any(mapping.get("T1" + letter) != "T1" + letter for letter in "ABCD"):
        raise SyncError("The printer's current CFS mapping differs from T0→1A through T3→1D.")
    lanes = api(base, "/server/database/item?namespace=lane_data")["value"]
    slots = []
    for index, letter in enumerate("ABCD"):
        value = lanes.get(f"lane{index + 1}", {})
        spool_id = value.get("spool_id")
        color = value.get("color", "")
        name = value.get("spool_name") or value.get("name")
        material = value.get("helix_material") or value.get("material")
        if (str(value.get("lane")) != str(index) or type(spool_id) is not int or spool_id < 1
                or not name or not material or not COLOR.fullmatch(str(color))):
            raise SyncError(f"Slot 1{letter} needs a Spoolman assignment with a material and color.")
        slots.append(Slot(index, spool_id, name, material.upper(),
                          value.get("vendor_name") or value.get("vendor") or "", color.upper()))
    return slots


def profile_for(slot, overrides):
    override = overrides.get(str(slot.spool_id))
    if override is not None:
        if (not isinstance(override, dict) or str(override.get("material", "")).upper() != slot.material
                or not isinstance(override.get("preset"), str) or not override["preset"]):
            raise SyncError(f"Check the mapping for {slot.label}, spool #{slot.spool_id}.")
        return override["preset"]
    name = re.sub(r"[^a-z0-9]", "", slot.name.lower())
    if slot.vendor.casefold() == "polymaker":
        if slot.material in {"ASA", "ASA-X", "ASA-CF"} and "asacf08" in name:
            return "Polymaker ASA-CF08"
        if slot.material == "ASA" and "cf" not in name and "gf" not in name:
            return "Polymaker ASA"
        if (slot.material == "PLA" and "matte" in name
                and any(family in name for family in ("panchroma", "polychroma", "polyterra"))):
            return "Polymaker PolyChroma Matte"
    raise SyncError(f"No preset mapping for {slot.label}: spool #{slot.spool_id}, "
                    f"{slot.name} ({slot.material}). Add its approved preset to spool-presets.json.")


def ini_entries(text, project=False):
    marker = r"; " if project else ""
    pattern = re.compile(marker + r"([a-zA-Z][a-zA-Z0-9_]*)\s*=[ \t]*(.*)")
    entries = {}
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        if match:
            key, value = match.groups()
            if key in entries:
                raise SyncError(f"Duplicate configuration option: {key}.")
            entries[key] = value
    return entries


def installed_preset(data_dir, group, name):
    if name in {".", ".."} or any(c in name for c in ("\\", "/", ":", "\0")):
        raise SyncError(f"Invalid {group} preset name: {name!r}.")
    path = data_dir / group / (name + ".ini")
    if not path.is_file():
        raise SyncError(f"The installed {group} preset {name!r} could not be found.")
    return path


def assemble(data_dir, work, printer, selected, slots):
    keys = set()
    for preset in dict.fromkeys(selected):
        path = installed_preset(data_dir, "filament", preset)
        options = ini_entries(path.read_text(encoding="utf-8-sig"))
        if options.get("inherits"):
            raise SyncError(f"The mapping requires a standalone local filament preset: {preset}. "
                            "Save an independent copy in PrusaSlicer before mapping it.")
        keys.update(options)
    keys -= PRESET_ONLY_KEYS
    # PrusaSlicer does the per-filament vector assembly, including quoted G-code.
    scratch = work / "presets"
    scratch.mkdir()
    shutil.copy2(data_dir / "PrusaSlicer.ini", scratch)
    for group in ("printer", "print", "filament", "vendor"):
        path = data_dir / group
        if path.is_dir():
            shutil.copytree(path, scratch / group)
    for group in ("printer", "print"):
        installed_preset(scratch, group, printer)
    output = work / "assembled.ini"
    command = [str(CONSOLE), "--datadir", str(scratch), "--printer-profile", printer,
               "--print-profile", printer]
    for preset in selected:
        command += ["--material-profile", preset]
    result = subprocess.run(command + ["--save", str(output)],
                            capture_output=True, text=True, errors="replace", timeout=60)
    if result.returncode or not output.is_file():
        raise SyncError("PrusaSlicer could not assemble the installed filament presets.\n" +
                        (result.stderr or result.stdout).strip())
    rendered = ini_entries(output.read_text(encoding="utf-8-sig"))
    names = json.loads("[" + rendered.get("filament_settings_id", '""').replace('";"', '","') + "]")
    if names != selected:
        raise SyncError("PrusaSlicer did not retain the expected order of the four filament presets.")
    types = rendered.get("filament_type", "").split(";")
    if len(types) != 4:
        raise SyncError("PrusaSlicer did not return four filament material types.")
    for slot, preset, preset_material in zip(slots, selected, types):
        cfs_material = slot.material
        if preset == "Polymaker ASA-CF08" and cfs_material in {"ASA-X", "ASA-CF"}:
            cfs_material = "ASA"
        if preset_material != cfs_material:
            raise SyncError(f"{slot.label}: {preset} is {preset_material}, but the CFS reports "
                            f"{slot.material} for spool #{slot.spool_id}.")
    if keys - rendered.keys():
        raise SyncError("An installed preset has options not resolved by PrusaSlicer: " +
                        ", ".join(sorted(keys - rendered.keys())))
    updates = {key: rendered[key] for key in keys}
    updates["extruder_colour"] = ";".join(slot.color for slot in slots)
    return updates


def rewrite_project_config(data, updates):
    text = data.decode("utf-8")
    entries = ini_entries(text, project=True)
    printer = entries.get("printer_settings_id", "")
    if not K2_PRESET.fullmatch(printer) or entries.get("printer_technology") != "FFF":
        raise SyncError("Open a saved PrusaSlicer project that uses one of your Creality K2 nozzle presets.")
    if (entries.get("single_extruder_multi_material") != "1"
            or len(entries.get("nozzle_diameter", "").split(",")) != 4):
        raise SyncError("This project does not use the K2's four virtual extruders.")
    if entries.get("wipe_tower") != "0" or entries.get("single_extruder_multi_material_priming") != "0":
        raise SyncError("This project's wipe tower or slicer priming does not match your K2 CFS presets.")
    newline = "\r\n" if "\r\n" in text else "\n"
    patchable = re.compile(r"; ([a-zA-Z][a-zA-Z0-9_]*)\s*=")
    applied = set()
    lines = []
    for line in text.splitlines(keepends=True):
        match = patchable.match(line)
        if match and match[1] in updates:
            key = match[1]
            lines.append(f"; {key} = {updates[key]}{newline}")
            applied.add(key)
        else:
            lines.append(line)
    for key in sorted(updates.keys() - applied):
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += newline
        lines.append(f"; {key} = {updates[key]}{newline}")
    return "".join(lines).encode("utf-8"), printer


def next_output(project):
    stem = re.sub(r" - CFS synced(?: \(\d+\))?$", "", project.stem)
    base = project.with_name(stem + " - CFS synced.3mf")
    number = 2
    while base.exists():
        base = project.with_name(f"{stem} - CFS synced ({number}).3mf")
        number += 1
    return base


def sync(project, destination, base, data_dir, mapping_path):
    if project.suffix.lower() != ".3mf" or destination.suffix.lower() != ".3mf":
        raise SyncError("Choose a saved PrusaSlicer .3mf project.")
    if destination.exists() or project.resolve() == destination.resolve():
        raise SyncError("Choose a new output filename. Existing projects are preserved.")
    with ZipFile(project) as original:
        try:
            data = original.read(PROJECT_CONFIG)
        except KeyError as error:
            raise SyncError("The 3MF has no PrusaSlicer project settings.") from error
        _, printer = rewrite_project_config(data, {})
        slots = read_slots(base)
        overrides = json.loads(mapping_path.read_text(encoding="utf-8-sig"))
        if not isinstance(overrides, dict):
            raise SyncError("Spool preset mappings must be a JSON object keyed by spool ID.")
        profiles = [profile_for(slot, overrides) for slot in slots]
        with TemporaryDirectory(prefix="k2-cfs-", dir=destination.parent) as temp:
            work = Path(temp)
            updated, _ = rewrite_project_config(data, assemble(data_dir, work, printer, profiles, slots))
            staging = work / destination.name
            with ZipFile(staging, "w") as result:
                result.comment = original.comment
                for member in original.infolist():
                    if member.filename == PROJECT_CONFIG:
                        result.writestr(member, updated)
                    else:
                        with original.open(member) as reader, result.open(member, "w") as writer:
                            shutil.copyfileobj(reader, writer)
            # On Windows rename publishes the finished file without replacing an existing name.
            staging.rename(destination)
    return slots, profiles


def choose_file():
    from tkinter import Tk, filedialog
    root = Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
        return filedialog.askopenfilename(parent=root, title="Sync a saved K2 project from Moonraker",
                                          filetypes=[("PrusaSlicer project", "*.3mf")])
    finally:
        root.destroy()


def main():
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--open", action="store_true", help="open the synced copy in PrusaSlicer")
    parser.add_argument("--moonraker", default=MOONRAKER)
    parser.add_argument("--datadir", type=Path, default=DATA_DIR)
    parser.add_argument("--mappings", type=Path, default=HERE / "spool-presets.json")
    args = parser.parse_args()
    interactive = args.project is None
    if interactive:
        chosen = choose_file()
        if not chosen:
            return 0
        args.project = Path(chosen)
    output = args.output or next_output(args.project)
    try:
        slots, profiles = sync(args.project, output, args.moonraker, args.datadir, args.mappings)
        print(output)
        for slot, preset in zip(slots, profiles):
            print(f"T{slot.index} -> {slot.label}: #{slot.spool_id} {slot.name} "
                  f"({slot.material}, {slot.color}) -> {preset}")
        if interactive or args.open:
            subprocess.Popen([str(GUI), "--no-single-instance", str(output)])
    except (SyncError, OSError, KeyError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"CFS sync failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
