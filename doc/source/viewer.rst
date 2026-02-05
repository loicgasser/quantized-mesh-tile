.. _viewer:

Quantized Mesh Tile Viewer
==========================

Interactive 3D viewer for quantized-mesh terrain tiles. Use your mouse to rotate, zoom, and pan.

.. raw:: html

  <script type="importmap">
  {
    "imports": {
      "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
    }
  }
  </script>

  <script type="module">
    import * as THREE from 'three';
    import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

    // Make THREE and OrbitControls available globally for tileLoader.js
    window.THREE = THREE;
    window.OrbitControls = OrbitControls;

    // Load our tile loader after THREE is ready
    const script = document.createElement('script');
    script.src = '_static/tileLoader.js';
    document.head.appendChild(script);
  </script>

  <style>
    #viewer-container {
      width: 100%;
      height: 400px;
      background: #1a1a2e;
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 1em;
    }
    #viewer-container canvas {
      display: block;
    }
    #status {
      font-family: monospace;
      color: #666;
      margin-bottom: 1em;
    }
    .viewer-controls {
      display: flex;
      gap: 0.5em;
      margin-bottom: 1em;
      flex-wrap: wrap;
    }
    #tile-url-input {
      flex: 1;
      min-width: 200px;
      padding: 0.5em;
      border: 1px solid #ccc;
      border-radius: 4px;
    }
    #load-tile-btn {
      padding: 0.5em 1em;
      background: #3498db;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    #load-tile-btn:hover {
      background: #2980b9;
    }
  </style>

  <div id="viewer-container"></div>
  <div id="status">Initializing...</div>
  <div class="viewer-controls">
    <input type="text" id="tile-url-input" placeholder="Enter terrain tile URL (.terrain)">
    <button id="load-tile-btn">Load Tile</button>
  </div>

Controls
--------

- **Left click + drag**: Rotate view
- **Right click + drag**: Pan
- **Scroll wheel**: Zoom in/out

About
-----

This viewer demonstrates the quantized-mesh terrain format. It loads a ``.terrain`` file and renders it using Three.js.

The demo tile shows terrain data from the Swiss Alps region.

You can load your own terrain tiles by entering a URL in the input field above.
