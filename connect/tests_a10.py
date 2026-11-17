"""
Tests for P1-A10: the AI request log and the /analytics/ dashboard.

    python manage.py test connect.tests_a10

No model is loaded: generate_reply is patched, as in tests_a6.py.
"""

import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from connect import ai_search
from connect.analytics import build
from connect.models import AIRequestLog


@override_settings(AI_LOCAL_ENABLED=True, AI_EMBED_ENABLED=False)
class RequestLogTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client.force_login(User.objects.create_user("member"))

    def ask(self, q):
        with patch("connect.ai_search.generate_reply", return_value='{"interests": ["Gaming"]}'):
            return self.client.get(reverse("connect:student-ask"), {"q": q})

    def test_each_search_is_logged_and_a_repeat_is_logged_as_cached(self):
        self.ask("gamers")
        self.ask("gamers")
        first, second = AIRequestLog.objects.order_by("created_at")
        self.assertEqual((first.source, first.request), ("model", "gamers"))
        self.assertEqual((second.source, second.prompt_tokens, second.completion_tokens), ("cached", 0, 0))

    def test_tokens_counted_by_the_model_reach_the_log(self):
        def reply(messages):
            ai_search.usage.prompt += 700
            ai_search.usage.completion += 9
            return '{"interests": ["Gaming"]}'
        with patch("connect.ai_search.generate_reply", side_effect=reply):
            self.client.get(reverse("connect:student-ask"), {"q": "gamers please"})
        log = AIRequestLog.objects.get()
        self.assertEqual((log.prompt_tokens, log.completion_tokens), (700, 9))


class DashboardTests(TestCase):

    url = reverse("connect:analytics")

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_data", stdout=StringIO())

    def test_staff_see_every_chart_and_students_do_not(self):
        self.client.force_login(User.objects.get(username="mohitg2"))
        response = self.client.get(self.url, {"days": 30})
        self.assertEqual(response.status_code, 200)
        specs = json.loads(json.dumps(response.context["charts"]))  # what json_script sends: must serialise
        self.assertEqual(len(specs), 8)
        self.assertTrue(all(spec["data"]["values"] for spec in specs.values()))
        self.assertGreater(response.context["kpis"]["requests"], 100)

        self.client.force_login(User.objects.create_user("student"))
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_seeding_twice_adds_nothing(self):
        count = AIRequestLog.objects.count()
        call_command("seed_ai_logs", stdout=StringIO())
        self.assertEqual(AIRequestLog.objects.count(), count)

    def test_the_costliest_requests_table_is_in_cents(self):
        from datetime import date, datetime

        from django.utils import timezone
        at = timezone.make_aware(datetime(2026, 11, 12, 12))
        logs = [AIRequestLog(created_at=at, request="gamers", source="model", latency_ms=2000, prompt_tokens=700,
                             completion_tokens=20, filter_kinds="interests", students_found=3) for _ in range(2)]
        kpis, charts, top, costly = build(logs, 7, date(2026, 11, 12))
        # One answer: (700 x $0.10 + 20 x $0.20) per million tokens = $0.000074 = 0.0074 cents.
        self.assertAlmostEqual(costly[0]["cost"], 2 * 0.0074)
        # The table can never add up to more than everything in the window.
        self.assertAlmostEqual(sum(q["cost"] for q in costly), kpis["total_cost"] * 100)

    def test_no_logs_still_builds(self):
        from datetime import date
        kpis, charts, top, costly = build([], 7, date(2026, 11, 12))
        self.assertEqual((kpis["requests"], top, costly), (0, [], []))
