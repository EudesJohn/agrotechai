import axios from 'axios';
import { auth } from './firebase';

// Base configuration: VITE_API_URL from .env takes priority in production.
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api/',
    headers: {
        'Content-type': 'application/json',
    },
});

// Intercepteur pour injecter le token d'authentification Firebase
api.interceptors.request.use(async (config) => {
    const user = auth.currentUser;
    if (user) {
        // Récupère le token JWT (force le rafraîchissement si nécessaire)
        const token = await user.getIdToken();
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

export default api;