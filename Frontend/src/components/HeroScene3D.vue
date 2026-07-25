<script setup>
/**
 * HeroScene3D.vue — Scène 3D cinématographique pour le hero
 *
 * Rendu en temps réel avec Three.js : plante 3D stylisée,
 * éclairage cinématographique (soleil chaud + bloom),
 * particules dorées flottantes et animation organique.
 *
 * Conçue pour l'agrotech — mêle élégance végétale et tech.
 */
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'

const container = ref(null)

let scene, camera, renderer, composer
let plant, leaves = [], particles, stalk
let clock = new THREE.Timer()
let animId = null
let resizeObs = null
const PARTICLE_COUNT = 80

// ─── Geometry helpers ───

function createLeafShape(length, width) {
  const shape = new THREE.Shape()
  const hw = width / 2
  shape.moveTo(0, 0)
  shape.bezierCurveTo(hw * 0.9, length * 0.2, hw * 1.3, length * 0.5, hw * 0.5, length * 0.85)
  shape.quadraticCurveTo(0, length, 0, length)
  shape.bezierCurveTo(-hw * 0.5, length * 0.85, -hw * 1.3, length * 0.5, -hw * 0.9, length * 0.2)
  shape.quadraticCurveTo(0, 0, 0, 0)
  return shape
}

function createLeafGeometry(length, width, bend) {
  const geo = new THREE.ShapeGeometry(createLeafShape(length, width))
  const pos = geo.attributes.position
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i)
    const y = pos.getY(i)
    pos.setZ(i, Math.sin((y / length) * Math.PI) * bend)
  }
  pos.needsUpdate = true
  geo.computeVertexNormals()
  return geo
}

// ─── Scene building ───

function init() {
  if (!container.value) return
  const el = container.value
  if (el.clientWidth < 50 || el.clientHeight < 50) return

  const w = el.clientWidth
  const h = el.clientHeight

  // ── Scene ──
  scene = new THREE.Scene()

  // ── Camera ──
  camera = new THREE.PerspectiveCamera(28, w / h, 0.1, 50)
  camera.position.set(2.8, 2.2, 5.5)
  camera.lookAt(0, 1.2, 0)

  // ── Renderer ──
  renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFShadowMap
  renderer.outputColorSpace = THREE.SRGBColorSpace
  el.appendChild(renderer.domElement)

  // ── Composer ──
  composer = new EffectComposer(renderer)
  composer.addPass(new RenderPass(scene, camera))

  const bloom = new UnrealBloomPass(
    new THREE.Vector2(w, h),
    0.35,   // strength
    0.4,    // radius
    0.05    // threshold
  )
  composer.addPass(bloom)

  // ── Build scene ──
  createLights()
  createGround()
  createPlant()
  createParticles()

  // ── Resize ──
  window.addEventListener('resize', onResize)
  resizeObs = new ResizeObserver(() => onResize())
  resizeObs.observe(el)

  // ── Go ──
  animate()
}

function createLights() {
  // Ambient base
  scene.add(new THREE.AmbientLight('#2a4a2a', 0.25))

  // Hemisphere
  scene.add(new THREE.HemisphereLight('#87ceeb', '#2e1a0e', 0.3))

  // Sun (warm directional)
  const sun = new THREE.DirectionalLight('#ffb74d', 2.5)
  sun.position.set(4, 8, 3)
  sun.castShadow = true
  sun.shadow.mapSize.set(1024, 1024)
  const sd = 5
  sun.shadow.camera.left = -sd
  sun.shadow.camera.right = sd
  sun.shadow.camera.top = sd
  sun.shadow.camera.bottom = -sd
  sun.shadow.camera.near = 1
  sun.shadow.camera.far = 15
  scene.add(sun)

  // Sun glow (visible sphere)
  const glowGeo = new THREE.SphereGeometry(0.15, 16, 16)
  const glowMat = new THREE.MeshBasicMaterial({ color: '#ffb74d' })
  const glowMesh = new THREE.Mesh(glowGeo, glowMat)
  glowMesh.position.copy(sun.position)
  scene.add(glowMesh)

  // Sun lens flare proxy (additive billboard)
  const flareGeo = new THREE.SphereGeometry(0.4, 8, 8)
  const flareMat = new THREE.MeshBasicMaterial({
    color: '#ffd54f',
    transparent: true,
    opacity: 0.15,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  const flare = new THREE.Mesh(flareGeo, flareMat)
  flare.position.copy(sun.position).multiplyScalar(0.7)
  scene.add(flare)

  // Fill light (cool)
  const fill = new THREE.DirectionalLight('#4fc3f7', 0.3)
  fill.position.set(-2, 1, 4)
  scene.add(fill)

  // Rim light (primary green)
  const rim = new THREE.DirectionalLight('#00e676', 0.5)
  rim.position.set(-3, 3, -4)
  scene.add(rim)
}

function createGround() {
  // Soil mound
  const soilGeo = new THREE.SphereGeometry(1.3, 28, 20, 0, Math.PI * 2, 0, Math.PI / 2)
  const soilMat = new THREE.MeshStandardMaterial({
    color: '#3e2723',
    roughness: 0.95,
    metalness: 0.0,
  })
  const soil = new THREE.Mesh(soilGeo, soilMat)
  soil.position.y = -0.4
  soil.receiveShadow = true
  scene.add(soil)

  // Small rocks / soil bumps
  for (let i = 0; i < 6; i++) {
    const a = Math.random() * Math.PI * 2
    const r = 0.4 + Math.random() * 0.7
    const size = 0.03 + Math.random() * 0.06
    const rock = new THREE.Mesh(
      new THREE.DodecahedronGeometry(size, 0),
      new THREE.MeshStandardMaterial({
        color: '#4e342e',
        roughness: 1,
        metalness: 0,
      })
    )
    rock.position.set(Math.cos(a) * r, -0.3 + Math.random() * 0.05, Math.sin(a) * r)
    rock.rotation.set(Math.random(), Math.random(), Math.random())
    scene.add(rock)
  }

  // Shadow catcher (invisible plane)
  const shadowMat = new THREE.ShadowMaterial({ opacity: 0.3, color: '#000000' })
  const shadowPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(6, 6),
    shadowMat
  )
  shadowPlane.rotation.x = -Math.PI / 2
  shadowPlane.position.y = -0.55
  shadowPlane.receiveShadow = true
  scene.add(shadowPlane)
}

function createPlant() {
  plant = new THREE.Group()

  // ── Stalk ──
  const pts = []
  const segs = 12
  for (let i = 0; i <= segs; i++) {
    const t = i / segs
    const sway = Math.sin(t * Math.PI * 1.3) * 0.25
    pts.push(new THREE.Vector3(
      sway,
      t * 3.0 - 0.25,
      Math.sin(t * Math.PI * 0.8) * 0.12
    ))
  }
  const curve = new THREE.CatmullRomCurve3(pts)

  // Stalk mesh
  const tubeGeo = new THREE.TubeGeometry(curve, 20, 0.07, 6, false)
  const tubeMat = new THREE.MeshPhysicalMaterial({
    color: '#5d8a3c',
    roughness: 0.5,
    metalness: 0.0,
    clearcoat: 0.1,
  })
  stalk = new THREE.Mesh(tubeGeo, tubeMat)
  stalk.castShadow = true
  plant.add(stalk)

  // ── Leaves ──
  const configs = [
    { t: 0.15, len: 0.5, wid: 0.18, bend: 0.04, angle: 0.3, color: '#2e7d32' },
    { t: 0.28, len: 0.7, wid: 0.22, bend: 0.06, angle: 1.0, color: '#388e3c' },
    { t: 0.40, len: 0.9, wid: 0.26, bend: 0.08, angle: 1.7, color: '#43a047' },
    { t: 0.52, len: 1.0, wid: 0.28, bend: 0.10, angle: 2.4, color: '#4caf50' },
    { t: 0.63, len: 0.95, wid: 0.26, bend: 0.09, angle: 3.1, color: '#388e3c' },
    { t: 0.74, len: 0.85, wid: 0.22, bend: 0.07, angle: 3.8, color: '#43a047' },
    { t: 0.85, len: 0.6, wid: 0.18, bend: 0.05, angle: 4.5, color: '#2e7d32' },
  ]

  configs.forEach((cfg) => {
    const geo = createLeafGeometry(cfg.len, cfg.wid, cfg.bend)
    const mat = new THREE.MeshPhysicalMaterial({
      color: cfg.color,
      roughness: 0.3,
      metalness: 0.0,
      clearcoat: 0.35,
      clearcoatRoughness: 0.3,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.95,
    })

    const mesh = new THREE.Mesh(geo, mat)
    const pos = curve.getPoint(cfg.t)
    const tangent = curve.getTangent(cfg.t)

    mesh.position.copy(pos)

    // Orient along tangent
    const up = new THREE.Vector3(0, 1, 0)
    const q = new THREE.Quaternion().setFromUnitVectors(up, tangent)
    mesh.quaternion.copy(q)

    // Spiral rotation
    const spiral = new THREE.Quaternion().setFromAxisAngle(tangent, cfg.angle)
    mesh.quaternion.multiply(spiral)

    // Slight random variation
    mesh.quaternion.multiply(
      new THREE.Quaternion().setFromUnitVectors(
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(
          1 - Math.random() * 0.1,
          1,
          1 - Math.random() * 0.1
        ).normalize()
      )
    )

    mesh.castShadow = true
    mesh.userData = {
      swaySpeed: 0.4 + Math.random() * 0.3,
      swayAmp: 0.02 + Math.random() * 0.015,
      phase: Math.random() * Math.PI * 2,
    }

    plant.add(mesh)
    leaves.push(mesh)
  })

  scene.add(plant)
}

function createParticles() {
  const count = PARTICLE_COUNT
  const positions = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const speeds = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    const a = Math.random() * Math.PI * 2
    const r = 0.8 + Math.random() * 2.2
    positions[i * 3] = Math.cos(a) * r
    positions[i * 3 + 1] = -0.3 + Math.random() * 4
    positions[i * 3 + 2] = Math.sin(a) * r
    sizes[i] = 0.02 + Math.random() * 0.05
    speeds[i] = 0.15 + Math.random() * 0.4
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

  const mat = new THREE.PointsMaterial({
    color: '#ffd54f',
    size: 0.045,
    transparent: true,
    opacity: 0.5,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  })

  particles = new THREE.Points(geo, mat)
  particles.userData = { speeds, positions }
  scene.add(particles)
}

// ─── Animation loop ───

function animate() {
  animId = requestAnimationFrame(animate)
  const delta = Math.min(clock.getDelta(), 0.05) // cap 50ms pour éviter les sauts
  const time = clock.getElapsed()

  // Plant sway
  if (plant) {
    plant.rotation.z = Math.sin(time * 0.25) * 0.015
    plant.rotation.x = Math.sin(time * 0.18 + 0.8) * 0.012
  }

  // Leaf flutter
  leaves.forEach((leaf) => {
    const ud = leaf.userData
    if (!ud) return
    const val = Math.sin(time * ud.swaySpeed + ud.phase)
    leaf.rotation.z += val * delta * ud.swayAmp * 3
  })

  // Particles
  if (particles) {
    const pos = particles.geometry.attributes.position
    const arr = pos.array
    const speeds = particles.userData.speeds
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      arr[i * 3 + 1] += delta * speeds[i] * 0.2
      if (arr[i * 3 + 1] > 4) {
        arr[i * 3 + 1] = -0.3
        const a = Math.random() * Math.PI * 2
        const r = 0.8 + Math.random() * 2.2
        arr[i * 3] = Math.cos(a) * r
        arr[i * 3 + 2] = Math.sin(a) * r
      }
    }
    pos.needsUpdate = true
  }

  composer.render()
}

// ─── Resize ───

function onResize() {
  if (!container.value || !camera || !renderer || !composer) return
  const w = container.value.clientWidth
  const h = container.value.clientHeight
  if (w < 50 || h < 50) return
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
  composer.setSize(w, h)
}

// ─── Lifecycle ───

onMounted(() => {
  // Small delay to ensure layout is ready
  setTimeout(() => init(), 100)
})

onUnmounted(() => {
  cancelAnimationFrame(animId)
  window.removeEventListener('resize', onResize)
  resizeObs?.disconnect()
  renderer?.dispose()
  scene = null
  camera = null
  renderer = null
  composer = null
  plant = null
  leaves = []
})
</script>

<template>
  <div ref="container" class="hero-3d-container" aria-hidden="true"></div>
</template>

<style scoped>
.hero-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.hero-3d-container :deep(canvas) {
  display: block;
  width: 100% !important;
  height: 100% !important;
}
</style>
