-- ==============================================================
-- Schéma Supabase pour Agrotech
-- Migration Firestore → PostgreSQL
-- À exécuter dans Supabase SQL Editor (en une fois)
-- ==============================================================

-- 0. Extension UUID (déjà activée par défaut sur Supabase)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================
-- 1. PROFILES (remplace Firestore users/{uid})
-- ==============================================================
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    username TEXT UNIQUE,
    display_name TEXT,
    bio TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    cover_url TEXT DEFAULT '',
    location TEXT DEFAULT '',
    website TEXT DEFAULT '',
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator')),
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    is_online BOOLEAN DEFAULT false,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger: créer un profil automatiquement à l'inscription
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, username, display_name)
    VALUES (
        NEW.id,
        NEW.email,
        LOWER(SPLIT_PART(NEW.email, '@', 1)) || '-' || SUBSTRING(MD5(NEW.id::TEXT)::TEXT, 1, 6),
        COALESCE(NEW.raw_user_meta_data->>'full_name', SPLIT_PART(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Trigger: updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Tout le monde peut lire les profils
CREATE POLICY "profiles_select_public" ON public.profiles
    FOR SELECT USING (true);

-- Seul le propriétaire peut modifier son profil
CREATE POLICY "profiles_update_own" ON public.profiles
    FOR UPDATE USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Seul le propriétaire peut supprimer son profil
CREATE POLICY "profiles_delete_own" ON public.profiles
    FOR DELETE USING (auth.uid() = id);

-- ==============================================================
-- 2. POSTS (remplace Firestore posts/{postId})
-- ==============================================================
CREATE TABLE public.posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    image_url TEXT DEFAULT '',
    type TEXT DEFAULT 'post' CHECK (type IN ('post', 'question', 'tip', 'diagnostic')),
    tags TEXT[] DEFAULT '{}',
    reactions_count JSONB DEFAULT '{"like": 0, "love": 0, "helpful": 0}'::jsonb,
    comments_count INTEGER DEFAULT 0,
    is_pinned BOOLEAN DEFAULT false,
    is_edited BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER posts_updated_at
    BEFORE UPDATE ON public.posts
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- Index pour le feed (tri chronologique inverse)
CREATE INDEX idx_posts_created_at ON public.posts(created_at DESC);
CREATE INDEX idx_posts_user_id ON public.posts(user_id);
CREATE INDEX idx_posts_tags ON public.posts USING GIN(tags);

ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;

-- Tout le monde peut lire les posts
CREATE POLICY "posts_select_public" ON public.posts
    FOR SELECT USING (true);

-- Utilisateurs authentifiés peuvent créer
CREATE POLICY "posts_insert_auth" ON public.posts
    FOR INSERT WITH CHECK (auth.role() = 'authenticated' AND user_id = auth.uid());

-- Propriétaire peut modifier/supprimer
CREATE POLICY "posts_update_own" ON public.posts
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "posts_delete_own" ON public.posts
    FOR DELETE USING (auth.uid() = user_id);

-- ==============================================================
-- 3. POST REACTIONS (remplace posts/{id}/reactions/{uid})
-- ==============================================================
CREATE TABLE public.post_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    reaction_type TEXT NOT NULL CHECK (reaction_type IN ('like', 'love', 'helpful')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, user_id) -- un utilisateur = une réaction par post
);

CREATE INDEX idx_reactions_post_id ON public.post_reactions(post_id);
CREATE INDEX idx_reactions_user_id ON public.post_reactions(user_id);

-- Trigger: mettre à jour reactions_count sur posts
CREATE OR REPLACE FUNCTION public.update_reactions_count()
RETURNS TRIGGER AS $$
DECLARE
    counts_json JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT JSONB_OBJECT_AGG(r_type, cnt)
        INTO counts_json
        FROM (
            SELECT reaction_type AS r_type, COUNT(*) AS cnt
            FROM public.post_reactions
            WHERE post_id = NEW.post_id
            GROUP BY reaction_type
        ) sub;
        UPDATE public.posts SET reactions_count = COALESCE(counts_json, '{}'::jsonb) WHERE id = NEW.post_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        SELECT JSONB_OBJECT_AGG(r_type, cnt)
        INTO counts_json
        FROM (
            SELECT reaction_type AS r_type, COUNT(*) AS cnt
            FROM public.post_reactions
            WHERE post_id = OLD.post_id
            GROUP BY reaction_type
        ) sub;
        UPDATE public.posts SET reactions_count = COALESCE(counts_json, '{}'::jsonb) WHERE id = OLD.post_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER reactions_after_insert
    AFTER INSERT ON public.post_reactions
    FOR EACH ROW EXECUTE FUNCTION public.update_reactions_count();

CREATE TRIGGER reactions_after_delete
    AFTER DELETE ON public.post_reactions
    FOR EACH ROW EXECUTE FUNCTION public.update_reactions_count();

ALTER TABLE public.post_reactions ENABLE ROW LEVEL SECURITY;

-- Tout le monde peut lire les réactions
CREATE POLICY "reactions_select_public" ON public.post_reactions
    FOR SELECT USING (true);

-- Utilisateur authentifié peut créer/supprimer ses propres réactions
CREATE POLICY "reactions_insert_own" ON public.post_reactions
    FOR INSERT WITH CHECK (auth.role() = 'authenticated' AND user_id = auth.uid());

CREATE POLICY "reactions_delete_own" ON public.post_reactions
    FOR DELETE USING (auth.uid() = user_id);

-- ==============================================================
-- 4. POST COMMENTS (remplace posts/{id}/comments/{commentId})
-- ==============================================================
CREATE TABLE public.post_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_id UUID REFERENCES public.post_comments(id) ON DELETE CASCADE, -- pour réponses
    is_edited BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER post_comments_updated_at
    BEFORE UPDATE ON public.post_comments
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE INDEX idx_comments_post_id ON public.post_comments(post_id, created_at ASC);

-- Trigger: mettre à jour comments_count sur posts
CREATE OR REPLACE FUNCTION public.update_comments_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.posts SET comments_count = comments_count + 1 WHERE id = NEW.post_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.posts SET comments_count = GREATEST(comments_count - 1, 0) WHERE id = OLD.post_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER comments_after_insert
    AFTER INSERT ON public.post_comments
    FOR EACH ROW EXECUTE FUNCTION public.update_comments_count();

CREATE TRIGGER comments_after_delete
    AFTER DELETE ON public.post_comments
    FOR EACH ROW EXECUTE FUNCTION public.update_comments_count();

ALTER TABLE public.post_comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "comments_select_public" ON public.post_comments
    FOR SELECT USING (true);

CREATE POLICY "comments_insert_auth" ON public.post_comments
    FOR INSERT WITH CHECK (auth.role() = 'authenticated' AND user_id = auth.uid());

CREATE POLICY "comments_update_own" ON public.post_comments
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "comments_delete_own" ON public.post_comments
    FOR DELETE USING (auth.uid() = user_id);

-- ==============================================================
-- 5. FOLLOWS (remplace Firestore follows/{id})
-- ==============================================================
CREATE TABLE public.follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(follower_id, following_id),
    CHECK (follower_id != following_id) -- pas de self-follow
);

CREATE INDEX idx_follows_follower ON public.follows(follower_id);
CREATE INDEX idx_follows_following ON public.follows(following_id);

-- Trigger: mettre à jour followers_count / following_count
CREATE OR REPLACE FUNCTION public.update_follows_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.profiles SET followers_count = followers_count + 1 WHERE id = NEW.following_id;
        UPDATE public.profiles SET following_count = following_count + 1 WHERE id = NEW.follower_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.profiles SET followers_count = GREATEST(followers_count - 1, 0) WHERE id = OLD.following_id;
        UPDATE public.profiles SET following_count = GREATEST(following_count - 1, 0) WHERE id = OLD.follower_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER follows_after_insert
    AFTER INSERT ON public.follows
    FOR EACH ROW EXECUTE FUNCTION public.update_follows_count();

CREATE TRIGGER follows_after_delete
    AFTER DELETE ON public.follows
    FOR EACH ROW EXECUTE FUNCTION public.update_follows_count();

ALTER TABLE public.follows ENABLE ROW LEVEL SECURITY;

CREATE POLICY "follows_select_public" ON public.follows
    FOR SELECT USING (true);

CREATE POLICY "follows_insert_own" ON public.follows
    FOR INSERT WITH CHECK (auth.uid() = follower_id);

CREATE POLICY "follows_delete_own" ON public.follows
    FOR DELETE USING (auth.uid() = follower_id);

-- ==============================================================
-- 6. CHATS + MESSAGES (remplace Firestore chats/{id} + messages)
-- ==============================================================
CREATE TABLE public.chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participants UUID[] NOT NULL,
    last_message TEXT DEFAULT '',
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_sender_id UUID REFERENCES public.profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chats_participants ON public.chats USING GIN(participants);

CREATE TABLE public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'system')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_chat_id ON public.chat_messages(chat_id, created_at ASC);

-- Trigger: mettre à jour last_message dans chats
CREATE OR REPLACE FUNCTION public.update_chat_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.chats
    SET last_message = NEW.content,
        last_message_at = NEW.created_at,
        last_message_sender_id = NEW.sender_id
    WHERE id = NEW.chat_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER messages_after_insert
    AFTER INSERT ON public.chat_messages
    FOR EACH ROW EXECUTE FUNCTION public.update_chat_last_message();

ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;

-- Les participants peuvent voir le chat
CREATE POLICY "chats_select_participant" ON public.chats
    FOR SELECT USING (auth.uid() = ANY(participants));

-- Créer un chat (authentifié)
CREATE POLICY "chats_insert_auth" ON public.chats
    FOR INSERT WITH CHECK (auth.role() = 'authenticated' AND auth.uid() = ANY(participants));

ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- Les participants peuvent voir les messages du chat
CREATE POLICY "messages_select_participant" ON public.chat_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.chats
            WHERE id = chat_id AND auth.uid() = ANY(participants)
        )
    );

-- Les participants peuvent envoyer des messages
CREATE POLICY "messages_insert_participant" ON public.chat_messages
    FOR INSERT WITH CHECK (
        auth.role() = 'authenticated'
        AND sender_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM public.chats
            WHERE id = chat_id AND auth.uid() = ANY(participants)
        )
    );

-- ==============================================================
-- 7. PRODUCTS (remplace Firestore products/{id})
-- ==============================================================
CREATE TABLE public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2),
    category TEXT NOT NULL,
    image_url TEXT DEFAULT '',
    seller_id UUID REFERENCES public.profiles(id),
    location TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    rating DECIMAL(3, 2) DEFAULT 0,
    reviews_count INTEGER DEFAULT 0,
    in_stock BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER products_updated_at
    BEFORE UPDATE ON public.products
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE INDEX idx_products_category ON public.products(category);
CREATE INDEX idx_products_created_at ON public.products(created_at DESC);
CREATE INDEX idx_products_seller ON public.products(seller_id);
CREATE INDEX idx_products_tags ON public.products USING GIN(tags);

ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "products_select_public" ON public.products
    FOR SELECT USING (true);

CREATE POLICY "products_insert_auth" ON public.products
    FOR INSERT WITH CHECK (auth.role() = 'authenticated' AND seller_id = auth.uid());

CREATE POLICY "products_update_own" ON public.products
    FOR UPDATE USING (auth.uid() = seller_id)
    WITH CHECK (auth.uid() = seller_id);

CREATE POLICY "products_delete_own" ON public.products
    FOR DELETE USING (auth.uid() = seller_id);

-- ==============================================================
-- 8. SCAN HISTORY (remplace users/{uid}/history/{id})
-- ==============================================================
CREATE TABLE public.scan_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    plant_name TEXT DEFAULT '',
    disease TEXT DEFAULT '',
    confidence DECIMAL(5, 2) DEFAULT 0,
    image_url TEXT DEFAULT '',
    diagnosis JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scan_history_user ON public.scan_history(user_id, created_at DESC);

ALTER TABLE public.scan_history ENABLE ROW LEVEL SECURITY;

-- Chacun voit son historique
CREATE POLICY "scan_history_select_own" ON public.scan_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "scan_history_insert_own" ON public.scan_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "scan_history_delete_own" ON public.scan_history
    FOR DELETE USING (auth.uid() = user_id);

-- ==============================================================
-- 9. ACTIVER REPLICATION (Realtime)
-- ==============================================================
-- Activer Realtime pour chat_messages (temps réel)
ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE public.posts;
ALTER PUBLICATION supabase_realtime ADD TABLE public.post_comments;
ALTER PUBLICATION supabase_realtime ADD TABLE public.chats;
ALTER PUBLICATION supabase_realtime ADD TABLE public.profiles;

-- ==============================================================
-- 10. STORAGE BUCKET: profiles
-- ==============================================================
-- À créer dans Supabase Dashboard > Storage
-- Bucket: "profiles" (public)
-- Policy: SELECT public
-- Policy: INSERT/UPDATE/DELETE si auth.uid() est le owner
--
-- Ou exécuter via l'API de gestion (ne peut pas se faire en SQL pur)
-- => Faire dans le Dashboard > Storage > Create bucket > "profiles" (Public)
