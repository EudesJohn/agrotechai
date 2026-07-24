<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { supabase } from '../supabase'
import { useAuthStore } from '../authStore'
import gsap from 'gsap'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// State
const chats = ref([])
const messages = ref([])
const newMessage = ref('')
const activeChatId = ref(null)
const chatPartner = ref(null)
const loading = ref(true)
const chatsLoading = ref(true)
const scrollContainer = ref(null)
const showMobileList = ref(true)
const chatError = ref(null)
const isProcessingPrefill = ref(false)

let chatsChannel = null
let msgChannel = null

const PLACEHOLDER_AVATAR = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 50'%3E%3Crect width='50' height='50' fill='%232a2a2a'/%3E%3Ccircle cx='25' cy='17' r='9' fill='%23555'/%3E%3Cpath d='M7 45a18 18 0 0 1 36 0' fill='%23555'/%3E%3C/svg%3E"

const buildChatListFromData = async (chatData) => {
  const chatList = []
  for (const chat of chatData) {
    const partnerId = chat.participants.find(p => p !== authStore.user.id)
    let partnerInfo = chat.partnerInfo
    if (!partnerInfo) {
      const { data: pData } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', partnerId)
        .single()
      partnerInfo = pData || { display_name: 'Utilisateur Inconnu' }
    }
    chatList.push({
      id: chat.id,
      ...chat,
      partnerId,
      partnerName: partnerInfo.display_name,
      partnerPic: partnerInfo.avatar_url,
      isOnline: partnerInfo.is_online || false,
      lastUpdate: chat.last_message_at,
      lastMessage: chat.last_message
    })
  }
  return chatList
}

// Load all chats for the current user
const loadChats = async () => {
  if (!authStore.user) return

  try {
    const { data: chatData, error } = await supabase
      .from('chats')
      .select('*')
      .contains('participants', [authStore.user.id])
      .order('last_message_at', { ascending: false })

    if (error) throw error

    chats.value = await buildChatListFromData(chatData || [])
    chatsLoading.value = false
    chatError.value = null

    // Auto-select chat if query param exists
    const targetUser = route.query.to || route.query.newChat;
    if (targetUser && !activeChatId.value && !isProcessingPrefill.value) {
      startChatWith(targetUser)

      if (route.query.prefill) {
         isProcessingPrefill.value = true
         newMessage.value = route.query.prefill

         setTimeout(async () => {
           if (activeChatId.value && newMessage.value) {
             await sendMessage()
             router.replace('/messages')
           }
           isProcessingPrefill.value = false
         }, 800)
      }
    }
  } catch (err) {
    console.error("Chats update error:", err)
    chatsLoading.value = false
    chatError.value = "Erreur de chargement des conversations."
  }

  // Subscribe to realtime changes (unsubscribe old first to avoid duplicates)
  if (chatsChannel) chatsChannel.unsubscribe()
  chatsChannel = supabase.channel('chats')
  chatsChannel.on('postgres_changes',
    { event: '*', schema: 'public', table: 'chats' },
    async () => {
      const { data: updatedChats } = await supabase
        .from('chats')
        .select('*')
        .contains('participants', [authStore.user.id])
        .order('last_message_at', { ascending: false })

      if (updatedChats) {
        chats.value = await buildChatListFromData(updatedChats)
      }
    }
  ).subscribe()
}

const startChatWith = async (partnerId) => {
  const myId = authStore.user.id
  const participants = [myId, partnerId].sort()
  const pgArray = `{${participants.join(',')}}`

  // Find existing chats where I'm a participant, filter client-side for partner
  const { data: myChats } = await supabase
    .from('chats')
    .select('id, participants')
    .contains('participants', [myId])

  let chatId
  const existing = (myChats || []).find(c =>
    Array.isArray(c.participants) && c.participants.includes(partnerId)
  )

  if (existing) {
    chatId = existing.id
  } else {
    // Create chat with PostgreSQL array literal
    const { data: newChat, error: createError } = await supabase
      .from('chats')
      .insert({ participants: pgArray })
      .select('id')
      .single()

    if (createError) {
      console.error("Chat creation error:", createError)
      return
    }
    chatId = newChat.id

    const { data: pData } = await supabase
      .from('profiles')
      .select('display_name, avatar_url')
      .eq('id', partnerId)
      .single()
    const profile = pData || {}

    if (!chats.value.find(c => c.id === chatId)) {
      chats.value.unshift({
        id: chatId,
        partnerId,
        partnerName: profile.display_name || 'Nouvel Ami',
        partnerPic: profile.avatar_url,
        lastMessage: 'Démarrer la conversation...',
        lastUpdate: new Date().toISOString()
      })
    }
  }

  selectChat(chatId, partnerId)
}

const selectChat = async (chatId, partnerId) => {
  if (msgChannel) msgChannel.unsubscribe()

  activeChatId.value = chatId
  showMobileList.value = false

  // Fetch full partner info
  const { data: pData } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', partnerId)
    .single()
  chatPartner.value = pData || { display_name: 'Utilisateur' }

  // Fetch initial messages
  const { data: msgData } = await supabase
    .from('chat_messages')
    .select('*')
    .eq('chat_id', chatId)
    .order('created_at', { ascending: true })
    .limit(100)

  messages.value = (msgData || []).map(m => ({
    id: m.id,
    senderId: m.sender_id,
    text: m.content,
    createdAt: m.created_at,
    ...m
  }))
  scrollToBottom()

  // Subscribe to new messages
  msgChannel = supabase.channel(`messages:${chatId}`)
  msgChannel.on('postgres_changes',
    { event: 'INSERT', schema: 'public', table: 'chat_messages', filter: `chat_id=eq.${chatId}` },
    (payload) => {
      const newMsg = {
        id: payload.new.id,
        senderId: payload.new.sender_id,
        text: payload.new.content,
        createdAt: payload.new.created_at,
        ...payload.new
      }
      messages.value.push(newMsg)
      scrollToBottom()
    }
  ).subscribe()
}

const sendMessage = async () => {
  if (!newMessage.value.trim() || !activeChatId.value) return

  const msg = newMessage.value
  const chatId = activeChatId.value
  newMessage.value = ''

  try {
    const participants = [authStore.user.id, chatPartner.value.id].sort()

    // Insert message (trigger updates chats.last_message automatically)
    const { error: msgError } = await supabase.from('chat_messages').insert({
      chat_id: chatId,
      sender_id: authStore.user.id,
      content: msg,
      message_type: 'text'
    })
    if (msgError) throw msgError
  } catch (err) {
    console.error("Chat Error:", err)
    newMessage.value = msg
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
}

onMounted(() => {
  if (authStore.user) {
    loadChats()
  }
  gsap.from(".messenger-layout", { opacity: 0, scale: 0.98, duration: 0.8, ease: "power3.out" })
})

// Watch for auth ready
watch(() => authStore.user, (newVal) => {
  if (newVal && !chats.value.length && chatsLoading.value) {
    loadChats()
  }
}, { immediate: true })

// Watch for direct message target changes
watch(() => route.query.to, (newTo) => {
  if (newTo) startChatWith(newTo)
})

onUnmounted(() => {
  if (chatsChannel) chatsChannel.unsubscribe()
  if (msgChannel) msgChannel.unsubscribe()
})

// Navigation help for mobile
const backToList = () => {
  showMobileList.value = true
  activeChatId.value = null
}
</script>

<template>
  <div class="chat-page">
    <div class="container full-height">
      <div class="messenger-layout glass-panel">
        <!-- Sidebar: Chat List -->
        <aside :class="['chat-sidebar', { 'mobile-hidden': !showMobileList }]">
          <div class="sidebar-header">
            <h2>Discussions</h2>
            <div class="search-box">
              <input type="text" placeholder="Rechercher..." />
            </div>
          </div>
          
          <div class="chat-list-scroll">
            <div v-if="chatsLoading" class="list-loader">
              <div class="mini-spinner-chat"></div>
              Chargement...
            </div>
            <div v-else-if="chatError" class="error-list">{{ chatError }}</div>
            <div v-else-if="chats.length === 0" class="empty-list">
              Aucune conversation pour le moment.
            </div>
            <div v-for="chat in chats" :key="chat.id" 
                 :class="['chat-item', { active: activeChatId === chat.id }]"
                 @click="selectChat(chat.id, chat.partnerId)">
              <div class="item-avatar">
                <img :src="chat.partnerPic || PLACEHOLDER_AVATAR" />
                <span v-if="chat.isOnline" class="online-indicator"></span>
              </div>
              <div class="item-info">
                <div class="item-head">
                  <span class="partner-name">{{ chat.partnerName }}</span>
                  <span class="chat-time">{{ chat.lastUpdate ? new Date(chat.lastUpdate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '' }}</span>
                </div>
                <p class="last-msg">{{ chat.lastMessage }}</p>
              </div>
            </div>
          </div>
        </aside>

        <!-- Main Window: Messages -->
        <main :class="['chat-window', { 'mobile-hidden': showMobileList }]">
          <template v-if="activeChatId">
            <header class="window-header">
              <button class="btn-back" @click="backToList">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
              </button>
              <div class="header-user" @click="router.push('/profile/' + chatPartner.id)">
                <img :src="chatPartner.avatar_url || '/avatar-placeholder.svg'" class="h-avatar" />
                <div class="h-info">
                  <h3>{{ chatPartner.display_name || 'Utilisateur' }}</h3>
                  <span class="h-status">En ligne</span>
                </div>
              </div>
            </header>

            <div class="messages-viewport" ref="scrollContainer">
               <div v-for="m in messages" :key="m.id" 
                    :class="['msg-line', m.senderId === authStore.user?.id ? 'mine' : 'theirs']">
                  <img v-if="m.senderId !== authStore.user?.id" :src="chatPartner.avatar_url || PLACEHOLDER_AVATAR" class="msg-mini-avatar" />
                  <div class="msg-bubble" :title="m.createdAt ? new Date(m.createdAt).toLocaleString() : ''">
                    {{ m.text }}
                  </div>
               </div>
               <div v-if="messages.length === 0" class="chat-start">
                 Dites bonjour à {{ chatPartner.display_name || chatPartner.displayName || 'votre contact' }} !
               </div>
            </div>

            <footer class="window-footer">
               <div class="input-area">
                 <button class="btn-media">
                   <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
                 </button>
                 <input v-model="newMessage" @keyup.enter="sendMessage" placeholder="Écrire un message..." />
                 <button class="btn-send-msg" @click="sendMessage" :disabled="!newMessage.trim()">
                   <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
                 </button>
               </div>
            </footer>
          </template>
          
          <div v-else class="no-chat-selected">
            <div class="centered-box">
              <div class="messenger-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="1.5" opacity="0.6"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <h2>AgroMessenger Elite</h2>
              <p>Sélectionnez un expert pour démarrer une discussion sécurisée.</p>
            </div>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page { padding-top: 120px; height: 100vh; background: var(--bg-deep); }
.full-height { height: calc(100vh - 160px); display: flex; flex-direction: column; }
.messenger-layout { flex: 1; display: flex; overflow: hidden; height: 100%; }

/* Sidebar */
.chat-sidebar { width: 360px; border-right: 1px solid var(--border); display: flex; flex-direction: column; background: rgba(255,255,255,0.02); }
.sidebar-header { padding: 25px; border-bottom: 1px solid var(--border); }
.sidebar-header h2 { font-size: 1.5rem; margin-bottom: 20px; color: var(--text-primary); }
.search-box input { background: rgba(255,255,255,0.05); border: none; border-radius: 12px; padding: 12px 16px; color: var(--text-primary); width: 100%; outline: none; }

.chat-list-scroll { flex: 1; overflow-y: auto; }
.chat-item { padding: 15px 25px; display: flex; align-items: center; gap: 15px; cursor: pointer; transition: background 200ms ease-out, border-color 200ms ease-out; border-left: 4px solid transparent; }
@media (hover: hover) and (pointer: fine) {
  .chat-item:hover { background: rgba(255,255,255,0.05); }
}
.chat-item:active { background: rgba(255,255,255,0.08); }
.chat-item.active { background: rgba(0, 230, 118, 0.08); border-left-color: var(--primary); }

.item-avatar { position: relative; }
.item-avatar img { width: 54px; height: 54px; border-radius: 50%; border: 2px solid var(--border); }
.online-indicator { position: absolute; bottom: 3px; right: 3px; width: 12px; height: 12px; background: #00e676; border: 2px solid #000; border-radius: 50%; }

.item-info { flex: 1; overflow: hidden; }
.item-head { display: flex; justify-content: space-between; margin-bottom: 4px; }
.partner-name { font-weight: 700; color: var(--text-primary); font-size: 1rem; }
.chat-time { font-size: 0.75rem; color: var(--text-muted); }
.last-msg { font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Chat Window */
.chat-window { flex: 1; display: flex; flex-direction: column; background: rgba(0,0,0,0.2); }
.window-header { padding: 15px 30px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 20px; background: rgba(255,255,255,0.01); }
.btn-back { display: none; background: transparent; border: none; color: var(--text-primary); cursor: pointer; transition: transform 120ms ease-out, color 200ms ease-out; }
.btn-back:active { transform: scale(0.9); }
.header-user { display: flex; align-items: center; gap: 15px; cursor: pointer; }
.h-avatar { width: 44px; height: 44px; border-radius: 50%; border: 2px solid var(--primary); }
.h-info h3 { margin: 0; font-size: 1.1rem; }
.h-status { font-size: 0.75rem; color: var(--primary); }

.messages-viewport { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 12px; }
.msg-line { display: flex; align-items: flex-end; gap: 10px; width: 100%; max-width: 80%; }
.msg-line.mine { align-self: flex-end; flex-direction: row-reverse; max-width: 80%; }
.msg-line.theirs { align-self: flex-start; }

.msg-mini-avatar { width: 28px; height: 28px; border-radius: 50%; }
.msg-bubble { 
  padding: 12px 18px; border-radius: 20px; font-size: 0.95rem; line-height: 1.4;
  position: relative;
}
.mine .msg-bubble { background: var(--primary); color: #000; border-bottom-right-radius: 4px; font-weight: 500; }
.theirs .msg-bubble { background: rgba(255,255,255,0.08); color: var(--text-primary); border-bottom-left-radius: 4px; }

.window-footer { padding: 20px 30px; border-top: 1px solid var(--border); }
.input-area { background: rgba(255,255,255,0.05); border-radius: 25px; padding: 5px 15px; display: flex; align-items: center; gap: 15px; }
.input-area input { flex: 1; background: transparent; border: none; color: var(--text-primary); padding: 12px 5px; outline: none; font-size: 0.95rem; }
.btn-media { background: transparent; border: none; color: var(--text-muted); cursor: pointer; display: flex; transition: color 200ms ease-out, transform 120ms ease-out; }
.btn-media:active { transform: scale(0.9); }
@media (hover: hover) and (pointer: fine) {
  .btn-media:hover { color: var(--primary); }
}
.btn-send-msg { background: transparent; border: none; color: var(--primary); cursor: pointer; display: flex; padding: 8px; border-radius: 50%; transition: background 200ms ease-out, transform 120ms ease-out; }
.btn-send-msg:disabled { opacity: 0.3; cursor: default; }
.btn-send-msg:active:not(:disabled) { transform: scale(0.9); }
@media (hover: hover) and (pointer: fine) {
  .btn-send-msg:not(:disabled):hover { background: rgba(0, 230, 118, 0.1); }
}

.no-chat-selected { flex: 1; display: flex; align-items: center; justify-content: center; text-align: center; }
.centered-box { max-width: 400px; opacity: 0.6; }
.messenger-icon { margin-bottom: 20px; display: flex; justify-content: center; }

@media (max-width: 768px) {
  .chat-sidebar { width: 100%; }
  .chat-window { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; background: var(--bg-dark); }
  .mobile-hidden { display: none !important; }
  .btn-back { display: block; }
}

.mini-spinner-chat {
  width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.1);
  border-top-color: var(--primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; margin-bottom: 10px;
}
.list-loader { display: flex; flex-direction: column; align-items: center; padding: 40px; color: var(--text-muted); }
.error-list { padding: 20px; color: var(--danger); font-size: 0.85rem; text-align: center; }

@keyframes spin { to { transform: rotate(360deg); } }
</style>
