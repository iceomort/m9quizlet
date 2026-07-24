// Single Supabase client instance, shared by index.html's inline script.
// Loaded as a plain <script> (no build step / no ES modules) — the `const`
// below is a global binding visible to any <script> tag that runs after it.
const SUPABASE_URL = "https://uvipjhiuxrihrdyohrtc.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_oukcLGNC7CyZY3M_mOytuw_7Dtiy7JK";
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
