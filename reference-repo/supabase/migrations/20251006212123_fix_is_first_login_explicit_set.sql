-- Fix handle_new_user function to explicitly set is_first_login
-- This ensures proper synchronization with auth hook and prevents setup completion issues

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
DECLARE
    first_name text;
    last_name text;
    base_username text;
    new_username text;
    random_num integer;
    username_exists boolean;
BEGIN
    -- Extract first and last name from full_name
    first_name := split_part(NEW.raw_user_meta_data->>'full_name', ' ', 1);
    last_name := split_part(NEW.raw_user_meta_data->>'full_name', ' ', 2);

    -- If last name is empty, use first name only
    IF last_name = '' OR last_name IS NULL THEN
        base_username := lower(first_name);
    ELSE
        base_username := lower(first_name) || '-' || lower(last_name);
    END IF;

    -- Handle case where first_name is also empty (shouldn't happen but be defensive)
    IF base_username = '' OR base_username IS NULL THEN
        base_username := 'user';
    END IF;

    -- Generate unique username with random number
    LOOP
        -- Generate random 4-digit number
        random_num := floor(random() * 9000 + 1000)::integer;
        new_username := base_username || '-' || random_num::text;

        -- Check if username exists
        SELECT EXISTS (
            SELECT 1 FROM public.user_roles WHERE user_roles.username = new_username
        ) INTO username_exists;

        -- Exit loop if username is unique
        EXIT WHEN NOT username_exists;
    END LOOP;

    -- Insert new user with generated username
    -- IMPORTANT: Explicitly set is_first_login to true for proper auth hook synchronization
    INSERT INTO public.user_roles (user_id, role, username, email, is_first_login)
    VALUES (NEW.id, 'user', new_username, NEW.email, true);

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        -- Log the error for debugging
        RAISE LOG 'Error in handle_new_user: % - %', SQLERRM, SQLSTATE;
        -- Re-raise to prevent user creation
        RAISE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
