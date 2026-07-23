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

const handleSend = async () => {
  if (!message.value.trim() || !props.partnerId || !authStore.user) return
  
  loading.value = true
  try {
    const participants = [authStore.user.id, props.partnerId].sort()
    const chatId = participants.join('_')

    // 1. Update/Create Chat Doc
    await supabase.from('chats').upsert({
      id: chatId,
      participants,
      last_message: message.value,
      last_message_sender_id: authStore.user.id,
    })

    // 2. Add Message to chat_messages table
    await supabase.from('chat_messages').insert({
      chat_id: chatId,
      sender_id: authStore.user.id,
      content: message.value,
      message_type: 'text',
    })

    message.value = ''
    emit('sent')
    emit('close')
  } catch (err) {
    console.error("Error sending quick message:", err)
    alert("Erreur lors de l'envoi du message.")
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
            <img :src="partnerPic || 'https://via.placeholder.com/40'" class="avatar" />
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
  outline: none; transition: 0.3s; resize: none;
}
textarea:focus { border-color: var(--primary); box-shadow: 0 0 15px var(--primary-glow); }

.modal-footer {
  padding: 16px 24px 24px; display: flex; justify-content: flex-end; gap: 12px;
}
.btn {
  padding: 10px 24px; border-radius: 10px; font-weight: 700; cursor: pointer; transition: 0.3s; border: none;
}
.btn-primary { background: var(--primary); color: #000; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 5px 15px var(--primary-glow); }
.btn-ghost { background: rgba(255,255,255,0.05); color: #fff; }
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
  cursor: pointer; opacity: 0.6; transition: 0.3s;
}
.btn-close:hover { opacity: 1; color: var(--primary); }
</style>
