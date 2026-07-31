ARG PYTHON_BASE_IMAGE=python:3.13-slim
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_HEALTH_HOST=127.0.0.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /tmp/common-requirements.txt
COPY servers/sharepoint_mcp/requirements.txt /tmp/service-requirements.txt
RUN pip install --no-cache-dir \
      -r /tmp/common-requirements.txt \
      -r /tmp/service-requirements.txt \
    && rm /tmp/common-requirements.txt \
    && rm /tmp/service-requirements.txt \
    && mkdir -p /app/servers \
    && addgroup --system mcp \
    && adduser --system --ingroup mcp --home /app --no-create-home mcp \
    && mkdir -p /tmp/mcp \
    && chown -R mcp:mcp /app /tmp/mcp

COPY images/mcp_python_base/container_healthcheck.py /usr/local/bin/mcp-container-healthcheck.py
RUN chmod 0755 /usr/local/bin/mcp-container-healthcheck.py

COPY --chown=mcp:mcp common ./common
COPY --chown=mcp:mcp servers/__init__.py ./servers/__init__.py
COPY --chown=mcp:mcp servers/sharepoint_mcp ./servers/sharepoint_mcp

USER mcp

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 CMD ["python", "/usr/local/bin/mcp-container-healthcheck.py"]

CMD ["python", "-m", "servers.sharepoint_mcp.src.server"]
