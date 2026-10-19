"""
Download and test the local Hugging Face model before the first web request.

    python manage.py warm_ai_model

The first request to /ai/profile-assistant/ would otherwise spend a minute (or
several, on a slow connection) downloading the weights. This command does it
up front, then runs one real extraction so you can see the model answering.
"""

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from connect import ai_local


class Command(BaseCommand):
    help = "Download the local LLM's weights (settings.LOCAL_LLM_MODEL) and run one test extraction."

    def handle(self, *args, **options):
        if not settings.LOCAL_LLM_ENABLED:
            raise CommandError("LOCAL_LLM_ENABLED=0: the local model is switched off in .env.")
        self.stdout.write(f"Model: {settings.LOCAL_LLM_MODEL}")
        started = time.perf_counter()
        sample = "I'm a quiet engineering junior. I'd rather have one real conversation about technology than go to a loud party."
        try:
            reply = ai_local.generate_text(ai_local.build_messages(sample, ai_local.interest_catalogue()))
        except ai_local.LocalLLMUnavailable as error:
            raise CommandError(str(error)) from error
        self.stdout.write(f"Loaded and answered in {time.perf_counter() - started:.1f}s:")
        self.stdout.write(reply)
        parsed = ai_local.extract_json(reply)
        if parsed is None:
            raise CommandError("The model answered, but not with JSON. Try a larger LOCAL_LLM_MODEL.")
        self.stdout.write(self.style.SUCCESS("OK: the local model is ready."))
