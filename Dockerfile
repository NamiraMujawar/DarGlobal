# Author: Namira Mujawar | Project date: 2026-11-18
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app
COPY app.py company_briefs.py conversations.py guardrails.py knowledge.py orchestrator.py scraper.py ./
COPY static ./static
RUN mkdir -p /app/data \
    && addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; p = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/api/health', timeout=2).read()" || exit 1

CMD ["python", "app.py"]
