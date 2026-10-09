// Use 3 of the QuadConnect public API: Excel (P1-A5 Part 3.4).
//
// Excel > Data > Get Data > From Other Sources > Blank Query > Advanced
// Editor, paste this, then Close & Load. (Data > Get Data > From Web with
// the URL below builds the same table through the menus: To Table, then
// expand the columns.) Data > Refresh All pulls the current numbers;
// nothing is copied by hand. 3_excel_power_query.xlsx is the saved result,
// with formulas and a chart over the loaded table.
let
    Source = Json.Document(Web.Contents("https://manojkmohan43.pythonanywhere.com/api/summary/")),
    Rows = Table.FromRecords(Source, {"category", "count", "type"}),
    Typed = Table.TransformColumnTypes(Rows, {{"category", type text}, {"count", Int64.Type}, {"type", type text}}),
    Renamed = Table.RenameColumns(Typed, {{"category", "Interest"}, {"count", "Students"}, {"type", "Type"}})
in
    Renamed
