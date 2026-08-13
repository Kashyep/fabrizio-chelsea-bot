FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATE_PATH=/app/data/state.db

WORKDIR /app

RUN groupadd --system --gid 10001 bot \
    && useradd --system --uid 10001 --gid bot --home-dir /app bot \
    && mkdir -p /app/data \
    && chown -R bot:bot /app

COPY --chown=bot:bot pyproject.toml README.md LICENSE ./
COPY --chown=bot:bot src ./src
RUN pip install --no-cache-dir .

USER bot
VOLUME ["/app/data"]
ENTRYPOINT ["chelsea-bot"]
CMD ["daemon", "--live", "--interval", "300"]
