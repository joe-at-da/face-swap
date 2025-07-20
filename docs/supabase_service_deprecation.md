# SupabaseService Deprecation Plan

## Current Status

The `SupabaseService` class in `backend/services/integration/supabase_client.py` was previously marked for deprecation in favor of the newer `SupabaseUploader` class. However, the deprecation warnings have been temporarily removed to avoid disrupting existing functionality while the migration is in progress.

## Methods Requiring Migration

The following methods in `SupabaseService` need to be migrated to `SupabaseUploader`:

- `insert_video`
- `insert_clip`
- `get_video_status`
- `upload_file`
- `get_public_url`
- `upload_full_video`
- `add_to_video_processing_queue`
- `add_to_clip_creation_queue`

## Migration Plan

1. **Identify Dependencies**: Find all code that currently uses `SupabaseService` methods
2. **Update Dependencies**: Modify dependent code to use `SupabaseUploader` instead
3. **Testing**: Ensure all functionality works with the new implementation
4. **Re-add Deprecation Warnings**: Once dependencies are updated, re-add deprecation warnings
5. **Final Removal**: Eventually remove the `SupabaseService` class entirely

## Implementation Notes

- The `upload_full_video` method has already been partially updated to handle large files better
- The `SupabaseUploader` class provides better support for large file uploads with extended timeouts
- For backward compatibility, both classes should coexist until all dependencies are migrated

## Technical Debt

This represents technical debt that should be addressed in future sprints. The goal is to have a single, well-maintained interface for Supabase operations through the `SupabaseUploader` class.

## Timeline

- **Short-term**: Keep both implementations working side by side
- **Mid-term**: Add back deprecation warnings once dependencies are migrated
- **Long-term**: Remove `SupabaseService` entirely
