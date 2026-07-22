<template>
  <div class="community-page container">
    <div class="community-layout">
      <!-- Left Sidebar: Profile Snippet -->
      <aside class="side-panel left">
        <div class="mini-profile glass-panel" @click="router.push('/profile')" style="cursor: pointer">
          <div class="p-cover"></div>
          <div class="p-avatar">
             <img v-if="authStore.profile?.photoURL" :src="authStore.profile.photoURL" />
             <svg v-else width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          </div>
          <h3>{{ authStore.profile?.displayName || 'Expert Agrotech' }}</h3>
          <p class="p-bio">{{ authStore.profile?.bio || "Passionné par l'innovation agricole." }}</p>
          <div class="p-stats">
            <div class="s-item"><span>{{ authStore.profile?.followersCount || 0 }}</span> abonnés</div>
            <div class="s-item"><span>{{ authStore.profile?.followingCount || 0 }}</span> suivi(s)</div>
          </div>
        </div>

        <div class="trending glass-panel mt-24">
          <h4>Sujets Brûlants</h4>
          <ul class="trend-list">
            <li>#MainsVertes</li>
            <li>#CotonBénin</li>
            <li>#IA_Agricole</li>
          </ul>
        </div>
      </aside>

      <!-- Center: Feed -->
      <main class="feed-area">
        <!-- Modern Search Bar -->
        <div class="community-search-container mb-32">
          <div class="search-box-modern glass-panel" :class="{ 'is-focused': isSearchFocused }">
            <div class="search-input-inner">
               <svg class="search-icon-anim" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
               <input 
                 type="text" 
                 v-model="searchQuery" 
                 @input="searchUsers" 
                 @focus="isSearchFocused = true"
                 @blur="isSearchFocused = false"
                 placeholder="Trouver un expert, un producteur ou une commune..." 
               />
               <div v-if="searchQuery" class="search-clear" @click="searchQuery = ''; searchResults = []">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
               </div>
            </div>
            
            <Transition name="slide-up">
              <div v-if="searchResults.length > 0" class="modern-search-results shadow-2xl glass-panel">
                  <div class="results-header">Experts trouvés ({{ searchResults.length }})</div>
                  <div class="results-scroll">
                    <div v-for="user in searchResults" :key="user.uid" class="search-wrap">
                      <div @click.stop="goToProfile(user.uid)" class="search-item-modern cursor-pointer">
                         <div class="avatar-ring">
                           <img :src="user.photoURL || 'https://via.placeholder.com/40'" />
                         </div>
                         <div class="s-info">
                            <div class="s-name">{{ user.displayName }}</div>
                            <div class="s-loc">{{ user.location || 'Bénin' }} • {{ user.user_type }}</div>
                         </div>
                         <button 
                           class="btn sm-round" 
                           :class="user.isFollowing ? 'btn-ghost' : 'btn-primary'"
                           @click.prevent.stop="toggleFollow(user.uid)"
                           :disabled="followLoading[user.uid]"
                         >
                            <span v-if="followLoading[user.uid]" class="mini-spinner-btn"></span>
                            <template v-else>
                              {{ user.isFollowing ? 'Suivi' : 'Suivre' }}
                            </template>
                         </button>

                          <button 
                            v-if="authStore.user && user.uid !== authStore.user.uid"
                            class="btn btn-ghost sm-round ml-8"
                            @click.stop="openQuickMsg(user)"
                            title="Envoyer un message"
                          >
                             <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                          </button>
                      </div>
                    </div>
                  </div>
              </div>
            </Transition>
          </div>
        </div>

        <!-- Create Post -->
        <div class="create-post glass-panel mb-32">
          <div class="cp-top">
            <div class="cp-avatar">
               <img v-if="authStore.profile?.photoURL" :src="authStore.profile.photoURL" class="tiny-avatar" />
               <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <textarea v-model="newPost.content" placeholder="Partagez vos conseils, réussites ou questions..."></textarea>
          </div>
          <div class="cp-actions">
            <button class="cp-btn"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg> Photo</button>
            <button class="btn btn-primary" @click="publishPost" :disabled="!newPost.content || publishing">
               {{ publishing ? 'Publication...' : 'Publier' }}
            </button>
          </div>
        </div>

        <!-- Feed List -->
        <div class="posts-list">
          <div v-if="loading" class="text-center p-32">
            <div class="spinner"></div>
            <p>Chargement du flux Cloud...</p>
          </div>
          
          <div v-for="post in posts" :key="post.id" class="post-card glass-panel mb-24 animate-post">
            <div class="post-head">
              <div @click.stop="goToProfile(post.authorId)" class="post-avatar-link cursor-pointer">
                <img :src="post.authorPic || 'https://via.placeholder.com/50'" class="post-avatar" />
              </div>
              <div class="post-meta">
                <div @click.stop="goToProfile(post.authorId)" class="post-author-name cursor-pointer">
                  <h4>{{ post.authorName }}</h4>
                </div>
                <span class="post-date text-muted">{{ formatDate(post.createdAt) }}</span>
              </div>

               <!-- Quick Message Trigger -->
               <button 
                 v-if="authStore.user && post.authorId !== authStore.user.uid"
                 class="btn-quick-msg"
                 @click.stop="openQuickMsg({ uid: post.authorId, displayName: post.authorName, photoURL: post.authorPic })"
                 title="Envoyer un message"
               >
                 <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
               </button>

              <div v-if="authStore.user && post.authorId === authStore.user.uid" class="post-menu">
                 <button class="btn-menu" @click="post.showMenu = !post.showMenu">⋮</button>
                 <div v-if="post.showMenu" class="menu-dropdown glass-panel">
                   <button @click="startEdit(post)">Modifier</button>
                   <button class="danger" @click="deletePost(post.id)">Supprimer</button>
                 </div>
              </div>
            </div>
            
            <div class="post-content">
              <div v-if="post.isEditing" class="edit-mode mb-12">
                <textarea v-model="post.editContent" class="edit-textarea"></textarea>
                <div class="edit-actions mt-8">
                  <button class="btn btn-primary sm" @click="saveEdit(post)">Sauvegarder</button>
                  <button class="btn btn-ghost sm" @click="post.isEditing = false">Annuler</button>
                </div>
              </div>
              <p v-else>{{ post.content }}</p>
              <img v-if="post.image_url" :src="post.image_url" class="post-img" />
            </div>

            <div class="post-interactions">
              <div class="i-summary">
                <div class="reactions-summary">
                   <span v-for="(count, type) in post.reactionsCount" :key="type" v-show="count > 0" class="r-badge">
                     {{ type }} {{ count }}
                   </span>
                </div>
                <span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  {{ post.commentsCount || 0 }} commentaires
                </span>
              </div>
              <div class="i-actions">
                <!-- Reaction Button with Popover -->
                <div class="reaction-trigger" @mouseenter="showPop(post)" @mouseleave="hidePop(post)">
                  <button class="i-btn" :class="{ 'active-r': post.userReaction }" @click="toggleReaction(post.id, '🌱')">
                    <span v-if="post.userReaction">{{ post.userReaction }}</span>
                    <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.7 0l-1.1 1-1-1a5.5 5.5 0 0 0-7.7 7.7l1 1 7.8 7.8 7.7-7.7 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg> 
                    {{ post.userReaction ? 'Réagi' : 'Réagir' }}
                  </button>
                  <div v-if="post.showPop" class="reaction-popover glass-panel" @mouseenter="showPop(post)">
                    <span v-for="emoji in ['🌱', '🚜', '🍎', '💧', '☀️']" :key="emoji" @click="toggleReaction(post.id, emoji)">{{ emoji }}</span>
                  </div>
                </div>

                <button class="i-btn" @click="toggleComments(post.id)">
                   <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                   Commenter
                </button>
                <button class="i-btn" @click="sharePost(post)">
                   <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13"/></svg>
                   Partager
                </button>
              </div>

              <!-- Comments Section -->
              <div v-if="post.showComments" class="comments-drawer mt-16 animate-fade">
                <div class="comments-list">
                  <div v-for="c in post.comments.filter(cm => !cm.parentId)" :key="c.id" class="c-group">
                    <div class="c-item">
                      <div @click.stop="goToProfile(c.authorId)" class="c-avatar-link cursor-pointer">
                        <img :src="c.authorPic || 'https://via.placeholder.com/30'" class="c-avatar" />
                      </div>
                      <div class="c-body">
                        <div @click.stop="goToProfile(c.authorId)" class="c-author-name cursor-pointer">
                          <h6>{{ c.authorName }}</h6>
                        </div>
                        <p>{{ c.content }}</p>
                        <button class="btn-reply" @click="post.replyTo = c.id">Répondre</button>
                      </div>
                    </div>
                    <!-- Replies -->
                    <div class="replies-list ml-32 mt-8">
                       <div v-for="r in post.comments.filter(rm => rm.parentId === c.id)" :key="r.id" class="c-item sm-gap">
                         <div @click.stop="goToProfile(r.authorId)" class="c-avatar-link cursor-pointer">
                           <img :src="r.authorPic || 'https://via.placeholder.com/25'" class="c-avatar sm" />
                         </div>
                         <div class="c-body sm-pad">
                           <div @click.stop="goToProfile(r.authorId)" class="c-author-name cursor-pointer">
                             <h6>{{ r.authorName }}</h6>
                           </div>
                           <p>{{ r.content }}</p>
                         </div>
                       </div>
                    </div>
                  </div>
                </div>
                <div class="c-input-box mt-16">
                  <div v-if="post.replyTo" class="reply-indicator">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
                    Réponse à {{ post.comments.find(c => c.id === post.replyTo)?.authorName }}
                    <button @click="post.replyTo = null">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
                    </button>
                  </div>
                  <input v-model="post.newComment" @keyup.enter="addComment(post.id)" :placeholder="post.replyTo ? 'Votre réponse...' : 'Ajouter un commentaire...'" />
                  <button class="btn btn-primary sm" @click="addComment(post.id)">Envoyer</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <aside class="side-panel right">
        <!-- Suggestions logic will go here -->
      </aside>
    </div>

    <!-- Quick Message Modal -->
    <QuickMessageModal 
      :show="showQuickMsg"
      :partnerId="msgPartner?.uid"
      :partnerName="msgPartner?.displayName"
      :partnerPic="msgPartner?.photoURL"
      @close="showQuickMsg = false"
      @sent="onMessageSent"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../authStore'
import { db } from '../firebase'
import QuickMessageModal from '../components/QuickMessageModal.vue'
import { 
  collection, 
  addDoc, 
  getDocs, 
  query, 
  orderBy, 
  limit, 
  where, 
  serverTimestamp,
  doc,
  updateDoc,
  increment,
  setDoc,
  getDoc
} from 'firebase/firestore'
import gsap from 'gsap'

const router = useRouter()
const authStore = useAuthStore()

const posts = ref([])
const loading = ref(true)
const publishing = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const isSearchFocused = ref(false)
const followersCount = ref(0)
const followingCount = ref(0)

// Quick Message State
const showQuickMsg = ref(false)
const msgPartner = ref(null)

const openQuickMsg = (user) => {
  msgPartner.value = user
  showQuickMsg.value = true
}

const onMessageSent = () => {
  // Optional: show a snackbar or notification
  console.log("Message sent successfully!")
}

// Hover management
let popTimeout = null
const showPop = (post) => {
  if (popTimeout) clearTimeout(popTimeout)
  post.showPop = true
}
const hidePop = (post) => {
  popTimeout = setTimeout(() => {
    post.showPop = false
  }, 300)
}

const newPost = reactive({
  content: '',
  image_url: ''
})

const fetchPosts = async () => {
  try {
    const q = query(collection(db, 'posts'), orderBy('createdAt', 'desc'), limit(20))
    const querySnapshot = await getDocs(q)
    posts.value = await Promise.all(querySnapshot.docs.map(async docSnapshot => {
      const data = docSnapshot.data()
      const postId = docSnapshot.id
      
      // Check user reaction
      let userReaction = null
      if (authStore.user) {
        const rSnap = await getDoc(doc(db, 'posts', postId, 'reactions', authStore.user.uid))
        if (rSnap.exists()) userReaction = rSnap.data().type
      }

      return { 
        id: postId, 
        ...data, 
        showPop: false, 
        showComments: false, 
        comments: [], 
        newComment: '',
        replyTo: null,
        userReaction,
        reactionsCount: data.reactionsCount || {},
        showMenu: false,
        isEditing: false,
        editContent: data.content,
        views: data.views || 0
      }
    }))
    
    setTimeout(() => {
      gsap.from(".animate-post", { y: 20, opacity: 0, duration: 0.8, stagger: 0.1, ease: "power2.out" })
    }, 100)
  } catch (err) {
    console.error("Erreur Firestore Posts", err)
  } finally {
    loading.value = false
  }
}

const publishPost = async () => {
  if (!authStore.user) return
  publishing.value = true
  try {
    const postData = {
      authorId: authStore.user.uid,
      authorName: authStore.profile?.displayName || authStore.user.displayName || 'Expert',
      authorPic: authStore.profile?.photoURL || authStore.user.photoURL || '',
      content: newPost.content,
      image_url: newPost.image_url,
      createdAt: serverTimestamp(),
      likesCount: 0,
      commentsCount: 0
    }
    await addDoc(collection(db, 'posts'), postData)
    newPost.content = ''
    newPost.image_url = ''
    fetchPosts()
  } catch (err) {
    alert("Erreur publication Firestore.")
  } finally {
    publishing.value = false
  }
}

const searchUsers = async () => {
  if (searchQuery.value.length < 2) {
    searchResults.value = []
    return
  }
  try {
    // Normalization: capitalize first letter for better matching in Firestore
    const term = searchQuery.value.charAt(0).toUpperCase() + searchQuery.value.slice(1)
    
    const q = query(
      collection(db, 'users'), 
      where('displayName', '>=', term),
      where('displayName', '<=', term + '\uf8ff'),
      limit(5)
    )
    const snap = await getDocs(q)
    const results = snap.docs.map(d => ({ uid: d.id, ...d.data() }))
    
    // Check follow status for each result
    if (authStore.user) {
      for (const res of results) {
        const fSnap = await getDoc(doc(db, 'follows', `${authStore.user.uid}_${res.uid}`))
        res.isFollowing = fSnap.exists()
      }
    }
    searchResults.value = results
  } catch (err) {
    console.error("Erreur recherche Firestore", err)
  }
}

const toggleReaction = async (postId, type) => {
  if (!authStore.user) return
  const post = posts.value.find(p => p.id === postId)
  if (!post) return

  try {
    const reactionRef = doc(db, 'posts', postId, 'reactions', authStore.user.uid)
    const postRef = doc(db, 'posts', postId)
    
    if (post.userReaction === type) {
      // Remove reaction
      await deleteDoc(reactionRef)
      await updateDoc(postRef, {
        [`reactionsCount.${type}`]: increment(-1)
      })
      post.reactionsCount[type] -= 1
      post.userReaction = null
    } else {
      // Switch or add reaction
      const oldType = post.userReaction
      await setDoc(reactionRef, { type, userId: authStore.user.uid })
      
      const updateData = { [`reactionsCount.${type}`]: increment(1) }
      if (oldType) updateData[`reactionsCount.${oldType}`] = increment(-1)
      
      await updateDoc(postRef, updateData)
      
      post.reactionsCount[type] = (post.reactionsCount[type] || 0) + 1
      if (oldType) post.reactionsCount[oldType] -= 1
      post.userReaction = type
    }
  } catch (err) {
    console.error("Reaction error", err)
  }
}

const toggleComments = async (postId) => {
  const post = posts.value.find(p => p.id === postId)
  if (!post) return
  post.showComments = !post.showComments
  if (post.showComments) {
    if (post.comments.length === 0) {
      const q = query(collection(db, 'posts', postId, 'comments'), orderBy('createdAt', 'asc'))
      const snap = await getDocs(q)
      post.comments = snap.docs.map(d => ({ id: d.id, ...d.data() }))
    }
    // Track view
    try {
      await updateDoc(doc(db, 'posts', postId), { views: increment(1) })
      post.views = (post.views || 0) + 1
    } catch (e) {}
  }
}

const addComment = async (postId) => {
  if (!authStore.user) return
  const post = posts.value.find(p => p.id === postId)
  if (!post || !post.newComment) return

  try {
    const commentData = {
      authorId: authStore.user.uid,
      authorName: authStore.profile?.displayName || 'Expert',
      authorPic: authStore.profile?.photoURL || '',
      content: post.newComment,
      parentId: post.replyTo || null,
      createdAt: serverTimestamp()
    }
    const docRef = await addDoc(collection(db, 'posts', postId, 'comments'), commentData)
    await updateDoc(doc(db, 'posts', postId), { commentsCount: increment(1) })
    
    post.comments.push({ id: docRef.id, ...commentData, createdAt: new Date() })
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
    text: `${post.content.substring(0, 100)}... \n\nLisez la suite sur Agrotech AI :`,
    url: postUrl
  }
  
  if (navigator.share) {
    try {
      await navigator.share(shareData)
    } catch (err) {
      console.log("Share cancelled or failed")
    }
  } else {
    await navigator.clipboard.writeText(`${shareData.text}\n${shareData.url}`)
    alert("Lien et message copiés dans le presse-papier !")
  }
}

const followLoading = ref({})

const toggleFollow = async (targetUid) => {
  if (!authStore.user) {
    alert("Veuillez vous connecter pour suivre cet expert.")
    return
  }
  if (targetUid === authStore.user.uid) return
  if (followLoading.value[targetUid]) return
  
  const followId = `${authStore.user.uid}_${targetUid}`
  const followRef = doc(db, 'follows', followId)
  const user = searchResults.value.find(u => u.uid === targetUid)
  const isCurrentlyFollowing = user?.isFollowing
  
  followLoading.value[targetUid] = true
  
  try {
    if (isCurrentlyFollowing) {
      await deleteDoc(followRef)
      await updateDoc(doc(db, 'users', targetUid), { followersCount: increment(-1) })
      await updateDoc(doc(db, 'users', authStore.user.uid), { followingCount: increment(-1) })
      if (user) user.isFollowing = false
    } else {
      await setDoc(followRef, {
        followerId: authStore.user.uid,
        followedId: targetUid,
        createdAt: serverTimestamp()
      })
      if (user) user.isFollowing = true
    }
  } catch (err) {
    console.error("DEBUG FOLLOW ERROR DETAILS:", {
      code: err.code,
      message: err.message,
      targetUid,
      currentUser: authStore.user?.uid
    })
    if (err.code === 'failed-precondition') {
      alert("Index Firestore manquant pour les abonnements.")
    } else {
      alert("Une erreur est survenue lors du changement d'abonnement. Vérifiez votre connexion.")
    }
  } finally {
    followLoading.value[targetUid] = false
  }
}

const goToProfile = (uid) => {
  router.push(`/profile/${uid}`)
}

const startEdit = (post) => {
  post.editContent = post.content
  post.isEditing = true
  post.showMenu = false
}

const saveEdit = async (post) => {
  try {
    await updateDoc(doc(db, 'posts', post.id), { content: post.editContent })
    post.content = post.editContent
    post.isEditing = false
  } catch (err) {
    console.error("Edit error", err)
  }
}

const deletePost = async (postId) => {
  if (!confirm("Supprimer cette publication ?")) return
  try {
    await deleteDoc(doc(db, 'posts', postId))
    posts.value = posts.value.filter(p => p.id !== postId)
  } catch (err) {
    console.error("Delete error", err)
  }
}

const formatDate = (ts) => {
  if (!ts) return 'À l\'instant'
  const d = ts.toDate ? ts.toDate() : new Date(ts)
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  fetchPosts()
})
</script>

<style scoped>
/* Les styles restent identiques à la version précédente */
.community-page { padding-top: 130px; min-height: 100vh; padding-bottom: 50px; }
.community-layout { display: grid; grid-template-columns: 280px 1fr 300px; gap: 32px; align-items: start; }
.side-panel { position: sticky; top: 130px; }

.btn-quick-msg {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--primary);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: 0.3s;
  margin-left: auto;
  margin-right: 10px;
}
.btn-quick-msg:hover {
  background: var(--primary);
  color: #000;
  transform: scale(1.1);
  box-shadow: 0 0 15px var(--primary-glow);
}

.post-menu { position: relative; }
.btn-menu { background: transparent; border: none; color: var(--text-primary); font-size: 1.2rem; cursor: pointer; padding: 0 10px; }
.menu-dropdown { 
  position: absolute; right: 0; top: 30px; width: 140px; 
  display: flex; flex-direction: column; z-index: 100; 
  border-radius: 8px; overflow: hidden; background: rgba(20,20,20,0.95);
  border: 1px solid var(--border);
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.menu-dropdown button { padding: 12px 16px; background: transparent; border: none; color: #fff; text-align: left; font-size: 0.9rem; cursor: pointer; transition: 0.2s; }
.menu-dropdown button:hover { background: rgba(255,255,255,0.1); }
.menu-dropdown button.danger { color: #ff5252; }

.edit-textarea {
  width: 100%; min-height: 100px; background: rgba(0,0,0,0.3);
  border: 1px solid var(--primary); border-radius: 8px; color: var(--text-primary);
  padding: 12px; font-family: inherit; resize: vertical; outline: none; margin-bottom: 12px;
}
.edit-actions { display: flex; gap: 10px; }

.mini-profile { overflow: hidden; padding: 0; }
.p-cover { height: 80px; background: linear-gradient(135deg, var(--primary), var(--accent)); }
.p-avatar { 
  width: 70px; height: 70px; border-radius: 50%; background: var(--bg-dark); 
  border: 4px solid var(--bg-dark); margin: -35px auto 16px; 
  display: flex; align-items: center; justify-content: center; font-size: 2rem; overflow: hidden;
}
.p-avatar img { width: 100%; height: 100%; object-fit: cover; }
.tiny-avatar { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
.mini-profile h3 { text-align: center; font-size: 1.1rem; margin-bottom: 4px; }
.p-bio { text-align: center; font-size: 0.85rem; color: var(--text-muted); padding: 0 16px; margin-bottom: 20px; }
.p-stats { display: flex; border-top: 1px solid var(--border); padding: 16px 0; }
.s-item { flex: 1; text-align: center; font-size: 0.8rem; color: var(--text-muted); }
.s-item span { display: block; color: var(--text-primary); font-weight: 800; font-size: 1rem; }
h4 { font-size: 1rem; margin-bottom: 20px; color: var(--text-primary); font-family: 'Syne', sans-serif; }
.trend-list { list-style: none; display: flex; flex-direction: column; gap: 12px; }
.trend-list li { color: var(--primary); font-weight: 700; font-size: 0.9rem; cursor: pointer; }
.search-input-wrapper { 
  display: flex; align-items: center; gap: 12px; padding: 4px 16px; 
  background: rgba(255,255,255,0.05); border-radius: 12px; border: 1px solid var(--border);
}
.search-input-wrapper input { border: none; background: transparent; padding: 12px 0; }
.search-box { position: relative; }
.search-results { 
  position: absolute; top: calc(100% + 10px); left: 0; width: 100%; 
  background: var(--bg-darker); border: 1px solid var(--border); border-radius: 12px; z-index: 100;
  max-height: 400px; overflow-y: auto;
}
.search-item { 
  display: flex; align-items: center; gap: 16px; padding: 16px; 
  border-bottom: 1px solid var(--border); cursor: pointer; transition: 0.3s;
}
.search-item:hover { background: rgba(255,255,255,0.05); }
.search-item img { width: 45px; height: 45px; border-radius: 50%; object-fit: cover; }
.s-name { font-weight: 700; color: var(--text-primary); }
.s-loc { font-size: 0.8rem; color: var(--text-muted); }
.cp-top { display: flex; gap: 16px; padding: 24px 24px 0; }
.cp-avatar { width: 40px; height: 40px; border-radius: 50%; background: var(--border); display: flex; align-items: center; justify-content: center; }
.create-post textarea {
  flex: 1; border: none; background: transparent; padding: 10px 0;
  resize: none; min-height: 80px; font-size: 1.1rem; color: var(--text-primary);
}
.cp-actions { 
  display: flex; justify-content: space-between; align-items: center; 
  padding: 16px 24px; border-top: 1px solid var(--border); margin-top: 16px;
}
.cp-btn { 
  display: flex; align-items: center; gap: 8px; background: transparent; 
  border: none; color: var(--text-muted); font-weight: 600; cursor: pointer;
}
.post-card { padding: 24px; }
.post-head { display: flex; gap: 16px; margin-bottom: 20px; }
.post-avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; }
.post-meta h4 { margin: 0 0 2px; font-size: 1.1rem; }
.post-author-name, .c-author-name { text-decoration: none; color: inherit; }
.post-author-name:hover h4, .c-author-name:hover h6 { color: var(--primary); }

.post-date { font-size: 0.8rem; }
.post-content p { font-size: 1.05rem; line-height: 1.6; margin-bottom: 16px; }
.post-img { width: 100%; border-radius: 12px; margin-bottom: 16px; border: 1px solid var(--border); }
.cursor-pointer { cursor: pointer; }
.post-interactions { border-top: 1px solid var(--border); padding-top: 16px; position: relative; }
.i-summary { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px; }
.reactions-summary { display: flex; gap: 8px; }
.r-badge { background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 100px; border: 1px solid var(--border); }
.i-actions { display: flex; justify-content: space-around; border-top: 1px solid var(--border); padding-top: 12px; }
.i-btn { 
  display: flex; align-items: center; gap: 8px; background: transparent; 
  border: none; color: var(--text-muted); font-weight: 700; cursor: pointer;
  transition: 0.3s;
}
.i-btn:hover, .i-btn.active-r { color: var(--primary); }

/* Reaction Popover */
.reaction-trigger { position: relative; }
.reaction-popover {
  position: absolute; bottom: 100%; left: 0; display: flex; gap: 12px; 
  padding: 12px 16px; border-radius: 40px; margin-bottom: 10px; z-index: 10;
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}
.reaction-popover span { 
  font-size: 1.5rem; cursor: pointer; transition: 0.2s; 
}
.reaction-popover span:hover { transform: scale(1.3); }

/* Comments */
.comments-drawer { border-top: 1px solid var(--border); padding-top: 16px; }
.c-item { display: flex; gap: 12px; margin-bottom: 16px; }
.c-avatar { width: 32px; height: 32px; border-radius: 50%; }
.c-body { background: rgba(255,255,255,0.03); padding: 10px 16px; border-radius: 12px; flex: 1; }
.c-body h6 { margin: 0 0 4px; font-size: 0.9rem; color: var(--text-primary); }
.c-body p { margin: 0; font-size: 0.9rem; line-height: 1.4; color: var(--text-muted); }
.btn-reply { background: transparent; border: none; color: var(--primary); font-size: 0.75rem; cursor: pointer; padding: 4px 0; margin-top: 4px; font-weight: 600; }
.btn-reply:hover { text-decoration: underline; }

.ml-32 { margin-left: 32px; }
.sm-gap { margin-bottom: 8px; }
.sm-pad { padding: 6px 12px; }
.c-avatar.sm { width: 24px; height: 24px; }

.reply-indicator { display: flex; justify-content: space-between; align-items: center; background: rgba(0,230,118,0.1); padding: 4px 12px; border-radius: 4px; font-size: 0.8rem; color: var(--primary); margin-bottom: 8px; border-left: 3px solid var(--primary); }
.reply-indicator button { background: transparent; border: none; color: var(--primary); font-size: 1.2rem; cursor: pointer; }

.c-input-box { display: flex; flex-direction: column; gap: 8px; }
.c-input-box input {
  flex: 1; background: rgba(0,0,0,0.2); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 16px; color: var(--text-primary);
}

.animate-fade { animation: fadeIn 0.4s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* Modern Search styles */
.search-box-modern {
  position: relative;
  padding: 8px;
  border-radius: 20px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--border);
  background: rgba(255,255,255,0.03);
}

.search-box-modern.is-focused {
  border-color: var(--primary);
  box-shadow: 0 0 30px var(--primary-glow);
  transform: translateY(-2px);
  background: rgba(0, 230, 118, 0.05);
}

.search-input-inner {
  display: flex;
  align-items: center;
  padding: 10px 15px;
  gap: 15px;
}

.search-icon-anim {
  color: var(--primary);
  transition: transform 0.3s;
}

.is-focused .search-icon-anim {
  transform: rotate(90deg) scale(1.1);
}

.search-input-inner input {
  background: transparent !important;
  border: none !important;
  color: var(--text-primary) !important;
  font-size: 1.05rem !important;
  width: 100% !important;
  outline: none !important;
  font-weight: 500 !important;
}

.search-clear {
  color: var(--text-muted);
  cursor: pointer;
  padding: 5px;
  border-radius: 50%;
  transition: 0.3s;
}
.search-clear:hover { background: rgba(255,255,255,0.1); color: var(--text-primary); }

.modern-search-results {
  position: absolute;
  top: 110%;
  left: 0;
  width: 100%;
  z-index: 1000;
  max-height: 400px;
  overflow: hidden;
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  border: 1px solid var(--border);
}

.results-header {
  padding: 15px 20px;
  font-size: 0.8rem;
  font-weight: 800;
  text-transform: uppercase;
  color: var(--primary);
  letter-spacing: 2px;
  border-bottom: 1px solid var(--border);
}

.results-scroll {
  max-height: 330px;
  overflow-y: auto;
}

.search-item-modern {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 20px;
  text-decoration: none;
  transition: 0.3s;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.search-item-modern:hover {
  background: rgba(255, 255, 255, 0.05);
}

.avatar-ring {
  width: 45px;
  height: 45px;
  border-radius: 50%;
  padding: 2px;
  background: linear-gradient(45deg, var(--primary), var(--secondary));
}

.avatar-ring img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: #000;
  padding: 2px;
  object-fit: cover !important;
}

.sm-round {
  border-radius: 100px !important;
  padding: 6px 15px !important;
  font-size: 0.75rem !important;
  font-weight: 800 !important;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(10px); }

@media (max-width: 1100px) {
  .community-layout { grid-template-columns: 240px 1fr; }
  .side-panel.right { display: none; }
}

@media (max-width: 768px) {
  .community-page { padding-top: 100px; }
  .community-layout { grid-template-columns: 1fr; gap: 20px; }
  .side-panel.left { display: none; }
  .post-header { padding: 15px; }
  .post-content { padding: 0 15px; }
  .i-actions { padding: 10px 5px; }
  .i-btn span { display: none; } /* Hide text on mobile to save space */
  .i-btn { padding: 10px; }
}

@keyframes spin { to { transform: rotate(360deg); } }
.mini-spinner-btn { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; }
</style>
