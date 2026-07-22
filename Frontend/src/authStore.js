import { defineStore } from 'pinia';
import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    onAuthStateChanged
} from 'firebase/auth';
import { auth, db } from './firebase';
import { doc, getDoc, setDoc, updateDoc } from 'firebase/firestore';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        user: null,
        profile: null,
        loading: true,
        error: null,
        fetchError: null,
    }),

    getters: {
        isAuthenticated: (state) => !!state.user,
        isProfileComplete: (state) => !!(state.profile?.phone_number || state.profile?.location),
    },

    actions: {
        initAuth() {
            onAuthStateChanged(auth, async (currentUser) => {
                this.user = currentUser;
                if (currentUser) {
                    await this.fetchProfile(currentUser.uid);
                    await this.updateOnlineStatus(true);
                } else {
                    this.profile = null;
                }
                this.loading = false;
            });
        },

        async updateOnlineStatus(status) {
            if (!this.user) return;
            try {
                const docRef = doc(db, 'users', this.user.uid);
                await updateDoc(docRef, { isOnline: status, lastSeen: new Date().toISOString() });
            } catch (err) {
                console.error("Online Status Error:", err);
            }
        },

        async fetchProfile(uid) {
            this.fetchError = null;
            try {
                const docRef = doc(db, 'users', uid);
                const docSnap = await getDoc(docRef);
                if (docSnap.exists()) {
                    this.profile = docSnap.data();
                } else {
                    const newProfile = {
                        uid: uid,
                        email: this.user.email,
                        displayName: this.user.displayName || '',
                        photoURL: this.user.photoURL || '',
                        createdAt: new Date().toISOString(),
                        user_type: 'FARMER',
                        followersCount: 0,
                        followingCount: 0
                    };
                    await setDoc(docRef, newProfile);
                    this.profile = newProfile;
                }
            } catch (err) {
                console.error("Erreur fetchProfile:", err);
                const technicalError = err.code || err.message || 'Erreur inconnue';
                this.fetchError = `Accès au profil restreint (${technicalError}). Veuillez vérifier que les règles de sécurité Firestore sont publiées sur votre console Firebase.`;
            }
        },

        async updateProfile(data) {
            if (!this.user) return;
            try {
                const docRef = doc(db, 'users', this.user.uid);
                await updateDoc(docRef, data);
                this.profile = { ...this.profile, ...data };
            } catch (err) {
                console.error("Erreur updateProfile:", err);
                throw err;
            }
        },

        async login(email, password) {
            this.error = null;
            try {
                await signInWithEmailAndPassword(auth, email, password);
            } catch (err) {
                this.error = err.message;
                throw err;
            }
        },

        async register(email, password, extraData = {}) {
            this.error = null;
            try {
                const result = await createUserWithEmailAndPassword(auth, email, password);
                const newProfile = {
                    uid: result.user.uid,
                    email: email,
                    displayName: extraData.fullName || '',
                    phone_number: extraData.phone || '',
                    location: extraData.commune || '',
                    user_type: extraData.sector || 'FARMER',
                    createdAt: new Date().toISOString(),
                    followersCount: 0,
                    followingCount: 0
                };
                await setDoc(doc(db, 'users', result.user.uid), newProfile);
                this.profile = newProfile;
            } catch (err) {
                this.error = err.message;
                throw err;
            }
        },

        async logout() {
            try {
                if (this.user) await this.updateOnlineStatus(false);
                await signOut(auth);
                this.profile = null;
            } catch (err) {
                console.error("Erreur lors de la déconnexion", err);
            }
        }
    }
});