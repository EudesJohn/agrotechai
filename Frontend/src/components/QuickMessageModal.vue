<script setup>
import { ref } from 'vue'
import { supabase } from '../supabase'
import { useAuthStore } from '../authStore'

const props = defineProps({
  show: Boolean,
  partnerId: String,
  partnerName: String,
  partnerPic: String
})

const emit = defineEmits(['close', 'sent'])
const authStore = useAuthStore()
const message = ref('')
const loading = ref(false)

const PLACEHOLDER_AVATAR = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 50 50'%3E%3Crect width='50' height='50' fill='%232a2a2a'/%3E%3Ccircle cx='25' cy='17' r='9' fill='%23555'/%3E%3Cpath d='M7 45a18 18 0 0 1 36 0' fill='%23555'/%3E%3C/svg%3E"

const handleSend = async () => {
  if (!message.value.trim() || !props.partnerId || !authStore.user) return

  loading.value = true
  try {
    const myId = authStore.user.id
    const partnerId = props.partnerId
    const participants = [myId, partnerId].sort()
    // Format PostgreSQL array literal {uuid1,uuid2} (évite les 400 du client JS)
    const pgArray = `{${participants.join(',')}}`

    // 1. Chercher un chat existant via un filtre simple (un seul participant)
    // puis filtrer côté client pour l'autre participant
    const { data: myChats, error: searchError } = await supabase
      .from('chats')
      .select('id, participants')
      .contains('participants', [myId])

    if (searchError) throw searchError

    let chatId
    const existing = (myChats || []).find(c =>
      Array.isArray(c.participants) && c.participants.includes(partnerId)
    )

    if (existing) {
      chatId = existing.id
    } else {
      // 2. Créer un nouveau chat avec le format PostgreSQL array
      const { data: newChat, error: createError } = await supabase
        .from('chats')
        .insert({ participants: pgArray })
        .select('id')
        .single()
      if (createError) throw createError
      chatId = newChat.id
    }

    // 3. Insérer le message avec vérification d'erreur
    const { error: msgError } = await supabase.from('chat_messages').insert({
      chat_id: chatId,
      sender_id: myId,
      content: message.value,
      message_type: 'text',
    })
    if (msgError) throw msgError

    message.value = ''
    emit('sent')
    emit('close')
  } catch (err) {
    console.error("Error sending quick message:", err)
    alert("Erreur lors de l'envoi du message. Veuillez réessayer.")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Transition name="fade">
    <div v-if="show" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-content glass-panel animate-pop">
        <div class="modal-header">
          <div class="user-info">
            <img :src="partnerPic || PLACEHOLDER_AVATAR" class="avatar" />
            <div>
              <h3>Message à {{ partnerName }}</h3>
              <span class="status">Expert Agrotech</span>
            </div>
          </div>
          <button class="btn-close" @click="emit('close')">×</button>
        </div>
        
        <div class="modal-body">
          <textarea 
            v-model="message" 
            placeholder="Écrivez votre message ici..."
            :disabled="loading"
            autofocus
          ></textarea>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="emit('close')" :disabled="loading">Annuler</button>
          <button class="btn btn-primary" @click="handleSend" :disabled="loading || !message.trim()">
            <span v-if="loading" class="spinner-small"></span>
            <span v-else>Envoyer</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.85); backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center; z-index: 2000;
  padding: 20px;
}
.modal-content {
  width: 100%; max-width: 500px; border-radius: 20px; overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}
.modal-header {
  padding: 24px; border-bottom: 1px solid rgba(255,255,255,0.08);
  display: flex; justify-content: space-between; align-items: center;
}
.user-info { display: flex; align-items: center; gap: 14px; }
.avatar { width: 48px; height: 48px; border-radius: 12px; object-fit: cover; }
.user-info h3 { font-size: 1.1rem; margin: 0; color: #fff; }
.status { font-size: 0.8rem; color: var(--primary); opacity: 0.8; }

.modal-body { padding: 24px; }
textarea {
  width: 100%; min-height: 150px; background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
  color: #fff; padding: 16px; font-size: 1rem; line-height: 1.5;
  outline: none; transition: border-color 200ms ease-out, box-shadow 200ms ease-out; resize: none;
}
textarea:focus { border-color: var(--primary); box-shadow: 0 0 15px var(--primary-glow); }

.modal-footer {
  padding: 16px 24px 24px; display: flex; justify-content: flex-end; gap: 12px;
}
.btn {
  padding: 10px 24px; border-radius: 10px; font-weight: 700; cursor: pointer; transition: transform 160ms ease-out, background 160ms ease-out; border: none;
}
.btn-primary { background: var(--primary); color: #000; }
.btn-primary:active:not(:disabled) { transform: scale(0.97); }
@media (hover: hover) and (pointer: fine) {
  .btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 5px 15px var(--primary-glow); }
}
.btn-ghost { background: rgba(255,255,255,0.05); color: #fff; }
.btn-ghost:active:not(:disabled) { transform: scale(0.97); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.animate-pop { animation: pop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
@keyframes pop { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }

.spinner-small {
  width: 20px; height: 20px; border: 2px solid rgba(0,0,0,0.1); border-top-color: #000;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.btn-close { 
  background: none; border: none; color: #fff; font-size: 1.8rem; 
  cursor: pointer; opacity: 0.6; transition: opacity 200ms ease-out, color 200ms ease-out, transform 120ms ease-out;
}
.btn-close:active { transform: scale(0.9); }
@media (hover: hover) and (pointer: fine) {
  .btn-close:hover { opacity: 1; color: var(--primary); }
}
</style>
