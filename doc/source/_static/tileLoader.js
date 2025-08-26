// Quantized-Mesh Tile Viewer
// Modern THREE.js implementation without Cesium dependency

// Parse quantized-mesh terrain format
function parseQuantizedMesh(buffer) {
  const view = new DataView(buffer);
  let pos = 0;

  // Header
  const centerX = view.getFloat64(pos, true); pos += 8;
  const centerY = view.getFloat64(pos, true); pos += 8;
  const centerZ = view.getFloat64(pos, true); pos += 8;

  const minimumHeight = view.getFloat32(pos, true); pos += 4;
  const maximumHeight = view.getFloat32(pos, true); pos += 4;

  // Bounding sphere
  const bsCenterX = view.getFloat64(pos, true); pos += 8;
  const bsCenterY = view.getFloat64(pos, true); pos += 8;
  const bsCenterZ = view.getFloat64(pos, true); pos += 8;
  const bsRadius = view.getFloat64(pos, true); pos += 8;

  // Horizon occlusion point
  const horizonX = view.getFloat64(pos, true); pos += 8;
  const horizonY = view.getFloat64(pos, true); pos += 8;
  const horizonZ = view.getFloat64(pos, true); pos += 8;

  // Vertex count
  const vertexCount = view.getUint32(pos, true); pos += 4;

  // Encoded vertex buffer (u, v, height)
  const encodedVertexBuffer = new Uint16Array(buffer, pos, vertexCount * 3);
  pos += vertexCount * 3 * 2;

  // Decode vertices using zigzag decoding
  const uBuffer = new Uint16Array(vertexCount);
  const vBuffer = new Uint16Array(vertexCount);
  const heightBuffer = new Uint16Array(vertexCount);

  function zigZagDecode(value) {
    return (value >> 1) ^ (-(value & 1));
  }

  let u = 0, v = 0, height = 0;
  for (let i = 0; i < vertexCount; i++) {
    u += zigZagDecode(encodedVertexBuffer[i]);
    v += zigZagDecode(encodedVertexBuffer[vertexCount + i]);
    height += zigZagDecode(encodedVertexBuffer[vertexCount * 2 + i]);

    uBuffer[i] = u;
    vBuffer[i] = v;
    heightBuffer[i] = height;
  }

  // Determine index size
  let bytesPerIndex = 2;
  if (vertexCount > 65536) {
    bytesPerIndex = 4;
  }

  // Align position
  if (pos % bytesPerIndex !== 0) {
    pos += bytesPerIndex - (pos % bytesPerIndex);
  }

  // Triangle indices
  const triangleCount = view.getUint32(pos, true); pos += 4;
  let indices;
  if (bytesPerIndex === 2) {
    indices = new Uint16Array(buffer, pos, triangleCount * 3);
  } else {
    indices = new Uint32Array(buffer, pos, triangleCount * 3);
  }
  pos += triangleCount * 3 * bytesPerIndex;

  // Decode indices (high water mark)
  const decodedIndices = new (bytesPerIndex === 2 ? Uint16Array : Uint32Array)(indices.length);
  let highest = 0;
  for (let i = 0; i < indices.length; i++) {
    const code = indices[i];
    decodedIndices[i] = highest - code;
    if (code === 0) {
      highest++;
    }
  }

  return {
    vertexCount,
    triangleCount,
    uBuffer,
    vBuffer,
    heightBuffer,
    indices: decodedIndices,
    minimumHeight,
    maximumHeight
  };
}

// Scene variables
let scene, camera, renderer, controls, animationId;

function initViewer(containerId) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error('Container not found:', containerId);
    return;
  }

  const width = container.clientWidth || 600;
  const height = 400;

  // Scene
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1a2e);

  // Camera
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(0, -50, 30);
  camera.up.set(0, 0, 1);

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(renderer.domElement);

  // Controls
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;

  // Lighting
  const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
  directionalLight.position.set(1, 1, 1);
  scene.add(directionalLight);

  // Axes helper
  const axesHelper = new THREE.AxesHelper(20);
  scene.add(axesHelper);

  // Grid
  const gridHelper = new THREE.GridHelper(40, 20, 0x444444, 0x222222);
  gridHelper.rotation.x = Math.PI / 2;
  scene.add(gridHelper);

  // Start animation loop
  animate();
}

function animate() {
  animationId = requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

function loadTile(url) {
  const statusEl = document.getElementById('status');
  if (statusEl) statusEl.textContent = 'Loading tile...';

  fetch(url)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.arrayBuffer();
    })
    .then(buffer => {
      const tile = parseQuantizedMesh(buffer);
      displayTile(tile);
      if (statusEl) {
        statusEl.textContent = `Loaded: ${tile.vertexCount} vertices, ${tile.triangleCount} triangles`;
      }
    })
    .catch(error => {
      console.error('Failed to load tile:', error);
      if (statusEl) statusEl.textContent = `Error: ${error.message}`;
    });
}

function displayTile(tile) {
  // Remove existing mesh
  const existing = scene.getObjectByName('terrainMesh');
  if (existing) scene.remove(existing);

  // Create geometry
  const geometry = new THREE.BufferGeometry();

  // Convert quantized values to positions
  const positions = new Float32Array(tile.vertexCount * 3);
  const scale = 30 / 32767; // Scale to reasonable size
  const heightScale = 20 / 32767;

  for (let i = 0; i < tile.vertexCount; i++) {
    positions[i * 3] = (tile.uBuffer[i] - 16383) * scale;
    positions[i * 3 + 1] = (tile.vBuffer[i] - 16383) * scale;
    positions[i * 3 + 2] = tile.heightBuffer[i] * heightScale;
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setIndex(new THREE.BufferAttribute(tile.indices, 1));
  geometry.computeVertexNormals();

  // Create mesh with material
  const material = new THREE.MeshPhongMaterial({
    color: 0x3498db,
    side: THREE.DoubleSide,
    flatShading: true
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = 'terrainMesh';
  scene.add(mesh);

  // Add wireframe overlay
  const wireframeMaterial = new THREE.MeshBasicMaterial({
    color: 0x000000,
    wireframe: true,
    transparent: true,
    opacity: 0.1
  });
  const wireframe = new THREE.Mesh(geometry, wireframeMaterial);
  wireframe.name = 'terrainWireframe';
  scene.add(wireframe);

  // Center camera on mesh
  geometry.computeBoundingSphere();
  const center = geometry.boundingSphere.center;
  controls.target.copy(center);
  camera.lookAt(center);
}

// Initialize viewer - called directly since DOM is already ready when this script loads
function init() {
  const container = document.getElementById('viewer-container');
  if (!container || typeof THREE === 'undefined' || typeof OrbitControls === 'undefined') {
    return;
  }

  initViewer('viewer-container');
  loadTile('_static/demo.terrain');

  // Handle custom URL input
  const loadBtn = document.getElementById('load-tile-btn');
  const urlInput = document.getElementById('tile-url-input');

  if (loadBtn && urlInput) {
    loadBtn.addEventListener('click', function() {
      const url = urlInput.value.trim();
      if (url) loadTile(url);
    });
  }
}

// Run init immediately since this script is loaded after DOM is ready
init();
