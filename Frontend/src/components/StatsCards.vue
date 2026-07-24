<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [
    { label: 'Récoltes Sauvées', value: '12,400', icon: 'leaf', color: '#00e676' },
    { label: 'Agriculteurs', value: '5,000', icon: 'users', color: '#00e5ff' },
    { label: 'Analyses IA', value: '50,000', icon: 'brain', color: '#b388ff' },
  ]},
  animate: { type: Boolean, default: true },
})

const vals = ref(props.data.map(() => ''))

function animateCounters() {
  props.data.forEach((item, i) => {
    const t = parseInt(item.value.replace(/[^0-9]/g, ''), 10) || 0
    const dur = 1500 + i * 200
    const s = performance.now()
    function step(n) {
      const p = Math.min(1, (n - s) / dur)
      vals.value[i] = Math.round((1 - Math.pow(1 - p, 3)) * t).toLocaleString()
      if (p < 1) requestAnimationFrame(step)
      else vals.value[i] = item.value
    }
    requestAnimationFrame(step)
  })
}

onMounted(() => props.animate ? animateCounters() : props.data.forEach((item, i) => { vals.value[i] = item.value }))

const icons = {
  leaf: { d1: 'M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z', d2: 'M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12' },
  users: { d1: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2', d2: 'M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', d3: 'M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75' },
  brain: { d1: 'M12 4a4 4 0 0 1 3.5 2.1A4 4 0 0 1 19 6a4 4 0 0 1 0 8 4 4 0 0 1-3.5 2.1A4 4 0 0 1 12 18a4 4 0 0 1-3.5-1.9A4 4 0 0 1 5 14a4 4 0 0 1 0-8 4 4 0 0 1 3.5-1.9A4 4 0 0 1 12 4z', d2: 'M12 4v14 M9 8h6 M9 12h6 M9 16h4' },
}
const getIcon = (n) => icons[n] || icons.leaf
</script>

<template>
  <div class="stats-grid">
    <div v-for="(item, i) in data" :key="item.label" class="stat-card glass-panel" :style="{ '--c': item.color, '--i': i }">
      <div class="card-glow"></div>
      <div class="icon-wrap" :style="{ color: item.color }">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path :d="getIcon(item.icon).d1" />
          <path v-if="getIcon(item.icon).d2" :d="getIcon(item.icon).d2" />
          <path v-if="getIcon(item.icon).d3" :d="getIcon(item.icon).d3" />
        </svg>
      </div>
      <div class="stat-num" :style="{ color: item.color }">
        <span>{{ vals[i] || '0' }}</span><span class="plus">+</span>
      </div>
      <div class="stat-lbl">{{ item.label }}</div>
      <div class="bar-bg"><div class="bar-fill" :style="{ width: vals[i] ? '100%' : '0%' }"></div></div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
  padding: 10px;
}

.stat-card {
  position: relative;
  flex: 1;
  min-width: 200px;
  max-width: 280px;
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.04);
  background: rgba(255,255,255,0.02);
  backdrop-filter: blur(16px);
  overflow: hidden;
  animation: appear 0.6s ease-out both;
  animation-delay: calc(0.1s * var(--i, i));
  transition: transform 200ms ease-out, box-shadow 200ms ease-out;
}

@media (hover: hover) and (pointer: fine) {
  .stat-card:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: 0 20px 50px rgba(0,0,0,0.4), 0 0 30px color-mix(in srgb, var(--c) 10%, transparent);
  }
}

.card-glow {
  position: absolute;
  top: -60%; left: -60%;
  width: 220%; height: 220%;
  background: radial-gradient(ellipse at center, var(--c) 0%, transparent 60%);
  opacity: 0.03;
  pointer-events: none;
  animation: spin 15s linear infinite;
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.icon-wrap {
  width: 52px; height: 52px;
  padding: 12px;
  margin-bottom: 16px;
  border-radius: 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  transition: transform 200ms ease-out;
}
@media (hover: hover) and (pointer: fine) {
  .stat-card:hover .icon-wrap { transform: scale(1.08); }
}

.icon-wrap svg { width: 100%; height: 100%; filter: drop-shadow(0 0 6px var(--c)); }

.stat-num {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-bottom: 6px;
  font-family: 'Syne', sans-serif;
  font-size: 2.4rem;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.5px;
  text-shadow: 0 0 20px color-mix(in srgb, var(--c) 30%, transparent);
}
.plus { font-size: 1.4rem; font-weight: 900; opacity: 0.6; }

.stat-lbl {
  font-size: 0.8rem;
  color: rgba(255,255,255,0.5);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 16px;
}

.bar-bg {
  width: 80%; height: 3px;
  border-radius: 4px;
  background: rgba(255,255,255,0.04);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--c);
  box-shadow: 0 0 8px var(--c);
  transition: width 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes appear {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .stat-card { min-width: 140px; padding: 22px 16px; }
  .stat-num { font-size: 1.8rem; }
  .icon-wrap { width: 44px; height: 44px; padding: 10px; }
}
</style>
