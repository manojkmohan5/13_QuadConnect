Motion (motion.dev), the animation library that was Framer Motion, served
from our own static files rather than a CDN (no third-party request when a
page loads, as with the fonts and Vega).

  motion.js   motion   14.12.0   unpkg.com/motion@14.12.0/dist/motion.js

Framer Motion's components need React, which this site does not use. This
is the same library's plain-JavaScript build: it defines window.Motion,
and static/js/site.js uses Motion.animate and Motion.inView for the one
entrance each page has. The file is as published, unchanged.

Licence: MIT, Motion B.V. (LICENSE.md).
