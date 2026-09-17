FROM python:3.13-slim
RUN pip install --no-cache-dir 'uv>=0.9,<1'
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home --uid 10001 citenexus
USER citenexus
ENTRYPOINT ["cite-nexus-mcp"]
