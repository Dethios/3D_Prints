# OneDrive library migration — November 10, 2026

Source: `C:\Users\vic-l\OneDrive\.codex_sync\3D Prints`. Destination: `D:\Build\3D Prints`.

[Import manifest](import-manifest.csv) records the original path, destination, byte count and SHA-256 for all 1,186 source files (6,042,805,654 bytes). It is a snapshot of the imported files **before** upstream Git updates. The [copy log](copy.log) records the staging copy: 1,186 files, zero failures. [The organization script](organize_import.py) compared every source and staged hash, routed the staged files and rechecked every final hash.

One identical Polymaker `insert.stl` was represented by the existing workspace copy; both originals had the same hash. The Ryobi ZIP is preserved, and its maker PDF and second STL variant were extracted and verified separately. The three checkout directories retain their own Git metadata; A4Tv2 was added from upstream rather than imported.

The original and destination hashes were checked again before sending 33 verified top-level entries to the Windows Recycle Bin. The OneDrive folder itself remains empty. Recover the original layout from the Recycle Bin or use the manifest to map files back to their old paths.

After source cleanup, A4T `main` fast-forwarded from `e1fc27113bb3061458f528db837d517c35e0b88a` to `d675d3518c5a6213bb0d9dcc7380bbf9342066df`. The previous commit remains at local branch `codex/pre-onedrive-update-2026-11-10`. The update changed the upstream README and added an image. A4Tv2 was cloned at `888755a97da9e1bd3062c35c914538342ef7d6f2`; `whopping_Voron_mods` remains at its imported `62268ed`. All three checkouts were verified clean.

This was an organization and provenance pass. Assets and existing print jobs were not edited, sliced, sent to the printer, or physically tested.

The [rewiring reorganization record](rewiring-reorganization.csv) supersedes the original destination column for the 19 rewiring parts. Its hashes match the imported files. The two ear projects moved from the workspace root to `Projects/` as sibling folders.
