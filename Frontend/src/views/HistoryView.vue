<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../supabase'
import { useAuthStore } from '../authStore'
import gsap from 'gsap'

const authStore = useAuthStore()
const historyList = ref([])
const loading = ref(true)
const error = ref(null)

const fetchHistory = async () => {
  const user = authStore.user
  if (!user) {
    loading.value = false
    return
  }
  try {
    // Récupération de l'historique des scans depuis Supabase
    const { data, error: err } = await supabase
      .from('scan_history')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (err) throw err
    historyList.value = (data || []).map(item => ({
      id: item.id,
      ...item,
      image: item.image_url,
      formattedDate: item.created_at ? new Date(item.created_at).toLocaleDateString('fr-FR', {
        day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
      }) : 'Date inconnue'
    }))
  } catch (err) {
    console.error("Erreur chargement historique:", err)
    error.value = "Impossible de charger votre historique."
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (authStore.user) {
    fetchHistory()
  } else {
    loading.value = false
  }
  gsap.from(".history-title", { y: -30, opacity: 0, duration: 1, ease: "power3.out" })
  gsap.from(".prod-card", {
    y: 50, opacity: 0, duration: 0.8, stagger: 0.1, delay: 0.3, ease: "back.out(1.4)"
  })
})
</script>

<template>
  <div class="history-page">
    <div class="container history-content">
      <header class="history-header">
        <div class="history-title">
          <h1 class="text-glow">Historique des Analyses</h1>
          <p>Retrouvez toutes les maladies diagnostiquées par votre IA sur vos plantations.</p>
        </div>
      </header>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Récupération des archives médicales...</p>
      </div>

      <div v-else-if="error" class="error-container container">
         <div class="alert-glow error">
            <span class="alert-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </span>
            {{ error }}
            <button @click="fetchHistory" class="btn btn-secondary btn-sm">Réessayer</button>
         </div>
      </div>

      <div v-else-if="!auth.currentUser" class="history-empty">
        <div class="empty-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        </div>
        <h3>Connexion Requise</h3>
        <p>Veuillez vous connecter pour accéder à votre historique de diagnostics.</p>
      </div>

      <div v-else-if="historyList.length === 0" class="history-empty">
        <div class="empty-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
        </div>
        <h3>Aucune donnée</h3>
        <p>Vous n'avez pas encore scanné de plante avec PlantGuard AI.</p>
      </div>

      <div v-else class="products-grid">
        <div v-for="item in historyList" :key="item.id" class="prod-card glass-panel">
          <div class="prod-visual">
            <!-- Réaffichage de la photo miniature sauvegardée dans Firestore -->
            <!-- Correction: Ne pas doubler le préfixe data:image if it's already in the string -->
            <div v-if="item.image" class="prod-img" :style="{ backgroundImage: `url(${item.image})` }"></div>
            <div v-else class="prod-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="1.5"><path d="M12 2a3 3 0 0 0-3 3v2h6V5a3 3 0 0 0-3-3Z"/><path d="M5 11a7 7 0 0 1 14 0v2a7 7 0 0 1-14 0Z"/><path d="M3 16h18M12 22v-3"/></svg>
            </div>
            <div class="prod-type-badge">{{ item.formattedDate }}</div>
          </div>
          
          <div class="prod-details">
            <div class="plant-name-badge">{{ item.plante || 'Plante' }}</div>
            <h3 :class="{'text-danger': item.maladie !== 'Saine'}">{{ item.maladie }}</h3>
            <div class="prod-seller">
              <strong>Agent causal :</strong> {{ item.cause }}
            </div>
            <div v-if="item.utilite || item.proprietes_medicinales" class="prod-extras glass-panel">
              <div v-if="item.utilite" class="extra-item">
                <span class="extra-label">Usage:</span> {{ item.utilite }}
              </div>
              <div v-if="item.proprietes_medicinales" class="extra-item">
                <span class="extra-label">Santé:</span> {{ item.proprietes_medicinales }}
              </div>
            </div>
            <div class="prod-seller mt-2">
              <strong>Protocole :</strong> <span class="text-primary">{{ item.traitement }}</span>
            </div>
            
            <div class="prod-footer">
              <div class="prod-price">
                <span class="cur">Remède suggéré :</span>
                <span class="val text-accent">{{ item.produit_recommande }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-page {
  padding-top: 120px;
  min-height: 100vh;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 60px;
}

.history-title h1 { margin-bottom: 8px; }

/* Classes spécifiques à l'historique */
.text-danger { color: var(--danger) !important; }
.text-primary { color: var(--primary) !important; }
.text-accent { color: var(--accent) !important; font-size: 1.1rem !important; font-weight: bold; }

.loading-state { text-align: center; padding: 100px; }
.spinner { width: 50px; height: 50px; border: 4px solid var(--border); border-top-color: var(--primary); border-radius: 50%; margin: 0 auto 20px; animation: spin 1s linear infinite; }
.history-empty { text-align: center; padding: 80px; color: var(--text-muted); }
.empty-icon { margin-bottom: 20px; opacity: 0.7; display: flex; justify-content: center; }

.search-icon, .loc-icon { font-size: 1.2rem; opacity: 0.6; }

.filter-bar input, .filter-bar select {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 1.1rem;
  width: 100%;
  padding: 12px 0;
  outline: none;
}

/* Products Grid */
.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 30px;
  margin-bottom: 80px;
}

.prod-card {
  overflow: hidden;
  transition: transform 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
  cursor: default;
}

.prod-card:hover { transform: translateY(-10px); }

.prod-visual {
  height: 220px;
  position: relative;
  background: rgba(0,0,0,0.3);
}

.prod-img { width: 100%; height: 100%; background-size: cover; background-position: center; }
.prod-placeholder { height: 100%; display: flex; align-items: center; justify-content: center; font-size: 5rem; }

.prod-type-badge {
  position: absolute; bottom: 15px; left: 15px;
  background: rgba(0,0,0,0.6); backdrop-filter: blur(5px);
  padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700;
  color: var(--primary); border: 1px solid var(--primary-glow);
}

.prod-details { padding: 24px; }
.plant-name-badge { font-size: 0.7rem; text-transform: uppercase; color: var(--primary); font-weight: bold; margin-bottom: 8px; border: 1px solid rgba(0, 230, 118, 0.2); width: fit-content; padding: 2px 8px; border-radius: 4px; background: rgba(0, 230, 118, 0.05); }
.prod-details h3 { font-size: 1.2rem; margin-bottom: 12px; color: var(--text-primary); line-height: 1.4; }
.prod-seller { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5; }
.prod-seller strong { color: var(--text-primary); }
.mt-2 { margin-top: 10px; }
.prod-extras { background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; margin: 12px 0; font-size: 0.8rem; }
.extra-item { margin-bottom: 5px; color: var(--text-muted); line-height: 1.3; }
.extra-label { color: var(--primary); font-weight: bold; }

.prod-footer { margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); }
.prod-price { display: flex; flex-direction: column; gap: 6px; }
.prod-price .cur { font-size: 0.8rem; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }

@media (max-width: 768px) {
  .history-header { flex-direction: column; gap: 20px; text-align: center; }
}
</style>
