<script setup>
import PlantLeaf3D from '../components/PlantLeaf3D.vue'
import { useRouter } from 'vue-router'
import { onMounted, ref, inject, computed } from 'vue'
import { useAuthStore } from '../authStore'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'
import { supabase } from '../supabase'
import { plantDatabase } from '../plantData'
import DOMPurify from 'dompurify'
import api from '../api'

const router = useRouter()
gsap.registerPlugin(ScrollTrigger)

const authStore = useAuthStore()
const isAuthenticated = computed(() => authStore.isAuthenticated)

const heroTitle = ref(null)
const heroPara = ref(null)
const heroActions = ref(null)
const openAuth = inject('openAuth')

const stats = [
  { label: 'Récoltes Sauvées', value: '12,400', icon: '' },
  { label: 'Agriculteurs', value: '5,000', icon: '' },
  { label: 'Analyses IA', value: '50,000', icon: '' }
]

// Universal Search Logic
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)

const aiAnswer = ref('')
const aiSearchLoading = ref(false)
const aiSearchError = ref(null)

const searchInputRef = ref(null)

const formatAiResponse = (text) => {
  if (!text) return ''
  const html = text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^#{1,3} (.+)$/gm, '<h4 class="ai-h4">$1</h4>')
    .replace(/^\* (.+)$/gm, '<li>$1</li>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
  return DOMPurify.sanitize(html)
}

// Normalisation unique des données plantes au montage (évite le re-calcul à chaque frappe)
const normalize = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
const normalizedPlants = plantDatabase.map(p => ({
  original: p,
  name: normalize(p.name),
  keywords: p.keywords.map(k => normalize(k))
}))

const askGemini = async () => {
  if (!searchQuery.value.trim()) return
  
  aiSearchLoading.value = true
  aiSearchError.value = null
  // No need to clear aiAnswer immediately if we want a transition, but let's clear for now
  aiAnswer.value = ''
  
  try {
    // We use the api service defined in api.js
    const response = await api.post('ai_search/', { query: searchQuery.value })
    if (response.data && response.data.answer) {
      aiAnswer.value = response.data.answer
      // Smooth reveal
      setTimeout(() => {
        gsap.from(".ai-response-box", { opacity: 0, y: 20, duration: 0.8, ease: "power2.out" })
      }, 100)
    }
  } catch (err) {
    console.error("AI Search Error:", err);
    const isProd = window.location.hostname.includes('web.app') || window.location.hostname.includes('firebaseapp.com');
    if (err.message === 'Network Error') {
      aiSearchError.value = isProd 
        ? "L'Intelligence Agrotech se réveille... Patientez 30-60 secondes et relancez votre recherche."
        : "Erreur de connexion au serveur local. Vérifiez VITE_API_URL.";
    } else {
      aiSearchError.value = err.response?.data?.error || "Une erreur est survenue lors de l'analyse de l'Intelligence Agrotech.";
    }
  } finally {
    aiSearchLoading.value = false
  }
}

const handleSearch = () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    isSearching.value = false
    aiAnswer.value = ''
    return
  }
  
  isSearching.value = true
  const queryText = searchQuery.value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
  const queryWords = queryText.split(/\s+/).filter(w => w.length > 2)

  searchResults.value = normalizedPlants.filter(p => {
    const matchName = p.name.includes(queryText) || queryText.includes(p.name)
    const matchKeywords = p.keywords.some(k => queryText.includes(k) || k.includes(queryText))

    if (matchName || matchKeywords) return true

    // Word by word matches
    return queryWords.some(word =>
      p.name.includes(word) || p.keywords.some(k => k.includes(word))
    )
  }).map(p => p.original)
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
  isSearching.value = false
  aiAnswer.value = ''
  aiSearchError.value = null
}

const features = [
  { 
    title: 'IA Diagnostic Pro', 
    desc: 'Identifiez instantanément les maladies grâce à la puissance de Gemini Vision.',
    link: '/diagnostic',
    icon: ''
  },
  { 
    title: 'AgroSocial', 
    desc: 'Rejoignez le premier réseau social des experts de la terre au Bénin. Échangez, suivez et grandissez.',
    link: '/community',
    icon: ''
  }
]

const recentPosts = ref([])
const postsLoading = ref(true)

// Hover management
let popTimeoutSource = null
const showPop = (post) => {
  if (popTimeoutSource) clearTimeout(popTimeoutSource)
  post.showPop = true
}
const hidePop = (post) => {
  popTimeoutSource = setTimeout(() => {
    post.showPop = false
  }, 300)
}

const fetchRecentPosts = async () => {
  try {
    const { data: posts, error } = await supabase
      .from('posts')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(3)

    if (error) throw error

    recentPosts.value = await Promise.all((posts || []).map(async (post) => {
      // Charger le profil de l'auteur
      let authorName = 'Expert'
      let authorPic = ''
      let authorId = post.user_id
      if (post.user_id) {
        const { data: profile } = await supabase
          .from('profiles')
          .select('display_name, avatar_url')
          .eq('id', post.user_id)
          .single()
        if (profile) {
          authorName = profile.display_name || 'Expert'
          authorPic = profile.avatar_url || ''
        }
      }

      // Vérifier la réaction de l'utilisateur connecté
      let userReaction = null
      if (isAuthenticated.value) {
        const { data: reaction } = await supabase
          .from('post_reactions')
          .select('reaction_type')
          .eq('post_id', post.id)
          .eq('user_id', authStore.user.id)
          .maybeSingle()
        userReaction = reaction?.reaction_type || null
      }

      return {
        id: post.id,
        authorId,
        authorName,
        authorPic,
        content: post.content,
        image_url: post.image_url || '',
        reactionsCount: post.reactions_count || {},
        commentsCount: post.comments_count || 0,
        tags: post.tags || [],
        createdAt: post.created_at,
        showPop: false,
        showComments: false,
        comments: [],
        newComment: '',
        replyTo: null,
        userReaction,
      }
    }))
    
    setTimeout(() => {
      gsap.from(".home-post-card", {
        scrollTrigger: {
          trigger: ".home-feed-grid",
          start: "top 85%",
        },
        y: 30,
        opacity: 0,
        duration: 0.8,
        stagger: 0.2,
        ease: "power2.out"
      })
    }, 200)
  } catch (err) {
    console.error("Home feed error:", err)
  } finally {
    postsLoading.value = false
  }
}

const toggleReaction = async (postId, type) => {
  if (!isAuthenticated.value) { return openAuth('login') }
  const post = recentPosts.value.find(p => p.id === postId)
  if (!post) return

  try {
    if (post.userReaction === type) {
      // Supprimer la réaction (le trigger PostgreSQL met à jour reactions_count)
      await supabase.from('post_reactions').delete()
        .eq('post_id', postId)
        .eq('user_id', authStore.user.id)
      post.userReaction = null
    } else {
      // Ajouter ou changer la réaction
      await supabase.from('post_reactions').upsert({
        post_id: postId,
        user_id: authStore.user.id,
        reaction_type: type,
      }, { onConflict: 'post_id,user_id' })
      post.userReaction = type
    }
  } catch (err) {
    console.error("Reaction error", err)
  }
}

const toggleComments = async (postId) => {
  if (!isAuthenticated.value) { return openAuth('login') }
  const post = recentPosts.value.find(p => p.id === postId)
  if (!post) return
  post.showComments = !post.showComments
  if (post.showComments && post.comments.length === 0) {
    const { data: comments } = await supabase
      .from('post_comments')
      .select('*')
      .eq('post_id', postId)
      .order('created_at', { ascending: true })
    post.comments = (comments || []).map(c => ({
      id: c.id,
      authorId: c.user_id,
      content: c.content,
      createdAt: c.created_at,
    }))
  }
}

const addComment = async (postId) => {
  if (!isAuthenticated.value) return
  const post = recentPosts.value.find(p => p.id === postId)
  if (!post || !post.newComment) return

  try {
    const { data: newComment, error } = await supabase
      .from('post_comments')
      .insert({
        post_id: postId,
        user_id: authStore.user.id,
        content: post.newComment,
      })
      .select()
      .single()

    if (error) throw error

    post.comments.push({
      id: newComment.id,
      authorId: authStore.user.id,
      content: post.newComment,
      createdAt: newComment.created_at,
    })
    post.newComment = ''
    post.replyTo = null
    post.commentsCount = (post.commentsCount || 0) + 1
  } catch (err) {
    console.error("Comment error", err)
  }
}

const sharePost = async (post) => {
  const authorName = post.authorName || 'un expert Agrotech AI'
  const postUrl = `https://agrotech-ai-ff555.web.app/community?post=${post.id}`
  const shareData = {
    title: `Conseil de ${authorName} sur Agrotech AI`,
    text: `${post.content.substring(0, 80)}... \n\nLisez la suite :`,
    url: postUrl
  }
  
  if (navigator.share) {
    try {
      await navigator.share(shareData)
    } catch (err) {
      console.log("Share failed")
    }
  } else {
    await navigator.clipboard.writeText(`${shareData.text}\n${shareData.url}`)
    alert("Lien copié !")
  }
}

const formatDate = (ts) => {
  if (!ts) return 'Récemment'
  const d = ts.toDate ? ts.toDate() : new Date(ts)
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}

onMounted(() => {
  // Hero Animations
  const tl = gsap.timeline()
  tl.from(".hero-badge", { y: -20, opacity: 0, duration: 0.8, ease: "power3.out" })
    .from("h1 .line", { y: 100, opacity: 0, duration: 1, stagger: 0.2, ease: "power4.out" }, "-=0.4")
    .from(".hero-description", { opacity: 0, x: -30, duration: 1 }, "-=0.6")
    .from(".hero-search-wrapper-new", { y: 20, opacity: 0, duration: 0.8, ease: "power2.out" }, "-=0.7")
    .from(".hero-actions .btn", { scale: 0.8, opacity: 0, duration: 0.8, stagger: 0.2, ease: "back.out(1.7)" }, "-=0.5")

  // Statistics Grid Animation
  gsap.from(".stat-card", {
    scrollTrigger: {
      trigger: ".stats-grid",
      start: "top 85%",
    },
    y: 60,
    opacity: 0,
    duration: 1,
    stagger: 0.15,
    ease: "expo.out"
  })

  // Features Cards Animation
  gsap.from(".feat-card", {
    scrollTrigger: {
      trigger: ".features-grid",
      start: "top 80%",
    },
    scale: 0.9,
    opacity: 0,
    duration: 1,
    stagger: 0.2,
    ease: "power2.out"
  })

  // Parallax on 3D Element
  gsap.to(".hero-3d-container", {
    scrollTrigger: {
      trigger: ".hero-wrapper",
      start: "top top",
      end: "bottom top",
      scrub: true
    },
    y: 150,
    scale: 1.1,
    rotate: 10
  })

  fetchRecentPosts()
})
</script>

<template>
  <div class="home-container">
    <!-- Hero Section -->
    <section class="hero-wrapper">
      <div class="hero-3d-container">
        <PlantLeaf3D />
      </div>
      
      <div class="container hero-content">
        <!-- Hero text -->
        <div class="hero-inner">
          <div class="hero-badge animate-float">
            <span>BioTech Intelligence Bénin</span>
          </div>
          
          <h1>
            <span class="line">L'Agriculture</span>
            <span class="line text-glow">Révolutionnée</span>
            <span class="line">par l'IA.</span>
          </h1>
          
          <p class="hero-description">
            Protégez vos cultures avec la puissance d'<strong>Agrotech AI</strong>.
            Une expertise agronomique d'élite dans votre poche.
          </p>

          <!-- PROMINENT SEARCH TRIGGER -->
          <div class="ai-search-trigger-section">
            <button class="ai-search-pill" @click="isSearching = true">
              <div class="pill-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              </div>
              <span class="pill-text">Rechercher avec Agrotech AI</span>
              <div class="pill-badge">IA</div>
            </button>
            <div class="search-hints">
              <span @click="searchQuery = 'quelles plantes guérissent le paludisme ?'; isSearching = true; $nextTick(() => askGemini())" class="hint-chip">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                Plantes anti-palu
              </span>
              <span @click="searchQuery = 'comment cultiver le maïs ?'; isSearching = true; $nextTick(() => askGemini())" class="hint-chip">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M2 12h20"/></svg>
                Cultiver le maïs
              </span>
              <span @click="searchQuery = 'propriétés du neem'; isSearching = true; $nextTick(() => askGemini())" class="hint-chip">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.7 19.3 19.3 4.7M9.2 14.8l4.8-4.8"/></svg>
                Propriétés du Neem
              </span>
            </div>
          </div>

          <div class="hero-actions">
            <button @click="router.push('/diagnostic')" class="btn btn-primary">
              Lancer le Scan IA
            </button>
            <button @click="router.push('/history')" class="btn btn-secondary">
              Voir mon Historique
            </button>
          </div>
        </div>
      </div>

      <!-- FULL-SCREEN AI SEARCH MODAL - Teleported to body level to avoid z-index issues -->
      <Teleport to="body">
        <Transition name="search-modal">
          <div v-if="isSearching" class="ai-search-modal">
            <div class="modal-backdrop" @click="clearSearch"></div>
            <div class="modal-container">
              <!-- Search Input Header -->
              <div class="modal-search-header">
                <div class="modal-input-wrapper">
                  <svg class="modal-search-icon" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                  <input 
                    ref="searchInputRef"
                    v-model="searchQuery" 
                    @input="handleSearch"
                    @keyup.enter="askGemini"
                    placeholder="Ex: quelles plantes guérissent le paludisme ?" 
                    class="modal-input"
                    autofocus
                  />
                  <button v-if="searchQuery" @click="searchQuery = ''; searchResults = []; aiAnswer = ''" class="modal-clear">✕</button>
                </div>
                <button class="modal-ask-btn" @click="askGemini" :disabled="aiSearchLoading || !searchQuery">
                  <span v-if="!aiSearchLoading">Analyser</span>
                  <div v-else class="modal-loader"></div>
                </button>
                <button class="modal-close-btn" @click="clearSearch">✕</button>
              </div>

              <!-- Quick Suggestions -->
              <div v-if="!searchQuery" class="modal-suggestions">
                <p class="sugg-label">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                  Questions populaires</p>
                <div class="sugg-grid">
                  <div class="sugg-card" @click="searchQuery = 'quelles plantes guérissent le paludisme ?'; askGemini()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    <span>Plantes anti-paludisme</span>
                  </div>
                  <div class="sugg-card" @click="searchQuery = 'comment cultiver le maïs en saison sèche ?'; askGemini()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M2 12h20"/></svg>
                    <span>Culture du maïs</span>
                  </div>
                  <div class="sugg-card" @click="searchQuery = 'propriétés médicinales du neem'; askGemini()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.7 19.3 19.3 4.7M9.2 14.8l4.8-4.8"/></svg>
                    <span>Propriétés du Neem</span>
                  </div>
                  <div class="sugg-card" @click="searchQuery = 'comment traiter le mildiou sur les tomates ?'; askGemini()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    <span>Maladies de la tomate</span>
                  </div>
                  <div class="sugg-card" @click="searchQuery = 'plantes médicinales du Bénin'; askGemini()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a8 8 0 0 0-8 8c0 5 8 12 8 12s8-7 8-12a8 8 0 0 0-8-8z"/><circle cx="12" cy="10" r="3"/></svg>
                    <span>Plantes médicinales Bénin</span>
                  </div>
                  <div class="sugg-card" @click="searchQuery = 'comment améliorer la fertilité du sol ?'; askGemini()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 22V12a10 10 0 0 1 20 0v10"/><path d="M2 16h20"/><path d="M6 16v4"/><path d="M18 16v4"/></svg>
                    <span>Fertilité du sol</span>
                  </div>
                </div>
              </div>

              <!-- AI Loading State -->
              <div v-if="aiSearchLoading" class="modal-ai-thinking">
                <div class="thinking-dots">
                  <span></span><span></span><span></span>
                </div>
                <p>Agrotech AI analyse votre question...</p>
              </div>

              <!-- AI Response -->
              <div v-if="aiAnswer && !aiSearchLoading" class="modal-ai-response">
                <div class="ai-response-header">
                  <div class="ai-response-badge">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4c0 2-2 4-4 4s-4-2-4-4 2-4 4-4z"/><path d="M12 14c-4 0-6 2-6 4v2h12v-2c0-2-2-4-6-4z"/></svg>
                    <span>Analyse Agrotech AI</span>
                  </div>
                  <button class="ai-copy-btn" @click="navigator.clipboard?.writeText(aiAnswer)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    Copier
                  </button>
                </div>
                <div class="ai-response-content" v-html="formatAiResponse(aiAnswer)"></div>
              </div>

              <!-- Error -->
              <div v-if="aiSearchError && !aiSearchLoading" class="modal-error">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                {{ aiSearchError }}
              </div>

              <!-- Local Results -->
              <div v-if="searchResults.length > 0 && !aiAnswer" class="modal-local-results">
                <p class="local-results-label">Résultats trouvés ({{ searchResults.length }})</p>
                <div class="local-results-grid">
                  <div v-for="res in searchResults.slice(0,6)" :key="res.name" class="local-res-card" @click="router.push('/diagnostic'); clearSearch()">
                    <img :src="res.image" :alt="res.name" />
                    <div class="local-res-info">
                      <h5>{{ res.name }}</h5>
                      <p>{{ res.usage?.substring(0, 60) }}...</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>
      
      <div v-if="!isSearching" class="hero-scroll-indicator">
        <div class="mouse"></div>
        <span>Découvrir</span>
      </div>
    </section>

    <!-- Stats Section -->
    <section class="stats-section">
      <div class="container">
        <div class="stats-grid">
          <div v-for="(stat, idx) in stats" :key="stat.label" class="stat-card glass-panel">
            <div class="stat-icon">
              <svg v-if="idx === 0" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              <svg v-else-if="idx === 1" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              <svg v-else-if="idx === 2" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4M8 8l2 2M16 8l-2 2"/></svg>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stat.value }}</span>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
            <div class="stat-bg-glow"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="features-section container">
      <div class="section-header">
        <h2 class="text-glow">Nos Solutions</h2>
        <p>Des outils technologiques conçus pour l'avenir de la terre.</p>
      </div>

      <div class="features-grid">
        <div v-for="(feat, idx) in features" :key="feat.title" class="feat-card glass-panel" @click="router.push(feat.link)">
          <div class="feat-icon-top">
            <svg v-if="idx === 0" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v8M12 14v8M4.93 4.93l5.66 5.66M13.41 13.41l5.66 5.66M2 12h8M14 12h8M4.93 19.07l5.66-5.66M13.41 10.59l5.66-5.66"/></svg>
            <svg v-else-if="idx === 1" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20V10M18 20V4M6 20v-4"/></svg>
          </div>
          <div class="feat-content">
            <h3>{{ feat.title }}</h3>
            <p>{{ feat.desc }}</p>
            <button class="feat-btn">Accéder <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></button>
          </div>
        </div>
      </div>
    </section>

    <!-- Home Feed Section (PUBLIC) -->
    <section class="home-feed-section container">
      <div class="section-header">
        <h2 class="text-glow">Dernières Publications</h2>
        <p>Découvrez ce qui se passe dans la communauté des experts.</p>
      </div>

      <div v-if="postsLoading" class="feed-placeholder">
        <div class="spinner"></div>
      </div>

      <div v-else class="home-feed-grid">
        <div v-for="post in recentPosts" :key="post.id" class="home-post-card glass-panel">
          <div class="hp-head">
            <RouterLink :to="'/profile/' + post.authorId" class="hp-avatar-link">
              <img :src="post.authorPic || 'https://via.placeholder.com/40'" class="hp-avatar" />
            </RouterLink>
            <div class="hp-meta">
              <RouterLink :to="'/profile/' + post.authorId" class="hp-author-name">
                <h5>{{ post.authorName }}</h5>
              </RouterLink>
              <span>{{ formatDate(post.createdAt) }}</span>
            </div>
          </div>
          <div class="hp-content">
            <p>{{ post.content.substring(0, 120) }}{{ post.content.length > 120 ? '...' : '' }}</p>
            <img v-if="post.image_url" :src="post.image_url" class="hp-img" />
            
            <div class="post-interactions mt-16">
              <div class="i-summary">
                <div class="reactions-summary">
                   <span v-for="(count, type) in post.reactionsCount" :key="type" v-show="count > 0" class="r-badge-mini">
                     {{ type }} {{ count }}
                   </span>
                </div>
                <span class="c-badge-mini">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  {{ post.commentsCount || 0 }}
                </span>
              </div>
              <div class="i-actions-mini">
                <div class="reaction-trigger" @mouseenter="showPop(post)" @mouseleave="hidePop(post)">
                  <button class="i-btn-mini" :class="{ 'active-r': post.userReaction }" @click="toggleReaction(post.id, '🌱')">
                    <span v-if="post.userReaction">{{ post.userReaction }}</span>
                    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.7 0l-1.1 1-1-1a5.5 5.5 0 0 0-7.7 7.7l1 1 7.8 7.8 7.7-7.7 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg> 
                  </button>
                  <div v-if="post.showPop" class="reaction-popover glass-panel" @mouseenter="showPop(post)">
                    <span v-for="emoji in ['🌱', '🚜', '🍎', '💧', '☀️']" :key="emoji" @click="toggleReaction(post.id, emoji)">{{ emoji }}</span>
                  </div>
                </div>
                <button class="i-btn-mini" @click="toggleComments(post.id)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                </button>
                <button class="i-btn-mini" @click="sharePost(post)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
                </button>
              </div>

              <!-- Comments Section (Mini) -->
              <div v-if="post.showComments" class="comments-drawer-mini mt-12 animate-fade">
                <div class="comments-list-mini">
                  <div v-for="c in post.comments.filter(cm => !cm.parentId)" :key="c.id" class="c-group-mini">
                    <div class="c-item-mini">
                      <RouterLink :to="'/profile/' + c.authorId" class="c-avatar-link">
                        <img :src="c.authorPic || 'https://via.placeholder.com/25'" class="c-avatar-mini" />
                      </RouterLink>
                      <div class="c-body-mini">
                        <RouterLink :to="'/profile/' + c.authorId" class="c-author-name">
                          <h6>{{ c.authorName }}</h6>
                        </RouterLink>
                        <p>{{ c.content }}</p>
                        <button class="btn-reply-mini" @click="post.replyTo = c.id">Répondre</button>
                      </div>
                    </div>
                    <!-- Replies (Mini) -->
                    <div class="replies-list-mini ml-16 mt-4">
                       <div v-for="r in post.comments.filter(rm => rm.parentId === c.id)" :key="r.id" class="c-item-mini sm-gap">
                         <div class="c-body-mini sm-pad">
                           <h6>{{ r.authorName }}</h6>
                           <p>{{ r.content }}</p>
                         </div>
                       </div>
                    </div>
                  </div>
                </div>
                <div class="c-input-box-mini mt-12">
                  <div v-if="post.replyTo" class="reply-indicator-mini">
                    Réponse... <button @click="post.replyTo = null">×</button>
                  </div>
                  <input v-model="post.newComment" @keyup.enter="addComment(post.id)" :placeholder="post.replyTo ? 'Réponse...' : 'Répondre...'" />
                  <button class="btn btn-primary sm" @click="addComment(post.id)">ok</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="feed-footer-cta animate-float-slow">
        <div class="cta-glow-bg"></div>
        <button v-if="!isAuthenticated" @click="openAuth('register')" class="btn btn-premium">
          <span class="btn-text">Rejoindre pour en voir plus</span>
          <svg class="btn-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </button>
        <button v-else @click="router.push('/community')" class="btn btn-premium">
          <span class="btn-text">Explorer tout le flux</span>
          <svg class="btn-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </button>
      </div>
    </section>

    <!-- Immersive Steps Section -->
    <section class="steps-section">
      <div class="container">
        <div class="steps-inner glass-panel">
          <div class="step-item">
            <div class="step-num">01</div>
            <h4>Capture</h4>
            <p>Photographiez l'anomalie sur le terrain.</p>
          </div>
          <div class="step-connector"></div>
          <div class="step-item">
            <div class="step-num">02</div>
            <h4>Analyse</h4>
            <p>Gemini Vision diagnostique en 2 secondes.</p>
          </div>
          <div class="step-connector"></div>
          <div class="step-item">
            <div class="step-num">03</div>
            <h4>Guérison</h4>
            <p>Appliquez le traitement recommandé par l'IA.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Final CTA -->
    <section v-if="!isAuthenticated" class="final-cta container">
      <div class="cta-card glass-panel">
        <div class="cta-content">
          <h2>Prêt à prospérer ?</h2>
          <p>Rejoignez la révolution de l'AgroTech béninoise dès aujourd'hui.</p>
          <button @click="openAuth('register')" class="btn btn-primary">Créer mon compte expert</button>
        </div>
        <div class="cta-aura"></div>
      </div>
    </section>

    <footer class="home-footer">
      <div class="container footer-content">
        <p>&copy; 2026 Agrotech AI. Innovation for a Green Future.</p>
        <div class="footer-links">
          <span>Mentions Légales</span>
          <span>Support 24/7</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.home-container {
  overflow-x: hidden;
}

/* Hero Section */
.hero-wrapper {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding-top: 80px;
}

.hero-3d-container {
  position: absolute;
  top: 0;
  right: -5%;
  width: 60%;
  height: 100%;
  z-index: 1;
  opacity: 0.8;
}

.hero-content {
  position: relative;
  z-index: 2;
}

.hero-inner {
  max-width: 800px;
  position: relative;
  z-index: 10;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(0, 230, 118, 0.1);
  border: 1px solid var(--border-bright);
  border-radius: 100px;
  margin-bottom: 24px;
  max-width: 100%;
  flex-wrap: wrap;
  justify-content: center;
}

.hero-badge span {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.hero-badge .dot {
  width: 6px;
  height: 6px;
  background: var(--primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--primary);
}

h1 .line {
  display: block;
  overflow: hidden;
}

.hero-content h1 span {
  background: linear-gradient(135deg, var(--secondary), var(--accent));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}
.text-glow {
  background: linear-gradient(135deg, #fff 0%, var(--primary) 50%, var(--accent) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 20px var(--primary-glow));
}

.hero-description {
  font-size: clamp(0.9rem, 2vw, 1.3rem);
  margin-bottom: 30px;
  max-width: 600px;
  line-height: 1.6;
}
/* ========================
   AI SEARCH TRIGGER PILL
   ======================== */
.ai-search-trigger-section {
  margin: 28px 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 14px;
}

.ai-search-pill {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 28px;
  background: linear-gradient(135deg, rgba(0,230,118,0.15), rgba(0,163,230,0.10));
  border: 1.5px solid var(--primary);
  border-radius: 100px;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 1.05rem;
  font-weight: 700;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 30px var(--primary-glow), 0 4px 20px rgba(0,0,0,0.3);
  animation: pill-pulse 3s ease-in-out infinite;
  -webkit-tap-highlight-color: transparent;
}

.ai-search-pill:hover {
  background: linear-gradient(135deg, rgba(0,230,118,0.25), rgba(0,163,230,0.15));
  box-shadow: 0 0 50px rgba(0,230,118,0.4), 0 8px 30px rgba(0,0,0,0.4);
  transform: translateY(-2px) scale(1.02);
}

.ai-search-pill:active {
  transform: translateY(0) scale(0.98);
}

@keyframes pill-pulse {
  0%, 100% { box-shadow: 0 0 30px rgba(0,230,118,0.2), 0 4px 20px rgba(0,0,0,0.3); }
  50% { box-shadow: 0 0 50px rgba(0,230,118,0.4), 0 4px 20px rgba(0,0,0,0.3); }
}

.pill-icon {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(0,230,118,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}

.pill-text { flex: 1; }

.pill-badge {
  padding: 4px 10px;
  background: var(--primary);
  color: #000;
  border-radius: 100px;
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 1px;
}

.search-hints {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.hint-chip {
  padding: 6px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 100px;
  font-size: 0.78rem;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  transition: 0.3s;
  -webkit-tap-highlight-color: transparent;
}
.hint-chip:hover {
  background: rgba(0,230,118,0.1);
  border-color: var(--primary);
  color: var(--primary);
}

/* ========================
   AI SEARCH MODAL (Teleport to body)
   ======================== */
.ai-search-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  height: 100dvh;
  z-index: 99999;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 60px 20px 20px;
  box-sizing: border-box;
}

.modal-backdrop {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(2, 8, 4, 0.97);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
}

.modal-container {
  position: relative;
  width: 100%;
  max-width: 820px;
  max-height: calc(100dvh - 80px);
  background: rgba(10, 20, 12, 0.98);
  border: 1px solid rgba(0,230,118,0.3);
  border-radius: 24px;
  overflow-y: auto;
  z-index: 1;
  box-shadow: 0 40px 80px rgba(0,0,0,0.8), 0 0 60px rgba(0,230,118,0.1);
}

/* Search Header */
.modal-search-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  position: sticky;
  top: 0;
  background: rgba(8, 18, 10, 0.98);
  backdrop-filter: blur(20px);
  z-index: 10;
}

.modal-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(0,230,118,0.25);
  border-radius: 14px;
  padding: 12px 18px;
  transition: border-color 0.3s;
}

.modal-input-wrapper:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 20px rgba(0,230,118,0.15);
}

.modal-search-icon { color: var(--primary); flex-shrink: 0; }

.modal-input {
  flex: 1;
  background: transparent !important;
  border: none !important;
  color: #fff !important;
  font-size: 1rem !important;
  outline: none !important;
  font-weight: 500;
}

.modal-input::placeholder { color: rgba(255,255,255,0.35); }

.modal-clear {
  background: transparent;
  border: none;
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  font-size: 1rem;
  padding: 2px 6px;
  border-radius: 50%;
  line-height: 1;
  -webkit-tap-highlight-color: transparent;
}

.modal-ask-btn {
  padding: 12px 22px;
  background: var(--primary);
  color: #000;
  border: none;
  border-radius: 12px;
  font-weight: 800;
  font-size: 0.9rem;
  cursor: pointer;
  min-width: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: 0.3s;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}

.modal-ask-btn:hover:not(:disabled) { background: #00ff88; transform: scale(1.05); }
.modal-ask-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.modal-close-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: 0.3s;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
.modal-close-btn:hover { background: rgba(255,59,59,0.15); color: #ff5252; }

.modal-loader {
  width: 18px; height: 18px;
  border: 2px solid transparent;
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Suggestions */
.modal-suggestions { padding: 24px 24px 0; }
.sugg-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: rgba(255,255,255,0.4);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 14px;
}

.sugg-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.sugg-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  cursor: pointer;
  transition: 0.3s;
  color: rgba(255,255,255,0.7);
  font-size: 0.85rem;
  font-weight: 600;
  -webkit-tap-highlight-color: transparent;
}
.sugg-card:hover {
  background: rgba(0,230,118,0.06);
  border-color: rgba(0,230,118,0.3);
  color: var(--primary);
}
.sugg-emoji { font-size: 1.4rem; flex-shrink: 0; }

/* AI Thinking Loader */
.modal-ai-thinking {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px;
  color: rgba(255,255,255,0.5);
  font-size: 0.9rem;
}

.thinking-dots {
  display: flex;
  gap: 8px;
}

.thinking-dots span {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--primary);
  animation: dot-bounce 1.2s ease-in-out infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1.2); opacity: 1; }
}

/* AI Response */
.modal-ai-response {
  margin: 20px 24px;
  background: rgba(0,230,118,0.04);
  border: 1px solid rgba(0,230,118,0.2);
  border-radius: 16px;
  overflow: hidden;
}

.ai-response-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(0,230,118,0.1);
  background: rgba(0,230,118,0.06);
}

.ai-response-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: var(--primary);
  font-size: 0.9rem;
}

.ai-copy-btn {
  background: transparent;
  border: 1px solid rgba(0,230,118,0.2);
  border-radius: 8px;
  padding: 5px 12px;
  color: rgba(255,255,255,0.5);
  font-size: 0.75rem;
  cursor: pointer;
  transition: 0.3s;
}
.ai-copy-btn:hover { border-color: var(--primary); color: var(--primary); }

.ai-response-content {
  padding: 20px;
  color: rgba(255,255,255,0.88);
  font-size: 0.95rem;
  line-height: 1.75;
}

.ai-response-content :deep(strong) { color: var(--primary); font-weight: 700; }
.ai-response-content :deep(ul) { padding-left: 20px; margin: 8px 0; }
.ai-response-content :deep(li) { margin-bottom: 6px; color: rgba(255,255,255,0.8); }
.ai-response-content :deep(.ai-h4) { color: #fff; font-size: 1rem; margin: 14px 0 6px; }

/* Error */
.modal-error {
  margin: 20px 24px;
  padding: 14px 20px;
  background: rgba(255,59,59,0.08);
  border: 1px solid rgba(255,59,59,0.2);
  border-radius: 12px;
  color: #ff7070;
  font-size: 0.9rem;
}

/* Local Results */
.modal-local-results { padding: 20px 24px; }
.local-results-label {
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: rgba(255,255,255,0.35);
  margin-bottom: 12px;
}

.local-results-grid { display: flex; flex-direction: column; gap: 10px; }

.local-res-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  cursor: pointer;
  transition: 0.3s;
  -webkit-tap-highlight-color: transparent;
}
.local-res-card:hover { background: rgba(0,230,118,0.05); border-color: rgba(0,230,118,0.2); }
.local-res-card img { width: 48px; height: 48px; border-radius: 10px; object-fit: cover; flex-shrink: 0; }
.local-res-info h5 { color: #fff; font-size: 0.95rem; margin: 0 0 4px; }
.local-res-info p { color: rgba(255,255,255,0.45); font-size: 0.8rem; margin: 0; }

/* Modal Transition */
.search-modal-enter-active { animation: modal-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }
.search-modal-leave-active { animation: modal-out 0.2s ease forwards; }

@keyframes modal-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes modal-out {
  from { opacity: 1; }
  to { opacity: 0; }
}

.search-modal-enter-active .modal-container {
  animation: container-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}
.search-modal-leave-active .modal-container {
  animation: container-out 0.2s ease forwards;
}

@keyframes container-in {
  from { transform: translateY(-20px) scale(0.96); opacity: 0; }
  to { transform: translateY(0) scale(1); opacity: 1; }
}
@keyframes container-out {
  from { transform: translateY(0) scale(1); opacity: 1; }
  to { transform: translateY(-20px) scale(0.96); opacity: 0; }
}

/* Responsive */
@media (max-width: 768px) {
  .ai-search-modal { padding: 50px 12px 12px; }
  .sugg-grid { grid-template-columns: repeat(2, 1fr); }
  .modal-search-header { padding: 12px; gap: 8px; }
  .modal-ask-btn { padding: 10px 14px; font-size: 0.8rem; }
  .modal-input { font-size: 0.9rem !important; }
  .ai-search-pill { padding: 14px 20px; font-size: 0.92rem; }
  .sugg-card { font-size: 0.78rem; padding: 10px 12px; }
}

@media (max-width: 480px) {
  .sugg-grid { grid-template-columns: 1fr 1fr; }
  .ai-search-pill { width: 100%; justify-content: center; }
  .modal-container { border-radius: 16px; }
}


.integrated-results-list { display: flex; flex-direction: column; gap: 20px; }
.integrated-res-card {
  display: flex;
  gap: 25px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 18px;
  border: 1px solid var(--border);
  transition: 0.3s;
}

.integrated-res-card:hover { 
  background: rgba(255, 255, 255, 0.06); 
  border-color: var(--primary);
}

.res-visual { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.res-visual img { width: 100%; height: 100%; object-fit: cover; border-radius: 12px; }
.res-tag { position: absolute; top: -5px; right: -5px; background: var(--primary); color: #000; font-size: 0.6rem; font-weight: 800; padding: 2px 6px; border-radius: 4px; }

.res-details { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.res-details h4 { font-size: 1.3rem; color: var(--primary); margin: 0; }
.res-usage-text { font-size: 1rem; color: #fff; line-height: 1.5; }

.res-tips-box {
  background: rgba(0, 230, 118, 0.05);
  border-left: 2px solid var(--primary);
  padding: 8px 12px;
  margin-top: 5px;
}
.tips-label { font-size: 0.7rem; font-weight: 800; color: var(--primary); text-transform: uppercase; display: block; }
.res-tips-box p { font-size: 0.9rem; color: var(--text-muted); margin: 0; }

.no-results-integrated { text-align: center; padding: 40px 0; }
.ai-brain-icon { font-size: 4rem; margin-bottom: 20px; filter: drop-shadow(0 0 15px var(--primary)); }

.sample-questions {
  margin-top: 30px; display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
}
.chip { 
  background: rgba(255,255,255,0.05); border: 1px solid var(--border); 
  color: #fff; padding: 8px 16px; border-radius: 100px; cursor: pointer; 
  font-size: 0.85rem; transition: 0.3s;
}
.chip:hover { background: var(--primary); color: #000; }

/* Transitions */
.fade-scale-enter-active, .fade-scale-leave-active { transition: all 0.4s ease; }
.fade-scale-enter-from, .fade-scale-leave-to { opacity: 0; transform: scale(1.05); }

@keyframes popIn { 0% { transform: scale(0.9); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
.animate-pop-in { animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }

@media (max-width: 768px) {
  .integrated-res-card { flex-direction: column; gap: 15px; }
  .res-visual { width: 100%; height: 180px; }
  .hero-search-wrapper-new { max-width: 100%; margin: 20px 0; }
  .search-results-panel { max-height: 95vh; margin: 0; border-radius: 0; }
}

.hero-actions {
  gap: 20px;
}

@media (max-width: 768px) {
  .hero-inner {
    text-align: center;
    margin: 0 auto;
  }
  .hero-description {
    margin-left: auto;
    margin-right: auto;
  }
  .hero-actions {
    justify-content: center;
    flex-direction: column;
    width: 100%;
  }
  .hero-actions .btn {
    width: 100%;
  }
  .hero-badge {
    margin-left: auto;
    margin-right: auto;
  }
  .hero-3d-container {
    opacity: 0.3;
    right: 0;
    width: 100%;
  }
}

.hero-scroll-indicator {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  opacity: 0.6;
}

.mouse {
  width: 24px;
  height: 40px;
  border: 2px solid var(--text-muted);
  border-radius: 20px;
  position: relative;
}

.mouse::after {
  content: '';
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 8px;
  background: var(--primary);
  border-radius: 2px;
  animation: scrollAnim 1.5s infinite;
}

@keyframes scrollAnim {
  0% { opacity: 1; transform: translate(-50%, 0); }
  100% { opacity: 0; transform: translate(-50%, 15px); }
}

/* Stats Section */
.stats-section {
  padding: 60px 0;
  margin-top: -50px;
  position: relative;
  z-index: 10;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
}

.stat-card {
  padding: 32px;
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
  overflow: hidden;
}

.stat-icon {
  font-size: 2.5rem;
  filter: drop-shadow(0 0 10px var(--primary-glow));
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--text-primary);
}

.stat-label {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-weight: 500;
}

.stat-bg-glow {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
  opacity: 0.1;
  pointer-events: none;
}

/* Features Grid */
.features-section {
  padding: 120px 0;
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
}

.section-header p {
  font-size: 1.2rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 32px;
}

.feat-card {
  padding: 48px 32px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

/* Home Feed Section */
.home-feed-section { padding-bottom: 120px; }
.home-feed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
  margin-bottom: 40px;
}
.home-post-card { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.hp-head { display: flex; gap: 12px; align-items: center; }
.hp-avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.hp-meta h5 { margin: 0; font-size: 1rem; color: var(--text-primary); }
.hp-meta span { font-size: 0.8rem; color: var(--text-muted); }
.hp-content p { font-size: 0.95rem; line-height: 1.5; color: var(--text-muted); margin-bottom: 12px; }
.hp-img { width: 100%; height: 180px; object-fit: cover; border-radius: 8px; border: 1px solid var(--border); }

.hp-stats-mini { display: flex; gap: 8px; flex-wrap: wrap; }
.r-badge-mini, .c-badge-mini { 
  background: rgba(255,255,255,0.05); padding: 2px 6px; 
  border-radius: 100px; font-size: 0.75rem; color: var(--text-muted);
  border: 1px solid var(--border);
}

/* Home Social Interactions */
.post-interactions { border-top: 1px solid var(--border); padding-top: 12px; position: relative; }
.i-summary { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px; }
.reactions-summary { display: flex; gap: 6px; }
.i-actions-mini { display: flex; gap: 16px; border-top: 1px solid var(--border); padding-top: 10px; }
.i-btn-mini { 
  background: transparent; border: none; color: var(--text-muted); 
  font-size: 1rem; cursor: pointer; transition: 0.3s;
  display: flex; align-items: center; justify-content: center;
}
.i-btn-mini:hover, .i-btn-mini.active-r { color: var(--primary); }

.reaction-trigger { position: relative; }
.reaction-popover {
  position: absolute; bottom: 100%; left: 0; display: flex; gap: 10px; 
  padding: 8px 12px; border-radius: 20px; margin-bottom: 8px; z-index: 100;
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}
.reaction-popover span { font-size: 1.2rem; cursor: pointer; transition: 0.2s; }
.reaction-popover span:hover { transform: scale(1.3); }

.comments-drawer-mini { border-top: 1px dashed var(--border); padding-top: 10px; }
.c-item-mini { display: flex; gap: 10px; margin-bottom: 10px; }
.c-avatar-mini { width: 25px; height: 25px; border-radius: 50%; }
.c-body-mini { background: rgba(255,255,255,0.02); padding: 6px 12px; border-radius: 8px; flex: 1; }
.c-body-mini h6 { margin: 0; font-size: 0.8rem; color: #fff; }
.c-body-mini p { margin: 0; font-size: 0.8rem; color: var(--text-muted); }
.btn-reply-mini { background: transparent; border: none; color: var(--primary); font-size: 0.7rem; cursor: pointer; padding: 2px 0; font-weight: 600; }

.ml-16 { margin-left: 16px; }
.reply-indicator-mini { background: rgba(0,230,118,0.1); padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; color: var(--primary); border-left: 2px solid var(--primary); display: flex; justify-content: space-between; }
.reply-indicator-mini button { background: transparent; border: none; color: var(--primary); cursor: pointer; }

.c-input-box-mini { display: flex; flex-direction: column; gap: 6px; }
.c-input-box-mini input { 
  flex: 1; background: rgba(0,0,0,0.2); border: 1px solid var(--border); 
  border-radius: 6px; padding: 4px 12px; color: #fff; font-size: 0.8rem;
}

.animate-fade { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
.feed-footer-cta { 
  display: flex; justify-content: center; padding-top: 40px; position: relative; 
}
.feed-placeholder { display: flex; justify-content: center; padding: 40px; }

/* Premium CTA Button */
.btn-premium {
  position: relative;
  padding: 18px 42px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  color: var(--bg-dark);
  font-weight: 850;
  font-size: 1.15rem;
  border-radius: 100px;
  border: none;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 230, 118, 0.3);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.btn-premium:hover {
  transform: translateY(-5px) scale(1.02);
  box-shadow: 0 20px 60px rgba(0, 230, 118, 0.5);
}

.btn-premium .btn-arrow {
  transition: transform 0.3s ease;
}

.btn-premium:hover .btn-arrow {
  transform: translateX(5px);
}

.cta-glow-bg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 300px;
  height: 100px;
  background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
  opacity: 0.3;
  filter: blur(40px);
  pointer-events: none;
}

.animate-float-slow {
  animation: floatSlow 6s ease-in-out infinite;
}

@keyframes floatSlow {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.feat-icon-top {
  font-size: 3.5rem;
  margin-bottom: 32px;
}

.feat-card h3 {
  font-size: 1.8rem;
  margin-bottom: 16px;
}

.feat-btn {
  margin-top: 24px;
  background: transparent;
  border: none;
  color: var(--primary);
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: gap 0.3s;
}

.feat-card:hover .feat-btn {
  gap: 15px;
}

/* Steps Section */
.steps-section {
  padding: 100px 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0, 230, 118, 0.05) 50%, transparent 100%);
}

.steps-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 60px 40px;
  gap: 20px;
}

.step-item {
  flex: 1;
  text-align: center;
}

.step-num {
  font-family: 'Syne', sans-serif;
  font-size: 3.5rem;
  font-weight: 900;
  color: var(--primary);
  opacity: 0.2;
  margin-bottom: -30px;
}

.step-item h4 {
  font-size: 1.5rem;
  margin-bottom: 12px;
  position: relative;
}

.step-connector {
  flex: 0.2;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--border), transparent);
}

/* Final CTA */
.final-cta {
  padding: 120px 0;
}

.cta-card {
  padding: 80px 40px;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.cta-aura {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 150%;
  height: 150%;
  background: radial-gradient(circle, var(--primary-glow) 0%, transparent 60%);
  opacity: 0.2;
  z-index: 0;
}

.cta-content {
  position: relative;
  z-index: 1;
}

/* Footer */
.home-footer {
  padding: 60px 0;
  border-top: 1px solid var(--border);
  background: linear-gradient(0deg, var(--bg-deep) 0%, transparent 100%);
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-content p {
  color: var(--text-dim);
  font-size: 0.85rem;
}

.footer-links {
  display: flex;
  gap: 40px;
  font-size: 0.85rem;
  color: var(--text-dim);
}

.footer-links span {
  cursor: pointer;
  transition: color 0.3s ease;
}

.footer-links span:hover {
  color: var(--primary);
}

@media (max-width: 992px) {
  .hero-3d-container { right: -20%; width: 80%; opacity: 0.5; }
  .hero-inner { max-width: 100%; text-align: center; }
  .hero-actions { justify-content: center; }
  .features-grid { grid-template-columns: 1fr; }
  .hero-description { margin: 0 auto 30px; }
  .hero-search-wrapper-new { max-width: 100%; margin: 15px auto 24px; }
  .hero-badge { margin-left: auto; margin-right: auto; }
}

@media (max-width: 768px) {
  /* Force overflow hidden on the whole hero to prevent rightward drift */
  .hero-wrapper { overflow-x: hidden; }
  
  .hero-inner {
    padding: 0 12px;
    box-sizing: border-box;
    width: 100%;
    text-align: center;
  }
  
  .hero-badge {
    font-size: 0.7rem;
    padding: 4px 10px;
    margin-bottom: 16px;
  }
  
  .hero-badge span {
    font-size: 0.72rem;
    letter-spacing: 0.5px;
  }
  
  .hero-content h1,
  .hero-inner h1 {
    font-size: 1.75rem !important;
    line-height: 1.15 !important;
    margin-bottom: 16px !important;
    word-break: break-word;
  }
  
  .hero-description {
    font-size: 0.88rem !important;
    line-height: 1.5 !important;
    margin-bottom: 20px !important;
    padding: 0 !important;
    max-width: 100% !important;
    text-align: center;
  }
  
  .hero-actions {
    flex-direction: column !important;
    width: 100% !important;
    max-width: 260px !important;
    margin: 0 auto !important;
    gap: 10px !important;
  }
  
  .hero-actions .btn {
    width: 100% !important;
    padding: 12px !important;
    font-size: 0.9rem !important;
  }
  
  .hero-3d-container { display: none !important; }
  .hero-content { padding-top: 20px !important; }
  
  .stats-section { margin-top: -20px !important; padding: 30px 0 !important; }
  .stats-grid { grid-template-columns: 1fr !important; gap: 12px !important; }
  .stat-card { padding: 12px !important; }
  .stat-value { font-size: 1.3rem !important; }
  
  .hero-search-wrapper-new {
    margin: 14px auto 20px !important;
    max-width: 100% !important;
    box-sizing: border-box;
  }

  .search-main-container { border-radius: 14px; }
  .search-input-group { flex-wrap: nowrap; gap: 6px; }
  .btn-search-trigger span { display: none; }
  .btn-search-trigger { padding: 8px 12px; }
}

@media (max-width: 480px) {
  .hero-inner h1,
  .hero-content h1 {
    font-size: 1.5rem !important;
  }
  
  .hero-description {
    font-size: 0.82rem !important;
  }
}

.hp-author-name, .c-author-name { text-decoration: none; }
.hp-author-name:hover h5, .c-author-name:hover h6 { color: var(--primary); }
.hp-avatar-link, .c-avatar-link { display: block; border-radius: 50%; overflow: hidden; }

/* Scroll Indicator Fix */
.hero-scroll-indicator {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 0.8rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  z-index: 5;
}

.mouse {
  width: 24px;
  height: 40px;
  border: 2px solid rgba(0, 230, 118, 0.3);
  border-radius: 20px;
  position: relative;
}

.mouse::after {
  content: '';
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  background: var(--primary);
  border-radius: 50%;
  animation: scrollMouse 2s infinite ease-in-out;
}

@keyframes scrollMouse {
  0% { transform: translate(-50%, 0); opacity: 0; }
  20% { opacity: 1; }
  80% { transform: translate(-50%, 15px); opacity: 0; }
  100% { opacity: 0; }
}

@keyframes slideIn { from { transform: translateX(-20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.animate-slide-in { animation: slideIn 0.5s forwards; }

.integrated-res-card:hover { 
  background: rgba(255, 255, 255, 0.06); 
  border-color: var(--primary);
}

.res-visual { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.res-visual img { width: 100%; height: 100%; object-fit: cover; border-radius: 12px; }
.res-tag { position: absolute; top: -5px; right: -5px; background: var(--primary); color: #000; font-size: 0.6rem; font-weight: 800; padding: 2px 6px; border-radius: 4px; }

.res-details { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.res-details h4 { font-size: 1.3rem; color: var(--primary); margin: 0; }
.res-usage-text { font-size: 1rem; color: #fff; line-height: 1.5; }

.res-tips-box {
  background: rgba(0, 230, 118, 0.05);
  border-left: 2px solid var(--primary);
  padding: 8px 12px;
  margin-top: 5px;
}
.tips-label { font-size: 0.7rem; font-weight: 800; color: var(--primary); text-transform: uppercase; display: block; }
.res-tips-box p { font-size: 0.9rem; color: var(--text-muted); margin: 0; }

.no-results-integrated { text-align: center; padding: 40px 0; }
.ai-brain-icon { font-size: 4rem; margin-bottom: 20px; filter: drop-shadow(0 0 15px var(--primary)); }

.sample-questions {
  margin-top: 30px; display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
}
.chip { 
  background: rgba(255,255,255,0.05); border: 1px solid var(--border); 
  color: #fff; padding: 8px 16px; border-radius: 100px; cursor: pointer; 
  font-size: 0.85rem; transition: 0.3s;
}
.chip:hover { background: var(--primary); color: #000; }

/* Transitions */
.fade-scale-enter-active, .fade-scale-leave-active { transition: all 0.4s ease; }
.fade-scale-enter-from, .fade-scale-leave-to { opacity: 0; transform: scale(1.05); }

@keyframes popIn { 0% { transform: scale(0.9); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
.animate-pop-in { animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }

@media (max-width: 768px) {
  .integrated-res-card { flex-direction: column; gap: 15px; }
  .res-visual { width: 100%; height: 180px; }
  .hero-search-wrapper-new { max-width: 100%; margin: 20px 0; }
  .search-results-panel { max-height: 95vh; margin: 0; border-radius: 0; }
}

/* New Search Trigger Button */
.btn-search-trigger {
  background: var(--primary);
  border: none;
  color: #000;
  padding: 8px 18px;
  border-radius: 100px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 0.9rem;
  margin-right: 6px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 15px var(--primary-glow);
}

.btn-search-trigger:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--primary-glow);
}

.ai-search-cta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  margin-bottom: 30px;
  border-radius: 16px;
  border: 1px solid var(--primary-glow);
  background: rgba(0, 230, 118, 0.08);
}

.ai-badge-mini {
  font-size: 0.7rem;
  background: var(--primary);
  color: #000;
  padding: 3px 10px;
  border-radius: 100px;
  font-weight: 900;
  display: inline-block;
  margin-bottom: 10px;
}

.ai-cta-info p { margin: 0; font-weight: 600; font-size: 1rem; color: #fff; }

.btn-ask-ai {
  background: var(--primary);
  color: #000;
  border: none;
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 900;
  cursor: pointer;
  transition: 0.3s;
}

.btn-ask-ai:hover { transform: scale(1.05); }

.ai-response-box {
  padding: 28px;
  border-radius: 16px;
  border: 1px solid var(--primary);
  background: rgba(0, 0, 0, 0.5);
  margin-bottom: 30px;
}

.ai-res-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.ai-avatar {
  background: var(--primary);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  box-shadow: 0 0 15px var(--primary-glow);
}

.ai-res-content {
  line-height: 1.8;
  color: var(--text-primary);
  font-size: 1.1rem;
}

.results-divider {
  margin: 40px 0 20px;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--primary);
  letter-spacing: 3px;
  font-weight: 900;
  text-align: center;
  opacity: 0.6;
}

.loader-mini {
  width: 22px;
  height: 22px;
  border: 3px solid #000;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 480px) {
  .ai-search-cta { flex-direction: column; gap: 20px; text-align: center; }
  .btn-ask-ai { width: 100%; }
}
</style>
