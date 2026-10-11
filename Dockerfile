FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
# APIFY_TOKEN is needed only to call the tools; listing tools works without it
ENTRYPOINT ["poland-housing-mcp"]
