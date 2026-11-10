"""
Download the local models and run one search with them, before the first web request.

    python manage.py download_ai_model

The first "Ask in plain English" search (/search/ask/) downloads the weights by
itself. This command does it ahead of time, so that first search is not the one
that waits, and shows the models answering: the language model (P1-A6) and,
since P1-A9, the embedding model that places the interests it writes in its own
words. The weights go into the Hugging Face cache (~/.cache/huggingface), never
into this repository.
"""

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from connect import ai_search

SAMPLE = "someone for one-on-one coffee on Sunday around noon"
SAMPLE_WORDS = ["Painting", "Tech"]  # words the language model wrote in P1-A6's tests (T08, T10)


class Command(BaseCommand):
    help = "Download the local models (settings.AI_LOCAL_MODEL, settings.AI_EMBED_MODEL) and run one test search."

    def handle(self, *args, **options):
        if not settings.AI_LOCAL_ENABLED:
            raise CommandError("AI_LOCAL_ENABLED=0 in .env: the local model is switched off.")
        self.stdout.write(f"Model: {settings.AI_LOCAL_MODEL} (downloads once, then loads from the cache)")
        interests, colleges = ai_search.vocabulary()
        started = time.perf_counter()
        try:
            reply = ai_search.generate_reply(ai_search.build_messages(SAMPLE, interests, colleges))
        except ai_search.ModelUnavailable as error:
            raise CommandError(str(error)) from error
        filters = ai_search.clean_filters(ai_search.first_json_object(reply), interests, colleges)
        self.stdout.write(f"Loaded and answered in {time.perf_counter() - started:.1f} s.")
        self.stdout.write(f"Request:  {SAMPLE}\nReply:    {reply.strip()}\nFilters:  {filters}")
        if not filters:
            raise CommandError("The model answered, but nothing usable came out of it.")
        self.stdout.write(self.style.SUCCESS("The local model is ready."))

        if not settings.AI_EMBED_ENABLED:
            self.stdout.write("AI_EMBED_ENABLED=0: interests are matched by spelling only.")
            return
        self.stdout.write(f"\nEmbedding model: {settings.AI_EMBED_MODEL} (downloads once, then loads from the cache)")
        started = time.perf_counter()
        try:  # match_by_meaning() never raises, so ask the model directly to see why it failed
            ai_search.embed_similarities(SAMPLE_WORDS, interests)
        except ai_search.ModelUnavailable as error:
            raise CommandError(str(error)) from error
        placed = ai_search.match_by_meaning(SAMPLE_WORDS, interests)
        self.stdout.write(f"Loaded and answered in {time.perf_counter() - started:.1f} s.")
        self.stdout.write(f"Words:    {SAMPLE_WORDS}\nPlaced:   {placed}")
        if not placed:
            raise CommandError("The embedding model answered, but placed none of the words.")
        self.stdout.write(self.style.SUCCESS("The embedding model is ready."))
