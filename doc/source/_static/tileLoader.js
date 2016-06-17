// Prepare cesium to load a single tile
// This is a copy of cesium internal code in cesiumterrainprovider
var createQuantizedMeshTerrainData = function(buffer, level, x, y, tmsY) {
  var pos = 0;
  var cartesian3Elements = 3;
  var boundingSphereElements = cartesian3Elements + 1;
  var cartesian3Length = Float64Array.BYTES_PER_ELEMENT * cartesian3Elements;
  var boundingSphereLength = Float64Array.BYTES_PER_ELEMENT * boundingSphereElements;
  var encodedVertexElements = 3;
  var encodedVertexLength = Uint16Array.BYTES_PER_ELEMENT * encodedVertexElements;
  var triangleElements = 3;
  var bytesPerIndex = Uint16Array.BYTES_PER_ELEMENT;
  var triangleLength = bytesPerIndex * triangleElements;

  var view = new DataView(buffer);
  var center = new Cesium.Cartesian3(view.getFloat64(pos, true), view.getFloat64(pos + 8, true), view.getFloat64(pos + 16, true));
  pos += cartesian3Length;

  var minimumHeight = view.getFloat32(pos, true);
  pos += Float32Array.BYTES_PER_ELEMENT;
  var maximumHeight = view.getFloat32(pos, true);
  pos += Float32Array.BYTES_PER_ELEMENT;

  var boundingSphere = new Cesium.BoundingSphere(
    new Cesium.Cartesian3(view.getFloat64(pos, true), view.getFloat64(pos + 8, true), view.getFloat64(pos + 16, true)),
    view.getFloat64(pos + cartesian3Length, true));
  pos += boundingSphereLength;

  var horizonOcclusionPoint = new Cesium.Cartesian3(view.getFloat64(pos, true), view.getFloat64(pos + 8, true), view.getFloat64(pos + 16, true));
  pos += cartesian3Length;

  var vertexCount = view.getUint32(pos, true);
  pos += Uint32Array.BYTES_PER_ELEMENT;
  var encodedVertexBuffer = new Uint16Array(buffer, pos, vertexCount * 3);
  pos += vertexCount * encodedVertexLength;

  if (vertexCount > 64 * 1024) {
    // More than 64k vertices, so indices are 32-bit.
    bytesPerIndex = Uint32Array.BYTES_PER_ELEMENT;
    triangleLength = bytesPerIndex * triangleElements;
  }

  // Decode the vertex buffer.
  var uBuffer = encodedVertexBuffer.subarray(0, vertexCount);
  var vBuffer = encodedVertexBuffer.subarray(vertexCount, 2 * vertexCount);
  var heightBuffer = encodedVertexBuffer.subarray(vertexCount * 2, 3 * vertexCount);

  var i;
  var u = 0;
  var v = 0;
  var height = 0;

  function zigZagDecode(value) {
    return (value >> 1) ^ (-(value & 1));
  }

  for (i = 0; i < vertexCount; ++i) {
    u += zigZagDecode(uBuffer[i]);
    v += zigZagDecode(vBuffer[i]);
    height += zigZagDecode(heightBuffer[i]);

    uBuffer[i] = u;
    vBuffer[i] = v;
    heightBuffer[i] = height;
  }

  // skip over any additional padding that was added for 2/4 byte alignment
  if (pos % bytesPerIndex !== 0) {
    pos += (bytesPerIndex - (pos % bytesPerIndex));
  }

  var triangleCount = view.getUint32(pos, true);
  pos += Uint32Array.BYTES_PER_ELEMENT;
  var indices = Cesium.IndexDatatype.createTypedArrayFromArrayBuffer(vertexCount, buffer, pos, triangleCount * triangleElements);
  pos += triangleCount * triangleLength;

  // High water mark decoding based on decompressIndices_ in webgl-loader's loader.js.
  // https://code.google.com/p/webgl-loader/source/browse/trunk/samples/loader.js?r=99#55
  // Copyright 2012 Google Inc., Apache 2.0 license.
  var highest = 0;
  for (i = 0; i < indices.length; ++i) {
    var code = indices[i];
    indices[i] = highest - code;
    if (code === 0) {
      ++highest;
    }
  }

  var westVertexCount = view.getUint32(pos, true);
  pos += Uint32Array.BYTES_PER_ELEMENT;
  var westIndices = Cesium.IndexDatatype.createTypedArrayFromArrayBuffer(vertexCount, buffer, pos, westVertexCount);
  pos += westVertexCount * bytesPerIndex;

  var southVertexCount = view.getUint32(pos, true);
  pos += Uint32Array.BYTES_PER_ELEMENT;
  var southIndices = Cesium.IndexDatatype.createTypedArrayFromArrayBuffer(vertexCount, buffer, pos, southVertexCount);
  pos += southVertexCount * bytesPerIndex;

  var eastVertexCount = view.getUint32(pos, true);
  pos += Uint32Array.BYTES_PER_ELEMENT;
  var eastIndices = Cesium.IndexDatatype.createTypedArrayFromArrayBuffer(vertexCount, buffer, pos, eastVertexCount);
  pos += eastVertexCount * bytesPerIndex;

  var northVertexCount = view.getUint32(pos, true);
  pos += Uint32Array.BYTES_PER_ELEMENT;
  var northIndices = Cesium.IndexDatatype.createTypedArrayFromArrayBuffer(vertexCount, buffer, pos, northVertexCount);
  pos += northVertexCount * bytesPerIndex;

  var encodedNormalBuffer;
  var waterMaskBuffer;
  while (pos < view.byteLength) {
    var extensionId = view.getUint8(pos, true);
    pos += Uint8Array.BYTES_PER_ELEMENT;
    var extensionLength = view.getUint32(pos);
    pos += Uint32Array.BYTES_PER_ELEMENT;
    var OCT_VERTEX_NORMALS = 1;
    var WATER_MASK = 2;
    if (extensionId === OCT_VERTEX_NORMALS) {
      encodedNormalBuffer = new Uint8Array(buffer, pos, vertexCount * 2);
    } else if (extensionId === WATER_MASK) {
      waterMaskBuffer = new Uint8Array(buffer, pos, extensionLength);
    }
    pos += extensionLength;
  }
  return {
    indices: indices,
    xVertices: uBuffer,
    yVertices: vBuffer,
    hVertices: heightBuffer,
    encodedNormalBuffer: encodedNormalBuffer,
    waterMaskBuffer: waterMaskBuffer
  }
};

var id, scene, axes, camera, renderer, material, controls, width, height;

var createScene = function(z, x, y, tileUrl) {
  scene = new THREE.Scene();
  axes = new THREE.AxisHelper(2000000);
  scene.add(axes);
  camera = new THREE.PerspectiveCamera(45, width / height, 1.0, 1000);
  camera.position.set(0, 0, 50);
  renderer = new THREE.WebGLRenderer();
  renderer.setSize(width, height);
  material = new THREE.MeshPhongMaterial({
    color: 0xdddddd,
    wireframe: true
  });
  loadTerrain(tileUrl);
  render();
  addTile(z, x, z, tileUrl);
};

var destroyScene = function() {
  if (id) {
    cancelAnimationFrame(id);
  }
  scene = null;
  camera = null;
  controls = null;
  material = null;
};

var updateScene = function(z, x, y, tileUrl) {
  width  = $('#quantized-mesh-tile-viewer').innerWidth();
  height = $(window).innerHeight();
  if (scene) {
    destroyScene();
    empty(document.getElementById('webgl'));
  }
  createScene(z, x, y, tileUrl);
};

var loadTerrain = function(tileUrl) {
  var terrainLoader = new THREE.TerrainLoader();
  terrainLoader.load(tileUrl, function(data) {
    var geometry = new THREE.PlaneGeometry(60, 60, 199, 199);
    for (var i = 0, l = geometry.vertices.length; i < l; i++) {
      geometry.vertices[i].z = data[i] / 65535 * 10;
    }
    var plane = new THREE.Mesh(geometry, material);
  });
  controls = new THREE.TrackballControls(camera); 
  document.getElementById('webgl').appendChild(renderer.domElement);
};

function render() {
  controls.update();    
  id = requestAnimationFrame(render);
  renderer.render(scene, camera);
}

function empty(elem) {
  while (elem.lastChild) elem.removeChild(elem.lastChild);
}

var addTile = function(lod, x, y, tileUrl) {
  Cesium.loadArrayBuffer(tileUrl).then(function(arrayBuffer) {
    var t = createQuantizedMeshTerrainData(arrayBuffer, lod, x, y, 0);
    var geo = new THREE.Geometry();
    var factor = 1000.0;
    var offset = 32767 / 2;
    var normalMaterial = new THREE.LineBasicMaterial({
        color: 0x0000ff
    });
    var hasNormals = t.encodedNormalBuffer && t.encodedNormalBuffer.length == t.xVertices.length * 2;
    for (var i = 0; i < t.xVertices.length; i++) {
      var v = new THREE.Vector3((t.xVertices[i]-offset)/factor, (t.yVertices[i]-offset)/factor, t.hVertices[i]/factor);
      geo.vertices.push(v);
      if (hasNormals) {
        var normal = new Cesium.Cartesian3(0.0, 0.0, 0.0);
        Cesium.AttributeCompression.octDecode(t.encodedNormalBuffer[i], t.encodedNormalBuffer[i+1], normal)
        //Adding normal for this point (right now it's hard coded normal)
        var threenormal = new THREE.Vector3(normal.x, normal.y, normal.z);
        var other =new THREE.Vector3(v.x, v.y, v.z);
        other.add(threenormal);
        var normal = new THREE.Geometry();
        normal.vertices.push(v);
        normal.vertices.push(other);
      }

      var line = new THREE.Line(normal, normalMaterial);
      scene.add(line);
    }
    for (var i = 0; i < t.indices.length - 1; i = i + 3) {
      geo.faces.push(new THREE.Face3(t.indices[i], t.indices[i+1], t.indices[i+2]));
    }
    geo.computeFaceNormals();
    var plane = new THREE.Mesh(geo, material);
    scene.add(plane);
  }).otherwise(function(error) {
    console.log('error occured ', error);
  });
};

$(document).ready(function() {
  var QueryString = function () {
    // This function is anonymous, is executed immediately and 
    // the return value is assigned to QueryString!
    var query_string = {};
    var query = window.location.search.substring(1);
    var vars = query.split("&");
    for (var i=0;i<vars.length;i++) {
      var pair = vars[i].split("=");
          // If first entry with this name
      if (typeof query_string[pair[0]] === "undefined") {
        query_string[pair[0]] = decodeURIComponent(pair[1]);
          // If second entry with this name
      } else if (typeof query_string[pair[0]] === "string") {
        var arr = [ query_string[pair[0]],decodeURIComponent(pair[1]) ];
        query_string[pair[0]] = arr;
          // If third or later entry with this name
      } else {
        query_string[pair[0]].push(decodeURIComponent(pair[1]));
      }
    } 
    return query_string;
  }();
  var z = parseInt(QueryString.z);
  var x = parseInt(QueryString.x);
  var y = parseInt(QueryString.y);
  var tileUrl = QueryString.tileUrl;
  if (!z || !x || !y || !tileUrl) {
    updateScene(14, 24297, 10735, 'https://assets.agi.com/stk-terrain/world/14/24297/10735.terrain?v=1.16389.0');
  } else {
    updateScene(z, x, y, tileUrl);
  } 
});
