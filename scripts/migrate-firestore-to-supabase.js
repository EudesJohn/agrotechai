/**
 * Script de migration Firestore → Supabase pour Agrotech
 *
 * Prérequis :
 *   1. Firebase Service Account JSON (depuis Console Firebase > Service Accounts)
 *   2. Variables d'environnement :
 *      - SUPABASE_URL
 *      - SUPABASE_SERVICE_KEY
 *      - GOOGLE_APPLICATION_CREDENTIALS=chemin/vers/service-account.json
 *
 * Usage :
 *   cd scripts
 *   npm install firebase-admin @supabase/supabase-js
 *   node migrate-firestore-to-supabase.js
 */

const { createClient } = require('@supabase/supabase-js');
const admin = require('firebase-admin');
const path = require('path');

// ======== CONFIGURATION ========
const SUPABASE_URL = process.env.SUPABASE_URL || 'https://grwolhpoijmrwvsvcucc.supabase.co';
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdyd29saHBvaWptcnd2c3ZjdWNjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDcyNTU0MCwiZXhwIjoyMTAwMzAxNTQwfQ.IId-m1jnFJmp9DtkQenRlPbQPonv2FL6Wn-nqs19NCk';

// ======== INITIALIZATION ========
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// Initialiser Firebase Admin
// Nécessite un fichier de clé de service téléchargé depuis Firebase Console
const serviceAccountPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
if (!serviceAccountPath || !require('fs').existsSync(serviceAccountPath)) {
  console.error('\n❌ Fichier de clé de service Firebase requis.');
  console.error('   Téléchargez-le depuis Firebase Console > Project Settings > Service Accounts');
  console.error('   Puis : export GOOGLE_APPLICATION_CREDENTIALS=./chemin/vers/firebase-key.json\n');
  process.exit(1);
}

admin.initializeApp({
  credential: admin.credential.applicationDefault(),
});

const db = admin.firestore();

// Stats
const stats = { users: 0, posts: 0, reactions: 0, comments: 0, follows: 0, chats: 0, messages: 0, products: 0, history: 0 };

// Helper : convertir les Timestamps Firestore en ISO string
function toISO(value) {
  if (!value) return null;
  if (typeof value === 'object' && value.toDate) return value.toDate().toISOString();
  if (value instanceof Date) return value.toISOString();
  return value;
}

// Helper : batch insert avec gestion des erreurs
async function batchInsert(table, rows, batchSize = 50) {
  if (rows.length === 0) return;
  for (let i = 0; i < rows.length; i += batchSize) {
    const batch = rows.slice(i, i + batchSize);
    const { error } = await supabase.from(table).insert(batch);
    if (error) {
      console.error(`  ⚠ Erreur ${table} (lot ${i / batchSize + 1}):`, error.message);
    }
  }
}

// ======== MIGRATION ========
async function migrate() {
  console.log('🚀 Début de la migration Firestore → Supabase\n');
  const startTime = Date.now();

  // ---- 1. USERS → PROFILES ----
  console.log('📦 Migration des profils...');
  try {
    const usersSnap = await db.collection('users').get();
    const profiles = [];
    usersSnap.forEach(doc => {
      const data = doc.data();
      profiles.push({
        id: doc.id,
        email: data.email || '',
        username: data.displayName?.toLowerCase()?.replace(/\s+/g, '-') || `user-${doc.id.slice(0, 8)}`,
        display_name: data.displayName || '',
        avatar_url: data.photoURL || '',
        bio: data.bio || '',
        location: data.location || '',
        phone_number: data.phone_number || '',
        user_type: data.user_type || 'FARMER',
        followers_count: data.followersCount || 0,
        following_count: data.followingCount || 0,
        posts_count: data.postsCount || 0,
        created_at: toISO(data.createdAt) || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });
    await batchInsert('profiles', profiles);
    stats.users = profiles.length;
    console.log(`  ✅ ${profiles.length} profils migrés`);
  } catch (err) {
    console.error('  ❌ Erreur profils:', err.message);
  }

  // ---- 2. POSTS ----
  console.log('📦 Migration des posts...');
  try {
    const postsSnap = await db.collection('posts').get();
    const posts = [];
    const reactionsToInsert = [];
    const commentsToInsert = [];

    for (const doc of postsSnap.docs) {
      const data = doc.data();
      posts.push({
        id: doc.id,
        user_id: data.authorId || data.user_id || '',
        content: data.content || '',
        image_url: data.image_url || '',
        type: data.type || 'post',
        tags: data.tags || [],
        reactions_count: data.reactionsCount || { like: 0, love: 0, helpful: 0 },
        comments_count: data.commentsCount || 0,
        is_pinned: data.isPinned || false,
        is_edited: data.isEdited || false,
        created_at: toISO(data.createdAt) || new Date().toISOString(),
        updated_at: toISO(data.updatedAt) || new Date().toISOString(),
      });

      // Réactions (sous-collection)
      try {
        const rSnap = await db.collection('posts').doc(doc.id).collection('reactions').get();
        rSnap.forEach(rDoc => {
          const rData = rDoc.data();
          reactionsToInsert.push({
            post_id: doc.id,
            user_id: rDoc.id,
            reaction_type: rData.type || 'like',
            created_at: toISO(rData.createdAt) || new Date().toISOString(),
          });
        });
      } catch (e) { /* pas de réactions */ }

      // Commentaires (sous-collection)
      try {
        const cSnap = await db.collection('posts').doc(doc.id).collection('comments').get();
        cSnap.forEach(cDoc => {
          const cData = cDoc.data();
          commentsToInsert.push({
            id: cDoc.id,
            post_id: doc.id,
            user_id: cData.authorId || '',
            content: cData.content || '',
            parent_id: cData.parentId || null,
            created_at: toISO(cData.createdAt) || new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
        });
      } catch (e) { /* pas de commentaires */ }
    }

    await batchInsert('posts', posts);
    await batchInsert('post_reactions', reactionsToInsert);
    await batchInsert('post_comments', commentsToInsert);
    stats.posts = posts.length;
    stats.reactions = reactionsToInsert.length;
    stats.comments = commentsToInsert.length;
    console.log(`  ✅ ${posts.length} posts, ${reactionsToInsert.length} réactions, ${commentsToInsert.length} commentaires`);
  } catch (err) {
    console.error('  ❌ Erreur posts:', err.message);
  }

  // ---- 3. FOLLOWS ----
  console.log('📦 Migration des follows...');
  try {
    const followsSnap = await db.collection('follows').get();
    const follows = [];
    followsSnap.forEach(doc => {
      const data = doc.data();
      follows.push({
        id: doc.id,
        follower_id: data.followerId || '',
        following_id: data.followedId || '',
        created_at: toISO(data.createdAt) || new Date().toISOString(),
      });
    });
    await batchInsert('follows', follows);
    stats.follows = follows.length;
    console.log(`  ✅ ${follows.length} follows migrés`);
  } catch (err) {
    console.error('  ❌ Erreur follows:', err.message);
  }

  // ---- 4. CHATS + MESSAGES ----
  console.log('📦 Migration des chats...');
  try {
    const chatsSnap = await db.collection('chats').get();
    const chats = [];
    const messages = [];

    for (const doc of chatsSnap.docs) {
      const data = doc.data();
      chats.push({
        id: doc.id,
        participants: data.participants || [],
        last_message: data.lastMessage || '',
        last_message_at: toISO(data.lastUpdate) || new Date().toISOString(),
        last_message_sender_id: data.lastSenderId || '',
        created_at: toISO(data.createdAt) || new Date().toISOString(),
      });

      // Messages (sous-collection)
      try {
        const mSnap = await db.collection('chats').doc(doc.id).collection('messages').get();
        mSnap.forEach(mDoc => {
          const mData = mDoc.data();
          messages.push({
            id: mDoc.id,
            chat_id: doc.id,
            sender_id: mData.senderId || '',
            content: mData.text || mData.content || '',
            message_type: 'text',
            created_at: toISO(mData.createdAt) || new Date().toISOString(),
          });
        });
      } catch (e) { /* pas de messages */ }
    }

    await batchInsert('chats', chats);
    await batchInsert('chat_messages', messages);
    stats.chats = chats.length;
    stats.messages = messages.length;
    console.log(`  ✅ ${chats.length} chats, ${messages.length} messages`);
  } catch (err) {
    console.error('  ❌ Erreur chats:', err.message);
  }

  // ---- 5. PRODUCTS ----
  console.log('📦 Migration des produits...');
  try {
    const productsSnap = await db.collection('products').get();
    const products = [];
    productsSnap.forEach(doc => {
      const data = doc.data();
      products.push({
        id: doc.id,
        name: data.name || '',
        description: data.description || '',
        price: parseFloat(data.price) || 0,
        category: data.category || 'general',
        image_url: data.image_url || '',
        seller_id: data.seller_id || '',
        location: data.location || '',
        phone: data.seller_phone || '',
        tags: [data.quantity].filter(Boolean),
        in_stock: true,
        created_at: toISO(data.createdAt) || new Date().toISOString(),
      });
    });
    await batchInsert('products', products);
    stats.products = products.length;
    console.log(`  ✅ ${products.length} produits migrés`);
  } catch (err) {
    console.error('  ❌ Erreur produits:', err.message);
  }

  // ---- 6. SCAN HISTORY ----
  console.log('📦 Migration de l\'historique des scans...');
  try {
    const usersSnap2 = await db.collection('users').get();
    let totalHistory = 0;

    for (const userDoc of usersSnap2.docs) {
      try {
        const hSnap = await db.collection('users').doc(userDoc.id).collection('history').get();
        const history = [];
        hSnap.forEach(hDoc => {
          const data = hDoc.data();
          history.push({
            id: hDoc.id,
            user_id: userDoc.id,
            plant_name: data.plante || '',
            disease: data.maladie || 'Saine',
            image_url: data.image || '',
            diagnosis: {
              plante: data.plante || '',
              utilite: data.utilite || '',
              proprietes_medicinales: data.proprietes_medicinales || '',
              maladie: data.maladie || 'Saine',
              cause: data.cause || '',
              traitement: data.traitement || '',
              produit_recommande: data.produit_recommande || '',
            },
            created_at: toISO(data.date) || new Date().toISOString(),
          });
        });
        if (history.length > 0) {
          await batchInsert('scan_history', history);
          totalHistory += history.length;
        }
      } catch (e) { /* pas d'historique */ }
    }
    stats.history = totalHistory;
    console.log(`  ✅ ${totalHistory} scans migrés`);
  } catch (err) {
    console.error('  ❌ Erreur historique:', err.message);
  }

  // ---- RESULTATS ----
  const duration = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log('\n' + '='.repeat(50));
  console.log('📊 RÉSULTATS DE LA MIGRATION');
  console.log('='.repeat(50));
  console.log(`   Profils        : ${stats.users}`);
  console.log(`   Posts          : ${stats.posts}`);
  console.log(`   Réactions      : ${stats.reactions}`);
  console.log(`   Commentaires   : ${stats.comments}`);
  console.log(`   Follows        : ${stats.follows}`);
  console.log(`   Chats          : ${stats.chats}`);
  console.log(`   Messages       : ${stats.messages}`);
  console.log(`   Produits       : ${stats.products}`);
  console.log(`   Scan History   : ${stats.history}`);
  console.log('='.repeat(50));
  console.log(`⏱  Durée : ${duration}s`);
  console.log('✅ Migration terminée !\n');

  console.log('⚠️  ATTENTION : Les profils migrés ont un ID Firebase UUID.');
  console.log('   Les nouveaux utilisateurs créés via Supabase Auth auront un UUID différent.');
  console.log('   Le champ firebase_uid dans Django UserProfile permet de faire le lien.\n');
}

migrate().catch(console.error);
