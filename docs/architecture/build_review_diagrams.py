from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET


HERE = Path(__file__).resolve().parent
DRAWIO_PATH = HERE / "enterprise-mcp-platform-review.drawio"

COLORS = {
    "ink": "#17324D",
    "muted": "#526579",
    "line": "#7890A8",
    "blue": "#2E74B5",
    "blue_fill": "#EAF2F8",
    "purple": "#6F42C1",
    "purple_fill": "#F1ECFA",
    "orange": "#C56A00",
    "orange_fill": "#FFF3E0",
    "green": "#2E7D32",
    "green_fill": "#EAF6EC",
    "red": "#B42318",
    "red_fill": "#FDEDEC",
    "gray_fill": "#F5F7FA",
    "white": "#FFFFFF",
}


@dataclass(frozen=True)
class Box:
    id: str
    x: int
    y: int
    w: int
    h: int
    title: str
    detail: str = ""
    fill: str = COLORS["white"]
    stroke: str = COLORS["blue"]
    dashed: bool = False
    kind: str = "node"


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    label: str = ""
    dashed: bool = False
    color: str = COLORS["line"]
    source_anchor: tuple[float, float] | None = None
    target_anchor: tuple[float, float] | None = None
    points: tuple[tuple[float, float], ...] = ()
    label_offset: tuple[int, int] = (4, -5)
    arrow: bool = True


@dataclass
class Page:
    id: str
    name: str
    width: int
    height: int
    title: str
    subtitle: str
    boxes: list[Box] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    output: str = ""


def architecture_page() -> Page:
    p = Page(
        id="target-architecture",
        name="Target Architecture",
        width=1000,
        height=1320,
        title="Enterprise MCP Platform - Target Architecture",
        subtitle="One governed Gateway, separate Runtime per MCP server, and explicit identity/trust boundaries",
        output="enterprise-mcp-platform-target-architecture.svg",
    )
    p.boxes.extend(
        [
            Box("zone_clients", 30, 105, 940, 200, "CALLERS", "", COLORS["gray_fill"], "#C7D0D9", kind="zone"),
            Box("zone_identity", 30, 325, 940, 160, "IDENTITY", "", COLORS["purple_fill"], "#C7B6EA", kind="zone"),
            Box("zone_aws", 30, 505, 940, 540, "AWS / AGENTCORE", "", COLORS["blue_fill"], "#A9C9E7", kind="zone"),
            Box("zone_downstream", 30, 1070, 940, 220, "DOWNSTREAM", "", COLORS["orange_fill"], "#E4C08F", kind="zone"),
            Box("claude", 60, 145, 250, 80, "Claude Code", "Delegated Entra token", COLORS["white"], COLORS["purple"]),
            Box("aws_ai", 375, 145, 250, 80, "AI agent / application", "Runs in AWS; app-only caller", COLORS["white"], COLORS["purple"]),
            Box("other", 690, 145, 250, 80, "Future callers", "Other approved clients", COLORS["white"], COLORS["line"], dashed=True),
            Box("mcp_request", 390, 245, 220, 50, "MCP request", "HTTPS + Entra bearer JWT", COLORS["white"], COLORS["purple"]),
            Box("entra", 55, 355, 205, 100, "Microsoft Entra ID", "Enterprise MCP API\nclients and roles", COLORS["white"], COLORS["purple"]),
            Box("identity_future", 285, 355, 205, 100, "AgentCore Identity", "Inbound JWT capability\nOutbound broker off", COLORS["white"], COLORS["purple"], dashed=True),
            Box("iam", 515, 355, 205, 100, "AWS IAM", "Gateway + Runtime\nservice roles", COLORS["white"], COLORS["blue"]),
            Box("graph_identity", 745, 355, 205, 100, "Graph app identity", "Runtime obtains Token B\nseparate credential", COLORS["white"], COLORS["purple"]),
            Box("ingress", 365, 550, 270, 75, "Gateway ingress", "AWS-managed URL\nPrivateLink where supported", COLORS["white"], COLORS["green"]),
            Box("gateway", 335, 655, 330, 110, "AgentCore Gateway", "MCP + CUSTOM_JWT\nPolicy engine + semantic search", COLORS["white"], COLORS["blue"]),
            Box("sp_target", 335, 795, 330, 85, "sharepoint-mcp target", "Authorized Gateway target", COLORS["white"], COLORS["blue"]),
            Box("sp_runtime", 335, 910, 330, 95, "SharePoint Runtime", "FastMCP /mcp + VPC mode", COLORS["white"], COLORS["blue"]),
            Box("tfe", 60, 670, 230, 80, "Azure DevOps + TFE", "Controlled deploy + policy", COLORS["white"], COLORS["green"]),
            Box("ecr", 60, 915, 230, 80, "Central ECR", "Immutable service images", COLORS["white"], COLORS["green"]),
            Box("future_target", 720, 668, 220, 85, "Future targets", "Disabled until approved", COLORS["white"], COLORS["line"], dashed=True),
            Box("future_runtime", 720, 805, 220, 85, "Future Runtimes", "Separate images and owners", COLORS["white"], COLORS["line"], dashed=True),
            Box("sharepoint", 330, 1140, 340, 100, "Microsoft Graph / SharePoint", "Selected sites and paths\nSystem of record", COLORS["white"], COLORS["orange"]),
            Box("crm", 700, 1095, 240, 75, "CRM / Dataverse", "Future / disabled", COLORS["white"], COLORS["line"], dashed=True),
            Box("internal_api", 700, 1195, 240, 75, "Internal APIs", "Future / disabled", COLORS["white"], COLORS["line"], dashed=True),
        ]
    )
    p.edges.extend(
        [
            Edge("claude", "mcp_request", source_anchor=(0.5, 1), target_anchor=(0, 0.5), points=((185, 270),)),
            Edge("aws_ai", "mcp_request", source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
            Edge("other", "mcp_request", dashed=True, source_anchor=(0.5, 1), target_anchor=(1, 0.5), points=((815, 270),)),
            Edge("entra", "mcp_request", "issues token", color=COLORS["purple"], source_anchor=(0.5, 0), target_anchor=(0.25, 1), points=((157.5, 315), (445, 315)), label_offset=(4, -7)),
            Edge("mcp_request", "ingress", source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
            Edge("ingress", "gateway", source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
            Edge("gateway", "sp_target", "authorized route", color=COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), label_offset=(8, -4)),
            Edge("sp_target", "sp_runtime", "SigV4", color=COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), label_offset=(8, -4)),
            Edge("sp_runtime", "sharepoint", "Bearer Graph token", color=COLORS["orange"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), label_offset=(8, -4)),
            Edge("identity_future", "gateway", "CUSTOM_JWT capability", dashed=True, color=COLORS["purple"], source_anchor=(0.317073, 1), target_anchor=(0.045455, 0), label_offset=(-140, -5)),
            Edge("tfe", "gateway", color=COLORS["green"], source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
            Edge("tfe", "ecr", "publish image", color=COLORS["green"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), label_offset=(7, -5)),
            Edge("ecr", "sp_runtime", color=COLORS["green"], source_anchor=(1, 0.5), target_anchor=(0, 0.473684)),
            Edge("gateway", "future_target", dashed=True, source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
            Edge("future_target", "future_runtime", dashed=True, source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
            Edge("future_runtime", "crm", dashed=True, source_anchor=(0.454545, 1), target_anchor=(0.5, 0)),
            Edge("future_runtime", "internal_api", dashed=True, source_anchor=(1, 0.5), target_anchor=(1, 0.5), points=((960, 847.5), (960, 1232.5))),
        ]
    )
    return p


def identity_page() -> Page:
    p = Page(
        id="identity-data-flow",
        name="Identity and Data Flow",
        width=1000,
        height=1320,
        title="Identity, Authorization and Data Flow",
        subtitle="Caller identity, AWS workload authorization and downstream Graph identity remain separate",
        output="enterprise-mcp-platform-identity-flow.svg",
    )
    p.boxes.extend(
        [
            Box("flow_caller", 320, 100, 360, 80, "1. Approved caller", "Managed device or AWS AI workload", COLORS["white"], COLORS["purple"]),
            Box("flow_entra", 320, 220, 360, 80, "2. Microsoft Entra", "Authenticates caller and issues Token A", COLORS["purple_fill"], COLORS["purple"]),
            Box("flow_request", 320, 340, 360, 80, "3. Caller sends MCP request", "HTTPS + Bearer Token A to Gateway", COLORS["white"], COLORS["purple"]),
            Box("flow_jwt", 320, 460, 360, 80, "4. Gateway JWT validation", "Issuer, audience, client and scope/claims", COLORS["blue_fill"], COLORS["blue"]),
            Box("flow_policy", 320, 580, 360, 80, "5. Gateway Policy", "Deterministic tool and input authorization", COLORS["blue_fill"], COLORS["blue"]),
            Box("flow_invoke", 320, 700, 360, 80, "6. Gateway invokes Runtime target", "SigV4 using the Gateway service role", COLORS["blue_fill"], COLORS["blue"]),
            Box("flow_runtime", 320, 820, 360, 80, "7. Runtime validation", "Schema, site, path and write controls", COLORS["blue_fill"], COLORS["blue"]),
            Box("flow_graph", 320, 940, 360, 90, "8. Microsoft Graph / SharePoint", "Graph API call + Token B; selected permission", COLORS["orange_fill"], COLORS["orange"]),
            Box("token_a", 35, 235, 235, 105, "Credential boundary A", "Enterprise MCP API token\nreturned to caller", COLORS["white"], COLORS["purple"]),
            Box("deny", 35, 480, 235, 180, "Fail closed", "Invalid token, denied policy\nor invalid Runtime input", COLORS["red_fill"], COLORS["red"]),
            Box("iam_boundary", 730, 685, 235, 110, "AWS IAM boundary", "Gateway service role signs call\nRuntime role remains separate", COLORS["white"], COLORS["blue"]),
            Box("token_b", 730, 930, 235, 110, "Credential boundary B", "Runtime obtains Graph token\nnever reuse Token A", COLORS["white"], COLORS["orange"]),
            Box("audit", 35, 1090, 235, 120, "Audit metadata", "Decision + result metadata\nNo secrets or documents", COLORS["green_fill"], COLORS["green"]),
        ]
    )
    for source, target, label in [
        ("flow_caller", "flow_entra", "authenticate"),
        ("flow_entra", "flow_request", "issue Token A to caller"),
        ("flow_request", "flow_jwt", "MCP + Bearer Token A"),
        ("flow_jwt", "flow_policy", "validated context"),
        ("flow_policy", "flow_invoke", "allow"),
        ("flow_invoke", "flow_runtime", "SigV4"),
        ("flow_runtime", "flow_graph", "Graph API + Token B"),
    ]:
        p.edges.append(Edge(source, target, label, source_anchor=(0.5, 1), target_anchor=(0.5, 0)))
    p.edges.extend(
        [
            Edge("flow_jwt", "deny", dashed=True, color=COLORS["red"], source_anchor=(0, 0.5), target_anchor=(1, 0.25), points=((290, 500), (290, 525))),
            Edge("flow_policy", "deny", dashed=True, color=COLORS["red"], source_anchor=(0, 0.5), target_anchor=(1, 0.5), points=((295, 620), (295, 570))),
            Edge("flow_runtime", "deny", dashed=True, color=COLORS["red"], source_anchor=(0, 0.35), target_anchor=(1, 0.75), points=((280, 848), (280, 615))),
            Edge("flow_runtime", "audit", "decision + result", dashed=True, color=COLORS["green"], source_anchor=(0, 0.65), target_anchor=(1, 0.33), points=((285, 872), (285, 1129.6)), label_offset=(-110, -6)),
            Edge("token_a", "flow_request", dashed=True, color=COLORS["purple"], source_anchor=(1, 0.5), target_anchor=(0, 0.5), points=((295, 287.5), (295, 380))),
            Edge("iam_boundary", "flow_invoke", dashed=True, color=COLORS["blue"], source_anchor=(0, 0.5), target_anchor=(1, 0.5)),
            Edge("token_b", "flow_graph", dashed=True, color=COLORS["orange"], source_anchor=(0, 0.5), target_anchor=(1, 0.5)),
        ]
    )
    return p


def migration_page() -> Page:
    p = Page(
        id="migration-roadmap",
        name="Migration Roadmap",
        width=1000,
        height=1260,
        title="Migration Roadmap and Approval Gates",
        subtitle="Progression from PoC evidence to production; SharePoint data remains in place",
        output="enterprise-mcp-platform-migration.svg",
    )
    phases = [
        ("p0", 60, 140, "Phase 0", "Approve architecture", "Gate A: owners, classification\nand risk conditions"),
        ("p1", 540, 140, "Phase 1", "Complete implementation", "Graph, claims, Cedar,\nidempotency, supply chain"),
        ("p2", 60, 390, "Phase 2", "Deploy nonprod", "Gate B: real identity, network\nand Runtime path pass"),
        ("p3", 540, 390, "Phase 3", "Read-only pilot", "Gate C: named cohort, token flow\nand policy ENFORCE"),
        ("p4", 60, 640, "Phase 4", "AWS AI caller read", "Optional app-only\nagent or application"),
        ("p5", 540, 640, "Phase 5", "Controlled write pilot", "Gate D: one site/path, ticket,\nidempotency and ETag"),
        ("p6", 300, 920, "Phase 6", "Production rollout", "Separate production state;\ngradual enablement + rollback"),
    ]
    for phase_id, x, y, phase, title, detail in phases:
        p.boxes.append(
            Box(
                phase_id,
                x,
                y,
                400,
                160 if phase_id == "p6" else 170,
                f"{phase}\n{title}",
                detail,
                COLORS["gray_fill"] if phase_id == "p4" else COLORS["white"],
                COLORS["line"] if phase_id == "p4" else COLORS["blue"],
                dashed=phase_id == "p4",
            )
        )
    p.boxes.extend(
        [
            Box("prod_gate", 335, 840, 330, 55, "Production approval gate", "Evidence accepted by accountable owners", COLORS["red_fill"], COLORS["red"]),
            Box("deferred", 60, 1140, 555, 90, "Production approval remains deferred", "Nonprod approval does not enable writes, broad cohorts or future targets", COLORS["red_fill"], COLORS["red"]),
            Box("future", 655, 1140, 285, 90, "Phase 7 - New server cycle", "Separate contracts, owners,\nthreat delta and approval", COLORS["gray_fill"], COLORS["line"], dashed=True),
        ]
    )
    p.edges.extend(
        [
            Edge("p0", "p1", "exit gate", color=COLORS["blue"], source_anchor=(1, 0.5), target_anchor=(0, 0.5), label_offset=(-25, -7)),
            Edge("p1", "p2", "exit gate", color=COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), points=((740, 350), (260, 350)), label_offset=(4, -7)),
            Edge("p2", "p3", "exit gate", color=COLORS["blue"], source_anchor=(1, 0.5), target_anchor=(0, 0.5), label_offset=(-25, -7)),
            Edge("p3", "p5", "pilot exit", color=COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), label_offset=(7, -5)),
            Edge("p3", "p4", "optional branch", dashed=True, source_anchor=(0.25, 1), target_anchor=(1, 0.5), points=((640, 600), (500, 600), (500, 725)), label_offset=(4, -7)),
            Edge("p5", "prod_gate", "production evidence", color=COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), points=((740, 825), (500, 825)), label_offset=(4, 3)),
            Edge("prod_gate", "p6", "approve", color=COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0), label_offset=(7, -5)),
            Edge("prod_gate", "deferred", dashed=True, color=COLORS["red"], source_anchor=(0, 0.5), target_anchor=(0.5, 0), points=((280, 867.5), (280, 1120), (337.5, 1120))),
            Edge("p6", "future", "new server approval cycle", dashed=True, source_anchor=(0.8, 1), target_anchor=(0.5, 0), points=((620, 1110), (797.5, 1110)), label_offset=(4, -7)),
        ]
    )
    return p


def drawio_style(box: Box) -> str:
    if box.kind == "zone":
        return (
            "swimlane;html=1;rounded=1;startSize=34;horizontal=1;"
            f"fillColor={box.fill};strokeColor={box.stroke};fontColor={COLORS['ink']};"
            "fontStyle=1;fontSize=14;arcSize=8;spacingLeft=10;"
        )
    dashed = "1" if box.dashed else "0"
    return (
        "rounded=1;whiteSpace=wrap;html=1;arcSize=10;align=center;verticalAlign=middle;"
        f"fillColor={box.fill};strokeColor={box.stroke};fontColor={COLORS['ink']};"
        f"strokeWidth=2;dashed={dashed};fontSize=13;spacing=8;"
    )


def box_value(box: Box) -> str:
    title = escape(box.title).replace("\n", "<br>")
    if box.kind == "zone" or not box.detail:
        return title
    detail = escape(box.detail).replace("\n", "<br>")
    return f"<b>{title}</b><br><font color=\"{COLORS['muted']}\">{detail}</font>"


def page_to_drawio(page: Page) -> ET.Element:
    diagram = ET.Element("diagram", {"id": page.id, "name": page.name})
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1600",
            "dy": "1000",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(page.width),
            "pageHeight": str(page.height),
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = Box("page_title", 35, 20, page.width - 70, 42, page.title, fill=COLORS["white"], stroke=COLORS["white"])
    subtitle = Box("page_subtitle", 35, 62, page.width - 70, 30, page.subtitle, fill=COLORS["white"], stroke=COLORS["white"])
    for box in [title, subtitle, *page.boxes]:
        style = drawio_style(box)
        if box.id == "page_title":
            style += "fontSize=24;fontStyle=1;align=left;strokeOpacity=0;"
        elif box.id == "page_subtitle":
            style += f"fontSize=13;align=left;fontColor={COLORS['muted']};strokeOpacity=0;"
        cell = ET.SubElement(
            root,
            "mxCell",
            {"id": box.id, "value": box_value(box), "style": style, "vertex": "1", "parent": "1"},
        )
        ET.SubElement(cell, "mxGeometry", {"x": str(box.x), "y": str(box.y), "width": str(box.w), "height": str(box.h), "as": "geometry"})

    for index, edge in enumerate(page.edges, 1):
        dashed = "1" if edge.dashed else "0"
        anchor_style = ""
        if edge.source_anchor is not None:
            anchor_style += f"exitX={edge.source_anchor[0]};exitY={edge.source_anchor[1]};exitDx=0;exitDy=0;"
        if edge.target_anchor is not None:
            anchor_style += f"entryX={edge.target_anchor[0]};entryY={edge.target_anchor[1]};entryDx=0;entryDy=0;"
        arrow_style = "endArrow=block;endFill=1;endSize=9;" if edge.arrow else "endArrow=none;endFill=0;"
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": f"edge_{index}",
                "value": escape(edge.label),
                "style": (
                    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
                    f"strokeColor={edge.color};fontColor={COLORS['muted']};strokeWidth=2;dashed={dashed};"
                    + arrow_style
                    + "fontSize=11;labelBackgroundColor=#FFFFFF;"
                    + anchor_style
                ),
                "edge": "1",
                "parent": "1",
                "source": edge.source,
                "target": edge.target,
            },
        )
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if edge.points:
            points = ET.SubElement(geometry, "Array", {"as": "points"})
            for x, y in edge.points:
                ET.SubElement(points, "mxPoint", {"x": str(x), "y": str(y)})
        if edge.label:
            ET.SubElement(
                geometry,
                "mxPoint",
                {"x": str(edge.label_offset[0]), "y": str(edge.label_offset[1]), "as": "offset"},
            )
    return diagram


def svg_text_lines(box: Box) -> list[str]:
    lines = box.title.split("\n")
    if box.detail:
        lines.extend(box.detail.split("\n"))
    return lines


def anchor(box: Box, target: Box) -> tuple[float, float]:
    cx = box.x + box.w / 2
    cy = box.y + box.h / 2
    tx = target.x + target.w / 2
    ty = target.y + target.h / 2
    if abs(tx - cx) >= abs(ty - cy):
        return (box.x + box.w if tx > cx else box.x, cy)
    return (cx, box.y + box.h if ty > cy else box.y)


def edge_endpoint(box: Box, target: Box, normalized: tuple[float, float] | None) -> tuple[float, float]:
    if normalized is None:
        return anchor(box, target)
    return (box.x + box.w * normalized[0], box.y + box.h * normalized[1])


def line_midpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
    segments: list[tuple[tuple[float, float], tuple[float, float], float]] = []
    total = 0.0
    for start, end in zip(points, points[1:]):
        length = abs(end[0] - start[0]) + abs(end[1] - start[1])
        if length:
            segments.append((start, end, length))
            total += length
    remaining = total / 2
    for start, end, length in segments:
        if remaining <= length:
            ratio = remaining / length
            return (start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio)
        remaining -= length
    return points[-1]


def page_to_svg(page: Page) -> str:
    boxes = {box.id: box for box in page.boxes}
    marker_colors = {
        "line": COLORS["line"],
        "red": COLORS["red"],
        "purple": COLORS["purple"],
        "blue": COLORS["blue"],
        "orange": COLORS["orange"],
        "green": COLORS["green"],
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page.width}" height="{page.height}" viewBox="0 0 {page.width} {page.height}">',
        "<defs>",
        "<style>text{font-family:Arial,Helvetica,sans-serif}.title{font-size:27px;font-weight:700;fill:#17324D}.subtitle{font-size:16px;fill:#526579}.zone{font-size:17px;font-weight:700;fill:#17324D}.box-title{font-size:18px;font-weight:700;fill:#17324D}.box-detail{font-size:15px;fill:#526579}.edge-label{font-size:13px;fill:#526579}</style>",
    ]
    for marker_name, marker_color in marker_colors.items():
        parts.append(
            f'<marker id="arrow-{marker_name}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" '
            f'orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L9,4.5 L0,9 z" fill="{marker_color}"/></marker>'
        )
    parts.extend(
        [
            "</defs>",
            '<rect width="100%" height="100%" fill="#FFFFFF"/>',
            f'<text x="35" y="48" class="title">{escape(page.title)}</text>',
            f'<text x="35" y="76" class="subtitle">{escape(page.subtitle)}</text>',
        ]
    )

    for box in page.boxes:
        if box.kind != "zone":
            continue
        dash = ' stroke-dasharray="8 5"' if box.dashed else ""
        parts.append(f'<rect x="{box.x}" y="{box.y}" width="{box.w}" height="{box.h}" rx="12" fill="{box.fill}" stroke="{box.stroke}" stroke-width="1.5"{dash}/>')
        parts.append(f'<text x="{box.x + 14}" y="{box.y + 23}" class="zone">{escape(box.title)}</text>')

    for edge in page.edges:
        source = boxes[edge.source]
        target = boxes[edge.target]
        sx, sy = edge_endpoint(source, target, edge.source_anchor)
        tx, ty = edge_endpoint(target, source, edge.target_anchor)
        route: list[tuple[float, float]] = [(sx, sy), *edge.points, (tx, ty)]
        if not edge.points and sx != tx and sy != ty:
            mid_x = (sx + tx) / 2
            route = [(sx, sy), (mid_x, sy), (mid_x, ty), (tx, ty)]
        path = " ".join([f"M {route[0][0]:.1f} {route[0][1]:.1f}", *[f"L {x:.1f} {y:.1f}" for x, y in route[1:]]])
        dash = ' stroke-dasharray="7 5"' if edge.dashed else ""
        marker = next((name for name, color in marker_colors.items() if color == edge.color), "line")
        marker_attribute = f' marker-end="url(#arrow-{marker})"' if edge.arrow else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="{edge.color}" stroke-width="2" '
            f'stroke-linecap="butt" stroke-linejoin="miter"{marker_attribute}{dash}/>'
        )
        if edge.label:
            midpoint_x, midpoint_y = line_midpoint(route)
            lx = midpoint_x + edge.label_offset[0]
            ly = midpoint_y + edge.label_offset[1]
            parts.append(f'<rect x="{lx - 3:.1f}" y="{ly - 12:.1f}" width="{max(45, len(edge.label) * 6.2):.1f}" height="17" fill="#FFFFFF" opacity="0.92"/>')
            parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="edge-label">{escape(edge.label)}</text>')

    for box in page.boxes:
        if box.kind == "zone":
            continue
        dash = ' stroke-dasharray="8 5"' if box.dashed else ""
        parts.append(f'<rect x="{box.x}" y="{box.y}" width="{box.w}" height="{box.h}" rx="10" fill="{box.fill}" stroke="{box.stroke}" stroke-width="2"{dash}/>')
        lines = svg_text_lines(box)
        line_height = 22
        total = len(lines) * line_height
        start_y = box.y + (box.h - total) / 2 + 14
        title_line_count = len(box.title.split("\n"))
        for idx, line in enumerate(lines):
            cls = "box-title" if idx < title_line_count else "box-detail"
            parts.append(f'<text x="{box.x + box.w / 2:.1f}" y="{start_y + idx * line_height:.1f}" text-anchor="middle" class="{cls}">{escape(line)}</text>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def build() -> None:
    pages = [architecture_page(), identity_page(), migration_page()]
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": "2026-07-10T00:00:00.000Z",
            "agent": "Codex",
            "version": "24.7.17",
            "compressed": "false",
            "pages": str(len(pages)),
        },
    )
    for page in pages:
        mxfile.append(page_to_drawio(page))
        (HERE / page.output).write_text(page_to_svg(page), encoding="utf-8")

    ET.indent(mxfile, space="  ")
    DRAWIO_PATH.write_text(ET.tostring(mxfile, encoding="unicode") + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
