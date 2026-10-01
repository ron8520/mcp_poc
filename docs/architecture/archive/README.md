# Archived Architecture References

These files preserve earlier diagrams and optional delivery proposals. They are
outside the current maintenance set and are not deployment or validation evidence.
Use the [current reading guide](../../../README.md#architecture-references) for
the phase-one architecture, identity flows and release gates.

| Reference | Retained material |
| --- | --- |
| [Legacy review diagrams](enterprise-mcp-platform-review.drawio) | Earlier target architecture, identity flow and migration pages, with matching SVG/PNG exports. |
| [Azure DevOps workflows](devops-workflows.md) | Future operating-model proposal with historical paths; the current PoC uses ClickOps. |
| [Base-image sequence](mcp-base-image-sequence.mmd) | Optional shared-image proposal, outside current service builds. |
| [People Assist sequence](people-assist-sequence.mmd) | Earlier application-access example, replaced in the current review by the generic M2M sequence. |

`../build_review_diagrams.py` remains because the current phase-one generator
imports its drawing model. Running that older generator writes its legacy
Draw.io and SVG pages here; it does not refresh the archived PNGs. Current
diagrams are maintained by `../build_layered_architecture.py` and
`../build_sharepoint_review.py`.
