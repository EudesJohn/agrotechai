import { defineStore } from 'pinia'
import { supabase } from './supabase'

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
        /**
         * Normalise l'objet user Supabase pour conserver
         * la compatibilité avec le reste de l'application
         * (notamment user.uid utilisé dans les templates/vues).
         */
        normalizeUser(sessionUser) {
            if (!sessionUser) return null
            return {
                id: sessionUser.id,
                uid: sessionUser.id, // backward compatibility
                email: sessionUser.email,
                displayName: sessionUser.user_metadata?.full_name || '',
                photoURL: sessionUser.user_metadata?.avatar_url || '',
                user_metadata: sessionUser.user_metadata || {},
            }
        },

        initAuth() {
            // 1) Vérifier s'il y a déjà une session au chargement
            supabase.auth.getSession().then(({ data: { session } }) => {
                this.user = this.normalizeUser(session?.user || null)
                if (session?.user) {
                    this.fetchProfile(session.user.id)
                    this.updateOnlineStatus(true)
                } else {
                    this.profile = null
                }
                this.loading = false
            })

            // 2) Écouter les changements d'auth (connexion, déconnexion, refresh)
            supabase.auth.onAuthStateChange((event, session) => {
                this.user = this.normalizeUser(session?.user || null)
                if (event === 'SIGNED_IN' && session?.user) {
                    this.fetchProfile(session.user.id)
                    this.updateOnlineStatus(true)
                } else if (event === 'SIGNED_OUT') {
                    this.profile = null
                }
                this.loading = false
            })
        },

        async updateOnlineStatus(status) {
            if (!this.user) return
            try {
                await supabase
                    .from('profiles')
                    .update({ is_online: status, last_seen: new Date().toISOString() })
                    .eq('id', this.user.id)
            } catch (err) {
                console.error('Online Status Error:', err)
            }
        },

        async fetchProfile(userId) {
            this.fetchError = null
            try {
                const { data: profile, error } = await supabase
                    .from('profiles')
                    .select('*')
                    .eq('id', userId)
                    .single()

                if (error) {
                    // Si le profil n'existe pas (cas rare en prod, mais possible),
                    // le créer
                    if (error.code === 'PGRST116') {
                        const newProfile = {
                            id: userId,
                            email: this.user?.email || '',
                            display_name: this.user?.displayName || '',
                            avatar_url: this.user?.photoURL || '',
                            created_at: new Date().toISOString(),
                        }
                        const { data: insertedProfile, error: insertError } = await supabase
                            .from('profiles')
                            .insert(newProfile)
                            .select()
                            .single()

                        if (insertError) throw insertError
                        this.profile = insertedProfile
                    } else {
                        throw error
                    }
                } else {
                    this.profile = profile
                }
            } catch (err) {
                console.error('Erreur fetchProfile:', err)
                this.fetchError = `Accès au profil restreint (${err.message || 'Erreur inconnue'}). Veuillez vérifier les policies RLS.`
            }
        },

        async updateProfile(data) {
            if (!this.user) return
            try {
                const { error } = await supabase
                    .from('profiles')
                    .update(data)
                    .eq('id', this.user.id)

                if (error) throw error
                this.profile = { ...this.profile, ...data }
            } catch (err) {
                console.error('Erreur updateProfile:', err)
                throw err
            }
        },

        async login(email, password) {
            this.error = null
            try {
                const { error } = await supabase.auth.signInWithPassword({ email, password })
                if (error) throw error
            } catch (err) {
                this.error = err.message
                throw err
            }
        },

        async register(email, password, extraData = {}) {
            this.error = null
            try {
                const { data, error } = await supabase.auth.signUp({
                    email,
                    password,
                    options: {
                        data: {
                            full_name: extraData.fullName || '',
                            phone: extraData.phone || '',
                        },
                    },
                })

                if (error) throw error

                // Si l'utilisateur est créé et connecté immédiatement
                // (email confirmations désactivé), mettre à jour le profil
                if (data?.user) {
                    const profileUpdate = {
                        display_name: extraData.fullName || '',
                        phone_number: extraData.phone || '',
                        location: extraData.commune || '',
                        user_type: extraData.sector || 'FARMER',
                    }
                    await supabase
                        .from('profiles')
                        .update(profileUpdate)
                        .eq('id', data.user.id)

                    this.profile = { ...this.profile, ...profileUpdate, id: data.user.id }
                }
            } catch (err) {
                this.error = err.message
                throw err
            }
        },

        async logout() {
            try {
                if (this.user) await this.updateOnlineStatus(false)
                await supabase.auth.signOut()
                this.user = null
                this.profile = null
            } catch (err) {
                console.error('Erreur lors de la déconnexion', err)
            }
        },
    },
})
