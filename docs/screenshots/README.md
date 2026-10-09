# Screenshots

Browser evidence, one folder per assignment.

## P1-A2 (this folder)

| File | URL | Shows | Owner |
|---|---|---|---|
| `01_fbv_httpresponse.png` | `/feedback/summary/` | HttpResponse FBV | Dhruv |
| `02_fbv_render.png` | `/matches/` | `render()` FBV | Manojkumar |
| `03_cbv_base.png` | `/locations/` | Base CBV | Prathamesh |
| `04_cbv_generic.png` | `/students/` | Generic CBV | Kritika |
| `05_list_normal.png` | `/students/` | List, populated | Kritika |
| `06_list_empty.png` | `/students/?college=Nonexistent` | Empty state | Kritika |
| `07_cbv_base_empty.png` | `/locations/?seats=25` | Empty state, base CBV | Prathamesh |

Files 05 and 06 are the Section 3 evidence: the same template rendering a
populated list and its `{% empty %}` branch. These predate P1-A3's stylesheet,
so they show the old inline design.

## P1-A3 ([`p1-a3/`](p1-a3/))

Taken in a headless browser at 1280 px wide, which shows no address bar. So
each image has a caption strip on top giving the URL that was actually loaded
and what the image proves. Port 8001 is the development server; 8002 is the
same code run with production settings (`DEBUG=False`) after `collectstatic`.

| File | Section | Shows |
|---|---|---|
| `01_home.png` | 1 | Home route `/` and the nav bar built with `{% url %}` |
| `02_nav_active_state.png` | 1 | Page reached through the nav; current section marked |
| `03_detail_via_link.png` | 1 | Match detail page reached by clicking a list row (`get_absolute_url()`) |
| `04_search_get_results.png` | 2 | GET search: filters in the URL, filtered results |
| `05_search_aggregates.png` | 2 | Total and grouped aggregations of those results |
| `06_search_post_lookup.png` | 2 | POST NetID lookup; the URL carries no NetID |
| `07_css_applied.png` | 3 | Site stylesheet, logo and font loaded with `{% static %}` |
| `08_cache_busting_page.png` | 3 (bonus) | Production page linking the content-hashed stylesheet |
| `09_cache_busting_file.png` | 3 (bonus) | The hashed file, served with an `immutable` cache header |
| `10_insights_page.png` | 4 | Chart embedded in a template, with caption |
| `11_insights_pie_and_table.png` | 4 | Pie chart with legend, and the numbers behind it |
| `12_chart_png_endpoint.png` | 4 | The PNG endpoint on its own URL |
| `13_form_post_errors.png` | 5 | POST form with validation errors next to each field |
| `14_form_post_success.png` | 5 | Success message after Post/Redirect/Get |
| `15_api_locations_json.png` | 6 | JSON output, class-based endpoint, filtered |
| `16_api_matches_json.png` | 6 | JSON output, function-based endpoint, filtered |
| `17_api_bad_param_400.png` | 6 | 400 response naming each bad parameter |
| `18_api_text_plain.png` | 6 | Same data through `HttpResponse`, `text/plain`: no Pretty-print toggle, unlike the JSON in 15 |
| `19_api_docs_mime.png` | 6 | Content-Type of each response class, read live |

## P1-A4 ([`p1-a4/`](p1-a4/))

Taken the same way as P1-A3: a headless browser at 1280 px wide, with a
caption strip giving the URL that was loaded and what the image shows. Port
8001 is the development server; 8002 runs the same code with production
settings after `collectstatic`. Screenshots 06 and 07 load our spec into the
public Vega-Lite editor, which reads its data from the local API. 16 shows
the two files the Reports page's buttons saved, with their real names and
first lines.

| File | Part | Shows |
|---|---|---|
| `01_vega_bar_chart.png` | 1.2 | Vega-Lite bar chart on the Insights page, data from `/api/summary/` |
| `02_vega_line_chart.png` | 1.2 | Vega-Lite line chart, data from `/api/summary/matches-per-week/` |
| `03_chart1_png.png` | 1.2 | `/vega-lite/chart1.png`, drawn on the server |
| `04_chart2_jpg.png` | 1.2 | `/vega-lite/chart2.jpg`, drawn on the server |
| `05_chart1_spec.png` | 1.2 | The spec as served: `data.url`, no inline data |
| `06_vega_editor_bar.png` | 1.2 | The bar chart's spec running in the Vega-Lite editor |
| `07_vega_editor_line.png` | 1.2 | The line chart's spec running in the Vega-Lite editor |
| `08_api_summary.png` | 1.1 | `/api/summary/`: chart-ready rows |
| `09_api_matches_per_week.png` | 1.1 | `/api/summary/matches-per-week/`: chart-ready records |
| `10_icebreakers_page.png` | 2 | Icebreakers page: Open Trivia DB questions on the group's shared topic |
| `11_icebreakers_api_counts.png` | 2 | `/api/icebreakers/?match=2`: our member counts per interest |
| `12_icebreakers_api_questions.png` | 2 | The same response: the topic the counts picked, and the questions |
| `13_icebreakers_api_400.png` | 2 | A bad `match` parameter: 400 with how to fix it |
| `14_icebreakers_busy.png` | 2 | Open Trivia DB busy (two requests within 5 s): the page explains |
| `15_reports_page.png` | 3 | Grouped summaries, totals, Download CSV and JSON buttons |
| `16_downloaded_files.png` | 3 | The two downloaded files: timestamped names and their first lines |
| `17_production_insights.png` | 4 | Production settings: hashed static files, charts still drawn |
| `18_vega_editor_deployed_bar.png` | 4 | The deployed bar chart spec in the Vega-Lite editor, data from https://manojkmohan43.pythonanywhere.com/api/summary/ |
| `19_vega_editor_deployed_line.png` | 4 | The deployed line chart spec in the Vega-Lite editor, data from the deployed API |

## P1-A5 ([`p1-a5/`](p1-a5/))

Each image has the same caption strip: the address it shows, and what it
proves. Images 01-04 read the public API on the live site,
<https://manojkmohan43.pythonanywhere.com/api/summary/>, with no login; they
are explained in [`docs/a5/README.md`](../a5/README.md). Images 05-10 were taken
on the live site after the P1-A5 deploy (2026-10-09). 05-07, 09 and 10 come from
a fresh headless browser with no cookies; 08 was taken in a real browser right
after "Continue with Google".

| File | Part | Shows |
|---|---|---|
| `01_vega_editor_public_api.png` | 3.3 | `group-13-vega-lite-API-demo.txt` in the Vega-Lite editor: two bar panels drawn from the public API, no warnings |
| `02_use1_python_report.png` | 3.4 | Use 1: `1_interest_report.py` run in a terminal |
| `03_use2_notebook.png` | 3.4 | Use 2: the pandas notebook, executed, with its chart |
| `04_use3_excel.png` | 3.4 | Use 3: the Excel workbook: the Power Query table, formulas by type, and a chart |
| `05_login_page_google.png` | 1.1, 2.4 | The site's own login page, with Continue with Google |
| `06_signup_page_google.png` | 1.1, 2.4 | The site's own sign-up page, with Continue with Google |
| `07_nav_signed_out.png` | 1.5 | Signed out: the menu shows only Home, Log in and Sign up; no student data |
| `08_google_signed_in_nav.png` | 2, 1.5 | After Continue with Google on the live site: signed in, with the full menu |
| `09_private_api_401.png` | 1.4 | A private API signed out: 401 JSON with a link to the login page |
| `10_privacy_page.png` | 2 | The public privacy page that Google's sign-in screen links to |
