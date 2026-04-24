-- Auto-assign Freddy (member_id 5296) to all @veedoo.io users
-- This migration updates the auth hook to automatically set member_id for Veedoo employees

-- First, update ALL existing @veedoo.io users to follow Freddy
UPDATE public.user_roles
SET member_id = 5296
WHERE user_id IN (
  SELECT id
  FROM auth.users
  WHERE email LIKE '%@veedoo.io'
)
AND (member_id IS NULL OR member_id != 5296);

-- Update metadata for existing @veedoo.io users to mark them as parliament members
UPDATE auth.users
SET raw_user_meta_data = raw_user_meta_data || jsonb_build_object(
  'is_parliament_member', true,
  'member_id', 5296
)
WHERE email LIKE '%@veedoo.io'
AND (raw_user_meta_data->>'member_id' IS NULL OR (raw_user_meta_data->>'member_id')::integer != 5296);

-- Now update the custom_access_token_hook to automatically assign Freddy to new @veedoo.io signups
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result_event jsonb;
  result_claims jsonb;
  user_role public.app_role;
  is_first_login boolean;
  input_user_id uuid;
  username text;
  stripe_customer_id text;
  stripe_account_id text;
  is_stripe_account_active boolean;
  is_online boolean;
  last_seen timestamp;
  member_id integer;
  user_email text;
  is_veedoo_user boolean;
BEGIN
  -- Make a deep copy of the event to avoid modifying it directly
  result_event := event;

  -- Get user_id and email
  input_user_id := (event->>'user_id')::uuid;
  user_email := event->>'email';

  -- Check if this is a @veedoo.io user
  is_veedoo_user := user_email LIKE '%@veedoo.io';

  -- Start with existing claims or empty object
  result_claims := coalesce(event->'claims', '{}'::jsonb);

  -- Get user data
  SELECT
    ur.role,
    ur.is_first_login,
    ur.username,
    ur.stripe_customer_id,
    ur.stripe_account_id,
    ur.is_stripe_account_active,
    ur.is_online,
    ur.updated_at,
    ur.member_id
  INTO
    user_role,
    is_first_login,
    username,
    stripe_customer_id,
    stripe_account_id,
    is_stripe_account_active,
    is_online,
    last_seen,
    member_id
  FROM public.user_roles ur
  WHERE ur.user_id = input_user_id;

  -- Apply user data to claims
  IF user_role IS NOT NULL THEN
    -- Existing user with role

    -- For @veedoo.io users, ensure they have member_id set to 5296
    IF is_veedoo_user AND (member_id IS NULL OR member_id != 5296) THEN
      UPDATE public.user_roles
      SET member_id = 5296
      WHERE user_id = input_user_id;

      member_id := 5296;
    END IF;

    result_claims := result_claims || jsonb_build_object(
      'user_role', user_role::text,
      'is_first_login', is_first_login,
      'username', username,
      'stripe_customer_id', stripe_customer_id,
      'stripe_account_id', stripe_account_id,
      'is_stripe_account_active', is_stripe_account_active,
      'is_online', is_online,
      'last_seen', last_seen,
      'member_id', COALESCE(member_id, null)
    );

    -- Update user metadata
    UPDATE auth.users
    SET raw_user_meta_data =
      COALESCE(raw_user_meta_data, '{}'::jsonb) ||
      jsonb_build_object(
        'user_role', user_role::text,
        'is_first_login', is_first_login,
        'username', username,
        'stripe_customer_id', stripe_customer_id,
        'stripe_account_id', stripe_account_id,
        'is_stripe_account_active', is_stripe_account_active,
        'is_online', is_online,
        'last_seen', last_seen,
        'member_id', COALESCE(member_id, null),
        -- Mark @veedoo.io users as parliament members
        'is_parliament_member', CASE WHEN is_veedoo_user THEN true ELSE COALESCE((raw_user_meta_data->>'is_parliament_member')::boolean, false) END
      )
    WHERE id = input_user_id;
  ELSE
    -- New user, set defaults

    -- For new @veedoo.io users, automatically assign member_id = 5296
    IF is_veedoo_user THEN
      INSERT INTO public.user_roles (user_id, role, member_id, is_first_login)
      VALUES (input_user_id, 'user', 5296, true)
      ON CONFLICT (user_id) DO UPDATE
      SET member_id = 5296;

      member_id := 5296;
    END IF;

    result_claims := result_claims || jsonb_build_object(
      'user_role', 'user',
      'is_first_login', true,
      'username', '',
      'stripe_customer_id', '',
      'stripe_account_id', '',
      'is_stripe_account_active', false,
      'is_online', false,
      'last_seen', now(),
      'member_id', COALESCE(member_id, null)
    );

    -- Set default values in metadata
    UPDATE auth.users
    SET raw_user_meta_data =
      COALESCE(raw_user_meta_data, '{}'::jsonb) ||
      jsonb_build_object(
        'user_role', 'user',
        'is_first_login', true,
        'username', '',
        'stripe_customer_id', '',
        'stripe_account_id', '',
        'is_stripe_account_active', false,
        'is_online', false,
        'last_seen', now(),
        'member_id', COALESCE(member_id, null),
        -- Mark @veedoo.io users as parliament members
        'is_parliament_member', is_veedoo_user
      )
    WHERE id = input_user_id;
  END IF;

  -- Set the modified claims back in the event
  result_event := jsonb_set(result_event, '{claims}', result_claims);

  RETURN result_event;
EXCEPTION
  WHEN OTHERS THEN
    -- Log the error details for debugging
    RAISE LOG 'Error in custom_access_token_hook: % - %', SQLERRM, SQLSTATE;
    -- Return the original event without modifications to prevent authentication failure
    RETURN event;
END;
$$;

-- Grant necessary permissions (re-apply to ensure they persist)
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO postgres;
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO service_role;

-- Revoke from public users
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM authenticated, anon, public;
