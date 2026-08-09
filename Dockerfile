FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tender_hunter ./tender_hunter
COPY partner_scout ./partner_scout
COPY event_mapper ./event_mapper
COPY dashboard ./dashboard
COPY notifications ./notifications
COPY control ./control
COPY chat ./chat
COPY api ./api

ENTRYPOINT ["python"]
