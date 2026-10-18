import AsyncStorage from '@react-native-async-storage/async-storage';
import { getSupabase, isSupabaseConfigured } from '@/config/supabaseConfig';

const DEVICE_ID_KEY = 'bleecker_bloom_device_id';

const randomId = () =>
  Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');

// Local development without Supabase: a random id saved on the device.
const getDeviceId = async (): Promise<string> => {
  const saved = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (saved) return saved;
  const deviceId = randomId();
  await AsyncStorage.setItem(DEVICE_ID_KEY, deviceId);
  return deviceId;
};

// Headers that tell the API which customer is talking: a Supabase access token from
// anonymous sign-in (verified by the server), or the device id in local development.
const getIdentityHeaders = async (): Promise<Record<string, string>> => {
  if (!isSupabaseConfigured()) {
    return { 'X-Device-Id': await getDeviceId() };
  }
  const supabase = getSupabase();
  let { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    const { data, error } = await supabase.auth.signInAnonymously();
    if (error || !data.session) throw error ?? new Error('Anonymous sign-in failed');
    session = data.session;
  }
  return { Authorization: `Bearer ${session.access_token}` };
};

export { getIdentityHeaders };
