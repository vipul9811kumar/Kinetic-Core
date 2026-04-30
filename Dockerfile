FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir setuptools wheel

COPY pyproject.toml .
COPY agents/ agents/
COPY api/ api/
COPY monitoring/ monitoring/
COPY prompts/ prompts/

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
