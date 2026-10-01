import json
import os

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import ConfigDict, StrictStr
from mcp.server.mcpserver.tools import Tool
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase, FuncMetadata

from servers.crm_mcp.src import auth, dataverse

config = auth.CRMConfig.from_environment()


def crm_update_case_summary(case_id: StrictStr, summary: StrictStr, ctx: Context) -> dict:
    """Replace the summary of one authorized Dynamics 365 case. No other fields are writable."""
    auth.require_guid(case_id)
    if not isinstance(summary, str) or not 1 <= len(summary) <= config.max_chars:
        raise ValueError("summary must be nonempty text within CRM_SUMMARY_MAX_CHARS")

    caller = auth.authorize(config, ctx.headers, case_id)
    token = auth.access_token(config)
    dataverse.update_case_summary(config, case_id, summary, token)
    print(
        json.dumps(
            {
                "event": "crm.summary.updated",
                "caller_client_id": caller,
                "case_id": case_id,
            }
        ),
        flush=True,
    )
    return {"status": "updated", "case_id": case_id}


class SummaryArguments(ArgModelBase):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    case_id: StrictStr
    summary: StrictStr


# SDK defaults ignore extra arguments; explicitly forbid them at this write boundary.
summary_tool = Tool.from_function(crm_update_case_summary)
summary_tool.fn_metadata = FuncMetadata(arg_model=SummaryArguments)
summary_tool.parameters = SummaryArguments.model_json_schema()
mcp = MCPServer("crm-mcp", tools=[summary_tool])


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")), stateless_http=True)
