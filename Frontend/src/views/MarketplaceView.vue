<template>
  <div class="marketplace-page">
    <div class="container">
      <header class="market-header text-center mb-40">
        <h1 class="text-glow">Marketplace Cloud</h1>
        <p>Commerce direct via Firestore - 0 Base de données locale.</p>
      </header>

      <!-- Publish Form -->
      <div v-if="authStore.user" class="publish-section glass-panel mb-60">
        <h2>Publier une offre</h2>
        <form @submit.prevent="publishProduct" class="publish-form mt-20">
          <div class="form-row">
            <input v-model="newProduct.name" placeholder="Produit" required>
            <input v-model="newProduct.price" type="number" placeholder="Prix FCFA/kg" required>
          </div>
          <div class="form-row">
            <input v-model="newProduct.quantity" type="number" placeholder="Quantité (kg)" required>
            <input v-model="newProduct.location" placeholder="Localisation" required>
          </div>
          <textarea v-model="newProduct.description" placeholder="Description de votre récolte..." required></textarea>
          <button type="submit" class="btn btn-primary" :disabled="publishing">
            {{ publishing ? 'Publication...' : 'Mettre en vente' }}
          </button>
        </form>
      </div>

      <!-- Products List -->
      <div class="products-section">
        <div class="section-header flex justify-between items-center mb-32">
          <h2>Annonces Récentes</h2>
          <input v-model="searchQuery" placeholder="Chercher un produit..." class="search-input">
        </div>
        
        <div v-if="loading" class="text-center p-40">
           <div class="spinner"></div>
           <p>Chargement du marché...</p>
        </div>

        <div v-else-if="filteredProducts.length === 0" class="text-center p-40 opacity-50">
           📭 Aucun produit en vente pour le moment.
        </div>

        <div v-else class="products-grid">
          <div v-for="product in filteredProducts" :key="product.id" class="prod-card glass-panel">
            <div class="prod-visual">
              <div class="prod-img-placeholder">🌽</div>
              <div class="prod-type-badge">{{ product.seller_type || 'Agriculteur' }}</div>
            </div>
            <div class="prod-details">
              <h3>{{ product.name }}</h3>
              <p class="prod-desc">{{ product.description }}</p>
              <div class="seller-info">
                <span>{{ product.seller_name }}</span>
                <span class="location">📍 {{ product.location }}</span>
              </div>
              <div class="prod-price flex justify-between items-center">
                <span class="price">{{ product.price }} FCFA</span>
                <span class="quantity">Stock: {{ product.quantity }}kg</span>
              </div>
              <a v-if="product.seller_phone" :href="'tel:'+product.seller_phone" class="btn btn-primary w-full text-center">Appeler le vendeur</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { supabase } from '../supabase'
import { useAuthStore } from '../authStore'
import gsap from 'gsap'

const authStore = useAuthStore()
const products = ref([])
const loading = ref(true)
const publishing = ref(false)
const searchQuery = ref('')

const newProduct = ref({
  name: '',
  description: '',
  quantity: '',
  price: '',
  location: ''
})

const filteredProducts = computed(() => {
  return products.value.filter(p => 
    p.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const fetchProducts = async () => {
  loading.value = true
  try {
    const { data, error: err } = await supabase
      .from('products')
      .select('*')
      .order('created_at', { ascending: false })
    if (err) throw err
    products.value = (data || []).map(p => ({
      id: p.id,
      name: p.name,
      description: p.description,
      price: p.price,
      quantity: p.quantity,
      location: p.location,
      seller_name: p.seller_name,
      seller_phone: p.phone,
      seller_type: p.seller_type,
      image_url: p.image_url,
      createdAt: p.created_at,
    }))
  } catch (err) {
    console.error('Erreur chargement produits', err)
  } finally {
    loading.value = false
    setTimeout(() => {
       gsap.from(".prod-card", { y: 30, opacity: 0, stagger: 0.1, duration: 0.8 })
    }, 100)
  }
}

const publishProduct = async () => {
  if (!authStore.user) return
  publishing.value = true
  try {
    const { error: err } = await supabase.from('products').insert({
      name: newProduct.value.name,
      description: newProduct.value.description,
      price: parseFloat(newProduct.value.price) || 0,
      category: 'general',
      seller_id: authStore.user.id,
      location: newProduct.value.location,
      phone: authStore.profile?.phone_number || '',
      tags: [newProduct.value.quantity].filter(Boolean),
    })
    if (err) throw err
    Object.assign(newProduct.value, { name: '', description: '', quantity: '', price: '', location: '' })
    fetchProducts()
  } catch (err) {
    alert("Erreur de publication: " + (err.message || 'Erreur inconnue'))
  } finally {
    publishing.value = false
  }
}

onMounted(fetchProducts)
</script>

<style scoped>
.marketplace-page { padding-top: 130px; min-height: 100vh; padding-bottom: 80px; }
.publish-section { padding: 40px; margin-bottom: 50px; }
.publish-form { display: flex; flex-direction: column; gap: 20px; max-width: 700px; margin-inline: auto; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
input, textarea { padding: 14px; border-radius: 12px; border: 1px solid var(--border); background: rgba(255,255,255,0.05); color: #fff; }

.products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 30px; }
.prod-visual { height: 180px; position: relative; background: linear-gradient(135deg, var(--primary), var(--accent)); display: flex; justify-content: center; align-items: center; font-size: 4rem; }
.prod-type-badge { position: absolute; top: 15px; right: 15px; background: rgba(0,0,0,0.5); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: var(--primary); border: 1px solid var(--primary); }
.prod-details { padding: 24px; }
.prod-desc { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 16px; min-height: 48px; }
.seller-info { margin-bottom: 16px; font-size: 0.85rem; }
.seller-info span:first-child { font-weight: 700; display: block; color: #fff; }
.price { font-size: 1.4rem; font-weight: 800; color: var(--primary); }
.w-full { width: 100%; display: block; margin-top: 10px; }
.spinner { width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; margin: 0 auto; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
