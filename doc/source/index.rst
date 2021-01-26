Quantized mesh tile Documentation
=================================

Reference Documentation
-----------------------

.. toctree::
   :maxdepth: 1

   tutorial
   encode
   terraintile
   terraintopology
   globalgeodetic
   viewer

Requirements
------------

Quantized mesh tile requires Python >= 3.5 and GEOS >= 3.3.

Installation
------------

Quantized mesh tile is available on the `Python Package Index`_. So it can be installed
with pip and easy_install tools.

.. _Python Package Index:
    https://pypi.python.org/pypi/quantized-mesh-tile/

Disclamer
---------

This library is only at a very early stage (very first version) and is subject to changes.

Development
-----------

The code is available on GitHub: https://github.com/loicgasser/quantized-mesh-tile

Author:

* Loïc Gasser (https://github.com/loicgasser)

Contributors:

* tiloSchlemmer (https://github.com/thiloSchlemmer)
* Gilbert Jeiziner (https://github.com/gjn)
* Roland Arsenault (https://github.com/rolker)
* Ulrich Meier (https://github.com/umeier)

Styling:

Max line length is 90.

We use flake8 to lint the project. Here are the rules we ignore.

* E128: continuation line under-indented for visual indent
* E221: multiple spaces before operator
* E241: multiple spaces after ':'
* E251: multiple spaces around keyword/parameter equals
* E402: module level import not at top of file

Vizualize a terrain tile
------------------------

Here is a viewer to vizualize the geometry of a single tile. Make sure you have CORS enabled.
Unit vectors are also displayed if they are present.

.. raw:: html

  <form class="tile" onsubmit="reload(event)">
    z: <input type="text" name="z" value="9"><br><br>
    x: <input type="text" name="x" value="536"><br><br>
    y: <input type="text" name="y" value="391"><br><br>
    tileUrl: <input type="text" name="tileUrl" value="https://maps.tilehosting.com/data/terrain-quantized-mesh/9/536/391.terrain?key=NUcY4qrAupTlR2xMwK6G" style="width: 489px;"><br><br>
    <button type="submit" value="submit">Go to viewer</button>
  </form>

  <script type="text/javascript">
    var reload = function(event) {
      var z, x, y, tileUrl, viewer;
      event.preventDefault();
      event.stopPropagation();
      z = event.target.z.value;
      x = event.target.x.value;
      y = event.target.y.value;
      tileUrl = event.target.tileUrl.value;
      viewer = 'viewer.html?z=' + z + '&x=' + x + '&y=' + y + '&tileUrl=' + encodeURIComponent(tileUrl);
      window.open(viewer);
    };
  </script>
