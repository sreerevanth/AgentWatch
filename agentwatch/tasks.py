"""Minimal Celery app for Docker compose."""

from __future__ import annotations

import os

from celery import Celery

celery_app = Celery(
    "agentwatch",
    broker=os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/1")),
    backend=os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/1")),
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="agentwatch.tasks.ping")
def ping() -> str:
    return "pong"
