import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import { useAuthStore } from './authStore'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Initialiser l'écouteur Firebase avant de monter l'application
// Cela évite les bugs de clignotement où la page de login s'affiche avant que Firebase ait vérifié la session
const authStore = useAuthStore()
authStore.initAuth()

app.mount('#app')
