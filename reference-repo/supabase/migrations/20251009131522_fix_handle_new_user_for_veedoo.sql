-- Fix handle_new_user function to automatically assign Freddy (member_id 5296) to @veedoo.io users
-- This ensures @veedoo.io users get member_id set during initial user_roles INSERT

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
    IF is_veedoo_user THEN
        INSERT INTO public.user_roles (user_id, role, username, email, is_first_login, member_id)
        VALUES (NEW.id, 'user', new_username, NEW.email, true, 5296);

        -- Update user metadata to mark them as parliament member
        UPDATE auth.users
        SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) || jsonb_build_object(
            'is_parliament_member', true,
            'member_id', 5296
        )
        WHERE id = NEW.id;
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
