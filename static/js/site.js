/*
 * The "More" menu in the navigation is a <details>, so it opens and closes
 * on its own summary without any script. This adds the two things a menu
 * is expected to do as well: close on Escape (focus goes back to "More"),
 * and close when the click or the focus goes somewhere else.
 */
(function () {
  var more = document.querySelector("nav.site details");
  if (!more) { return; }
  var summary = more.querySelector("summary");

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && more.open) {
      more.open = false;
      summary.focus();
    }
  });
  document.addEventListener("click", function (event) {
    if (!more.contains(event.target)) { more.open = false; }
  });
  more.addEventListener("focusout", function (event) {
    if (event.relatedTarget && !more.contains(event.relatedTarget)) { more.open = false; }
  });
})();
