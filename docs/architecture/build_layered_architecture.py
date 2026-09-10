"""Build the reference-led two-page Enterprise MCP architecture."""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET


HERE = Path(__file__).resolve().parent
ASSET_DIR = HERE / "assets" / "aws"
DRAWIO_PATH = HERE / "enterprise-mcp-platform-layered.drawio"

COLORS = {
    "ink": "#232F3E",
    "muted": "#53606F",
    "line": "#687586",
    "aws": "#FF9900",
    "aws_fill": "#FFF7E8",
    "blue": "#147EBA",
    "blue_fill": "#EAF5FB",
    "purple": "#6B4EA0",
    "purple_fill": "#F2ECFA",
    "green": "#1D8102",
    "green_fill": "#EEF8EB",
    "red": "#D13212",
    "red_fill": "#FFF0ED",
    "gray_fill": "#F7F8F9",
    "white": "#FFFFFF",
}

ICONS = {
    "agentcore": "Arch_Amazon-Bedrock-AgentCore_64.svg",
    "lambda": "Arch_AWS-Lambda_64.svg",
    "cloudwatch": "Arch_Amazon-CloudWatch_64.svg",
    "cloudtrail": "Arch_AWS-CloudTrail_64.svg",
    "ecr": "Arch_Amazon-Elastic-Container-Registry_64.svg",
    "iam": "Arch_AWS-Identity-and-Access-Management_64.svg",
    "secrets": "Arch_AWS-Secrets-Manager_64.svg",
    "privatelink": "Arch_AWS-PrivateLink_64.svg",
    "vpc": "Arch_Amazon-Virtual-Private-Cloud_64.svg",
    "route53": "Arch_Amazon-Route-53_64.svg",
    "vpc_endpoint": "Res_Amazon-VPC_Endpoints_48.svg",
    "aws_account": "AWS-Account_32.svg",
    "aws_cloud": "AWS-Cloud_32.svg",
    "private_subnet": "Private-subnet_32.svg",
    "vpc_group": "Virtual-private-cloud-VPC_32.svg",
}


@dataclass(frozen=True)
class Zone:
    id: str
    x: int
    y: int
    w: int
    h: int
    title: str
    fill: str
    stroke: str
    icon: str | None = None


@dataclass(frozen=True)
class Node:
    id: str
    x: int
    y: int
    w: int
    h: int
    title: str
    detail: str = ""
    fill: str = COLORS["white"]
    stroke: str = COLORS["line"]
    icon: str | None = None
    dashed: bool = False
    kind: str = "node"


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    label: str = ""
    color: str = COLORS["line"]
    dashed: bool = False
    bidirectional: bool = False
    source_anchor: tuple[float, float] | None = None
    target_anchor: tuple[float, float] | None = None
    points: tuple[tuple[float, float], ...] = ()
    label_offset: tuple[int, int] = (4, -6)


@dataclass
class Page:
    id: str
    name: str
    title: str
    subtitle: str
    output: str
    width: int = 1920
    height: int = 1080
    zones: list[Zone] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)


def common_zones() -> list[Zone]:
    return [
        Zone("zone_identity", 20, 300, 245, 620, "IDENTITY & CALLERS", COLORS["gray_fill"], "#B8C1CC"),
        Zone("zone_aws", 290, 105, 1285, 850, "AWS CLOUD · AP-SOUTHEAST-2", COLORS["aws_fill"], "#E6A23C", "aws_cloud"),
        Zone("zone_shared", 995, 135, 550, 130, "SHARED SERVICES ACCOUNT", "#FFFDF8", "#C58B2A", "aws_account"),
        Zone("zone_network_account", 315, 300, 220, 620, "NETWORK / PLATFORM", "#FFFDF8", "#C58B2A", "aws_account"),
        Zone("zone_workload_account", 555, 300, 990, 620, "MCP WORKLOAD ACCOUNT", "#FFFDF8", "#C58B2A", "aws_account"),
        Zone("zone_managed", 580, 350, 340, 365, "GATEWAY & MANAGED SERVICES", "#F7FBFE", "#7DA9C4", "agentcore"),
        Zone("zone_runtime", 945, 350, 575, 535, "AGENTCORE RUNTIME · VPC MODE", "#F5FAF3", "#7AA116", "vpc_group"),
        Zone("zone_support", 580, 740, 340, 145, "SUPPORT SERVICES", "#FAFAFA", "#9AA5B1", "aws_account"),
        Zone("zone_downstream", 1600, 300, 300, 620, "DOWNSTREAM SYSTEMS", COLORS["blue_fill"], "#9CC8E1"),
    ]


def shared_nodes(*, target: bool) -> list[Node]:
    app_fill = COLORS["white"] if target else COLORS["red_fill"]
    app_stroke = COLORS["purple"] if target else COLORS["red"]
    app_dashed = not target
    policy_detail = "Cedar · ENFORCE required" if target else "Cedar · current LOG_ONLY"
    return [
        Node("entra", 45, 350, 195, 95, "Microsoft Entra ID", "Enterprise MCP API\nToken A audience", COLORS["white"], COLORS["purple"]),
        Node(
            "user",
            45,
            500,
            195,
            85,
            "Employee via AI app / client" if target else "Claude Code user",
            "Delegated user token" if target else "Signed-in employee",
        ),
        Node(
            "apps",
            45,
            650,
            195,
            95,
            "Background workload",
            "Workflow · scheduler · daemon\napp-only token" if target else "People Assist · workflow\napp-only ingress gated",
            app_fill,
            app_stroke,
            dashed=app_dashed,
        ),
        Node("enterprise_route", 335, 365, 180, 80, "Enterprise route", "Approved private path", COLORS["white"], COLORS["green"], "privatelink"),
        Node("private_dns", 335, 480, 180, 80, "Route 53 private DNS", "Gateway regional hostname", COLORS["white"], COLORS["purple"], "route53"),
        Node("gateway_vpce", 335, 595, 180, 90, "Gateway interface endpoint", "AWS PrivateLink\nVPC endpoint ENIs", COLORS["white"], COLORS["blue"], "vpc_endpoint"),
        Node("endpoint_controls", 335, 730, 180, 85, "Endpoint policy + SG", "Network controls", COLORS["white"], COLORS["green"], "vpc"),
        Node("policy", 610, 380, 280, 85, "AgentCore Policy Engine", policy_detail, COLORS["white"], COLORS["blue"], "agentcore"),
        Node("gateway", 610, 495, 280, 95, "AgentCore Gateway", "MCP · CUSTOM_JWT", COLORS["white"], COLORS["blue"], "agentcore"),
        Node("build", 1020, 170, 190, 60, "CI / Docker build", "Signed service image", COLORS["white"], COLORS["line"]),
        Node("ecr", 1290, 155, 220, 90, "Amazon ECR", "Immutable service images", COLORS["white"], "#ED7100", "ecr"),
        Node("iam", 600, 775, 90, 75, "IAM", icon="iam", kind="icon_card"),
        Node("secrets", 705, 775, 90, 75, "Secrets", icon="secrets", kind="icon_card"),
        Node("cloudwatch", 810, 775, 90, 75, "Observability", icon="cloudwatch", kind="icon_card"),
        Node("graph", 1625, 390, 250, 90, "Microsoft Graph", "SharePoint first example"),
        Node("sharepoint", 1625, 520, 250, 100, "SharePoint Online", "Delegated ACLs\nSites.Selected for app-only"),
        Node("crm_system", 1625, 685, 250, 80, "Microsoft CRM", "Future · choose delegated / M2M", COLORS["gray_fill"], COLORS["line"], dashed=True),
        Node("internal_system", 1625, 800, 250, 80, "Internal / other platform", "Future · identity decision per server", COLORS["gray_fill"], COLORS["line"], dashed=True),
    ]


def shared_ingress_edges(*, target: bool) -> list[Edge]:
    app_color = COLORS["purple"] if target else COLORS["red"]
    return [
        Edge("user", "entra", "Acquire delegated Token A", COLORS["purple"], bidirectional=True, source_anchor=(0.35, 0), target_anchor=(0.35, 1)),
        Edge("apps", "entra", "client_credentials · gated" if not target else "client_credentials Token A", app_color, dashed=not target, bidirectional=True, source_anchor=(0.75, 0), target_anchor=(0.75, 1), points=((250, 625), (250, 470))),
        Edge("user", "enterprise_route", "MCP request + Token A", COLORS["purple"], source_anchor=(1, 0.45), target_anchor=(0, 0.45), points=((285, 538), (285, 401))),
        Edge("apps", "enterprise_route", "MCP + Token A · gated" if not target else "MCP request + Token A", app_color, dashed=not target, source_anchor=(1, 0.55), target_anchor=(0, 0.8), points=((300, 702), (300, 429))),
        Edge("private_dns", "gateway_vpce", "resolves", COLORS["purple"], dashed=True, source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
        Edge("endpoint_controls", "gateway_vpce", "enforces", COLORS["green"], dashed=True, source_anchor=(0.5, 0), target_anchor=(0.5, 1)),
        Edge("enterprise_route", "gateway_vpce", "private ingress", COLORS["green"], source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
        Edge("gateway_vpce", "gateway", "MCP request", COLORS["blue"], source_anchor=(1, 0.5), target_anchor=(0, 0.5), points=((550, 640), (550, 542))),
        Edge("gateway", "policy", "policy check / allow or deny", COLORS["blue"], bidirectional=True, source_anchor=(0.5, 0), target_anchor=(0.5, 1)),
        Edge("build", "ecr", "Push image", "#ED7100", source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
    ]


def current_page() -> Page:
    p = Page(
        id="current-poc",
        name="Current implemented PoC",
        title="Enterprise MCP Platform · Current implemented PoC",
        subtitle="Current repository PoC · solid arrows are active; red dashed paths are gated; gray dashed servers are future",
        output="enterprise-mcp-platform-current-poc.svg",
        zones=common_zones(),
    )
    p.nodes.extend(shared_nodes(target=False))
    p.nodes.extend(
        [
            Node("interceptor", 595, 625, 145, 75, "Request Lambda", "Bearer copy only", COLORS["white"], "#ED7100", "lambda"),
            Node("identity", 755, 625, 145, 75, "Outbound Identity", "Not used in current PoC", COLORS["red_fill"], COLORS["red"], "agentcore", dashed=True),
            Node("delegated_runtime", 970, 385, 250, 95, "SharePoint MCP · delegated", "Runtime lane · IAM/SigV4\nMSAL OBO in server", COLORS["white"], COLORS["green"], "agentcore"),
            Node("application_runtime", 970, 510, 250, 95, "SharePoint MCP · application", "IAM/SigV4 · client_credentials\napp-only JWT ingress gated", COLORS["red_fill"], COLORS["red"], "agentcore", dashed=True),
            Node("sp_tools_group", 1240, 380, 250, 240, "Shared SharePoint tool contract", fill=COLORS["white"], stroke=COLORS["blue"], kind="group"),
            Node("sp_tool_list", 1270, 425, 190, 38, "List site content", fill="#FFB4A8", stroke="#E36B5D", kind="pill"),
            Node("sp_tool_read", 1270, 480, 190, 38, "Read bounded PDF text", fill="#FFB4A8", stroke="#E36B5D", kind="pill"),
            Node("sp_tool_upload", 1270, 535, 190, 38, "Upload UTF-8 file", fill="#FFB4A8", stroke="#E36B5D", kind="pill"),
            Node("crm_runtime", 970, 665, 250, 80, "CRM MCP Runtime", "Disabled · tool contract TBD", COLORS["gray_fill"], COLORS["line"], "agentcore", dashed=True),
            Node("crm_tools", 1270, 685, 190, 38, "Tools TBD", fill=COLORS["gray_fill"], stroke=COLORS["line"], dashed=True, kind="pill"),
            Node("internal_runtime", 970, 775, 250, 80, "Internal MCP Runtime", "Future reviewed boundary", COLORS["gray_fill"], COLORS["line"], "agentcore", dashed=True),
            Node("internal_tools", 1270, 795, 190, 38, "Tools TBD", fill=COLORS["gray_fill"], stroke=COLORS["line"], dashed=True, kind="pill"),
            Node("current_note", 20, 975, 1880, 70, "CURRENT PoC", "SharePoint delegated is the active validation lane. The application Runtime/target is present in Terraform, app-only JWT ingress is gated, and Cedar remains LOG_ONLY. CRM and Internal are future boundaries. No outbound identity provider or resolver is implemented.", COLORS["gray_fill"], "#B8C1CC", kind="note"),
        ]
    )
    p.edges.extend(shared_ingress_edges(target=False))
    p.edges.extend(
        [
            Edge("gateway", "interceptor", "delegated transform", "#ED7100", bidirectional=True, source_anchor=(0.25, 1), target_anchor=(0.5, 0)),
            Edge("gateway", "delegated_runtime", "IAM/SigV4", COLORS["blue"], source_anchor=(1, 0.35), target_anchor=(0, 0.5), label_offset=(3, -14)),
            Edge("gateway", "application_runtime", "IAM/SigV4", COLORS["red"], dashed=True, source_anchor=(1, 0.75), target_anchor=(0, 0.5), label_offset=(3, 12)),
            Edge("delegated_runtime", "entra", "OBO Graph token", COLORS["purple"], bidirectional=True, source_anchor=(0.5, 0), target_anchor=(0.5, 0), points=((1095, 285), (142, 285))),
            Edge("application_runtime", "entra", "Graph app token · gated", COLORS["red"], dashed=True, bidirectional=True, source_anchor=(0.35, 0), target_anchor=(0.85, 0), points=((1058, 270), (210, 270))),
            Edge("ecr", "delegated_runtime", "Pull immutable image", "#ED7100", source_anchor=(0.5, 1), target_anchor=(0.5, 0), points=((1400, 330), (1120, 330), (1120, 375))),
            Edge("delegated_runtime", "sp_tools_group", color=COLORS["green"], source_anchor=(1, 0.45), target_anchor=(0, 0.25)),
            Edge("application_runtime", "sp_tools_group", color=COLORS["red"], dashed=True, source_anchor=(1, 0.55), target_anchor=(0, 0.72)),
            Edge("sp_tools_group", "graph", "Graph request with lane token", COLORS["purple"], source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
            Edge("graph", "sharepoint", "SharePoint operation", COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
            Edge("crm_runtime", "crm_system", color=COLORS["line"], dashed=True, source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
            Edge("internal_runtime", "internal_system", color=COLORS["line"], dashed=True, source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
        ]
    )
    return p


def target_page() -> Page:
    p = Page(
        id="target-identity",
        name="Target identity routing",
        title="Enterprise MCP Platform · Target identity routing",
        subtitle="PoC validation target · AgentCore Identity brokers delegated OBO and autonomous M2M; not the current implementation",
        output="enterprise-mcp-platform-target-identity.svg",
        zones=common_zones(),
    )
    p.nodes.extend(shared_nodes(target=True))
    p.nodes.extend(
        [
            Node("interceptor", 595, 625, 145, 75, "Request Lambda", "Signed JWT copy only", COLORS["white"], "#ED7100", "lambda"),
            Node("identity", 755, 625, 145, 75, "AgentCore Identity", "OBO + M2M\nOAuth broker", COLORS["white"], COLORS["purple"], "agentcore"),
            Node("delegated_runtime", 970, 385, 250, 95, "Delegated Runtime lane", "SharePoint first example\n3. OBO to downstream Token C", COLORS["white"], COLORS["green"], "agentcore"),
            Node("application_runtime", 970, 510, 250, 95, "M2M Runtime · domain D1", "Workflow / daemon\nIdentity M2M downstream", COLORS["white"], COLORS["green"], "agentcore"),
            Node("resolver", 970, 650, 250, 95, "Default-deny resolver", "caller + action + resource key\n→ approved M2M provider", COLORS["white"], COLORS["blue"]),
            Node("sp_tools_group", 1240, 380, 250, 240, "SharePoint MCP contract · first example", fill=COLORS["white"], stroke=COLORS["blue"], kind="group"),
            Node("sp_tool_list", 1270, 425, 190, 38, "List site content", fill="#FFB4A8", stroke="#E36B5D", kind="pill"),
            Node("sp_tool_read", 1270, 480, 190, 38, "Read bounded PDF text", fill="#FFB4A8", stroke="#E36B5D", kind="pill"),
            Node("sp_tool_upload", 1270, 535, 190, 38, "Upload UTF-8 file", fill="#FFB4A8", stroke="#E36B5D", kind="pill"),
            Node("provider_profiles", 1240, 650, 250, 135, "Lane-scoped Identity providers", "OBO provider · M2M providers\nARN-scoped by workload IAM", COLORS["white"], COLORS["purple"]),
            Node("config_bundle", 1240, 810, 250, 55, "Pinned configuration bundle", "Versioned mapping candidate", COLORS["white"], "#E7157B"),
            Node("target_note", 20, 975, 1880, 70, "TARGET", "Employee-facing AI apps use delegated/OBO when user ACLs apply; autonomous workflows use M2M. Both lanes use AgentCore Identity with separate provider-ARN IAM boundaries. Callers never select auth mode or credentials.", COLORS["gray_fill"], "#B8C1CC", kind="note"),
        ]
    )
    p.edges.extend(shared_ingress_edges(target=True))
    p.edges.extend(
        [
            Edge("gateway", "identity", "1. OBO A → B", COLORS["purple"], bidirectional=True, source_anchor=(0.75, 1), target_anchor=(0.5, 0)),
            Edge("identity", "entra", "Entra OAuth endpoint", COLORS["purple"], bidirectional=True, source_anchor=(0.5, 0), target_anchor=(0.5, 0), points=((827, 285), (142, 285))),
            Edge("gateway", "delegated_runtime", "2. Token B", COLORS["purple"], source_anchor=(1, 0.30), target_anchor=(0, 0.5), label_offset=(3, -22)),
            Edge("delegated_runtime", "identity", color=COLORS["purple"], bidirectional=True, source_anchor=(0, 0.8), target_anchor=(1, 0.35), points=((940, 461), (940, 651))),
            Edge("gateway", "interceptor", "app caller context", "#ED7100", bidirectional=True, source_anchor=(0.25, 1), target_anchor=(0.5, 0)),
            Edge("gateway", "application_runtime", "SigV4 + JWT", COLORS["blue"], source_anchor=(1, 0.75), target_anchor=(0, 0.5), label_offset=(3, 12)),
            Edge("application_runtime", "resolver", "validated caller context", COLORS["green"], source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
            Edge("resolver", "provider_profiles", "approved profile", COLORS["blue"], source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
            Edge("provider_profiles", "identity", "M2M request", COLORS["purple"], source_anchor=(0, 0.75), target_anchor=(1, 0.75), points=((930, 751), (930, 681))),
            Edge("identity", "application_runtime", "M2M token", COLORS["green"], source_anchor=(1, 0.35), target_anchor=(0, 0.85), points=((940, 651), (940, 591))),
            Edge("config_bundle", "resolver", color="#E7157B", dashed=True, source_anchor=(0, 0.5), target_anchor=(1, 0.8), points=((1230, 837), (1230, 726))),
            Edge("ecr", "delegated_runtime", "Pull immutable image", "#ED7100", source_anchor=(0.5, 1), target_anchor=(0.5, 0), points=((1400, 330), (1120, 330), (1120, 375))),
            Edge("delegated_runtime", "sp_tools_group", color=COLORS["green"], source_anchor=(1, 0.45), target_anchor=(0, 0.25)),
            Edge("application_runtime", "sp_tools_group", color=COLORS["green"], source_anchor=(1, 0.55), target_anchor=(0, 0.72)),
            Edge("sp_tools_group", "graph", "lane token", COLORS["purple"], source_anchor=(1, 0.5), target_anchor=(0, 0.5)),
            Edge("graph", "sharepoint", "SharePoint authorization", COLORS["blue"], source_anchor=(0.5, 1), target_anchor=(0.5, 0)),
        ]
    )
    return p


def icon_data(icon: str) -> str:
    raw = (ASSET_DIR / ICONS[icon]).read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")


def node_value(node: Node) -> str:
    title = escape(node.title).replace("\n", "<br>")
    if not node.detail:
        return f"<b>{title}</b>"
    detail = escape(node.detail).replace("\n", "<br>")
    return f"<b>{title}</b><br><font color=\"{COLORS['muted']}\">{detail}</font>"


def add_geometry(cell: ET.Element, x: float, y: float, w: float, h: float) -> None:
    ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})


def page_to_drawio(page: Page) -> ET.Element:
    diagram = ET.Element("diagram", {"id": page.id, "name": page.name})
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": str(page.width),
            "dy": str(page.height),
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

    for zone in page.zones:
        spacing_left = "42" if zone.icon else "10"
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": zone.id,
                "value": escape(zone.title),
                "style": (
                    "swimlane;html=1;rounded=0;startSize=34;horizontal=1;collapsible=0;"
                    f"fillColor={zone.fill};strokeColor={zone.stroke};fontColor={COLORS['ink']};"
                    f"fontStyle=1;fontSize=14;spacingLeft={spacing_left};"
                ),
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(cell, zone.x, zone.y, zone.w, zone.h)
        if zone.icon:
            icon_cell = ET.SubElement(
                root,
                "mxCell",
                {
                    "id": f"{zone.id}_icon",
                    "value": "",
                    "style": f"shape=image;image={icon_data(zone.icon)};aspect=fixed;imageAspect=0;strokeColor=none;fillColor=none;",
                    "vertex": "1",
                    "parent": "1",
                },
            )
            add_geometry(icon_cell, zone.x + 10, zone.y + 6, 22, 22)

    for node in page.nodes:
        dashed = "1" if node.dashed else "0"
        if node.kind == "icon_card":
            spacing_left = "4"
            align = "center"
            vertical_align = "bottom"
            spacing_bottom = "6"
            spacing_top = "0"
            rounded = "0"
            font_size = "13"
        elif node.kind == "pill":
            spacing_left = "4"
            align = "center"
            vertical_align = "middle"
            spacing_bottom = "0"
            spacing_top = "0"
            rounded = "1;arcSize=50"
            font_size = "11"
        elif node.kind == "group":
            spacing_left = "12"
            align = "left"
            vertical_align = "top"
            spacing_bottom = "0"
            spacing_top = "10"
            rounded = "0"
            font_size = "12"
        else:
            spacing_left = "58" if node.icon else "10"
            align = "left" if node.icon or node.kind == "note" else "center"
            vertical_align = "middle"
            spacing_bottom = "0"
            spacing_top = "0"
            rounded = "0"
            font_size = "13"
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": node.id,
                "value": node_value(node),
                "style": (
                    f"rounded={rounded};whiteSpace=wrap;html=1;verticalAlign={vertical_align};"
                    f"align={align};spacingLeft={spacing_left};spacingRight=8;spacingTop={spacing_top};spacingBottom={spacing_bottom};"
                    f"fillColor={node.fill};strokeColor={node.stroke};fontColor={COLORS['ink']};"
                    f"strokeWidth={'1' if node.kind == 'pill' else '2'};dashed={dashed};fontSize={font_size};"
                ),
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(cell, node.x, node.y, node.w, node.h)
        if node.icon:
            size = min(42, node.h - 16)
            if node.kind == "icon_card":
                icon_x = node.x + (node.w - size) / 2
                icon_y = node.y + 7
            else:
                icon_x = node.x + 10
                icon_y = node.y + (node.h - size) / 2
            icon_cell = ET.SubElement(
                root,
                "mxCell",
                {
                    "id": f"{node.id}_icon",
                    "value": "",
                    "style": f"shape=image;image={icon_data(node.icon)};aspect=fixed;imageAspect=0;strokeColor=none;fillColor=none;",
                    "vertex": "1",
                    "parent": "1",
                },
            )
            add_geometry(icon_cell, icon_x, icon_y, size, size)

    for idx, edge in enumerate(page.edges, 1):
        anchor_style = ""
        if edge.source_anchor:
            anchor_style += f"exitX={edge.source_anchor[0]};exitY={edge.source_anchor[1]};exitDx=0;exitDy=0;"
        if edge.target_anchor:
            anchor_style += f"entryX={edge.target_anchor[0]};entryY={edge.target_anchor[1]};entryDx=0;entryDy=0;"
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": f"edge_{idx}",
                "value": escape(edge.label),
                "style": (
                    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
                    f"strokeColor={edge.color};fontColor={COLORS['muted']};strokeWidth=2;"
                    f"dashed={'1' if edge.dashed else '0'};endArrow=block;endFill=1;endSize=9;"
                    f"startArrow={'block' if edge.bidirectional else 'none'};startFill=1;startSize=9;"
                    "fontSize=11;labelBackgroundColor=#FFFFFF;" + anchor_style
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
            ET.SubElement(geometry, "mxPoint", {"x": str(edge.label_offset[0]), "y": str(edge.label_offset[1]), "as": "offset"})

    for node_id, text_value, y, size, bold in [
        ("page_title", page.title, 20, 28, True),
        ("page_subtitle", page.subtitle, 62, 15, False),
    ]:
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": node_id,
                "value": escape(text_value),
                "style": (
                    "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
                    f"fontColor={COLORS['ink'] if bold else COLORS['muted']};fontSize={size};fontStyle={'1' if bold else '0'};"
                ),
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(cell, 20, y, page.width - 40, 40 if bold else 30)
    return diagram


def node_anchor(node: Node, other: Node, normalized: tuple[float, float] | None) -> tuple[float, float]:
    if normalized:
        return node.x + node.w * normalized[0], node.y + node.h * normalized[1]
    cx, cy = node.x + node.w / 2, node.y + node.h / 2
    ox, oy = other.x + other.w / 2, other.y + other.h / 2
    if abs(ox - cx) >= abs(oy - cy):
        return (node.x + node.w if ox > cx else node.x, cy)
    return (cx, node.y + node.h if oy > cy else node.y)


def route_points(edge: Edge, nodes: dict[str, Node]) -> list[tuple[float, float]]:
    source, target = nodes[edge.source], nodes[edge.target]
    start = node_anchor(source, target, edge.source_anchor)
    end = node_anchor(target, source, edge.target_anchor)
    points = [start, *edge.points, end]
    if not edge.points and start[0] != end[0] and start[1] != end[1]:
        mid = (start[0] + end[0]) / 2
        points = [start, (mid, start[1]), (mid, end[1]), end]
    orthogonal: list[tuple[float, float]] = [points[0]]
    for point in points[1:]:
        previous = orthogonal[-1]
        if previous[0] != point[0] and previous[1] != point[1]:
            orthogonal.append((point[0], previous[1]))
        orthogonal.append(point)
    return orthogonal


def midpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
    lengths = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(points, points[1:])]
    remaining = sum(lengths) / 2
    for start, end, length in zip(points, points[1:], lengths):
        if length and remaining <= length:
            ratio = remaining / length
            return start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio
        remaining -= length
    return points[-1]


def page_to_svg(page: Page) -> str:
    nodes = {node.id: node for node in page.nodes}
    title_prefix, separator, title_suffix = page.title.partition(" · ")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page.width}" height="{page.height}" viewBox="0 0 {page.width} {page.height}">',
        "<defs>",
        "<style>text{font-family:Arial,Helvetica,sans-serif}.title{font-size:28px;font-weight:700;fill:#232F3E}.subtitle{font-size:15px;fill:#53606F}.zone{font-size:14px;font-weight:700;fill:#232F3E}.node-title{font-size:13px;font-weight:700;fill:#232F3E}.node-detail{font-size:11px;fill:#53606F}.edge-label{font-size:10px;fill:#53606F}</style>",
    ]
    for name, color in [("line", COLORS["line"]), ("blue", COLORS["blue"]), ("purple", COLORS["purple"]), ("green", COLORS["green"]), ("red", COLORS["red"]), ("orange", "#ED7100"), ("pink", "#E7157B")]:
        parts.append(f'<marker id="arrow-{name}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto-start-reverse"><path d="M0,0 L9,4.5 L0,9 z" fill="{color}"/></marker>')
    parts.extend(["</defs>", '<rect width="100%" height="100%" fill="#FFFFFF"/>'])
    if separator:
        parts.append(f'<text x="20" y="50" class="title">{escape(title_prefix)}</text>')
        parts.append(f'<text x="344" y="50" class="title">· {escape(title_suffix)}</text>')
    else:
        parts.append(f'<text x="20" y="50" class="title">{escape(page.title)}</text>')
    parts.append(f'<text x="20" y="84" class="subtitle">{escape(page.subtitle)}</text>')

    for zone in page.zones:
        parts.append(f'<rect x="{zone.x}" y="{zone.y}" width="{zone.w}" height="{zone.h}" fill="{zone.fill}" stroke="{zone.stroke}" stroke-width="1.5"/>')
        parts.append(f'<line x1="{zone.x}" y1="{zone.y + 34}" x2="{zone.x + zone.w}" y2="{zone.y + 34}" stroke="{zone.stroke}" stroke-width="1"/>')
        if zone.icon:
            parts.append(f'<image href="{icon_data(zone.icon)}" x="{zone.x + 10}" y="{zone.y + 6}" width="22" height="22"/>')
            title_x = zone.x + 42
        else:
            title_x = zone.x + 12
        parts.append(f'<text x="{title_x}" y="{zone.y + 23}" class="zone">{escape(zone.title)}</text>')

    color_names = {COLORS["line"]: "line", COLORS["blue"]: "blue", COLORS["purple"]: "purple", COLORS["green"]: "green", COLORS["red"]: "red", "#ED7100": "orange", "#E7157B": "pink"}
    for edge in page.edges:
        points = route_points(edge, nodes)
        path = " ".join([f"M {points[0][0]:.1f} {points[0][1]:.1f}", *[f"L {x:.1f} {y:.1f}" for x, y in points[1:]]])
        dash = ' stroke-dasharray="7 5"' if edge.dashed else ""
        marker = color_names.get(edge.color, "line")
        marker_start = f' marker-start="url(#arrow-{marker})"' if edge.bidirectional else ""
        parts.append(f'<path d="{path}" fill="none" stroke="{edge.color}" stroke-width="2" stroke-linecap="butt" stroke-linejoin="miter" marker-end="url(#arrow-{marker})"{marker_start}{dash}/>')
        if edge.label:
            mx, my = midpoint(points)
            mx += edge.label_offset[0]
            my += edge.label_offset[1]
            width = max(52, len(edge.label) * 5.8)
            parts.append(f'<rect x="{mx - 3:.1f}" y="{my - 12:.1f}" width="{width:.1f}" height="16" fill="#FFFFFF" opacity="0.94"/>')
            parts.append(f'<text x="{mx:.1f}" y="{my:.1f}" class="edge-label">{escape(edge.label)}</text>')

    for node in page.nodes:
        dash = ' stroke-dasharray="7 5"' if node.dashed else ""
        radius = min(node.h / 2, 22) if node.kind == "pill" else 0
        stroke_width = 1 if node.kind == "pill" else 2
        parts.append(f'<rect x="{node.x}" y="{node.y}" width="{node.w}" height="{node.h}" rx="{radius}" ry="{radius}" fill="{node.fill}" stroke="{node.stroke}" stroke-width="{stroke_width}"{dash}/>')
        if node.kind == "icon_card":
            size = min(42, node.h - 16)
            x = node.x + (node.w - size) / 2
            y = node.y + 7
            parts.append(f'<image href="{icon_data(node.icon)}" x="{x}" y="{y}" width="{size}" height="{size}"/>')
            text_x = node.x + node.w / 2
            anchor = "middle"
        elif node.icon:
            size = min(42, node.h - 16)
            x = node.x + 10
            y = node.y + (node.h - size) / 2
            parts.append(f'<image href="{icon_data(node.icon)}" x="{x}" y="{y}" width="{size}" height="{size}"/>')
            text_x = node.x + 58
            anchor = "start"
        elif node.kind in {"note", "group"}:
            text_x = node.x + 12
            anchor = "start"
        else:
            text_x = node.x + node.w / 2
            anchor = "middle"
        title_lines = node.title.split("\n")
        detail_lines = node.detail.split("\n") if node.detail else []
        total = len(title_lines) * 18 + len(detail_lines) * 16
        if node.kind == "icon_card":
            y = node.y + node.h - 8
        elif node.kind == "pill":
            y = node.y + node.h / 2 + 4
        elif node.kind == "group":
            y = node.y + 25
        else:
            y = node.y + (node.h - total) / 2 + 14
        for line in title_lines:
            parts.append(f'<text x="{text_x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="node-title">{escape(line)}</text>')
            y += 18
        for line in detail_lines:
            parts.append(f'<text x="{text_x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="node-detail">{escape(line)}</text>')
            y += 16
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_outputs() -> dict[Path, str]:
    pages = [current_page(), target_page()]
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": "2026-08-25T00:00:00.000Z",
            "agent": "Codex",
            "version": "24.7.17",
            "compressed": "false",
            "pages": str(len(pages)),
        },
    )
    for page in pages:
        mxfile.append(page_to_drawio(page))
    ET.indent(mxfile, space="  ")
    outputs = {DRAWIO_PATH: ET.tostring(mxfile, encoding="unicode") + "\n"}
    outputs.update({HERE / page.output: page_to_svg(page) for page in pages})
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the layered Enterprise MCP Draw.io architecture.")
    parser.add_argument("--check", action="store_true", help="Fail when generated artifacts are missing or stale.")
    args = parser.parse_args()
    outputs = render_outputs()
    if args.check:
        stale = [str(path.relative_to(HERE.parent.parent)) for path, content in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            print("stale generated architecture artifacts:")
            for path in stale:
                print(f"- {path}")
            return 1
        print("layered architecture artifacts are current")
        return 0
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(path.relative_to(HERE.parent.parent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
