-- Fix the custom_access_token_hook function to handle team invitation acceptance properly
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
BEGIN
  -- Make a deep copy of the event to avoid modifying it directly
  result_event := event;

  -- Get user_id
  input_user_id := (event->>'user_id')::uuid;

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
        'member_id', COALESCE(member_id, null)
      )
    WHERE id = input_user_id;
  ELSE
    -- New user, set defaults
    result_claims := result_claims || jsonb_build_object(
      'user_role', 'user',
      'is_first_login', true,
      'username', '',
      'stripe_customer_id', '',
      'stripe_account_id', '',
      'is_stripe_account_active', false,
      'is_online', false,
      'last_seen', now(),
      'member_id', null
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
        'member_id', null
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

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO postgres;
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO service_role;

-- Revoke from public users
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM authenticated, anon, public;