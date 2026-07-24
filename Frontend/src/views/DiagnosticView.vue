<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import { supabase } from '../supabase'
import gsap from 'gsap'

const imageFile = ref(null)
const imagePreview = ref(null)
const loading = ref(false)
const error = ref(null)
const saveSuccess = ref(false)
const diagnostic = ref(null)
const cameraInput = ref(null)
const fileInput = ref(null)
// Camera Feed Logic
const isCameraMode = ref(false)
const videoRef = ref(null)
const canvasRef = ref(null)
let stream = null

const startCamera = async () => {
  isCameraMode.value = true
  diagnostic.value = null
  imagePreview.value = null
  try {
    stream = await navigator.mediaDevices.getUserMedia({ 
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } } 
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream
    }
  } catch (err) {
    console.error("Camera access error:", err)
    error.value = "Impossible d'accéder à la caméra. Vérifiez les permissions."
    isCameraMode.value = false
  }
}

const stopCamera = () => {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
  }
  isCameraMode.value = false
}

const capturePhoto = () => {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  
  imagePreview.value = canvas.toDataURL('image/jpeg')
  stopCamera()
}

const triggerCamera = () => {
  startCamera()
}

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  imageFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
  }
  reader.readAsDataURL(file)
  
  // Réinitialiser les états
  diagnostic.value = null
  error.value = null
}

const analyzePlant = async () => {
  if (!imagePreview.value) return
  
  loading.value = true
  error.value = null
  diagnostic.value = null
  
  try {
    // Optimisation : Réduire la taille de l'image avant l'envoi au backend
    // Cela évite les timeouts sur les connexions lentes et réduit la charge serveur.
    const optimizedImage = await resizeImageForFirestore(imagePreview.value, 800)
    
    // Appel à l'API Django qui gère Google Gemini Vision
    const response = await api.post('diagnose_plant/', {
      image: optimizedImage
    })
    
    if (response.data && response.data.diagnostic) {
      diagnostic.value = response.data.diagnostic
      
      // Sauvegarde asynchrone (non-bloquante) dans Firestore
      saveSuccess.value = false;
      if (auth.currentUser) {
        console.log(">>> Saving to history for user:", auth.currentUser.uid);
        saveToHistory(diagnostic.value, imagePreview.value)
          .then(() => {
            console.log(">>> Save successful!");
            saveSuccess.value = true;
          })
          .catch(err => {
            console.error("FULL FIRESTORE ERROR:", JSON.stringify(err, null, 2));
            console.error("Firestore error code:", err.code);
            console.error("Firestore error message:", err.message);
            error.value = "Analyse réussie, mais échec de la sauvegarde dans l'historique : [" + (err.code || "unknown") + "] " + (err.message || "");
          })
      } else {
        console.warn(">>> User not logged in, skipping save.");
        error.value = "Analyse réussie. Note: Vous n'êtes pas connecté, le résultat ne sera pas sauvegardé dans l'historique.";
      }
      
      // Animation des résultats
      setTimeout(() => {
        gsap.from(".result-item", { 
          y: 20, opacity: 0, duration: 0.6, stagger: 0.1, ease: "power2.out" 
        })
      }, 50)
    } else {
      throw new Error("Réponse invalide de l'IA.")
    }
    
  } catch (err) {
    console.error("Full Analysis Error:", err);
    const backendError = err.response?.data?.error || err.response?.data?.detail;
    
    if (backendError) {
      if (backendError.includes("API key not valid")) {
        error.value = "Erreur de configuration : La clé API Gemini dans le backend est invalide. Veuillez vérifier le fichier .env du backend.";
      } else {
        error.value = `Erreur Serveur : ${backendError}`;
      }
    } else if (err.message === "Network Error") {
      const isProd = window.location.hostname.includes('web.app') || window.location.hostname.includes('firebaseapp.com');
      error.value = isProd 
        ? "Connexion au serveur Agrotech AI impossible. Le serveur est peut-être en veille (prévoyez 1 min pour le réveil) ou votre connexion internet est faible." 
        : "Impossible de contacter le serveur. Sur mobile, vérifiez que votre téléphone est sur le même WiFi que votre ordinateur et que vous utilisez l'adresse IP de votre PC dans VITE_API_URL (ex: http://192.168.1.XX:5000/api/).";
    } else {
      error.value = `Erreur technique : ${err.message || 'Inconnue'}. ${err.response?.status ? '(Status: ' + err.response.status + ')' : ''}`;
    }
  } finally {
    loading.value = false
  }
}

// Résolution du bug "invalid-argument" : compression de l'image pour Firestore (Limite 1Mo)
const resizeImageForFirestore = (dataUrl, maxWidth = 600) => {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const scale = maxWidth / img.width
      canvas.width = maxWidth
      canvas.height = img.height * scale
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      resolve(canvas.toDataURL('image/jpeg', 0.7)) // 70% quality compression
    }
    img.src = dataUrl
  })
}

const saveToHistory = async (diag, image) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session?.user || !diag) return

  // Compresser l'image pour éviter de dépasser 1Mo
  const compressedImage = await resizeImageForFirestore(image)

  await supabase.from('scan_history').insert({
    user_id: session.user.id,
    image_url: compressedImage,
    plant_name: diag.plante || 'Plante inconnue',
    disease: diag.maladie || 'Saine',
    diagnosis: {
      plante: diag.plante || 'Plante inconnue',
      utilite: diag.utilite || 'Information non disponible',
      proprietes_medicinales: diag.proprietes_medicinales || 'Information non disponible',
      maladie: diag.maladie || 'Saine',
      cause: diag.cause || 'N/A',
      traitement: diag.traitement || 'N/A',
      produit_recommande: diag.produit_recommande || 'N/A',
    },
  })
}

onMounted(() => {
  gsap.from(".diag-header", { y: -30, opacity: 0, duration: 1, ease: "power3.out" })
  gsap.from(".upload-container", { scale: 0.95, opacity: 0, duration: 0.8, delay: 0.2, ease: "back.out(1.2)" })
})
</script>

<template>
  <div class="diagnostic-page container">
    <header class="diag-header">
      <h1 class="text-glow">PlantGuard IA</h1>
      <p>Photographiez une feuille malade. Notre intelligence artificielle agronomique identifie le problème en quelques secondes.</p>
    </header>

    <div class="workspace">
      <div class="upload-container glass-panel" :class="{'no-border': isCameraMode}">
        <input 
          type="file" 
          accept="image/*" 
          id="fileInput" 
          @change="handleFileUpload" 
          ref="fileInput"
          hidden 
        />
        
        <!-- Live Camera Mode -->
        <div v-if="isCameraMode" class="camera-mode">
          <video ref="videoRef" autoplay playsinline class="video-feed"></video>
          <canvas ref="canvasRef" style="display:none;"></canvas>
          <div class="camera-controls">
            <button class="btn btn-secondary circle" @click="stopCamera">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
            <button class="btn btn-primary capture-btn" @click="capturePhoto">
              <div class="capture-inner"></div>
            </button>
          </div>
        </div>

        <div v-else-if="!imagePreview" class="upload-prompt">
          <div class="cam-icon">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          </div>
          <h3>Diagnostic Instantané</h3>
          <p>Utilisez votre caméra en direct ou envoyez une photo existante.</p>
          
          <div class="upload-actions">
            <button class="btn btn-primary" @click="startCamera">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
              Ouvrir la Caméra
            </button>
            <button class="btn btn-secondary" @click="() => fileInput.click()">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
              Choisir un fichier
            </button>
          </div>
        </div>
        
        <div v-else class="image-preview-wrapper">
          <img :src="imagePreview" alt="Aperçu Plante" class="img-preview" />
          <div class="preview-actions">
            <button class="btn btn-secondary" @click="startCamera">Reprendre</button>
            <button class="btn btn-primary" @click="analyzePlant" :disabled="loading">
              {{ loading ? 'Analyse en cours...' : 'Lancer le Diagnostic' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="analysis-loading">
        <div class="scanner-line"></div>
        <p class="text-glow">Agrotech AI analyse les tissus foliaires...</p>
      </div>

      <!-- Error State -->
      <div v-if="error" class="error-message glass-panel">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        {{ error }}
      </div>

      <!-- Success State -->
      <div v-if="saveSuccess" class="success-message glass-panel">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        Diagnostic publié avec succès dans votre historique !
      </div>

      <!-- Results -->
      <div v-if="diagnostic" class="results-container">
        <h2 class="mb-4">Rapport Agronomique</h2>
        
        <div class="results-grid">
          <div class="result-item glass-panel plant-card">
            <span class="label">Plante Identifiée</span>
            <h3 class="text-primary">{{ diagnostic.plante || 'Non identifiée' }}</h3>
            <div class="plant-info-grid mt-3">
              <div v-if="diagnostic.utilite" class="info-item">
                <span class="sub-label">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.7 19.3 19.3 4.7M9.2 14.8l4.8-4.8"/></svg>
                  Utilité & Usage
                </span>
                <p>{{ diagnostic.utilite }}</p>
              </div>
              <div v-if="diagnostic.proprietes_medicinales" class="info-item">
                <span class="sub-label">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                  Vertus Médicinales
                </span>
                <p>{{ diagnostic.proprietes_medicinales }}</p>
              </div>
            </div>
          </div>
          <div class="result-item glass-panel">
            <span class="label">Maladie Détectée</span>
            <h3 :class="{'text-danger': diagnostic.maladie !== 'Saine'}">{{ diagnostic.maladie }}</h3>
          </div>
          <div class="result-item glass-panel">
            <span class="label">Agent Causal</span>
            <p>{{ diagnostic.cause }}</p>
          </div>
          <div class="result-item glass-panel protocol-card">
            <span class="label">Protocole de Traitement</span>
            <p>{{ diagnostic.traitement }}</p>
          </div>
          <div class="result-item glass-panel suggestion-card">
            <span class="label">Remède Suggéré</span>
            <h4 class="text-accent">{{ diagnostic.produit_recommande }}</h4>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.diagnostic-page { padding-top: 120px; min-height: 100vh; padding-bottom: 80px; }
.diag-header { text-align: center; margin-bottom: 50px; max-width: 600px; margin-inline: auto; }

.workspace { max-width: 800px; margin: 0 auto; display: flex; flex-direction: column; gap: 40px; }

.upload-container { padding: 40px; text-align: center; border: 2px dashed rgba(0, 230, 118, 0.3); border-radius: 20px; transition: border-color 0.3s; }
.upload-container:hover { border-color: var(--primary); }

.upload-prompt { cursor: pointer; padding: 40px 0; }
.cam-icon { margin-bottom: 20px; color: var(--primary); filter: drop-shadow(0 0 15px rgba(0,230,118,0.3)); display: flex; justify-content: center; }
.mt-4 { margin-top: 20px; }

.upload-actions { display: flex; flex-direction: column; gap: 15px; width: 100%; max-width: 320px; margin: 30px auto 0; }
.upload-actions .btn { display: flex; gap: 10px; align-items: center; justify-content: center; }

.image-preview-wrapper { display: flex; flex-direction: column; gap: 20px; align-items: center; }
.img-preview { max-width: 100%; max-height: 400px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
.preview-actions { display: flex; gap: 15px; }

.analysis-loading { text-align: center; padding: 40px; position: relative; }
.scanner-line { width: 100%; height: 4px; background: var(--primary); box-shadow: 0 0 20px var(--primary); border-radius: 2px; margin-bottom: 20px; animation: scan 1.5s ease-in-out infinite alternate; }
@keyframes scan { 0% { transform: scaleX(0.1); opacity: 0.5; } 100% { transform: scaleX(1); opacity: 1; } }

.error-message { padding: 20px; background: rgba(255, 82, 82, 0.1); color: var(--danger); border-color: rgba(255, 82, 82, 0.3); text-align: center; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 12px; }
.success-message { padding: 20px; background: rgba(0, 230, 118, 0.1); color: var(--primary); border-color: rgba(0, 230, 118, 0.3); text-align: center; font-weight: 600; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 12px; }

.results-container { margin-top: 20px; }
.results-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.result-item { padding: 24px; border-radius: 16px; }
.label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); display: block; margin-bottom: 10px; }
.text-danger { color: var(--danger); }
.text-accent { color: var(--accent); margin: 0; font-size: 1.3rem; }

/* Camera Mode Styles */
.camera-mode { position: relative; width: 100%; border-radius: 12px; overflow: hidden; background: var(--bg-deep); }
.video-feed { width: 100%; height: auto; display: block; }
.camera-controls { 
  position: absolute; bottom: 20px; left: 0; right: 0; 
  display: flex; justify-content: center; align-items: center; gap: 40px; 
}
.circle { width: 50px; height: 50px; border-radius: 50%; padding: 0; }
.capture-btn { 
  width: 70px; height: 70px; border-radius: 50%; padding: 4px; 
  background: #fff; border: 4px solid var(--primary); 
}
.capture-inner { width: 100%; height: 100%; border-radius: 50%; background: var(--primary); }
.capture-btn:active .capture-inner { transform: scale(0.9); }

.no-border { border: none !important; padding: 0 !important; }

.protocol-card, .suggestion-card, .plant-card { grid-column: span 2; }
.protocol-card p { line-height: 1.6; white-space: pre-line; }

.plant-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; text-align: left; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px; }
.sub-label { font-size: 0.7rem; font-weight: bold; color: var(--primary); text-transform: uppercase; display: block; margin-bottom: 5px; }
.info-item p { font-size: 0.9rem; color: var(--text-muted); line-height: 1.4; margin: 0; }

@media (max-width: 768px) {
  .diagnostic-page { padding-top: 95px; }
  .diag-header { margin-bottom: 30px; }
  .results-grid { grid-template-columns: 1fr; }
  .protocol-card, .suggestion-card { grid-column: span 1; }
  .preview-actions { flex-direction: column; width: 100%; }
  .preview-actions button { width: 100%; }
  .upload-container { padding: 20px; }
  .result-item { padding: 16px; }
}
</style>