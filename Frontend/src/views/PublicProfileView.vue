<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { supabase } from '../supabase'
import { useAuthStore } from '../authStore'
import QuickMessageModal from '../components/QuickMessageModal.vue'
import gsap from 'gsap'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const profile = ref(null)
const loading = ref(true)
const isFollowing = ref(false)
const userPosts = ref([])
const postsLoading = ref(true)
const followLoading = ref(false)

// Quick Message State
const showQuickMsg = ref(false)
const openQuickMsg = () => {
  showQuickMsg.value = true
}
const onMessageSent = () => {
  console.log("Message sent from profile")
}

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
    const userId = route.params.userId
    const fieldName = type === 'followers' ? 'following_id' : 'follower_id'
    const { data: follows } = await supabase.from('follows').select('*').eq(fieldName, userId).limit(50)

    const userIds = (follows || []).map(f => type === 'followers' ? f.follower_id : f.following_id)

    if (userIds.length > 0) {
      const limitedIds = userIds.slice(0, 20)
      const { data: profiles } = await supabase.from('profiles').select('*').in('id', limitedIds)
      socialList.value = (profiles || []).map(p => ({
        uid: p.id,
        displayName: p.display_name,
        photoURL: p.avatar_url,
        user_type: p.user_type
      }))
    }
  } catch (err) {
    console.error("Social list error", err)
  } finally {
    socialListLoading.value = false
  }
}

const fetchPublicProfile = async () => {
  try {
    const userId = route.params.userId
    const { data, error } = await supabase.from('profiles').select('*').eq('id', userId).single()

    if (data && !error) {
      profile.value = {
        uid: data.id,
        displayName: data.display_name,
        photoURL: data.avatar_url,
        followersCount: data.followers_count,
        followingCount: data.following_count,
        bio: data.bio,
        user_type: data.user_type,
        location: data.location,
        experience: data.experience
      }

      // Check if following
      if (authStore.user) {
        const { data: follow } = await supabase.from('follows').select('*').eq('follower_id', authStore.user.id).eq('following_id', userId).maybeSingle()
        isFollowing.value = !!follow
      }

      fetchUserPosts(userId)
    }
  } catch (err) {
    console.error("Erreur profil public:", err)
  } finally {
    loading.value = false
  }
}

const fetchUserPosts = async (userId) => {
  try {
    const { data: postsData } = await supabase.from('posts').select('*').eq('user_id', userId).order('created_at', { ascending: false }).limit(10)
    userPosts.value = (postsData || []).map(p => ({
      id: p.id,
      authorId: p.user_id,
      content: p.content,
      image_url: p.image_url,
      createdAt: p.created_at,
      commentsCount: p.comments_count,
      reactionsCount: p.reactions_count
    }))
  } catch (err) {
    console.error("Posts error", err)
  } finally {
    postsLoading.value = false
  }
}

const toggleFollow = async () => {
  if (!authStore.user) {
    alert("Veuillez vous connecter pour suivre cet expert.")
    return
  }
  if (followLoading.value) return

  const userId = profile.value.uid
  followLoading.value = true

  try {
    if (isFollowing.value) {
      // Optimistic update
      isFollowing.value = false
      profile.value.followersCount = Math.max(0, (profile.value.followersCount || 0) - 1)

      const { error } = await supabase.from('follows').delete().eq('follower_id', authStore.user.id).eq('following_id', userId)
      if (error) throw error
    } else {
      // Optimistic update
      isFollowing.value = true
      profile.value.followersCount = (profile.value.followersCount || 0) + 1

      const { error } = await supabase.from('follows').insert({ follower_id: authStore.user.id, following_id: userId })
      if (error) throw error
    }
  } catch (err) {
    console.error("DEBUG FOLLOW ERROR DETAILS:", {
      code: err.code,
      message: err.message,
      targetUid: userId,
      currentUser: authStore.user?.id
    })
    // Rollback on error
    isFollowing.value = !isFollowing.value
    profile.value.followersCount += isFollowing.value ? 1 : -1

    alert("Une erreur est survenue lors du changement d'abonnement. Vérifiez votre connexion.")
  } finally {
    followLoading.value = false
  }
}

onMounted(() => {
  fetchPublicProfile()
  gsap.from(".public-card", { opacity: 0, scale: 0.95, duration: 1, ease: "power3.out" })
})
</script>

<template>
  <div class="public-profile-page">
    <div class="container">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
      </div>

      <div v-else-if="profile" class="public-card glass-panel">
        <div class="banner"></div>
        
        <div class="main-info">
          <div class="avatar-wrapper">
            <img v-if="profile.photoURL" :src="profile.photoURL" class="avatar-large" />
            <div v-else class="avatar-large placeholder">
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
          </div>
          
          <div class="profile-header-text">
            <h1>{{ profile.displayName }}</h1>
            <p class="role-badge">{{ profile.user_type }} | {{ profile.location || 'Localisation non définie' }}</p>
            
            <div class="profile-stats-bar mt-16">
              <div class="stat-item clickable-stat" @click="openSocialModal('followers')">
                <span class="stat-num">{{ profile.followersCount || 0 }}</span>
                <span class="stat-label">Abonnés</span>
              </div>
              <div class="stat-item clickable-stat" @click="openSocialModal('following')">
                <span class="stat-num">{{ profile.followingCount || 0 }}</span>
                <span class="stat-label">Abonnements</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ userPosts.length }}</span>
                <span class="stat-label">Publications</span>
              </div>
            </div>
          </div>
        </div>

        <div class="profile-actions-top">
           <button 
             v-if="!authStore.user || authStore.user.id !== profile.uid"
             class="btn btn-premium btn-follow-new" 
             :class="{ 'followed-state': isFollowing }" 
             @click="toggleFollow" 
             :disabled="followLoading"
           >
             <span v-if="followLoading" class="mini-spinner-btn"></span>
             <template v-else>
                <svg v-if="!isFollowing" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                {{ isFollowing ? 'Abonné' : 'S\'abonner' }}
             </template>
           </button>
                      <button 
              v-if="authStore.user && authStore.user.id !== profile.uid" 
              class="btn btn-premium btn-message-new" 
              @click="openQuickMsg"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              Message
            </button>
        </div>

        <div class="profile-grid">
          <div class="profile-content-main">
            <h3 class="section-title">Publications de {{ profile.displayName.split(' ')[0] }}</h3>
            
            <div v-if="postsLoading" class="mini-spinner"></div>
            <div v-else-if="userPosts.length > 0" class="user-posts-feed">
              <RouterLink v-for="post in userPosts" :key="post.id" :to="'/community?post=' + post.id" class="mini-post-card glass-panel no-link">
                <p class="post-snippet">{{ post.content.substring(0, 150) }}...</p>
                <img v-if="post.image_url" :src="post.image_url" class="mini-post-img" />
                <div class="mini-post-footer">
                  <span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M12 2a3 3 0 0 0-3 3v2h6V5a3 3 0 0 0-3-3Z"/><path d="M5 11a7 7 0 0 1 14 0v2a7 7 0 0 1-14 0Z"/><path d="M3 16h18M12 22v-3"/></svg>
                    {{ post.reactionsCount?.['🌱'] || 0 }}
                  </span>
                  <span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    {{ post.commentsCount || 0 }}
                  </span>
                </div>
              </RouterLink>
            </div>
            <div v-else class="empty-feed">Cet expert n'a pas encore publié.</div>
          </div>

          <aside class="profile-sidebar">
            <div class="profile-section section-bio">
              <h3>À propos</h3>
              <p v-if="profile.bio">{{ profile.bio }}</p>
              <p v-else class="empty-text">Aucune bio disponible.</p>
            </div>

            <div class="profile-section section-exp mt-24">
              <h3>Expertise</h3>
              <p v-if="profile.experience" class="exp-text">{{ profile.experience }}</p>
              <p v-else class="empty-text">Informations non renseignées.</p>
            </div>
          </aside>
        </div>
      </div>

      <div v-else class="error-state">
        <h2>Profil introuvable</h2>
        <RouterLink to="/" class="btn btn-ghost">Retour à l'accueil</RouterLink>
      </div>
    </div>

    <!-- Social Lists Modal -->
    <div v-if="showSocialModal" class="modal-overlay" @click.self="showSocialModal = false">
      <div class="modal-content glass-panel animate-pop">
        <div class="modal-header">
          <h3>{{ socialModalTitle }}</h3>
          <button class="btn-close" @click="showSocialModal = false">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        
        <div class="modal-body">
          <div v-if="socialListLoading" class="mini-spinner"></div>
          <div v-else-if="socialList.length > 0" class="social-user-list">
            <div v-for="user in socialList" :key="user.uid" class="social-user-card" @click="() => { showSocialModal = false; router.push('/profile/' + user.uid); }">
              <img :src="user.photoURL || 'data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 50'%3E%3Crect width='50' height='50' fill='%232a2a2a'/%3E%3Ccircle cx='25' cy='17' r='9' fill='%23555'/%3E%3Cpath d='M7 45a18 18 0 0 1 36 0' fill='%23555'/%3E%3C/svg%3E'" class="social-avatar" />
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

    <!-- Quick Message Modal -->
    <QuickMessageModal 
      v-if="profile"
      :show="showQuickMsg"
      :partnerId="profile.uid"
      :partnerName="profile.displayName"
      :partnerPic="profile.photoURL"
      @close="showQuickMsg = false"
      @sent="onMessageSent"
    />
  </div>
</template>

<style scoped>
.public-profile-page { padding-top: 140px; min-height: 100vh; }
.public-card { max-width: 900px; margin: 0 auto; overflow: hidden; position: relative; }
.banner { height: 180px; background: linear-gradient(45deg, var(--primary-glow), var(--accent-glow)); opacity: 0.3; }
.main-info { display: flex; align-items: flex-end; gap: 30px; padding: 0 40px; margin-top: -60px; margin-bottom: 40px; }
.avatar-wrapper { position: relative; z-index: 10; }
.avatar-large { 
  width: 140px; height: 140px; border-radius: 50%; border: 5px solid var(--bg-card); 
  background: var(--bg-card); object-fit: cover;
}
.avatar-large.placeholder {
  display: flex; align-items: center; justify-content: center;
  color: var(--primary); font-weight: 700;
}
.profile-header-text h1 { font-size: 2.2rem; margin-bottom: 5px; }
.role-badge { color: var(--primary); font-weight: 600; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }

.profile-stats-bar { display: flex; gap: 30px; }
.stat-item { display: flex; flex-direction: column; align-items: flex-start; }
.clickable-stat { cursor: pointer; transition: 0.3s; }
.clickable-stat:hover .stat-num { color: var(--primary); transform: scale(1.1); }
.stat-num { font-size: 1.2rem; font-weight: 800; color: var(--text-primary); transition: 0.3s; }
.stat-label { font-size: 0.8rem; color: var(--text-muted); }

.profile-actions-top { padding: 0 40px 40px; display: flex; gap: 12px; margin-top: -10px; }

.btn-premium {
  display: flex; align-items: center; gap: 10px; padding: 12px 24px;
  border: none; border-radius: 12px; font-weight: 800; cursor: pointer;
  text-transform: uppercase; letter-spacing: 1px; font-size: 0.85rem;
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.btn-follow-new {
  background: linear-gradient(135deg, var(--primary), var(--accent));
  color: var(--bg-dark);
  box-shadow: 0 8px 20px var(--primary-glow);
}

.btn-follow-new.followed-state {
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-bright);
  color: var(--text-primary);
  box-shadow: none;
}

.btn-message-new {
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-bright);
  color: var(--text-primary);
  backdrop-filter: blur(10px);
}

.btn-premium:hover { transform: translateY(-4px) scale(1.02); }
.btn-follow-new:not(.followed-state):hover { box-shadow: 0 12px 30px var(--primary-glow); }
.btn-message-new:hover { background: rgba(255,255,255,0.1); border-color: var(--primary); }

.mini-spinner-btn { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; }

.profile-grid { display: grid; grid-template-columns: 1.8fr 1fr; gap: 40px; padding: 0 40px 40px; }
.section-title { font-size: 1.2rem; color: var(--text-primary); margin-bottom: 24px; border-left: 4px solid var(--primary); padding-left: 12px; }

.user-posts-feed { display: flex; flex-direction: column; gap: 20px; }
.mini-post-card { padding: 20px; border-radius: 12px; transition: 0.3s; cursor: pointer; }
.mini-post-card:hover { transform: translateY(-5px); border-color: var(--primary); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
.no-link { text-decoration: none; color: inherit; }
.post-snippet { font-size: 0.95rem; color: var(--text-muted); line-height: 1.5; margin-bottom: 12px; }
.mini-post-img { width: 100%; border-radius: 8px; margin-bottom: 12px; }
.mini-post-footer { display: flex; gap: 16px; font-size: 0.85rem; color: var(--text-muted); }

.profile-section h3 { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }
.empty-text { color: var(--border); font-style: italic; font-size: 0.9rem; }
.exp-text { white-space: pre-wrap; line-height: 1.6; font-size: 0.95rem; }

@media (max-width: 900px) {
  .profile-grid { grid-template-columns: 1fr; }
  .profile-sidebar { order: -1; }
  .main-info { flex-direction: column; align-items: center; text-align: center; margin-top: -70px; }
  .profile-stats-bar { justify-content: center; width: 100%; }
  .profile-actions-top { justify-content: center; }
}
.loading-state { text-align: center; padding: 100px; }
.spinner { width: 50px; height: 50px; border: 4px solid var(--border); border-top-color: var(--primary); border-radius: 50%; margin: 0 auto; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Social Modal Styles */
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
  cursor: pointer; opacity: 0.6; transition: 0.3s; display: flex; align-items: center;
}
.btn-close:hover { opacity: 1; color: var(--primary); }

.modal-body { padding: 10px 0; overflow-y: auto; }
.social-user-list { display: flex; flex-direction: column; }
.social-user-card {
  display: flex; align-items: center; gap: 16px; padding: 12px 24px;
  cursor: pointer; transition: 0.2s; border-bottom: 1px solid rgba(255,255,255,0.05);
}
.social-user-card:hover { background: rgba(255,255,255,0.05); }
.social-avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; border: 1px solid var(--border); }
.social-info { display: flex; flex-direction: column; }
.social-name { font-weight: 700; color: var(--text-primary); }
.social-type { font-size: 0.8rem; color: var(--text-muted); }
.empty-list-text { text-align: center; padding: 40px; color: var(--text-muted); }
</style>
