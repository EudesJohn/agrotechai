<script setup>
import { ref, onMounted, reactive, provide, watch } from 'vue'
import { RouterLink, RouterView, useRouter, useRoute } from 'vue-router'
import { supabase } from './supabase'
import { useAuthStore } from './authStore'
import { communesBenin, sectors } from './constants'
import gsap from 'gsap'

const authStore = useAuthStore()

const router = useRouter()
const route = useRoute()

// Auth State & Form
const showAuth = ref(false)
const authMode = ref('login') // 'login', 'register', 'forgot'
const loading = ref(false)

const authForm = reactive({
  email: '',
  password: '',
  fullName: '',
  phone: '',
  commune: 'Cotonou',
  sector: 'FARMER'
})

const openAuth = (mode) => {
  authMode.value = mode
  showAuth.value = true
}

provide('openAuth', openAuth)

const syncWithBackend = async (user, profileData = {}) => {
  // Supprimé au profit de Firestore Direct
  return { is_complete: !!(profileData.phone && profileData.commune) }
}

const handleGoogleLogin = async () => {
  try {
    loading.value = true
    // Supabase OAuth redirige vers Google puis revient à l'app
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    })
    // Le navigateur va quitter la page → le retour se fait via onAuthStateChange
  } catch (err) {
    alert('Erreur Google: ' + err.message)
    loading.value = false
  }
}

const handleAuth = async () => {
  loading.value = true
  try {
    if (authMode.value === 'register') {
      await authStore.register(authForm.email, authForm.password, authForm)
      alert("Compte créé avec succès !")
    } else {
      await authStore.login(authForm.email, authForm.password)
    }
    showAuth.value = false
    Object.assign(authForm, { email: '', password: '', fullName: '', phone: '' })
  } catch (err) {
    alert("Erreur d'authentification: " + err.message)
  } finally {
    loading.value = false
  }
}

const resetSent = ref(false)
const resetEmail = ref('')
const handleReset = async () => {
  if (!resetEmail.value) {
    alert("Veuillez saisir votre email.")
    return
  }
  loading.value = true
  try {
    await supabase.auth.resetPasswordForEmail(resetEmail.value, {
      redirectTo: window.location.origin + '/profile',
    })
    resetSent.value = true
    setTimeout(() => {
      resetSent.value = false
      authMode.value = 'login'
      showAuth.value = false
      resetEmail.value = ''
    }, 5000)
  } catch (err) {
    alert("Erreur d'envoi: " + err.message)
  } finally {
    loading.value = false
  }
}

const isMobileMenuOpen = ref(false)

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
  if (isMobileMenuOpen.value) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = 'auto'
  }
}

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false
  document.body.style.overflow = 'auto'
}

// Close menu on route change
watch(() => route.path, () => {
  closeMobileMenu()
})

onMounted(() => {
  gsap.from(".navbar", { y: -20, opacity: 0, duration: 1, ease: "power3.out" })

  // L'initialisation de l'auth est gérée par authStore.initAuth()
  // Appelé depuis App.vue au montage pour garantir que le state est prêt
  supabase.auth.getSession().then(({ data: { session } }) => {
    // authStore.initAuth() a déjà été appelé dans main.js ou est en cours
  })
})
</script>

<template>
  <div class="app-shell">
    <!-- Fond 3D fixe du site (Bouquet / Blossom) -->
    <div class="site-bg" aria-hidden="true">
      <div class="site-bg-glow"></div>
      <div class="site-bg-image"></div>
    </div>

    <header class="navbar">
      <div class="container nav-inner">
        <div class="logo-area">
          <RouterLink to="/" class="logo">
            <span class="logo-symbol">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.7 19.3 19.3 4.7M9.2 14.8l4.8-4.8M3 21l2-2m14-14 2-2M14 6l-6 6M21 3l-2 2M3 21l2-2"/></svg>
            </span>
            <span class="logo-text">Agrotech <span class="ai-suffix">AI</span></span>
          </RouterLink>
        </div>
        
        <nav class="nav-links desktop-only">
          <RouterLink to="/" class="nav-item">Accueil</RouterLink>
          <RouterLink v-if="authStore.user" to="/community" class="nav-item">Communauté</RouterLink>
          <RouterLink v-if="authStore.user" to="/diagnostic" class="nav-item">Diagnostic</RouterLink>
          <RouterLink v-if="authStore.user" to="/history" class="nav-item">Historique</RouterLink>
          <RouterLink v-if="authStore.user" to="/messages" class="nav-item">Messages</RouterLink>
          <RouterLink v-if="authStore.user" to="/profile" class="nav-item">Mon Profil</RouterLink>
        </nav>
        
        <div class="nav-actions">
          <template v-if="!authStore.user">
            <div class="desktop-only">
              <button class="btn-ghost" @click="openAuth('login')">Connexion</button>
              <button class="btn btn-primary btn-nav" @click="openAuth('register')">S'inscrire</button>
            </div>
          </template>
          <template v-else>
            <div class="user-profile-nav desktop-only" @click="router.push('/profile')" style="cursor: pointer">
              <span class="user-email">{{ authStore.user.email }}</span>
              <button class="btn-ghost" @click.stop="authStore.logout()">Déconnexion</button>
            </div>
          </template>
          
          <!-- Hamburger Button -->
          <button class="mobile-menu-btn" @click="toggleMobileMenu" :class="{ 'active': isMobileMenuOpen }">
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
      </div>
    </header>

    <!-- Mobile Menu Overlay -->
    <Transition name="fade">
      <div v-if="isMobileMenuOpen" class="mobile-menu-overlay" @click="closeMobileMenu"></div>
    </Transition>
    <Transition name="slide-right">
      <aside v-if="isMobileMenuOpen" class="mobile-menu-panel glass-panel">
        <div class="mobile-menu-header">
           <RouterLink to="/" class="logo" @click="closeMobileMenu">
             <span class="logo-symbol">
               <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.7 19.3 19.3 4.7M9.2 14.8l4.8-4.8M3 21l2-2m14-14 2-2M14 6l-6 6M21 3l-2 2M3 21l2-2"/></svg>
             </span>
             <span class="logo-text">Agrotech<span class="ai-suffix">AI</span></span>
           </RouterLink>
           <button class="close-btn" @click="closeMobileMenu">✕</button>
        </div>
        <nav class="mobile-nav-links">
          <RouterLink to="/" class="m-nav-item" @click="closeMobileMenu">Accueil</RouterLink>
          <template v-if="authStore.user">
            <RouterLink to="/community" class="m-nav-item" @click="closeMobileMenu">Communauté</RouterLink>
            <RouterLink to="/diagnostic" class="m-nav-item" @click="closeMobileMenu">Diagnostic</RouterLink>
            <RouterLink to="/history" class="m-nav-item" @click="closeMobileMenu">Historique</RouterLink>
            <RouterLink to="/messages" class="m-nav-item" @click="closeMobileMenu">Messages</RouterLink>
            <RouterLink to="/profile" class="m-nav-item" @click="closeMobileMenu">Mon Profil</RouterLink>
            <div class="m-divider"></div>
            <div class="m-profile-info">
              <span class="m-user-email">{{ authStore.user.email }}</span>
              <button class="btn btn-secondary m-btn" @click="authStore.logout(); closeMobileMenu()">Déconnexion</button>
            </div>
          </template>
          <template v-else>
            <button class="btn btn-primary m-btn" @click="openAuth('login'); closeMobileMenu()">Connexion</button>
            <button class="btn btn-secondary m-btn" @click="openAuth('register'); closeMobileMenu()">S'inscrire</button>
          </template>
        </nav>
      </aside>
    </Transition>

    <main class="main-content">
      <RouterView />
    </main>

    <!-- Auth Modal Ecosystem -->
    <Transition name="fade">
      <div v-if="showAuth" class="auth-overlay" @click.self="showAuth = false">
        <div class="auth-card glass-panel" :class="{ 'auth-card-wide': authMode === 'register' }">
          <button class="close-auth" @click="showAuth = false">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
          
          <!-- Views Logic -->
          <div v-if="authMode !== 'forgot'">
            <div class="auth-intro">
              <h2 class="auth-title">{{ authMode === 'login' ? 'Bienvenue' : 'Créer un compte' }}</h2>
              <p>{{ authMode === 'login' ? 'Accédez à vos données biologiques.' : 'Rejoignez le réseau agro-élite.' }}</p>
            </div>

            <button class="google-btn" @click="handleGoogleLogin">
              <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="" />
              Continuer avec Google
            </button>

            <div class="auth-sep"><span>ou continuer via email</span></div>

            <div class="auth-form">
              <div v-if="authMode === 'register'" class="grid-2">
                <div class="field">
                  <label>Nom Complet</label>
                  <input type="text" v-model="authForm.fullName" placeholder="Janvier Dossou" />
                </div>
                <div class="field">
                  <label>Téléphone</label>
                  <input type="tel" v-model="authForm.phone" placeholder="+229..." />
                </div>
                <div class="field">
                  <label>Commune</label>
                  <select v-model="authForm.commune">
                    <option value="" disabled>Sélectionnez votre commune</option>
                    <option v-for="c in communesBenin" :key="c" :value="c">{{ c }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Secteur</label>
                  <select v-model="authForm.sector">
                    <option value="" disabled>Sélectionnez votre secteur</option>
                    <option v-for="s in sectors" :key="s.value" :value="s.value">{{ s.label }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Email</label>
                  <input type="email" v-model="authForm.email" placeholder="nom@provider.bj" />
                </div>
                <div class="field">
                  <label>Mot de passe</label>
                  <input type="password" v-model="authForm.password" />
                </div>
              </div>

              <div v-else class="simple-form">
                <div class="field">
                  <label>Email</label>
                  <input type="email" v-model="authForm.email" placeholder="expert@agrotech.bj" />
                </div>
                <div class="field">
                  <div class="field-head">
                    <label>Mot de passe</label>
                  </div>
                  <input type="password" v-model="authForm.password" />
                  <div class="forgot-wrapper-link">
                    <span class="forgot-link" @click="authMode = 'forgot'">Mot de passe oublié ?</span>
                  </div>
                </div>
              </div>

              <button class="btn btn-primary w-full mt-32" @click="handleAuth" :disabled="loading">
                {{ loading ? 'Chargement...' : (authMode === 'login' ? 'Se connecter' : 'Valider mon inscription') }}
              </button>
            </div>

            <div class="auth-footer">
              {{ authMode === 'login' ? "Pas encore membre ?" : "Déjà inscrit ?" }}
              <span @click="authMode = authMode === 'login' ? 'register' : 'login'">
                {{ authMode === 'login' ? "S'inscrire" : "Se connecter" }}
              </span>
            </div>
          </div>

          <div v-else class="recovery-view">
             <div v-if="!resetSent">
                <h2 class="recovery-title">Récupération</h2>
                <p>Recevez un lien de sécurité temporaire.</p>
                <div class="field mt-24">
                  <label>Email de secours</label>
                  <input type="email" v-model="resetEmail" placeholder="votre@email.com" />
                </div>
                <button class="btn btn-primary w-full mt-24" @click="handleReset" :disabled="loading">
                  {{ loading ? 'Envoi...' : 'Envoyer le lien de récupération' }}
                </button>
                <button class="btn-back" @click="authMode = 'login'">Annuler</button>
             </div>
             <div v-else class="sent-success">
                <div class="success-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
                <h2>Email Expédié</h2>
                <p>Vérifiez votre boîte de réception.</p>
             </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding-top: 90px; /* Offset for the fixed navbar */
}

.navbar {
  position: fixed;
  top: 0; left: 0; width: 100%;
  height: 90px;
  background: rgba(2, 8, 4, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  z-index: 1000;
}

.nav-inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-symbol { font-size: 1.8rem; }
.logo-text {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 1.4rem;
  color: #fff;
  letter-spacing: -0.5px;
}

.ai-suffix {
  background: linear-gradient(135deg, var(--primary), var(--accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  padding-left: 2px;
}

.nav-links {
  display: flex;
  gap: 24px;
}

.nav-item {
  text-decoration: none;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 1.05rem;
  transition: color 200ms ease-out;
  position: relative;
}

@media (hover: hover) and (pointer: fine) { .nav-item:hover { color: #fff; } }
.nav-item.router-link-active { color: #fff; }
.nav-item.router-link-active::after {
  content: '';
  position: absolute;
  bottom: -4px; left: 0; width: 100%; height: 2px;
  background: var(--primary);
  box-shadow: 0 0 10px var(--primary);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-actions .desktop-only {
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn-ghost {
  background: transparent;
  border: none;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  font-size: 1rem;
}

.btn-nav {
  height: 44px;
  padding: 0 24px;
  font-size: 0.95rem;
  box-shadow: 0 4px 15px var(--primary-glow);
}

.user-profile-nav {
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(255,255,255,0.05);
  padding: 8px 16px;
  border-radius: 100px;
  border: 1px solid var(--border);
}

.user-email {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary);
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Auth Modal */
.auth-overlay {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.85);
  backdrop-filter: blur(15px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.auth-card {
  width: 100%;
  max-width: 480px;
  padding: 48px;
  position: relative;
}

.auth-card-wide { max-width: 720px; }

.close-auth {
  position: absolute; top: 24px; right: 24px;
  background: transparent; border: none; color: #fff;
  font-size: 1.2rem; cursor: pointer; opacity: 0.5;
  transition: opacity 200ms ease-out;
}
.close-auth:active { transform: scale(0.9); }

.auth-intro { text-align: center; margin-bottom: 32px; }
.auth-title { font-size: clamp(1.5rem, 4vw, 2rem) !important; margin-bottom: 8px; }

.recovery-title { 
  font-size: clamp(1.4rem, 4vw, 1.8rem) !important; 
  margin-bottom: 8px; 
  white-space: nowrap;
}

.forgot-wrapper-link {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.forgot-link {
  font-size: 0.85rem;
  color: var(--primary);
  font-weight: 700;
  cursor: pointer;
  opacity: 0.8;
  transition: opacity 200ms ease-out;
}

.forgot-link:hover { opacity: 1; text-decoration: underline; }

.google-btn {
  width: 100%; height: 50px; border-radius: 12px;
  border: 1px solid var(--border); background: #fff; color: #000;
  font-weight: 700; display: flex; align-items: center; justify-content: center;
  gap: 12px; cursor: pointer; transition: transform 200ms ease-out, background 200ms ease-out;
}

.google-btn img { width: 22px; }
@media (hover: hover) and (pointer: fine) {
  .google-btn:hover { background: #f5f5f5; transform: translateY(-2px); }
}
.google-btn:active { transform: scale(0.97); }

.auth-sep {
  text-align: center; margin: 24px 0; position: relative;
}
.auth-sep::before { content: ''; position: absolute; top: 50%; left: 0; width: 100%; height: 1px; background: var(--border); }
.auth-sep span { background: var(--bg-dark); padding: 0 15px; position: relative; color: var(--text-muted); font-size: 0.85rem; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.field { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
.field label { font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

.field-head { display: flex; justify-content: space-between; }
.field-head span { font-size: 0.8rem; color: var(--primary); cursor: pointer; font-weight: 700; }

input, select {
  width: 100%; padding: 14px; border-radius: 10px;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  color: #fff; font-size: 1rem; outline: none; transition: border-color 200ms ease-out, background 200ms ease-out, box-shadow 200ms ease-out;
}

input:focus { border-color: var(--primary); background: rgba(255,255,255,0.06); }

/* Fix pour la visibilité des options dans les menus déroulants */
option {
  background-color: var(--bg-dark);
  color: #fff;
  padding: 10px;
}

.auth-footer { text-align: center; margin-top: 32px; color: var(--text-muted); font-size: 0.95rem; }
.auth-footer span { color: var(--primary); font-weight: 800; cursor: pointer; margin-left: 6px; }

.w-full { width: 100%; }
.mt-32 { margin-top: 32px; }
.mt-24 { margin-top: 24px; }

.btn-back { background: transparent; border: none; color: var(--text-muted); width: 100%; margin-top: 15px; cursor: pointer; }

/* Responsive Auth Modal */
@media (max-width: 768px) {
  .auth-card { padding: 32px 24px; }
  .auth-card-wide { max-width: 100%; }
  .grid-2 { grid-template-columns: 1fr; gap: 0; }
  .auth-intro { margin-bottom: 24px; }
  .auth-sep { margin: 18px 0; }
  .mt-32 { margin-top: 24px; }
  .auth-footer { margin-top: 24px; }
}

@media (max-width: 480px) {
  .auth-card { padding: 24px 16px; }
  .auth-overlay { padding: 10px; align-items: flex-start; padding-top: 60px; }
  .google-btn { height: 44px; font-size: 0.9rem; }
}

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.mobile-menu-btn {
  display: none;
  flex-direction: column;
  gap: 6px;
  background: transparent;
  border: none;
  cursor: pointer;
  z-index: 2000;
  padding: 10px;
}

.mobile-menu-btn span {
  display: block;
  width: 25px;
  height: 2px;
  background: #fff;
  transition: transform 200ms ease-out, opacity 200ms ease-out;
}

.mobile-menu-btn.active span:nth-child(1) { transform: translateY(8px) rotate(45deg); }
.mobile-menu-btn.active span:nth-child(2) { opacity: 0; }
.mobile-menu-btn.active span:nth-child(3) { transform: translateY(-8px) rotate(-45deg); }

.mobile-menu-overlay {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(8px);
  z-index: 1500;
}

.mobile-menu-panel {
  position: fixed;
  top: 0; right: 0; width: 85%; max-width: 400px; height: 100%;
  z-index: 1600;
  display: flex;
  flex-direction: column;
  padding: 40px;
  border-radius: 0;
  border-left: 1px solid var(--border);
}

.mobile-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 50px;
}

.close-btn {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 2rem;
  cursor: pointer;
  transition: transform 120ms ease-out, color 200ms ease-out;
}

.close-btn:active {
  transform: scale(0.9);
}

.mobile-nav-links {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.m-nav-item {
  text-decoration: none;
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-muted);
  transition: color 200ms ease-out, transform 200ms ease-out;
}

.m-nav-item:hover, .m-nav-item.router-link-active {
  color: var(--primary);
}
@media (hover: hover) and (pointer: fine) {
  .m-nav-item:hover {
    transform: translateX(10px);
  }
}

.m-divider {
  height: 1px;
  background: var(--border);
  margin: 10px 0;
}

.m-profile-info {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.m-user-email {
  font-size: 0.9rem;
  color: var(--primary);
  word-break: break-all;
  font-weight: 600;
}

.m-btn { width: 100%; }

@media (max-width: 992px) {
  .desktop-only { display: none !important; }
  .mobile-menu-btn { display: flex; }
  .nav-links { display: none; }
}

@media (max-width: 768px) {
  .navbar { height: 75px; }
  .nav-inner { padding: 0 15px; }
  .logo-text { font-size: 1.1rem; }
  .logo-symbol { font-size: 1.5rem; }
  .logo-symbol svg { width: 22px; height: 22px; }
  .nav-actions { gap: 8px; }
  .main-content { padding-top: 75px; }
  .mobile-menu-panel { padding: 28px 20px; }
}

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-right-enter-active { transition: transform 350ms cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.slide-right-leave-active { transition: transform 200ms ease-out; }
.slide-right-enter-from, .slide-right-leave-to { transform: translateX(100%); }

/* ─── Site Background 3D ─── */
.site-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  pointer-events: none;
  overflow: hidden;
}

.site-bg-glow {
  position: absolute;
  top: 60%;
  right: 10%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(0, 230, 118, 0.06) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(60px);
  animation: bg-glow-drift 14s ease-in-out infinite;
}

.site-bg-image {
  position: absolute;
  top: 50%;
  right: 5%;
  width: 500px;
  height: 500px;
  background-image: url('https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Bouquet/3D/bouquet_3d.png');
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  opacity: 0.07;
  transform: translateY(-50%);
  animation: bg-float 20s ease-in-out infinite;
  filter: blur(0.5px);
}

@keyframes bg-float {
  0%, 100% {
    transform: translateY(-50%) translateX(0) scale(1);
    opacity: 0.07;
  }
  25% {
    transform: translateY(-55%) translateX(15px) scale(1.05);
    opacity: 0.09;
  }
  50% {
    transform: translateY(-48%) translateX(-10px) scale(0.97);
    opacity: 0.06;
  }
  75% {
    transform: translateY(-52%) translateX(20px) scale(1.03);
    opacity: 0.08;
  }
}

@keyframes bg-glow-drift {
  0%, 100% { transform: translate(0, 0); opacity: 0.6; }
  33% { transform: translate(30px, -20px); opacity: 1; }
  66% { transform: translate(-20px, 15px); opacity: 0.4; }
}

@media (max-width: 768px) {
  .site-bg-image { width: 300px; height: 300px; opacity: 0.04; }
  .site-bg-glow { width: 350px; height: 350px; }
}
</style>
