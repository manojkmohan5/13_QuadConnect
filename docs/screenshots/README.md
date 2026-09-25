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
