---
name: printable-art-design
description: Prepare supplied or generated illustrations for printable silhouettes, openwork, relief, or multipart color. Use for art briefs, fitted visual review, local image edits, and editable artwork handoff to CAD.
---

# Printable Art Design

## Brief and artwork

1. Read [the CAD and print workflow](../../../PRINT_WORKFLOW.md) and the project's source and attribution notes. Record the approved mating files, print scale, orientation, attachment, dimensioned decoration envelope, and keepouts. Use a front-view carrier overlay for flat artwork. Record the path, SHA-256, provenance, and role of each key reference. Distinguish appearance, placement, palette, and protected geometry. Record rights before publication.
2. Define the visual checks before generation or editing. Identify the silhouette, recognizable features, intended holes and joins, and intended treatment such as openwork, height relief, paint, or filament colors. For traceable flat artwork, request a straight-on view, clean continuous edges, broad regions, and genuine transparency when the input format uses alpha. Keep placement guides separate from the artwork. Use the assigned printer, nozzle, and process to set any feature targets.
3. Start from the selected source when editing. Use direct vector or pixel edits for precise contour, palette, or alpha changes. Use ImageGen for requested bitmap concepts, or the assigned local ComfyUI route when authorized and available. Record which regions may change and which features must be preserved. Save the source, raw result, actual masks, and final fitted revision separately where applicable.

## Local ComfyUI

- In a fresh run folder, record the brief, exact inputs and mask hashes, prompt, workflow graph, model and seed, and the allowed attempts. When using a hosted service, record only metadata the service exposes. Keep graph preparation and offline checks separate from submission. An offline-only assignment uses saved files and checks without submitting renders.
- For authorized renders, verify the required local models and nodes. Main assigns one owner for submissions on the shared GPU. Inspect the queue before submitting. Record the job ID, executed workflow or history when available, saved output, and final image hash. Inspect queue, history, and saved outputs before retrying an interrupted or timed-out job. Preserve active runs and prior evidence.
- Compare the source, raw output, actual mask, and fitted or converted result before choosing a retry. Check whether the defect starts in the image, compositing, placement or scaling, or the contour or relief conversion. Change the identified cause within the assigned retry scope. When exact preservation is required, compare the final saved pixels outside the actual composite mask, including alpha for transparent artwork.

## Review and CAD handoff

1. Compare the final saved image with the scoped references and overlay the carrier at print size. Check clipping, keepouts, intended joins, unwanted islands, alpha where applicable, and the smallest meaningful strokes, gaps, stems, and reliefs in millimeters. Record findings against the exact file hash. Recheck changed criteria after another export changes the file.
2. Convert to the owning project's editable format. Use continuous curves and close solid profiles. Check self-intersections, overlaps, and intended holes and islands. For relief, record the source layers or height map and the height mapping. For color, distinguish hand-paint regions from actual multipart or filament regions. Preserve mating geometry and multipart coordinates. Use the target printer's actual layer and extrusion settings to verify feature survival during slicer preflight.
3. Keep a revision record with the brief, reference roles, final image path and SHA-256, fitted front view, editable inputs and their revision or hashes, units, origin, scale, orientation, color or relief mapping, feature measurements, and unresolved decisions. Record render completion, visual review, artwork selection, and CAD or slicer verification independently. CAD verifies the recorded inputs and placement on import. Label provisional fit studies with the candidate used.
