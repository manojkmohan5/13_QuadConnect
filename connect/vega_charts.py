"""
Vega-Lite charts (P1-A4 Part 1.2).

The specs live in connect/specs/ as plain Vega-Lite JSON, each loading its
data with data.url from our own API (/api/summary/...), never inline values.

    GET /vega-lite/<chart>.vl.json   the spec, with data.url made absolute for
                                     the host serving it
    GET /vega-lite/<chart>.png       the chart rendered to an image on the
    GET /vega-lite/<chart>.jpg       server with vl-convert

The Insights page draws the same specs in the browser with vega-embed.
Since P1-A5 these URLs need a login, like the page itself; the chart built
on the public API for the Vega-Lite editor is docs/a5/
group-13-vega-lite-API-demo.txt.

Rendering on the server: the image views give vl-convert the rows from the
same functions the API uses, instead of letting it fetch data.url. A server
that fetches its own URL while answering a request can stall on hosts that
run a single worker, and with allowed_base_urls=[] the renderer can make no
network request at all. The spec, its marks and its encodings are
unchanged, so the image is the same chart.
"""

import json
from pathlib import Path

from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

from .api import interest_popularity, matches_per_week

SPEC_DIR = Path(__file__).resolve().parent / "specs"
VEGA_LITE_VERSION = "6.4"  # newest version vl-convert-python 1.9 renders
IMAGE_WIDTH = 640          # "container" width has no meaning off-screen

# name -> (spec file, function returning the chart's rows)
CHARTS = {
    "chart1": ("chart1_bar.vl.json", interest_popularity),
    "chart2": ("chart2_line.vl.json", matches_per_week),
}
FORMATS = {
    "png": ("image/png", "vegalite_to_png"),
    "jpg": ("image/jpeg", "vegalite_to_jpeg"),
}


def load_spec(name):
    """The chart's spec as stored on disk (read each time: the files are
    small, and a cached copy would go stale while a spec is being edited)."""
    if name not in CHARTS:
        raise Http404(f"No chart called {name!r}.")
    return json.loads((SPEC_DIR / CHARTS[name][0]).read_text(encoding="utf-8"))


def spec_for_browser(request, name):
    """The spec with data.url made absolute for the host serving it."""
    spec = load_spec(name)
    spec["data"]["url"] = request.build_absolute_uri(spec["data"]["url"])
    return spec


def spec_for_image(name):
    """The spec with this request's rows in place of data.url, sized for an
    image. Only used to render on the server; see the module docstring."""
    spec = load_spec(name)
    spec["data"] = {"values": CHARTS[name][1]()}
    spec["width"] = IMAGE_WIDTH
    return spec


@require_GET
def vega_spec(request, chart):
    """GET /vega-lite/<chart>.vl.json - the chart's Vega-Lite spec."""
    return JsonResponse(spec_for_browser(request, chart),
                        json_dumps_params={"indent": 2})


@cache_page(60)  # a render takes about a second; a minute-old chart is fine
@require_GET
def vega_image(request, chart, fmt):
    """GET /vega-lite/<chart>.png or .jpg - the chart rendered on the server."""
    if fmt not in FORMATS:
        raise Http404(f"Charts come as {', '.join(FORMATS)}, not {fmt!r}.")
    # Imported here, not at the top: if the renderer's native library fails
    # to load on a host, only these image URLs fail, not every page.
    import vl_convert

    content_type, function = FORMATS[fmt]
    image = getattr(vl_convert, function)(spec_for_image(chart), vl_version=VEGA_LITE_VERSION,
                                          scale=2, allowed_base_urls=[])
    return HttpResponse(image, content_type=content_type)
