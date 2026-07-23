import axios from 'axios'
import { supabase } from './supabase'

// Base configuration: VITE_API_URL from .env takes priority in production.
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api/',
    headers: {
        'Content-type': 'application/json',
    },
})

// Intercepteur pour injecter le token d'authentification Supabase
api.interceptors.request.use(async (config) => {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`
    }
    return config
}, (error) => {
    return Promise.reject(error)
})

export default api
