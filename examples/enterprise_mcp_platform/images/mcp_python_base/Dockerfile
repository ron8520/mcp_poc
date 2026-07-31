FROM python:3.13-slim

ARG IMAGE_CREATED="unknown"
ARG IMAGE_REVISION="unknown"
ARG IMAGE_VERSION="dev"

LABEL org.opencontainers.image.title="enterprise-mcp-python-base" \
      org.opencontainers.image.description="Shared Python base image for enterprise MCP servers" \
      org.opencontainers.image.created="${IMAGE_CREATED}" \
      org.opencontainers.image.revision="${IMAGE_REVISION}" \
      org.opencontainers.image.version="${IMAGE_VERSION}"

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

COPY images/mcp_python_base/requirements-base.txt /tmp/requirements-base.txt
RUN pip install --no-cache-dir -r /tmp/requirements-base.txt \
    && rm /tmp/requirements-base.txt

COPY images/mcp_python_base/container_healthcheck.py /usr/local/bin/mcp-container-healthcheck.py

RUN addgroup --system mcp \
    && adduser --system --ingroup mcp --home /app --no-create-home mcp \
    && mkdir -p /app /tmp/mcp \
    && chown -R mcp:mcp /app /tmp/mcp \
    && chmod 0755 /usr/local/bin/mcp-container-healthcheck.py

USER mcp

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-c", "print('enterprise MCP base image: provide a service CMD')"]
