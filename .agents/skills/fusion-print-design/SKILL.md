---
name: fusion-print-design
description: Use when creating or revising printable mechanical parts, inspecting assemblies, or exporting verified models through Autodesk Fusion MCP in this workspace.
---

# Fusion Print Design

Develop an editable CAD model and verified print exports for the requested part. Read [PRINT_WORKFLOW.md](../../../PRINT_WORKFLOW.md) for pathway selection and printer context. Locate the workspace from this skill's directory. For an existing CadQuery-owned part, preserve the generator as the source of truth unless the user requests a migration. Fusion can still provide assembly and dimension inspection.

## Identify the design and constraints

Capture mating dimensions, overall envelope, material, installed nozzle when known, loads, desired fit and finish. Use supplied measurements and existing references, marking unresolved values as assumptions. Read project attribution and mounting-family instructions before reusing source geometry.

Discover the currently callable Fusion MCP tools. List open documents with the read tool's document/open query and inspect the active command before editing. Confirm the intended target from the request and returned document identity. If an essential target is ambiguous, request clarification while inspecting available references. Preserve unsaved user work and use a dedicated design for new parts. If Fusion is unavailable, continue dimensional planning and report the access gap.

## Model and inspect

1. Query Fusion's apiDocumentation tool for the APIs used before writing a script. Use authoritative Autodesk documentation when MCP documentation is insufficient. Check application version and available methods instead of copying an assumed API signature.
2. For script execution, define run(_context: str) and let execution exceptions reach the tool. Set readOnly true only for inspection that creates, changes and deletes nothing. Read-only scripts also avoid executeTextCommand. Resolve an open modeling dialog before mutation using the server's supported workflow.
3. Express user-facing dimensions in millimeters and use documented unit conversion or explicit unit expressions in API calls. Verify internal length, area and volume units before reporting measurements. Parameterize dimensions that need iteration, including feature-specific allowances backed by fit evidence.
4. Use named components and bodies for functional parts. Preserve source mating patterns, assembly coordinates and color-part alignment. Choose wall thickness, hole orientation, fillets and support access using the intended material and slicer settings. Prefer understandable constrained features when a parametric timeline suits the design.
5. After each meaningful edit, read back critical dimensions, solid/body validity, expected component count, feature health and relevant assembly clearances. Capture a view when it helps assess shape or placement. Inspect state after partial failures before retrying so repeated commands do not duplicate bodies or features. After two failed recovery approaches, return partial evidence and the specific blocker.

## Export and hand off

Keep the editable Fusion document reference and revision. Save the Fusion document when the user has instructed saving, following the MCP server's save requirements. Export STEP for exchange and suitable print meshes into the requested project destination. Use a new revision name when replacing an existing result could lose recoverable work. Verify export existence, dimensions, units and tessellation at curved or fit-critical surfaces. Reimport or independently inspect exported geometry when needed to establish correctness.

Use voron-print-preflight for mesh, printer-profile and layer checks after export. Report completed work, model/document identity, parameters and assumptions, export paths and checks, save status and pending fit tests. Blender rendering is optional. Report completion of the requested design separately from physical fit evidence.

Main owns the Fusion session and approvals. Use the installed print3d role for CAD and fit work only after verifying its actual tool access, automation for reusable build/export helpers, reviewer for consequential independent review, and computer_use for supported UI tasks. Serialize Fusion and slicer mutations across agents. A skill or role declaration supplies workflow guidance, and runtime tools and permissions determine execution capability.
