<template>
  <div class="admin-dashboard">
    <div class="container">
      <header class="admin-header">
        <h1>Admin Dashboard - PlantGuard AI</h1>
        <p>Contrôle total de la plateforme agricole</p>
      </header>

      <div class="stats-grid">
        <div class="stat-card glass-panel">
          <div class="stat-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <h2>{{ stats.total_users }}</h2>
          <p>Agriculteurs</p>
        </div>
        <div class="stat-card glass-panel">
          <div class="stat-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a3 3 0 0 0-3 3v2h6V5a3 3 0 0 0-3-3Z"/><path d="M5 11a7 7 0 0 1 14 0v2a7 7 0 0 1-14 0Z"/><path d="M3 16h18M12 22v-3"/></svg>
          </div>
          <h2>{{ stats.total_products }}</h2>
          <p>Produits</p>
        </div>
        <div class="stat-card glass-panel">
          <div class="stat-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
          </div>
          <h2>{{ stats.total_orders }}</h2>
          <p>Commandes</p>
        </div>
        <div class="stat-card glass-panel">
          <div class="stat-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          </div>
          <h2>{{ Math.round(stats.avg_rating * 10) / 10 }}</h2>
          <p>Note moyenne</p>
        </div>
      </div>

      <div class="admin-actions">
        <button class="btn btn-primary">Gérer Utilisateurs</button>
        <button class="btn btn-primary">Modérer Produits</button>
        <button class="btn btn-primary">Vérifier Commandes</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'
import gsap from 'gsap'

const stats = ref({
  total_users: 0,
  total_products: 0,
  total_orders: 0,
  avg_rating: 0
})

const fetchStats = async () => {
  try {
    const response = await api.get('admin-stats/')
    stats.value = response.data
  } catch (err) {
    console.error('Admin stats error', err)
  }
}

onMounted(() => {
  fetchStats()
  gsap.from(".stat-card", {
    y: 50, opacity: 0, duration: 0.8, stagger: 0.2, ease: "back.out(1.7)"
  })
})
</script>

<style scoped>
.admin-dashboard { padding-top: 120px; min-height: 100vh; }
.admin-header { text-align: center; margin-bottom: 60px; }
.admin-header h1 { font-size: 3rem; margin-bottom: 16px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  margin-bottom: 60px;
}

.stat-card {
  text-align: center; padding: 40px 20px;
  transition: transform 200ms ease-out, box-shadow 200ms ease-out;
}

@media (hover: hover) and (pointer: fine) {
  .stat-card:hover {
    transform: translateY(-10px) scale(1.05);
    box-shadow: 0 20px 40px rgba(0,230,118,0.3);
  }
}
.stat-card:active { transform: scale(0.97); }

.stat-icon {
  margin-bottom: 20px;
  color: var(--primary);
  filter: drop-shadow(0 0 10px rgba(0,230,118,0.3));
  display: flex;
  justify-content: center;
}
.stat-card h2 { font-size: 3rem; margin-bottom: 8px; color: var(--primary); }
.stat-card p { color: var(--text-muted); font-size: 1.1rem; }

.admin-actions { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
</style>
