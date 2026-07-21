import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabaseConfigured = Boolean(url && anonKey && !anonKey.includes('paste-your'))

// Guard against accidentally shipping a service_role key: that JWT's payload
// carries "role":"service_role" instead of "role":"anon". Decode defensively
// (never throw on malformed input) and warn loudly in dev if it looks wrong.
function looksLikeServiceRoleKey(key) {
  try {
    const payload = key.split('.')[1]
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    return decoded.role === 'service_role'
  } catch {
    return false
  }
}

if (supabaseConfigured && looksLikeServiceRoleKey(anonKey)) {
  // eslint-disable-next-line no-console
  console.error(
    '[boq-dashboard] VITE_SUPABASE_ANON_KEY looks like a service_role key, not an anon key. ' +
    'Do not ship a service_role key in client-side code — replace it with the anon/public key ' +
    'from Supabase Dashboard -> Project Settings -> API, and rotate the service_role key immediately.'
  )
}

export const supabase = supabaseConfigured ? createClient(url, anonKey) : null
