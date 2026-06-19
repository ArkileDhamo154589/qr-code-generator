// Lightweight 3D animated background: floating wireframe shapes in red,
// with subtle mouse / device parallax. Degrades gracefully if WebGL or
// THREE is unavailable, and respects prefers-reduced-motion.
(function () {
  if (typeof THREE === "undefined") return;
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var canvas = document.getElementById("bg-canvas");
  if (!canvas) return;

  var renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  } catch (e) {
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
  camera.position.z = 14;

  var RED = 0xff3b30;
  var DIM = 0x5a1f1c;

  var group = new THREE.Group();
  scene.add(group);

  var geometries = [
    new THREE.IcosahedronGeometry(1.4, 0),
    new THREE.TorusGeometry(1.1, 0.4, 8, 16),
    new THREE.OctahedronGeometry(1.5, 0),
    new THREE.BoxGeometry(1.8, 1.8, 1.8),
    new THREE.DodecahedronGeometry(1.4, 0)
  ];

  var shapes = [];
  var COUNT = 18;
  for (var i = 0; i < COUNT; i++) {
    var geo = geometries[i % geometries.length];
    var mat = new THREE.MeshBasicMaterial({
      color: i % 3 === 0 ? RED : DIM,
      wireframe: true,
      transparent: true,
      opacity: i % 3 === 0 ? 0.55 : 0.32
    });
    var mesh = new THREE.Mesh(geo, mat);

    mesh.position.set(
      (Math.cos(i * 1.7) * 9),
      (Math.sin(i * 2.3) * 6),
      (Math.sin(i * 1.1) * 6) - 3
    );
    var s = 0.5 + (i % 5) * 0.18;
    mesh.scale.setScalar(s);

    mesh.userData.spin = {
      x: 0.0015 + (i % 4) * 0.0006,
      y: 0.0020 + (i % 3) * 0.0008
    };
    mesh.userData.floatPhase = i * 0.9;
    mesh.userData.baseY = mesh.position.y;

    group.add(mesh);
    shapes.push(mesh);
  }

  // Particle starfield for depth
  var particleCount = 700;
  var positions = new Float32Array(particleCount * 3);
  for (var p = 0; p < particleCount; p++) {
    positions[p * 3] = (Math.cos(p) * 0.5 + (p % 50) / 50 - 0.5) * 60 - 0 + (Math.sin(p * 3.7) * 30);
    positions[p * 3 + 1] = (Math.sin(p * 1.3) * 30);
    positions[p * 3 + 2] = (Math.cos(p * 0.7) * 30) - 10;
  }
  var pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  var pMat = new THREE.PointsMaterial({
    color: RED,
    size: 0.08,
    transparent: true,
    opacity: 0.6
  });
  var particles = new THREE.Points(pGeo, pMat);
  scene.add(particles);

  var target = { x: 0, y: 0 };
  var current = { x: 0, y: 0 };

  window.addEventListener("mousemove", function (e) {
    target.x = (e.clientX / window.innerWidth - 0.5) * 2;
    target.y = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  window.addEventListener("deviceorientation", function (e) {
    if (e.gamma == null || e.beta == null) return;
    target.x = Math.max(-1, Math.min(1, e.gamma / 45));
    target.y = Math.max(-1, Math.min(1, e.beta / 90));
  }, { passive: true });

  function resize() {
    var w = window.innerWidth;
    var h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize);
  resize();

  var t = 0;
  function animate() {
    requestAnimationFrame(animate);
    t += 0.01;

    current.x += (target.x - current.x) * 0.05;
    current.y += (target.y - current.y) * 0.05;

    group.rotation.y = current.x * 0.4 + t * 0.02;
    group.rotation.x = current.y * 0.3;

    particles.rotation.y -= 0.0006;
    particles.rotation.x = -current.y * 0.15;

    for (var i = 0; i < shapes.length; i++) {
      var m = shapes[i];
      m.rotation.x += m.userData.spin.x;
      m.rotation.y += m.userData.spin.y;
      m.position.y = m.userData.baseY + Math.sin(t + m.userData.floatPhase) * 0.6;
    }

    renderer.render(scene, camera);
  }
  animate();
})();
