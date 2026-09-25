"""
Charts for the Insights page (P1-A3 Section 4).

Each chart is built in three steps:

    *_data()   an ORM aggregation, returned as plain Python rows
    *_png()    a view that draws those rows with Matplotlib and returns
               the image as HttpResponse(content_type="image/png")
    insights   the HTML page that shows both images with a caption, alt
               text and a data table, all built from the same *_data()
               rows, so the three always agree

Memory: figures are built from matplotlib.figure.Figure, never pyplot.
pyplot keeps every figure in a global registry until plt.close(), so a
view that forgets to close one leaks a figure on every request; a bare
Figure is freed as soon as the view returns. pyplot's default backend
here is also a GUI one (TkAgg), which must not run inside a server. The
PNG is written to an in-memory BytesIO buffer instead of a temp file, and
the fixed size and dpi cap each render at 1200 x 675 px: about 3 MB of
RGBA while drawing and a ~40 KB PNG to send.
"""

from io import BytesIO

from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from matplotlib import patheffects
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from .models import ConnectionType, InterestCategory, ProfileInterest, StudentProfile

INK = "#1f2933"
MUTED = "#666e7b"
GRID = "#e3e3e0"

# Every series has a colour AND a hatch pattern, so a chart still reads in
# greyscale or with colour blindness (WCAG 1.4.1). Each colour is at least
# 3:1 against the white background (WCAG 1.4.11).
FRIEND = {"color": "#c0421c", "hatch": ""}
SQUAD = {"color": "#323f4b", "hatch": "//"}
CATEGORY_STYLE = {
    InterestCategory.HOBBY: {"color": "#c0421c", "hatch": ""},
    InterestCategory.RSO: {"color": "#323f4b", "hatch": "//"},
    InterestCategory.ACTIVITY: {"color": "#1f6f8b", "hatch": ".."},
}


# --- Data: ORM aggregations -------------------------------------------------


def students_by_college_data():
    """[(college, friend, squad), ...], largest college first.

    One grouped query: GROUP BY college, with two filtered counts.
    """
    rows = (
        StudentProfile.objects.values("college")
        .annotate(
            friend=Count("id", filter=Q(preferred_connection=ConnectionType.FRIEND)),
            squad=Count("id", filter=Q(preferred_connection=ConnectionType.SQUAD)),
            total=Count("id"),
        )
        .order_by("-total", "college")
    )
    return [(r["college"], r["friend"], r["squad"]) for r in rows]


def selections_by_category_data():
    """[(category, label, selections), ...], most selected first.

    Groups every student's interest picks by a field one relation away
    (interest__category), so the GROUP BY runs across a join.
    """
    labels = dict(InterestCategory.choices)
    rows = (
        ProfileInterest.objects.values("interest__category")
        .annotate(selections=Count("id"))
        .order_by("-selections", "interest__category")
    )
    return [(r["interest__category"], labels[r["interest__category"]],
             r["selections"]) for r in rows]


# --- Drawing ----------------------------------------------------------------


def _figure():
    # "constrained" layout makes room for long college names and the legend.
    return Figure(figsize=(8, 4.5), layout="constrained", facecolor="white")


def _png(fig):
    """Render a Figure to PNG in memory and wrap it in an HttpResponse."""
    with BytesIO() as buffer:
        fig.savefig(buffer, format="png", dpi=150)
        png = buffer.getvalue()
    return HttpResponse(png, content_type="image/png")


def _title(fig, text):
    # A figure-level title, left-aligned: constrained layout reserves room
    # for it, where a long axes title would run off the right edge.
    fig.suptitle(text, x=0.02, ha="left", fontsize=13, fontweight="bold",
                 color=INK)


def _no_data(fig, title):
    """A valid PNG that says there is nothing to plot yet."""
    _title(fig, title)
    fig.text(0.5, 0.5, "No data yet", ha="center", va="center",
             fontsize=14, color=MUTED)
    return _png(fig)


def students_by_college_png(request):
    """Stacked horizontal bar chart: students per college by connection."""
    title = "Verified students per college, by preferred connection"
    rows = students_by_college_data()
    fig = _figure()
    if not rows:
        return _no_data(fig, title)

    # barh draws from the bottom up; reverse so the largest college is on top.
    colleges, friend, squad = (list(reversed(col)) for col in zip(*rows))
    ax = fig.subplots()
    for values, left, style, label in (
        (friend, None, FRIEND, ConnectionType.FRIEND.label),
        (squad, friend, SQUAD, ConnectionType.SQUAD.label),
    ):
        bars = ax.barh(colleges, values, left=left, label=label,
                       edgecolor="white", linewidth=1, **style)
        # A solid box in the bar's own colour keeps the hatch lines from
        # running through the number.
        ax.bar_label(bars, labels=[str(v) if v else "" for v in values],
                     label_type="center", color="white", fontsize=10,
                     fontweight="bold", bbox={
                         "boxstyle": "round,pad=0.3", "linewidth": 0,
                         "facecolor": style["color"]})

    _title(fig, title)
    ax.set_xlabel("Students", color=INK)
    ax.set_ylabel("College", color=INK)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(title="Connection type", loc="lower right", frameon=False)
    return _png(fig)


def interest_categories_png(request):
    """Pie chart: share of all interest selections in each category."""
    title = "Interest selections by category"
    rows = selections_by_category_data()
    fig = _figure()
    if not rows:
        return _no_data(fig, title)

    keys, labels, counts = zip(*rows)
    ax = fig.subplots()
    wedges, _, percents = ax.pie(
        counts,
        colors=[CATEGORY_STYLE[k]["color"] for k in keys],
        hatch=[CATEGORY_STYLE[k]["hatch"] for k in keys],
        autopct="%1.0f%%",
        pctdistance=0.72,
        startangle=90,
        counterclock=False,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        textprops={"color": "white", "fontsize": 11, "fontweight": "bold"},
    )
    for text, key in zip(percents, keys):
        text.set_path_effects([patheffects.withStroke(
            linewidth=4, foreground=CATEGORY_STYLE[key]["color"])])
    _title(fig, title)
    # "outside" legends are laid out by the constrained engine, so a long
    # category name cannot be clipped at the edge of the image.
    fig.legend(wedges, [f"{label} ({n})" for label, n in zip(labels, counts)],
               title="Category (selections)", loc="outside right center",
               frameon=False)
    ax.set_aspect("equal")
    return _png(fig)


# --- Page -------------------------------------------------------------------


def _college_alt(rows):
    if not rows:
        return "Bar chart of students per college. There are no students yet."
    # A summary, not every bar: the table under the chart has all numbers.
    total = sum(f + s for _, f, s in rows)
    college, friend, squad = rows[0]
    return (f"Stacked bar chart of {total} verified students across "
            f"{len(rows)} colleges, split by preferred connection. Largest: "
            f"{college} with {friend + squad} ({friend} friend, {squad} "
            f"squad). Every number is in the table below.")


def _category_alt(rows):
    if not rows:
        return "Pie chart of interest selections. No student has picked an interest yet."
    total = sum(n for _, _, n in rows)
    parts = "; ".join(f"{label}: {n} ({round(n * 100 / total)}%)"
                      for _, label, n in rows)
    return f"Pie chart of {total} interest selections by category. {parts}."


def insights(request):
    """The Insights page: both charts, each with caption, alt text and table."""
    colleges = students_by_college_data()
    categories = selections_by_category_data()
    total = sum(n for _, _, n in categories)
    return render(request, "connect/insights.html", {
        "colleges": colleges,
        "categories": [(label, n, round(n * 100 / total))
                       for _, label, n in categories],
        "college_alt": _college_alt(colleges),
        "category_alt": _category_alt(categories),
    })
