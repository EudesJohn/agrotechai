<script setup>
/**
 * PlantIllustration.vue — Visualisation 3D de la croissance
 *
 * Affiche une illustration 3D différente selon le stade de croissance
 * en utilisant les Microsoft Fluent Emoji 3D (agriculture).
 *
 * Stades : Seedling → Herb → Shamrock → Tulip → Blossom
 * Source : https://github.com/microsoft/fluentui-emoji
 */
import { computed } from 'vue'

const props = defineProps({
  progress: { type: Number, default: 0 },
  color: { type: String, default: '#00e676' },
})

const stage = computed(() => {
  const p = props.progress
  if (p < 0.15) return 'seed'
  if (p < 0.35) return 'sprout'
  if (p < 0.6) return 'growing'
  if (p < 0.85) return 'mature'
  return 'flowering'
})

const stageLabel = computed(() => {
  const labels = {
    seed: '🌱 Semence',
    sprout: '🌿 Germination',
    growing: '☘️ Croissance',
    mature: '🌷 Mature',
    flowering: '🌸 Floraison',
  }
  return labels[stage.value] || '🌱 Semence'
})

const stageDescription = computed(() => {
  const descs = {
    seed: 'La vie commence à peine…',
    sprout: 'Les premières feuilles émergent',
    growing: 'La plante se développe vigoureusement',
    mature: 'Les bourgeons se forment',
    flowering: 'La floraison est complète !',
  }
  return descs[stage.value] || ''
})

// Images 3D Microsoft Fluent Emoji par stade de croissance
const stageImages = {
  seed: 'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Seedling/3D/seedling_3d.png',
  sprout: 'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Herb/3D/herb_3d.png',
  growing: 'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Shamrock/3D/shamrock_3d.png',
  mature: 'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Tulip/3D/tulip_3d.png',
  flowering: 'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Blossom/3D/blossom_3d.png',
}

const currentImage = computed(() => stageImages[stage.value] || stageImages.seed)
const progressPercent = computed(() => Math.round(props.progress * 100))
</script>

<template>
  <div class="plant-illustration">
    <!-- Halo lumineux de fond -->
    <div class="plant-ambient-glow" :style="{ background: `radial-gradient(circle, ${props.color}15 0%, transparent 70%)` }"></div>

    <!-- Image 3D principale -->
    <div class="image-container">
      <div class="image-wrapper">
        <div class="image-glow-ring" :style="{ borderColor: props.color }"></div>
        <img
          :src="currentImage"
          :alt="stageLabel"
          class="stage-image"
          draggable="false"
        />
      </div>
    </div>

    <!-- Overlay décoratif bas -->
    <div class="bottom-fade"></div>

    <!-- Brin lumineux décoratif -->
    <svg class="deco-line" viewBox="0 0 200 400" preserveAspectRatio="none">
      <path
        d="M100 400 Q130 250 110 150 Q100 80 120 0"
        :stroke="props.color"
        stroke-width="0.8"
        fill="none"
        opacity="0.15"
        stroke-dasharray="4 6"
      />
      <path
        d="M80 400 Q50 280 70 180 Q90 100 60 0"
        :stroke="props.color"
        stroke-width="0.6"
        fill="none"
        opacity="0.08"
        stroke-dasharray="3 8"
      />
    </svg>

    <!-- Barre de progression -->
    <div class="progress-track">
      <div
        class="progress-fill"
        :style="{
          width: progressPercent + '%',
          background: `linear-gradient(90deg, ${props.color}88, ${props.color})`,
          boxShadow: `0 0 12px ${props.color}`,
        }"
      ></div>
      <div class="progress-dot" :style="{ left: progressPercent + '%', background: props.color, boxShadow: `0 0 10px ${props.color}` }"></div>
    </div>

    <!-- Badge de stade -->
    <div class="stage-badge" :style="{ borderColor: props.color + '44' }">
      <div class="stage-dot" :style="{ background: props.color, boxShadow: `0 0 6px ${props.color}` }"></div>
      <div class="stage-text">
        <span class="stage-title">{{ stageLabel }}</span>
        <span class="stage-desc">{{ stageDescription }}</span>
      </div>
      <div class="stage-percent" :style="{ color: props.color }">{{ progressPercent }}%</div>
    </div>
  </div>
</template>

<style scoped>
.plant-illustration {
  width: 100%;
  height: 500px;
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    180deg,
    rgba(5, 15, 8, 0.4) 0%,
    rgba(2, 10, 4, 0.8) 100%
  );
}

/* ─── Halo ambiant ─── */
.plant-ambient-glow {
  position: absolute;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 400px;
  height: 400px;
  border-radius: 50%;
  animation: ambient-pulse 5s ease-in-out infinite;
  pointer-events: none;
}

@keyframes ambient-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.6; }
  50% { transform: translate(-50%, -50%) scale(1.2); opacity: 1; }
}

/* ─── Image 3D ─── */
.image-container {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 280px;
  height: 280px;
}

.image-wrapper {
  position: relative;
  width: 240px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: stage-float 6s ease-in-out infinite;
}

.image-glow-ring {
  position: absolute;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  border: 1.5px solid;
  opacity: 0.15;
  animation: ring-spin 12s linear infinite;
}

@keyframes ring-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.stage-image {
  width: 200px;
  height: 200px;
  object-fit: contain;
  image-rendering: auto;
  filter: drop-shadow(0 10px 40px rgba(0, 0, 0, 0.4))
          drop-shadow(0 0 30px rgba(0, 230, 118, 0.15));
  transition: transform 500ms cubic-bezier(0.22, 1, 0.36, 1), opacity 500ms ease-out;
  animation: stage-breathe 4s ease-in-out infinite;
}

@keyframes stage-float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-12px); }
}

@keyframes stage-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}

/* ─── Bottom decorative fade ─── */
.bottom-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 120px;
  background: linear-gradient(0deg, rgba(2, 10, 4, 0.6) 0%, transparent 100%);
  pointer-events: none;
  z-index: 1;
}

/* ─── Decorative line ─── */
.deco-line {
  position: absolute;
  left: 30px;
  bottom: 0;
  width: 80px;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

/* ─── Progress Bar ─── */
.progress-track {
  position: absolute;
  bottom: 70px;
  left: 50%;
  transform: translateX(-50%);
  width: 65%;
  max-width: 320px;
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  overflow: visible;
  z-index: 3;
}

.progress-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
}

.progress-dot {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: left 0.6s cubic-bezier(0.22, 1, 0.36, 1);
  border: 2px solid rgba(0, 0, 0, 0.3);
}

/* ─── Stage Badge ─── */
.stage-badge {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 20px;
  border-radius: 100px;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid;
  backdrop-filter: blur(16px);
  z-index: 3;
  white-space: nowrap;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  transition: background 200ms ease-out, border-color 200ms ease-out;
}

.stage-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  animation: dot-pulse 2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.stage-text {
  display: flex;
  flex-direction: column;
}

.stage-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  line-height: 1.2;
}

.stage-desc {
  font-size: 0.65rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.4);
  line-height: 1.2;
}

.stage-percent {
  font-size: 0.8rem;
  font-weight: 900;
  font-family: 'Syne', sans-serif;
  opacity: 0.8;
}

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .plant-illustration { height: 380px; }
  .image-container { width: 200px; height: 200px; }
  .image-wrapper { width: 170px; height: 170px; }
  .stage-image { width: 150px; height: 150px; }
  .image-glow-ring { width: 160px; height: 160px; }
  .plant-ambient-glow { width: 280px; height: 280px; }
  .deco-line { display: none; }
  .stage-badge { padding: 6px 14px; gap: 8px; }
  .stage-title { font-size: 0.75rem; }
  .stage-desc { display: none; }
  .stage-percent { font-size: 0.7rem; }
  .progress-track { width: 75%; bottom: 60px; }
  .stage-badge { bottom: 16px; }
}

@media (max-width: 480px) {
  .plant-illustration { height: 300px; }
  .image-container { width: 150px; height: 150px; }
  .image-wrapper { width: 130px; height: 130px; }
  .stage-image { width: 110px; height: 110px; }
  .image-glow-ring { width: 120px; height: 120px; }
  .stage-title { font-size: 0.7rem; }
  .stage-percent { font-size: 0.65rem; }
}
</style>
