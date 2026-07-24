<script setup>
/**
 * HeroIllustration.vue — Image 3D unique animée
 *
 * Utilise une illustration 3D du Microsoft Fluent Emoji (Sunflower)
 * avec des animations CSS immersives : lévitation, halo lumineux,
 * particules flottantes et rayons de lumière tournants.
 *
 * Source : https://github.com/microsoft/fluentui-emoji
 */
</script>

<template>
  <div class="hero-illustration">
    <!-- Halo lumineux principal (pulse) -->
    <div class="glow-main"></div>

    <!-- Rayons de lumière tournants -->
    <div class="light-rays">
      <div class="ray r1"></div>
      <div class="ray r2"></div>
      <div class="ray r3"></div>
      <div class="ray r4"></div>
      <div class="ray r5"></div>
      <div class="ray r6"></div>
    </div>

    <!-- Image 3D principale (Sunflower) avec lévitation -->
    <div class="image-orbit">
      <div class="image-float">
        <img
          src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Sunflower/3D/sunflower_3d.png"
          alt="Tournesol 3D"
          class="main-3d-image"
          draggable="false"
        />
      </div>
    </div>

    <!-- Deuxième halo interne -->
    <div class="glow-inner"></div>

    <!-- Particules flottantes -->
    <div class="particle p1"></div>
    <div class="particle p2"></div>
    <div class="particle p3"></div>
    <div class="particle p4"></div>
    <div class="particle p5"></div>
  </div>
</template>

<style scoped>
.hero-illustration {
  position: absolute;
  top: 0;
  right: -5%;
  width: 65%;
  height: 100%;
  z-index: 1;
  overflow: hidden;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ─── Halo lumineux principal ─── */
.glow-main {
  position: absolute;
  width: 500px;
  height: 500px;
  top: 45%;
  left: 55%;
  transform: translate(-50%, -50%);
  background: radial-gradient(
    circle,
    rgba(255, 193, 7, 0.25) 0%,
    rgba(255, 152, 0, 0.12) 30%,
    rgba(255, 87, 34, 0.05) 55%,
    transparent 75%
  );
  border-radius: 50%;
  animation: glow-pulse 4s ease-in-out infinite;
  filter: blur(10px);
}

@keyframes glow-pulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.8;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.3);
    opacity: 1;
  }
}

/* ─── Halo interne doré ─── */
.glow-inner {
  position: absolute;
  width: 300px;
  height: 300px;
  top: 48%;
  left: 55%;
  transform: translate(-50%, -50%);
  background: radial-gradient(
    circle,
    rgba(255, 215, 0, 0.15) 0%,
    rgba(255, 193, 7, 0.06) 40%,
    transparent 70%
  );
  border-radius: 50%;
  animation: glow-inner-pulse 3s ease-in-out infinite 0.5s;
  filter: blur(20px);
}

@keyframes glow-inner-pulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(0.9);
    opacity: 0.6;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.2);
    opacity: 1;
  }
}

/* ─── Rayons de lumière tournants ─── */
.light-rays {
  position: absolute;
  width: 450px;
  height: 450px;
  top: 45%;
  left: 55%;
  transform: translate(-50%, -50%);
  animation: rays-rotate 20s linear infinite;
}

.ray {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 200%;
  height: 2px;
  transform-origin: 0 0;
  background: linear-gradient(
    90deg,
    rgba(255, 193, 7, 0.12) 0%,
    rgba(255, 193, 7, 0.04) 50%,
    transparent 100%
  );
  border-radius: 1px;
}

.r1 { transform: rotate(0deg); }
.r2 { transform: rotate(30deg); }
.r3 { transform: rotate(60deg); }
.r4 { transform: rotate(90deg); }
.r5 { transform: rotate(120deg); }
.r6 { transform: rotate(150deg); }

@keyframes rays-rotate {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

/* ─── Image 3D principale orbit / float ─── */
.image-orbit {
  position: absolute;
  width: 350px;
  height: 350px;
  top: 48%;
  left: 55%;
  transform: translate(-50%, -50%);
  animation: orbit-float 10s ease-in-out infinite;
}

.image-float {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: image-levitate 6s ease-in-out infinite;
}

.main-3d-image {
  width: 280px;
  height: 280px;
  object-fit: contain;
  image-rendering: auto;
  filter: drop-shadow(0 20px 60px rgba(255, 193, 7, 0.3))
          drop-shadow(0 0 40px rgba(255, 193, 7, 0.15));
  animation: image-breathe 4s ease-in-out infinite;
}

@keyframes orbit-float {
  0%, 100% {
    transform: translate(-50%, -50%) translateX(0px);
  }
  25% {
    transform: translate(-50%, -50%) translateX(12px);
  }
  75% {
    transform: translate(-50%, -50%) translateX(-8px);
  }
}

@keyframes image-levitate {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-18px);
  }
}

@keyframes image-breathe {
  0%, 100% {
    transform: scale(1);
    filter: drop-shadow(0 20px 60px rgba(255, 193, 7, 0.3))
            drop-shadow(0 0 40px rgba(255, 193, 7, 0.15));
  }
  50% {
    transform: scale(1.04);
    filter: drop-shadow(0 30px 80px rgba(255, 193, 7, 0.4))
            drop-shadow(0 0 60px rgba(255, 193, 7, 0.2));
  }
}

/* ─── Particules flottantes ─── */
.particle {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(
    circle at 30% 30%,
    rgba(255, 235, 59, 0.6),
    rgba(255, 193, 7, 0.2) 50%,
    transparent 100%
  );
  pointer-events: none;
  filter: blur(1px);
}

.p1 {
  width: 10px; height: 10px;
  top: 25%; left: 60%;
  animation: float-p1 8s ease-in-out infinite;
}
.p2 {
  width: 6px; height: 6px;
  top: 60%; left: 75%;
  animation: float-p2 9s ease-in-out infinite 1s;
}
.p3 {
  width: 8px; height: 8px;
  top: 35%; left: 80%;
  animation: float-p1 7s ease-in-out infinite 2s;
}
.p4 {
  width: 5px; height: 5px;
  top: 70%; left: 50%;
  animation: float-p2 10s ease-in-out infinite 0.5s;
}
.p5 {
  width: 12px; height: 12px;
  top: 20%; left: 45%;
  animation: float-p1 11s ease-in-out infinite 3s;
}

@keyframes float-p1 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.6; }
  25% { transform: translate(15px, -20px) scale(1.2); opacity: 1; }
  50% { transform: translate(5px, -35px) scale(0.8); opacity: 0.4; }
  75% { transform: translate(-10px, -15px) scale(1.1); opacity: 0.8; }
}

@keyframes float-p2 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.4; }
  33% { transform: translate(-12px, -25px) scale(1.3); opacity: 0.9; }
  66% { transform: translate(15px, -10px) scale(0.9); opacity: 0.5; }
}

/* ─── Responsive ─── */
@media (max-width: 992px) {
  .glow-main { width: 350px; height: 350px; }
  .glow-inner { width: 200px; height: 200px; }
  .light-rays { width: 320px; height: 320px; }
  .image-orbit { width: 250px; height: 250px; }
  .main-3d-image { width: 200px; height: 200px; }
}

@media (max-width: 768px) {
  .hero-illustration { opacity: 0.35; }
  .glow-main { width: 250px; height: 250px; }
  .image-orbit { width: 180px; height: 180px; }
  .main-3d-image { width: 150px; height: 150px; }
  .light-rays { display: none; }
  .particle { display: none; }
}
</style>
