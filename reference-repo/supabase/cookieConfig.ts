// Shared cookie name for Supabase auth across server and browser clients.
// Both clients MUST use the same cookie name for session sharing to work.
// This allows the server to use internal Docker URLs (SUPABASE_URL) while
// the browser uses public URLs (NEXT_PUBLIC_SUPABASE_URL).
export const SUPABASE_COOKIE_NAME = "sb-mpai-auth-token";
