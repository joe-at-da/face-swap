-- Update the user_avatars bucket to be public
update storage.buckets
set public = true
where id = 'user_avatars';

-- Drop existing RLS policies for user_avatars bucket
drop policy if exists "Users can view their own avatar" on storage.objects;
drop policy if exists "Users can upload their own avatar" on storage.objects;
drop policy if exists "Users can update their own avatar" on storage.objects;
drop policy if exists "Users can delete their own avatar" on storage.objects;

-- Create new policies that allow public viewing but maintain user control over their own avatars
create policy "Public can view all avatars" on storage.objects for select
using (bucket_id = 'user_avatars');

create policy "Users can upload their own avatar" on storage.objects for insert
with check (
  bucket_id = 'user_avatars'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "Users can update their own avatar" on storage.objects for update
using (
  bucket_id = 'user_avatars'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "Users can delete their own avatar" on storage.objects for delete
using (
  bucket_id = 'user_avatars'
  and auth.uid()::text = (storage.foldername(name))[1]
);

-- Add comment explaining the changes
-- comment on table storage.objects is 'User avatars are now publicly viewable, but users can only modify their own avatars.';