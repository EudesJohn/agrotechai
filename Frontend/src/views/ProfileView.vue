<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '../authStore'
import { useRouter } from 'vue-router'
import { sectors, communesBenin } from '../constants'
import { storage, db } from '../firebase'
import { ref as storageRef, uploadBytes, getDownloadURL } from 'firebase/storage'
import { doc, updateDoc, collection, query, where, getDocs, limit, getDoc } from 'firebase/firestore'
import gsap from 'gsap'

const authStore = useAuthStore()
const router = useRouter()

const profile = ref({
  user: { first_name: '', last_name: '', email: '' },
  phone_number: '',
  location: '',
  user_type: 'FARMER',
  bio: '',
  experience: ''
})

const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)
const fileInput = ref(null)
const message = ref({ text: '', type: '' })

// Social Lists State
const showSocialModal = ref(false)
const socialModalTitle = ref('')
const socialList = ref([])
const socialListLoading = ref(false)

const openSocialModal = async (type) => {
  socialModalTitle.value = type === 'followers' ? 'Abonnés' : 'Abonnements'
  showSocialModal.value = true
  socialList.value = []
  socialListLoading.value = true
  
  try {
    const userId = authStore.user.uid
    const field = type === 'followers' ? 'followedId' : 'followerId'
    const q = query(collection(db, 'follows'), where(field, '==', userId), limit(50))
    const snap = await getDocs(q)
    
    const userIds = snap.docs.map(d => type === 'followers' ? d.data().followerId : d.data().followedId)
    
    if (userIds.length > 0) {
      const limitedIds = userIds.slice(0, 20)
      const profiles = await Promise.all(limitedIds.map(async id => {
        const uSnap = await getDoc(doc(db, 'users', id))
        return uSnap.exists() ? { uid: id, ...uSnap.data() } : null
      }))
      socialList.value = profiles.filter(p => p !== null)
    }
  } catch (err) {
    console.error("Social list error", err)
  } finally {
    socialListLoading.value = false
  }
}

const loadFromAuthStore = () => {
  if (authStore.profile) {
    // Adapter les données de base pour le formulaire
    const p = authStore.profile
    profile.value = {
      ...p,
      user: { 
        first_name: p.firstName || p.displayName?.split(' ')[0] || '', 
        last_name: p.lastName || p.displayName?.split(' ')[1] || '',
        email: p.email || authStore.user?.email || ''
      }
    }
    loading.value = false
  } else if (!authStore.loading) {
    // Si l'authentification est finie mais pas de profil, on arrête le chargement
    loading.value = false
  }
}

watch(() => authStore.profile, loadFromAuthStore, { immediate: true })

const saveProfile = async () => {
  saving.value = true
  message.value = { text: '', type: '' }
  try {
    const updateData = {
      ...profile.value,
      displayName: `${profile.value.user.first_name} ${profile.value.user.last_name}`.trim(),
      firstName: profile.value.user.first_name,
      lastName: profile.value.user.last_name
    }
    // Supprimer le champ 'user' imbriqué pour Firestore si on veut rester à plat
    delete updateData.user
    
    await authStore.updateProfile(updateData)
    message.value = { text: 'Paramètres neuronaux mis à jour avec succès.', type: 'success' }
    setTimeout(() => message.value.text = '', 4000)
  } catch (err) {
    console.error(err)
    message.value = { text: 'Échec de la synchronisation.', type: 'error' }
  } finally {
    saving.value = false
  }
}

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  uploading.value = true
  message.value = { text: 'Optimisation et envoi de la photo...', type: 'success' }

  try {
    // Compression avant envoi (cible 400px)
    const compressedBlob = await new Promise((resolve) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = (e) => {
        const img = new Image()
        img.onload = () => {
          const canvas = document.createElement('canvas')
          const scale = 400 / img.width
          canvas.width = 400
          canvas.height = img.height * scale
          const ctx = canvas.getContext('2d')
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
          canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.7)
        }
        img.src = e.target.result
      }
    })

    const sRef = storageRef(storage, `profiles/${authStore.user.uid}`)
    await uploadBytes(sRef, compressedBlob)
    const url = await getDownloadURL(sRef)
    
    // Update Firestore
    await updateDoc(doc(db, 'users', authStore.user.uid), { photoURL: url })
    
    // Update local state
    if (authStore.profile) {
      authStore.profile.photoURL = url
    }
    
    message.value = { text: 'Photo de profil mise à jour.', type: 'success' }
  } catch (err) {
    console.error("Upload error:", err)
    if (err.code === 'storage/unauthorized') {
      message.value = { 
        text: 'Permission refusée. Vérifiez les règles Firebase Storage (autoriser lecture/écriture pour les utilisateurs authentifiés).', 
        type: 'error' 
      }
    } else if (err.code === 'storage/object-not-found') {
      message.value = { text: 'Fichier introuvable.', type: 'error' }
    } else {
      message.value = { text: `Erreur photo: ${err.message || 'Inconnue'}`, type: 'error' }
    }
  } finally {
    uploading.value = false
    setTimeout(() => message.value.text = '', 6000)
  }
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/')
}

onMounted(() => {
  if (!authStore.user && !authStore.loading) {
    router.push('/')
  }
  setTimeout(() => {
    gsap.from(".profile-hero", { x: -50, opacity: 0, duration: 1, ease: "power4.out" })
    gsap.from(".profile-main", { x: 50, opacity: 0, duration: 1, delay: 0.2, ease: "power4.out" })
    gsap.from(".form-section", { 
      y: 30, opacity: 0, duration: 0.8, stagger: 0.2, delay: 0.5, ease: "power2.out" 
    })
  }, 300)
})
</script>

<template>
  <div class="profile-page container">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Chargement de votre espace élite...</p>
    </div>

    <div v-else-if="authStore.fetchError" class="error-container container">
       <div class="alert-glow error">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          {{ authStore.fetchError }}
          <button @click="authStore.initAuth()" class="btn btn-secondary btn-sm">Réessayer</button>
       </div>
    </div>

    <div v-else class="profile-layout">
      <!-- Profile Sidebar / Hero -->
      <aside class="profile-hero glass-panel animate-section">
        <div class="avatar-wrapper">
          <div class="avatar-glow"></div>
          <div class="avatar-circle">
            <img v-if="authStore.profile?.photoURL" :src="authStore.profile.photoURL" class="profile-img-preview" />
            <template v-else>
              <svg v-if="!profile.user.first_name" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <span v-else>{{ profile.user.first_name[0] }}{{ profile.user.last_name[0] }}</span>
            </template>
          </div>
          <button class="edit-avatar-btn" @click="triggerFileInput" :disabled="uploading">
            <span v-if="uploading" class="loader-tiny"></span>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          </button>
          <input type="file" ref="fileInput" @change="handleFileUpload" accept="image/*" style="display: none" />
        </div>
        
        <div class="hero-info">
          <h1 class="user-name text-glow">{{ profile.user.first_name }} {{ profile.user.last_name }}</h1>
          <p class="user-role">{{ profile.user_type === 'FARMER' ? 'Producteur Expert' : 'Conseiller Agronomique' }}</p>
          <div class="user-badge">Membre Vérifié</div>
        </div>

        <div class="hero-stats">
          <div class="h-stat clickable-stat" @click="openSocialModal('followers')">
            <span class="h-val">{{ authStore.profile?.followersCount || 0 }}</span>
            <span class="h-lbl">Abonnés</span>
          </div>
          <div class="h-stat clickable-stat" @click="openSocialModal('following')">
            <span class="h-val">{{ authStore.profile?.followingCount || 0 }}</span>
            <span class="h-lbl">Suivis</span>
          </div>
        </div>

        <button @click="handleLogout" class="btn btn-logout-modern">
          <div class="logout-icon-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
          </div>
          <span>Quitter la session</span>
        </button>
      </aside>

      <!-- Main Form Area -->
      <main class="profile-main animate-section">
        <div v-if="message.text" :class="['alert-glow', message.type]">
          <span class="alert-icon">
            <svg v-if="message.type === 'success'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </span>
          {{ message.text }}
        </div>

        <form @submit.prevent="saveProfile" class="premium-form">
          <!-- Section: Identité -->
          <section class="form-section glass-panel">
            <div class="section-head">
              <div class="section-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2 8h20"/><circle cx="8" cy="14" r="2"/><path d="M14 14h4M14 12h2"/></svg>
              </div>
              <div class="section-title">
                <h3>Identité Numérique</h3>
                <p>Vos informations de base sur le réseau.</p>
              </div>
            </div>

            <div class="grid-2">
              <div class="premium-field">
                <label>Prénom</label>
                <div class="input-wrapper">
                  <svg class="field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  <input type="text" v-model="profile.user.first_name" required placeholder="Ex: Jean" />
                </div>
              </div>
              <div class="premium-field">
                <label>Nom de famille</label>
                <div class="input-wrapper">
                   <svg class="field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  <input type="text" v-model="profile.user.last_name" required placeholder="Ex: Dossou" />
                </div>
              </div>
            </div>

            <div class="premium-field">
              <label>Email (Lecture seule)</label>
              <div class="input-wrapper disabled">
                <svg class="field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
                <input type="email" :value="profile.user.email" disabled />
              </div>
            </div>
          </section>

          <!-- Section: Expertise & Contact -->
          <section class="form-section glass-panel">
            <div class="section-head">
              <div class="section-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              </div>
              <div class="section-title">
                <h3>Vocation & Localisation</h3>
                <p>Aidez-nous à personnaliser votre expérience.</p>
              </div>
            </div>

            <div class="grid-2">
              <div class="premium-field">
                <label>Téléphone Professionnel</label>
                <div class="input-wrapper">
                  <svg class="field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                  <input type="tel" v-model="profile.phone_number" placeholder="+229 00 00 00 00" />
                </div>
              </div>
              <div class="premium-field">
                <label>Type d'Acteur</label>
                <div class="input-wrapper">
                  <svg class="field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                  <select v-model="profile.user_type">
                    <option value="" disabled>Sélectionnez votre secteur</option>
                    <option v-for="sec in sectors" :key="sec.value" :value="sec.value">{{ sec.label }}</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="premium-field">
              <label>Commune Mandataire</label>
              <div class="input-wrapper">
                <svg class="field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                <select v-model="profile.location">
                  <option value="" disabled>Sélectionnez votre commune</option>
                  <option v-for="com in communesBenin" :key="com" :value="com">{{ com }}</option>
                </select>
              </div>
            </div>

            <div class="premium-field">
              <label>Ma Biographie Agronomique</label>
              <div class="input-wrapper area">
                <textarea v-model="profile.bio" rows="4" placeholder="Décrivez vos exploitations, vos défis et votre vision..."></textarea>
              </div>
            </div>
          </section>

          <div class="form-actions">
            <button type="submit" class="btn btn-save" :disabled="saving">
              <span v-if="saving" class="loader-small"></span>
              <span v-else>Propulser les changements</span>
            </button>
          </div>
        </form>
      </main>
    </div>

    <!-- Social Lists Modal -->
    <div v-if="showSocialModal" class="modal-overlay" @click.self="showSocialModal = false">
      <div class="modal-content glass-panel animate-pop">
        <div class="modal-header">
          <h3>{{ socialModalTitle }}</h3>
          <button class="btn-close" @click="showSocialModal = false">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>
        
        <div class="modal-body">
          <div v-if="socialListLoading" class="mini-spinner"></div>
          <div v-else-if="socialList.length > 0" class="social-user-list">
            <div v-for="user in socialList" :key="user.uid" class="social-user-card" @click="() => { showSocialModal = false; router.push('/profile/' + user.uid); }">
              <img :src="user.photoURL || 'https://via.placeholder.com/40'" class="social-avatar" />
              <div class="social-info">
                <span class="social-name">{{ user.displayName }}</span>
                <span class="social-type">{{ user.user_type }}</span>
              </div>
            </div>
          </div>
          <p v-else class="empty-list-text">Aucun résultat trouvé.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  padding-top: 140px;
  padding-bottom: 100px;
  min-height: 100vh;
}

.profile-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 40px;
  align-items: start;
}

/* Hero Sidebar */
.profile-hero {
  padding: 48px 32px;
  text-align: center;
  position: sticky;
  top: 140px;
}

.avatar-wrapper {
  position: relative;
  width: 140px;
  height: 140px;
  margin: 0 auto 32px;
}

.avatar-circle {
  width: 100%; height: 100%;
  background: var(--bg-dark);
  border: 3px solid var(--primary);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 3rem; font-weight: 800; color: var(--text-primary);
  position: relative; z-index: 2;
  box-shadow: 0 0 30px var(--primary-glow);
}

.avatar-glow {
  position: absolute; top: -10%; left: -10%; width: 120%; height: 120%;
  background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
  z-index: 1; animation: pulse 3s infinite;
}

@keyframes pulse {
  0% { opacity: 0.4; transform: scale(0.9); }
  50% { opacity: 0.8; transform: scale(1.1); }
  100% { opacity: 0.4; transform: scale(0.9); }
}

.edit-avatar-btn {
  position: absolute; bottom: 5px; right: 5px;
  width: 40px; height: 40px; border-radius: 50%;
  background: var(--primary); color: var(--bg-dark);
  border: none; cursor: pointer; z-index: 3;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 15px rgba(0,0,0,0.3);
  transition: transform 0.3s;
}

.edit-avatar-btn:hover { transform: scale(1.1) rotate(15deg); }

.profile-img-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.loader-tiny {
  width: 16px; height: 16px; border: 2px solid rgba(0,0,0,0.1);
  border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite;
}

.hero-info h1 { font-size: 1.8rem; margin-bottom: 8px; }
.user-role { font-size: 1rem; color: var(--text-muted); font-weight: 500; margin-bottom: 16px; }
.user-badge {
  display: inline-block; padding: 4px 16px; border-radius: 100px;
  background: rgba(0, 230, 118, 0.1); border: 1px solid var(--primary-glow);
  color: var(--primary); font-size: 0.75rem; font-weight: 800; text-transform: uppercase;
}

.hero-stats {
  display: flex; justify-content: center; gap: 40px;
  margin: 40px 0; padding: 24px 0;
  border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
}

.h-stat { display: flex; flex-direction: column; gap: 4px; transition: 0.3s; }
.clickable-stat { cursor: pointer; }
.clickable-stat:hover .h-val { color: var(--primary); transform: scale(1.1); }
.h-val { font-size: 1.5rem; font-weight: 800; color: var(--text-primary); transition: 0.3s; }
.h-lbl { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; }

.btn-logout-modern {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 14px;
  color: var(--danger);
  font-weight: 700;
  cursor: pointer;
  transition: 0.3s;
}

.btn-logout-modern:hover {
  background: rgba(255, 82, 82, 0.1);
  border-color: rgba(255, 82, 82, 0.3);
  transform: translateY(-2px);
}

.logout-icon-box {
  width: 36px;
  height: 36px;
  background: rgba(255, 82, 82, 0.1);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Main Content */
.premium-form { display: flex; flex-direction: column; gap: 32px; }

.form-section { padding: 40px; }
.section-head { display: flex; gap: 20px; align-items: center; margin-bottom: 40px; }
.section-icon { font-size: 2rem; opacity: 0.8; }
.section-title h3 { font-size: 1.4rem; margin-bottom: 4px; color: var(--text-primary); }
.section-title p { font-size: 0.9rem; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }

.premium-field { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.premium-field label { font-size: 0.85rem; font-weight: 700; color: var(--text-primary); opacity: 0.8; margin-left: 4px; }

.input-wrapper {
  position: relative;
  display: flex; align-items: center;
}

.input-wrapper .field-icon {
  position: absolute; left: 16px; color: var(--primary); opacity: 0.6;
}

input, select, textarea {
  width: 100%; padding: 16px 16px 16px 48px;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  color: var(--text-primary); border-radius: 14px; font-size: 1rem; outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

textarea { padding-left: 20px; }

input:focus, select:focus, textarea:focus {
  background: rgba(255,255,255,0.06); border-color: var(--primary);
  box-shadow: 0 0 20px rgba(0, 230, 118, 0.15);
}

/* Fix pour la visibilité des options dans les menus déroulants */
option {
  background-color: var(--bg-surface);
  color: var(--text-primary);
  padding: 10px;
}

.input-wrapper.disabled input { opacity: 0.5; cursor: not-allowed; }

.alert-glow {
  padding: 16px 24px; border-radius: 14px; margin-bottom: 32px;
  display: flex; align-items: center; gap: 15px; font-weight: 600;
  animation: slideIn 0.5s ease-out;
}
.alert-glow.success { background: rgba(0, 230, 118, 0.1); color: var(--primary); border: 1px solid var(--primary-glow); }
.alert-glow.error { background: rgba(255, 82, 82, 0.1); color: var(--danger); border: 1px solid rgba(255, 82, 82, 0.3); }

@keyframes slideIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

.btn-save {
  width: 100%; height: 64px; font-size: 1.1rem;
  background: linear-gradient(135deg, var(--primary), #00c853);
  color: var(--bg-darker); border: none; border-radius: 18px;
  font-weight: 800; cursor: pointer; transition: 0.4s;
  box-shadow: 0 10px 30px var(--primary-glow);
}

.btn-save:hover { transform: translateY(-4px); box-shadow: 0 15px 40px var(--primary-glow); }

.loading-state { text-align: center; padding: 100px; width: 100%; }
.spinner { width: 50px; height: 50px; border: 4px solid var(--border); border-top-color: var(--primary); border-radius: 50%; margin: 0 auto 20px; animation: spin 1s linear infinite; }

@keyframes spin { to { transform: rotate(360deg); } }

/* Social Modal Styles (Sync with PublicProfileView) */
.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.8); backdrop-filter: blur(5px);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
  padding: 20px;
}
.modal-content {
  width: 100%; max-width: 450px; max-height: 80vh; overflow: hidden;
  display: flex; flex-direction: column; border-radius: 20px;
}
.animate-pop { animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
@keyframes popIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }

.modal-header {
  padding: 20px 24px; border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
}
.modal-header h3 { margin: 0; font-size: 1.2rem; color: var(--primary); }
.btn-close {
  background: none; border: none; color: var(--text-primary); font-size: 1.8rem;
  cursor: pointer; opacity: 0.6; transition: 0.3s; display: flex; align-items: center; justify-content: center;
}
.btn-close:hover { opacity: 1; color: var(--primary); }

.modal-body { padding: 10px 0; overflow-y: auto; }
.social-user-list { display: flex; flex-direction: column; }
.social-user-card {
  display: flex; align-items: center; gap: 16px; padding: 12px 24px;
  cursor: pointer; transition: 0.2s; border-bottom: 1px solid rgba(255,255,255,0.05);
  text-align: left;
}
.social-user-card:hover { background: rgba(255,255,255,0.05); }
.social-avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; border: 1px solid var(--border); }
.social-info { display: flex; flex-direction: column; }
.social-name { font-weight: 700; color: var(--text-primary); }
.social-type { font-size: 0.8rem; color: var(--text-muted); }
.empty-list-text { text-align: center; padding: 40px; color: var(--text-muted); }

.mini-spinner { width: 30px; height: 30px; border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--primary); border-radius: 50%; margin: 20px auto; animation: spin 0.8s linear infinite; }

@media (max-width: 1024px) {
  .profile-layout { grid-template-columns: 1fr; }
  .profile-hero { position: relative; top: 0; }
}

@media (max-width: 768px) {
  .grid-2 { grid-template-columns: 1fr; gap: 0; }
  .form-section { padding: 24px; }
}
</style>