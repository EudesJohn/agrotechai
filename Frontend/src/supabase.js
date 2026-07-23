import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://grwolhpoijmrwvsvcucc.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdyd29saHBvaWptcnd2c3ZjdWNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ3MjU1NDAsImV4cCI6MjEwMDMwMTU0MH0.bPNksXWgQSVO5r3z5WJYY6Wo3cJQWCs5enSiRpKmzww'

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
})
