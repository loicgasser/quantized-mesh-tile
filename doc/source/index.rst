Quantized mesh tile Documentation
=================================

Reference Documentation
-----------------------

.. toctree::
   :maxdepth: 1

   terraintopology
   terraintile
   viewer


Vizualize a terrain tile
------------------------

Here is a viewer to vizualize the geometry of a single tile.
Unit vectors are also displayed if they are present.

.. raw:: html

  <form class="tile" onsubmit="reload(event)">
    z: <input type="text" name="z" value="14">
    x: <input type="text" name="x" value="24297">
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
