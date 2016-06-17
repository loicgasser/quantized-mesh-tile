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

Quantized mesh tile requires Python >=2.7 (not including Python 3.x) and GEOS >= 3.3.

Installation
------------

Quantized mesh tile is available on the Python Package Index. So it can be installed
with pip and easy_install tools.

Disclamer
---------

This library is only at a very early stage (very first version) and is subject to changes.

Known issue
-----------

This library can read and write tiles with the lighting extension header, but still fail to create correct unit 
vectors from scratch. PRs are welcome though!

Development
-----------

The code is available on GitHub: https://github.com/loicgasser/quantized-mesh-tile

Contributors:

* Loïc Gasser (https://github.com/loicgasser)
* Gilbert Jeiziner (https://github.com/gjn)

Styling:

Max line length is 90.

We use flake8 to lint the project. Here are the rules we ignore.

* E128: continuation line under-indented for visual indent
* E221: multiple spaces before operator
* E241: multiple spaces after ':'
* E251: multiple spaces around keyword/parameter equals
* E272: multiple spaces before keyword
* E731: do not assign a lambda expression, use a def
* W503: line break before binary operator

Vizualize a terrain tile
------------------------

Here is a viewer to vizualize the geometry of a single tile.
Unit vectors are also displayed if they are present.

.. raw:: html

  <form class="tile" onsubmit="reload(event)">
    z: <input type="text" name="z" value="14"><br><br>
    x: <input type="text" name="x" value="24297"><br><br>
    y: <input type="text" name="y" value="10735"><br><br>
    tileUrl: <input type="text" name="tileUrl" value="https://assets.agi.com/stk-terrain/world/14/24297/10735.terrain?v=1.16389.0" style="width: 489px;"><br><br>
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
