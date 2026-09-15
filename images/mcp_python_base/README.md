# Enterprise MCP Python Base Image

This is an optional platform-owned base image for Python MCP servers.

Current service Dockerfiles are self-contained and do not require this image.
If adopted later, service teams can extend this image instead of starting every
MCP server from `python:*-slim` directly. The base image gives every server the
same baseline runtime behavior:

- non-root container user
- unbuffered structured stdout/stderr logs
- common MCP runtime dependencies
- local TCP healthcheck helper
- shared OCI labels for image inventory
- `tini` as PID 1 for signal handling

Keep business code and downstream credentials outside this base image. Tool
authorization belongs in direct Cedar at Gateway; server images own only
service-specific input validation and safe execution.

## Build

If adopted, build and publish this image from the central platform image
pipeline:

```bash
cd examples/enterprise_mcp_platform
docker build \
  -f images/mcp_python_base/Dockerfile \
  -t 111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/internal/mcp-python-base:2026-07-04 \
  .
```

Production builds should use an internally approved upstream Python base image,
pin dependencies with hashes, generate an SBOM, run vulnerability scanning, and
sign the pushed image before service teams consume it.
