-- Create the auth hook function
create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
security definer
as $$
declare
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
begin
  -- Make a deep copy of the event to avoid modifying it directly
  result_event := event;
  
  -- Get user_id
  input_user_id := (event->>'user_id')::uuid;
  
  -- Start with existing claims or empty object
  result_claims := coalesce(event->'claims', '{}'::jsonb);
  
  -- Get user data
  select 
    ur.role,
    ur.is_first_login,
    ur.username,
    ur.stripe_customer_id,
    ur.stripe_account_id,
    ur.is_stripe_account_active,
    ur.is_online,
    ur.updated_at,
    ur.member_id
  into 
    user_role,
    is_first_login,
    username,
    stripe_customer_id,
    stripe_account_id,
    is_stripe_account_active,
    is_online,
    last_seen,
    member_id
  from public.user_roles ur
  where ur.user_id = input_user_id;
  
  -- Apply user data to claims
  if user_role is not null then
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
    
    -- Update user metadata - ensure is_first_login is explicitly set to the correct value
    update auth.users
    set raw_user_meta_data = (
        -- Remove the existing is_first_login value if present
        case when raw_user_meta_data ? 'is_first_login' 
             then raw_user_meta_data - 'is_first_login' 
             else raw_user_meta_data 
        end
      ) || jsonb_build_object(
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
    where id = input_user_id;
  else
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
    update auth.users
    set raw_user_meta_data = (
        -- Remove the existing is_first_login value if present
        case when raw_user_meta_data ? 'is_first_login' 
             then raw_user_meta_data - 'is_first_login' 
             else raw_user_meta_data 
        end
      ) || jsonb_build_object(
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
    where id = input_user_id;
  end if;

  -- Set the modified claims back in the event
  result_event := jsonb_set(result_event, '{claims}', result_claims);
  
  return result_event;
end;
$$;

-- Ensure the hook has necessary permissions
grant execute on function public.custom_access_token_hook to supabase_auth_admin;
grant execute on function public.custom_access_token_hook to postgres;
grant execute on function public.custom_access_token_hook to service_role;

grant usage on schema public to supabase_auth_admin;
grant usage on schema public to postgres;
grant usage on schema public to service_role;

revoke execute
  on function public.custom_access_token_hook
  from authenticated, anon, public;

grant all
  on table public.user_roles
to supabase_auth_admin;

grant all
  on table public.user_roles
to postgres;

grant all
  on table public.user_roles
to service_role;

revoke all
  on table public.user_roles
  from authenticated, anon, public;

-- Update the handle_role_change function to properly update is_first_login
create or replace function public.handle_role_change()
returns trigger as $$
begin
  -- Explicitly handle the is_first_login value
  update auth.users
  set raw_user_meta_data = (
      -- Remove the existing is_first_login value if present
      case when raw_user_meta_data ? 'is_first_login' 
           then raw_user_meta_data - 'is_first_login' 
           else raw_user_meta_data 
      end
    ) || jsonb_build_object(
      'user_role', NEW.role::text,
      'is_first_login', NEW.is_first_login,
      'username', NEW.username,
      'stripe_customer_id', NEW.stripe_customer_id,
      'stripe_account_id', NEW.stripe_account_id,
      'is_stripe_account_active', NEW.is_stripe_account_active,
      'is_online', NEW.is_online
    ),
    -- Set a very short refresh time to force token refresh
    updated_at = now()
  where id = NEW.user_id;

  -- Update all existing refresh tokens to require a refresh
  update auth.refresh_tokens
  set updated_at = now(),
      created_at = now() - interval '1 year'
  where user_id = NEW.user_id::text;

  return NEW;
end;
$$ language plpgsql security definer;




-- Create a new storage bucket for user avatars with better defaults
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
select 
  'user_avatars',
  'user_avatars',
  true,
  26214400, -- 25MB limit
  array['image/jpeg', 'image/png', 'image/webp']
where not exists (
  select 1 from storage.buckets where id = 'user_avatars'
);

-- alter table storage.objects enable row level security;


-- Create policy to allow users to upload their own avatar
create policy "Users can upload their own avatar" on storage.objects for insert
with check (
  bucket_id = 'user_avatars'
  and auth.uid()::text = (storage.foldername(name))[1]
);

-- Create policy to allow users to update their own avatar
create policy "Users can update their own avatar" on storage.objects for update
using (
  bucket_id = 'user_avatars'
  and auth.uid()::text = (storage.foldername(name))[1]
);

-- Create policy to allow users to delete their own avatar
create policy "Users can delete their own avatar" on storage.objects for delete
using (
  bucket_id = 'user_avatars'
  and auth.uid()::text = (storage.foldername(name))[1]
);

-- Improve the delete_old_avatar function with better error handling
create or replace function delete_old_avatar()
returns trigger as $$
declare
  old_avatar_path text;
begin
  -- Validate input
  if NEW.bucket_id != 'user_avatars' then
    return NEW;
  end if;

  -- Find the old avatar for this user
  select name into old_avatar_path 
  from storage.objects
  where bucket_id = 'user_avatars'
  and (storage.foldername(name))[1] = (storage.foldername(NEW.name))[1]  -- Match the folder
  and name != NEW.name  -- Don't delete the new file
  and created_at < NEW.created_at;  -- Only delete older files

  -- If found, delete it
  if old_avatar_path is not null then
    delete from storage.objects 
    where name = old_avatar_path;
  end if;

  return NEW;
exception
  when others then
    -- Log error but don't block the upload
    raise warning 'Error in delete_old_avatar: %', SQLERRM;
    return NEW;
end;
$$ language plpgsql security definer;

drop trigger if exists on_avatar_upload on storage.objects;


-- Create trigger to run function on avatar upload
create trigger on_avatar_upload
  after insert or update on storage.objects
  for each row
  when (NEW.bucket_id = 'user_avatars')
  execute function delete_old_avatar();


-- Improve the delete_user_avatars function with better error handling
create or replace function delete_user_avatars()
returns trigger as $$
declare
  deleted_count int;
begin
  -- Delete all files in the user's folder
  with deleted as (
    delete from storage.objects 
    where bucket_id = 'user_avatars'
    and (storage.foldername(name))[1] = OLD.id::text
    returning *
  )
  select count(*) into deleted_count from deleted;

  -- Log the number of files deleted
  raise notice 'Deleted % avatar files for user %', deleted_count, OLD.id;
  
  return OLD;
exception
  when others then
    -- Log error but don't block the user deletion
    raise warning 'Error in delete_user_avatars: %', SQLERRM;
    return OLD;
end;
$$ language plpgsql security definer;

-- Create trigger to run function when user is deleted
create trigger on_user_delete
  after delete on auth.users
  for each row
  execute function delete_user_avatars();

  

-- Create function to refresh user claims when role changes
create or replace function public.handle_role_change()
returns trigger as $$
begin
  -- Update user metadata
  update auth.users
  set raw_user_meta_data = 
    raw_user_meta_data || 
    jsonb_build_object('user_role', NEW.role::text, 'username', NEW.username, 'stripe_customer_id', NEW.stripe_customer_id, 'stripe_account_id', NEW.stripe_account_id, 'is_stripe_account_active', NEW.is_stripe_account_active, 'is_online', NEW.is_online),
    -- Set a very short refresh time to force token refresh
    -- This will make the current token expire almost immediately
    -- causing the client to automatically request a new one
    updated_at = now()
  where id = NEW.user_id;

  -- Update all existing refresh tokens to require a refresh
  update auth.refresh_tokens
  set updated_at = now(),
      created_at = now() - interval '1 year'
  where user_id = NEW.user_id::text;  -- Cast UUID to text

  return NEW;
end;
$$ language plpgsql security definer;


-- Create trigger to refresh claims when role changes
create trigger on_role_change
  after insert or update of role, is_first_login, username, stripe_customer_id, stripe_account_id, is_stripe_account_active, is_online on public.user_roles
  for each row
  execute function public.handle_role_change();



-- Add policy for admin to update user_roles
create policy "Allow auth admin to update user roles"
on public.user_roles 
for update to supabase_auth_admin
using (true)
with check (true);

grant update on public.user_roles to supabase_auth_admin;

-- Grant ALL permissions on user_roles to supabase_auth_admin
grant all
  on table public.user_roles
to supabase_auth_admin;



-- Revoke permissions from other roles to be explicit
revoke all
  on table public.user_roles
  from authenticated, anon, public;


  -- Add explicit select policy for auth admin
create policy "Allow auth admin to read user roles" ON public.user_roles
as permissive for select
to supabase_auth_admin
using (true);

-- Create function to check and update is_first_login based on metadata
create or replace function public.check_profile_completion()
returns trigger as $$
declare
  bio text;
  avatar_url text;
begin
  -- Extract bio and avatar_url from metadata
  bio := NEW.raw_user_meta_data->>'bio';
  avatar_url := NEW.raw_user_meta_data->>'avatar_url';

  -- Check if both bio and avatar meet the length requirements
  if bio is not null 
    and length(bio) > 3 
    and avatar_url is not null 
    and length(avatar_url) > 3 
  then
    -- Update is_first_login to false in user_roles
    update public.user_roles
    set is_first_login = false
    where user_id = NEW.id
    and is_first_login = true;
    
    -- Directly update the metadata to ensure consistency
    update auth.users
    set raw_user_meta_data = (
        case when raw_user_meta_data ? 'is_first_login' 
             then raw_user_meta_data - 'is_first_login' 
             else raw_user_meta_data 
        end
      ) || jsonb_build_object(
        'is_first_login', false
      ),
      updated_at = now()
    where id = NEW.id
    and (raw_user_meta_data->>'is_first_login')::boolean = true;
  end if;

  return NEW;
exception
  when others then
    -- Log error but don't block the metadata update
    raise warning 'Error in check_profile_completion: %', SQLERRM;
    return NEW;
end;
$$ language plpgsql security definer;


-- Create trigger to run function when user metadata is updated
create trigger on_profile_update
  after update of raw_user_meta_data on auth.users
  for each row
  execute function public.check_profile_completion();

-- Grant necessary permissions
grant update on public.user_roles to postgres;
grant update on public.user_roles to supabase_auth_admin;

CREATE OR REPLACE FUNCTION public.user_heartbeat(user_uuid text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Update the user's updated_at timestamp to indicate activity
  -- Also ensure they're marked as online if they have valid sessions
  UPDATE public.user_roles
  SET
    updated_at = now(),
    is_online = true -- Ensure the user stays online when heartbeats are received
  WHERE user_id = user_uuid::uuid;
END;
$$;