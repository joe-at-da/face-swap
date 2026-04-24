-- Remove metadata update from handle_new_user to fix race condition
-- The custom_access_token_hook will handle metadata updates properly
-- This function should ONLY create the user_roles record with member_id

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
DECLARE
    first_name text;
    last_name text;
    base_username text;
    new_username text;
    random_num integer;
    username_exists boolean;
    is_veedoo_user boolean;
BEGIN
    -- Check if this is a @veedoo.io user
    is_veedoo_user := NEW.email LIKE '%@veedoo.io';

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
    -- For @veedoo.io users, automatically assign member_id = 5296 (Freddy)
    -- The custom_access_token_hook will handle metadata updates
    IF is_veedoo_user THEN
        INSERT INTO public.user_roles (user_id, role, username, email, is_first_login, member_id)
        VALUES (NEW.id, 'user', new_username, NEW.email, true, 5296);
    ELSE
        -- Regular user without member_id
        INSERT INTO public.user_roles (user_id, role, username, email, is_first_login)
        VALUES (NEW.id, 'user', new_username, NEW.email, true);
    END IF;

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        -- Log the error for debugging
        RAISE LOG 'Error in handle_new_user: % - %', SQLERRM, SQLSTATE;
        -- Re-raise to prevent user creation if something goes wrong
        RAISE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
