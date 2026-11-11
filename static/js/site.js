/*
 * Three small things the pages share. None is needed to read or use a
 * page: without this script the menu still opens, nothing is hidden, and
 * a search still runs.
 */

/*
 * 1. "More" in the navigation is a <details>, so it opens and closes on its
 *    own summary. How it should behave depends on how it is laid out:
 *
 *    - On a small screen it is a menu that pops up over the page (the
 *      stylesheet positions it). A menu closes on Escape, with focus back
 *      on "More", and when the click or the focus goes somewhere else.
 *    - On a wide screen it opens in place, in the side navigation. There it
 *      stays as the reader left it, and starts open on one of its own pages.
 */
(function () {
  var more = document.querySelector("nav.site details");
  if (!more) { return; }
  var summary = more.querySelector("summary");
  var menu = more.querySelector(".menu");

  function popsUp() { return window.getComputedStyle(menu).position === "absolute"; }

  if (!popsUp() && summary.classList.contains("active")) { more.open = true; }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && more.open && popsUp()) {
      more.open = false;
      summary.focus();
    }
  });
  document.addEventListener("click", function (event) {
    if (popsUp() && !more.contains(event.target)) { more.open = false; }
  });
  more.addEventListener("focusout", function (event) {
    if (popsUp() && event.relatedTarget && !more.contains(event.relatedTarget)) { more.open = false; }
  });
})();

/*
 * 2. The entrance: the main content of a page fades in and rises 12px, a
 *    few items one after another. One entrance per page, on load or when a
 *    block scrolls into view; nothing loops and nothing moves afterwards.
 *
 *    Drawn with Motion (motion.dev, the plain-JavaScript build of the
 *    Framer Motion library; static/vendor/motion/). What enters is marked
 *    in the templates: data-enter on an element, or data-enter-list on a
 *    list, whose first six items enter.
 *
 *    The stylesheet hides those elements only for people who have not asked
 *    for reduced motion, and shows them by itself after 1.2 s, so a page is
 *    never left blank if this script or Motion fails to load. A <noscript>
 *    rule in base.html shows them at once without JavaScript.
 */
(function () {
  var selector = "[data-enter], [data-enter-list] > :nth-child(-n+6)";
  var items = document.querySelectorAll(selector);
  if (!items.length || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { return; }

  function show(elements) {
    Array.prototype.forEach.call(elements, function (element) {
      element.style.opacity = 1;
      element.style.animation = "none";
    });
  }
  // No Motion, or this script ran so late that the stylesheet has already
  // shown everything: leave the page as it is.
  if (!window.Motion || performance.now() > 1000) { show(items); return; }

  // Elements that come into view together enter together, 50 ms apart.
  var batch = [];
  function flush() {
    var elements = batch;
    batch = [];
    window.Motion.animate(elements, { opacity: [0, 1], y: [12, 0] }, {
      duration: 0.45,
      ease: [0.22, 1, 0.36, 1],
      delay: function (index) { return Math.min(index, 6) * 0.05; }
    });
  }
  window.Motion.inView(selector, function (element) {
    if (!batch.length) { window.requestAnimationFrame(flush); }
    batch.push(element);
  });
})();

/*
 * 3. "Ask in plain English": a search waits for the language model, about
 *    ten seconds on a laptop's processor. While it does, the line beside
 *    Search says so and counts the seconds, and Search is disabled: a second
 *    click would start a second search, which waits for the first and then
 *    gets the keyword parser. Without this script, the browser's own loading
 *    indicator is all there is.
 */
(function () {
  var status = document.querySelector("[data-reading]");
  if (!status) { return; }
  var form = status.closest("form");
  var button = form.querySelector("button[type=submit]");
  var timer = null;

  function reading() {
    var started = Date.now();
    // The words are announced once; the counting seconds are for the eyes only.
    status.innerHTML = '<span class="spinner" aria-hidden="true"></span>' +
      "The language model is reading your request…" +
      ' <span class="seconds" aria-hidden="true">0 s</span>';
    var seconds = status.querySelector(".seconds");
    timer = window.setInterval(function () {
      seconds.textContent = Math.round((Date.now() - started) / 1000) + " s";
    }, 1000);
    button.disabled = true;
    form.setAttribute("aria-busy", "true");
  }

  form.addEventListener("submit", function () {
    // Too short to search: the server answers at once with how to fix it.
    if (form.elements.q.value.trim().length >= 3) { reading(); }
  });
  Array.prototype.forEach.call(document.querySelectorAll(".samples a"), function (link) {
    link.addEventListener("click", function (event) {
      if (!(event.ctrlKey || event.metaKey || event.shiftKey)) { reading(); }  // not when it opens a new tab
    });
  });
  // Back on this page from the results, the browser may restore it as it was left.
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) { return; }
    window.clearInterval(timer);
    status.textContent = "";
    button.disabled = false;
    form.removeAttribute("aria-busy");
  });
})();
