FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml README.md ./
COPY src ./src
RUN poetry install --only main --no-interaction --no-ansi

COPY . .

ENTRYPOINT ["euro-fsqca"]
CMD ["--help"]
