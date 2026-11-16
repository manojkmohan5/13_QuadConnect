"""
AI analytics dashboard (P1-A10): /analytics/, staff only.

Monitors "Ask in plain English" (/search/ask/) from its AIRequestLog rows,
in three sections, each led by the questions it answers (docs/a10/README.md):

    System performance   how fast, how consistent, what makes it slow
    User behavior        how much, when, and what people ask for
    Cost                 per request, per query, and over time

The view computes the summary statistics in Python (median, p95, coefficient
of variation, correlation, 7-day moving average) and hands each chart a
Vega-Lite spec with its data inline; static/js/charts.js draws them.
"""

import statistics
from collections import Counter, defaultdict
from datetime import timedelta

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.utils import timezone

from .models import AIRequestLog

# Cost model. The model runs on our own server, so there is no bill per call;
# these are the prices of a hosted model of the same size (1.5B parameters),
# so cost tracks the work each request does and can be compared to an API.
PRICE_PER_M_PROMPT = 0.10  # USD per million prompt tokens
PRICE_PER_M_COMPLETION = 0.20  # USD per million completion tokens

WINDOWS = (7, 30, 90)
SOURCE_COLORS = {"model": "#1f5fbf", "cached": "#17794a", "keywords": "#ff5f05"}
SOURCE_LABELS = dict(AIRequestLog.Source.choices)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
KIND_LABELS = {"interests": "Interest", "day": "Day", "time": "Time of day", "college": "College",
               "connection": "Friend / Squad", "energy": "Social energy", "": "Nothing usable"}


def cost(log):
    return (log.prompt_tokens * PRICE_PER_M_PROMPT + log.completion_tokens * PRICE_PER_M_COMPLETION) / 1e6


def p95(values):
    return statistics.quantiles(values, n=20, method="inclusive")[18] if len(values) > 1 else (values or [0])[0]


def spec(title, subtitle, description, values, body, height=220):
    """A Vega-Lite spec in the site's style, its data inline. The card around it shows
    the question as its heading, so the chart's own title is only the subtitle;
    `title` names the chart in screen readers' description."""
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "title": {"text": subtitle, "anchor": "start", "fontWeight": "normal", "fontSize": 13, "color": "#566076"},
        "description": f"{title}. {description}",
        "data": {"values": values},
        "width": "container", "height": height, "background": "white",
        "config": {"font": "Figtree, sans-serif", "axis": {"labelColor": "#44506a", "titleColor": "#44506a",
                                                           "gridColor": "#e6e3dd"},
                   "view": {"stroke": None}, "legend": {"orient": "top", "title": None}},
        **body,
    }


SOURCE_SCALE = {"domain": [SOURCE_LABELS[k] for k in SOURCE_COLORS], "range": list(SOURCE_COLORS.values())}


def build(logs, days, end, before=()):
    """Every figure on the page, from the logs inside the window. `before` holds
    the 6 days ahead of it, so the window's first rolling-7-day points are full."""
    model = [log for log in logs if log.source == "model"]
    model_s = [log.latency_ms / 1000 for log in model]
    all_s = [log.latency_ms / 1000 for log in logs]
    costs = [cost(log) for log in logs]
    model_cost = statistics.mean(cost(log) for log in model) if model else 0
    by_source = Counter(log.source for log in logs)
    n = len(logs)

    # Per day: volume, latency median and p95 (model answers), cost.
    daily = defaultdict(list)
    for log in [*before, *logs]:
        daily[timezone.localdate(log.created_at)].append(log)
    dates = [end - timedelta(days=i) for i in range(days - 1, -1, -1)]
    day_rows, trend_rows = [], []
    for i, day in enumerate(dates):
        rows = daily.get(day, [])
        week_days = [day - timedelta(days=k) for k in range(7)]
        # 7-day rolling window: one day holds ~10 model answers, too few for a stable p95.
        secs = [r.latency_ms / 1000 for d in week_days for r in daily.get(d, []) if r.source == "model"]
        week = [len(daily.get(d, [])) for d in dates[max(0, i - 6):i + 1]]
        day_rows.append({"date": day.isoformat(), "requests": len(rows), "avg7": round(statistics.mean(week), 2),
                         "cost": round(sum(cost(r) for r in rows) * 1000, 4)})
        if secs:
            trend_rows += [{"date": day.isoformat(), "stat": "Median", "s": round(statistics.median(secs), 2)},
                           {"date": day.isoformat(), "stat": "95th percentile", "s": round(p95(secs), 2)}]

    points = [{"s": log.latency_ms / 1000, "source": SOURCE_LABELS[log.source],
               "filters": len(log.filter_kinds.split(",")) if log.filter_kinds else 0,
               "tokens": log.prompt_tokens + log.completion_tokens,
               "prompt": log.prompt_tokens, "completion": log.completion_tokens,
               "weekday": WEEKDAYS[timezone.localtime(log.created_at).weekday()],
               "hour": timezone.localtime(log.created_at).hour} for log in logs]
    kinds = Counter(kind for log in logs for kind in (log.filter_kinds.split(",") if log.filter_kinds else [""]))

    # Per distinct query, after lower-casing: how often, how useful, how costly.
    queries = defaultdict(list)
    for log in logs:
        queries[log.request.strip().lower()].append(log)
    query_rows = [{"text": text, "count": len(rows),
                   "found": round(statistics.mean(r.students_found for r in rows), 1),
                   "zero": round(100 * sum(r.students_found == 0 for r in rows) / len(rows)),
                   "tokens": round(statistics.mean(r.prompt_tokens + r.completion_tokens
                                                   for r in rows if r.source == "model"))
                   if any(r.source == "model" for r in rows) else 0,
                   "cost": sum(cost(r) for r in rows) * 1000}
                  for text, rows in queries.items()]

    filters_n = [p["filters"] for p in points if p["source"] == SOURCE_LABELS["model"]]
    try:
        r_filters = statistics.correlation(filters_n, model_s)
    except statistics.StatisticsError:  # fewer than two points, or all the same
        r_filters = None

    kpis = {
        "requests": n,
        "per_day": n / days,
        "median": statistics.median(model_s) if model_s else 0,
        "p95": p95(model_s),
        "cv": statistics.pstdev(model_s) / statistics.mean(model_s) if model_s else 0,
        "fallback": 100 * by_source["keywords"] / n if n else 0,
        "cached": 100 * by_source["cached"] / n if n else 0,
        "zero": 100 * sum(log.students_found == 0 for log in logs) / n if n else 0,
        "flagged": sum(log.flagged for log in logs),
        "distinct": len(queries),
        "total_cost": sum(costs),
        "per_1k": 1000 * statistics.mean(costs) if costs else 0,
        "model_per_1k": 1000 * model_cost,
        "tokens": sum(log.prompt_tokens + log.completion_tokens for log in logs),
        "prompt_share": 100 * sum(log.prompt_tokens for log in logs)
        / max(1, sum(log.prompt_tokens + log.completion_tokens for log in logs)),
        "saved": by_source["cached"] * model_cost,
        "r_filters": r_filters,
        "slow_share": 100 * sum(s > 5 for s in all_s) / n if n else 0,
    }

    color = {"field": "source", "type": "nominal", "scale": SOURCE_SCALE}
    x_date = {"field": "date", "type": "temporal", "title": None, "axis": {"format": "%b %d", "labelAngle": 0}}
    charts = {
        "perf_trend": spec(
            "Latency over time", "Language-model answers, seconds, over a rolling 7 days",
            "Line chart of the rolling 7-day median and 95th-percentile latency of language-model answers.",
            trend_rows,
            {"mark": {"type": "line", "point": True, "strokeWidth": 2},
             "encoding": {"x": x_date, "y": {"field": "s", "type": "quantitative", "title": "Seconds"},
                          "color": {"field": "stat", "type": "nominal",
                                    "scale": {"range": ["#1f5fbf", "#6b3fc4"]}},
                          "strokeDash": {"field": "stat", "type": "nominal",
                                         "scale": {"range": [[5, 3], [1, 0]]}}}}),
        "perf_hist": spec(
            "How response time is distributed", "Requests per 0.5-second bin, by how they were answered",
            "Histogram of request latency in half-second bins, stacked by answer source.",
            [p for p in points if p["s"] <= 12],  # the tail beyond 12 s is counted in the KPI instead
            {"mark": {"type": "bar", "cornerRadiusEnd": 2},
             "encoding": {"x": {"field": "s", "bin": {"step": 0.5}, "title": "Seconds (up to 12)"},
                          "y": {"aggregate": "count", "title": "Requests"}, "color": color}}),
        "perf_box": spec(
            "Which requests are slower", "Language-model latency by how many filters the request turned into",
            "Box plot of language-model latency for requests that produced 0 to 3 or more filters.",
            [p for p in points if p["source"] == SOURCE_LABELS["model"]],
            {"mark": {"type": "boxplot", "extent": 1.5, "color": "#1f5fbf", "size": 36},
             "encoding": {"x": {"field": "filters", "type": "ordinal", "title": "Filters found",
                                "axis": {"labelAngle": 0}},
                          "y": {"field": "s", "type": "quantitative", "title": "Seconds"}}}),
        "use_daily": spec(
            "Searches per day", "Bars: each day. Line: 7-day moving average",
            "Bar chart of AI searches per day with a 7-day moving average line.",
            day_rows,
            {"encoding": {"x": x_date},
             "layer": [{"mark": {"type": "bar", "color": "#c9d7ef", "cornerRadiusEnd": 2},
                        "encoding": {"y": {"field": "requests", "type": "quantitative", "title": "Searches"}}},
                       {"mark": {"type": "line", "color": "#13294b", "strokeWidth": 2.5},
                        "encoding": {"y": {"field": "avg7", "type": "quantitative"}}}]}),
        "use_heat": spec(
            "When students search", "Searches by weekday and hour (Central time)",
            "Heat map of the number of searches by day of the week and hour of the day.",
            points,
            {"mark": {"type": "rect", "cornerRadius": 2},
             "encoding": {"x": {"field": "hour", "type": "ordinal", "title": "Hour of day",
                                "scale": {"domain": list(range(24))}, "axis": {"labelAngle": 0}},
                          "y": {"field": "weekday", "type": "ordinal", "sort": WEEKDAYS, "title": None},
                          "color": {"aggregate": "count", "title": "Searches",
                                    "scale": {"scheme": "blues"}}}}, height=200),
        "use_kinds": spec(
            "What students ask for", "Share of searches that included each kind of filter",
            "Horizontal bar chart of the share of searches that asked for each kind of filter.",
            [{"kind": KIND_LABELS.get(k, k), "share": round(100 * c / n, 1)} for k, c in kinds.items()] if n else [],
            {"mark": {"type": "bar", "color": "#ff5f05", "cornerRadiusEnd": 3},
             "encoding": {"y": {"field": "kind", "type": "nominal", "sort": "-x", "title": None},
                          "x": {"field": "share", "type": "quantitative", "title": "% of searches"}}}),
        "cost_daily": spec(
            "Cost per day", "US cents, at hosted-model token prices",
            "Area chart of the estimated cost of AI searches per day, in US cents.",
            [{"date": r["date"], "cents": round(r["cost"] / 10, 4)} for r in day_rows],
            {"mark": {"type": "area", "color": "#6b3fc4", "opacity": 0.85, "line": True},
             "encoding": {"x": x_date, "y": {"field": "cents", "type": "quantitative", "title": "Cents"}}}),
        "cost_tokens": spec(
            "Tokens per request", "Mean tokens of a language-model answer, by filters found",
            "Stacked bar chart of the mean prompt and completion tokens per language-model request, "
            "by number of filters found.",
            [p for p in points if p["source"] == SOURCE_LABELS["model"]],
            {"transform": [{"fold": ["prompt", "completion"], "as": ["part", "n"]}],
             "mark": {"type": "bar"},
             "encoding": {"x": {"field": "filters", "type": "ordinal", "title": "Filters found",
                                "axis": {"labelAngle": 0}},
                          "y": {"aggregate": "mean", "field": "n", "type": "quantitative", "title": "Mean tokens"},
                          "color": {"field": "part", "type": "nominal", "sort": ["prompt", "completion"],
                                    "scale": {"domain": ["prompt", "completion"],
                                              "range": ["#c9bdf0", "#6b3fc4"]}}}}),
    }
    top = sorted(query_rows, key=lambda q: -q["count"])[:8]
    costly = sorted(query_rows, key=lambda q: (-q["tokens"], -q["cost"]))[:8]
    return kpis, charts, top, costly


@user_passes_test(lambda user: user.is_staff)  # the page shows what other students searched for
def analytics(request):
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    days = days if days in WINDOWS else 30
    newest = AIRequestLog.objects.order_by("-created_at").values_list("created_at", flat=True).first()
    # The window ends at the newest log, so an idle period does not show an empty page.
    end = timezone.localdate(newest) if newest else timezone.localdate()
    start = end - timedelta(days=days - 1)
    # shortcut: aggregates in Python (~600 rows a month here); move to SQL past ~100k rows.
    rows = list(AIRequestLog.objects.filter(created_at__date__gte=start - timedelta(days=6), created_at__date__lte=end))
    logs = [log for log in rows if timezone.localdate(log.created_at) >= start]
    kpis, charts, top, costly = build(logs, days, end, before=[log for log in rows if timezone.localdate(log.created_at) < start])
    return render(request, "connect/analytics.html", {
        "kpis": kpis, "charts": charts, "top": top, "costly": costly, "days": days, "windows": WINDOWS,
        "start": start, "end": end, "price_prompt": PRICE_PER_M_PROMPT, "price_completion": PRICE_PER_M_COMPLETION,
    })
