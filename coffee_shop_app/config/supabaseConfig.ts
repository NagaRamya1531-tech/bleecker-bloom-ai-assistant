import 'react-native-url-polyfill/auto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { AppState, Platform } from 'react-native';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL as string;
// The publishable (anon) key is safe to ship in the app; Row Level Security protects the data.
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY as string;

// Without Supabase keys (local development) the app uses the local API and a device id instead.
const isSupabaseConfigured = () => Boolean(supabaseUrl && supabaseAnonKey);

let supabase: SupabaseClient | undefined;

// Anonymous sign-in gives each phone a stable customer id; persisting the session in
// AsyncStorage keeps the same id (and saved conversation) across app restarts.
const getSupabase = (): SupabaseClient => {
  if (!supabase) {
    supabase = createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        storage: Platform.OS === 'web' ? undefined : AsyncStorage,
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
      },
    });
    // Refresh tokens only while the app is in the foreground (Supabase's React Native guidance).
    if (Platform.OS !== 'web') {
      AppState.addEventListener('change', (state) => {
        if (state === 'active') supabase?.auth.startAutoRefresh();
        else supabase?.auth.stopAutoRefresh();
      });
    }
  }
  return supabase;
};

export { getSupabase, isSupabaseConfigured };
