# Parliament Member Embedding System Fix

This document describes the comprehensive fix applied to the embedding system for reliable member recognition in Parliament TV streams.

## Problem Summary

The embedding system had several issues that prevented reliable member recognition:

1. Inconsistent embedding normalization between cache and matcher
2. Member ID format inconsistencies (string vs integer)
3. Improper similarity calculation in the matcher
4. Low default confidence threshold (0.1)
5. Database ID mismatches between SQLite and PostgreSQL

## Solution

The `comprehensive_embedding_fix.py` script implements a complete solution:

1. Normalizes all embeddings in the cache for consistent similarity calculation
2. Fixes the embedding module to properly handle and normalize embeddings
3. Updates the matcher module to correctly load and process embeddings
4. Adds detailed logging for transparency and debugging
5. Creates a visual debug tool for testing and verification
6. Increases the default confidence threshold to 0.5

## Key Changes

1. **Embedding Normalization**: All embeddings are consistently normalized to unit length before similarity calculation
2. **Member ID Handling**: All member IDs are consistently handled as strings
3. **Similarity Calculation**: The dot product is calculated between normalized embeddings
4. **Confidence Threshold**: Default threshold increased from 0.1 to 0.5
5. **Transparency**: Added detailed logging and visual debugging
6. **Database Consistency**: Ensured consistent member ID handling between SQLite and PostgreSQL

## Testing

The fix has been tested with real Parliament TV frames and shows high accuracy in member recognition. The visual debug tool provides clear feedback on recognition results.

## Visual Debug Tool

A new visual debug tool has been created at `/app/backend/tools/visual_debug.py` to help with testing and verification. It can be run with:

```bash
docker compose -f docker-compose.dev.yml exec app python /app/backend/tools/visual_debug.py --image /path/to/test/image.jpg
```

Options:
- `--image`: Path to the input image (default: `/app/data/temp/recognition/test_frame.jpg`)
- `--threshold`: Confidence threshold for matching (default: 0.5)
- `--house`: House ID to filter members (1=Commons, 2=Lords, None=All) (default: 1)
- `--output`: Output directory for debug images (default: `/app/data/temp/recognition/debug`)

## Clean-up

After verifying the fix works correctly, you can safely remove the following files:

```bash
# Test and fix scripts
rm analyze_darren_embedding.py analyze_embeddings.py check_darren_in_db.py check_house_filtering.py
rm compare_darren_face.py darren_jones_fix.py darren_jones_fix_corrected.py debug_matcher_decision.py
rm direct_darren_fix.py extract_darren_frame.py final_darren_fix.py final_darren_fix_corrected.py
rm final_darren_jones_fix.py final_darren_jones_fix_corrected.py final_embedding_fix.py final_fix.py
rm final_matcher_fix.py find_darren_in_rankings.py fix_darren_jones_embedding.py fix_darren_jones_specific.py
rm fix_darren_recognition.py fix_embedding_system.py fix_id_mismatch.py fix_matcher_comprehensive.py
rm fix_matcher_embedding.py fix_member_data.py inspect_member_data.py investigate_embedding_mismatch.py
rm show_frame.py simple_fix.py simple_verify_darren.py test_darren_match.py test_darren_visual.py
rm test_parliament_tv_match.py test_real_stream.py test_video_face_match.py test_visual_debug.py
rm trace_matcher_loading.py update_darren_embedding.py update_matcher.py verify_darren_jones_embedding.py
rm verify_darren_recognition.py

# Keep only comprehensive_embedding_fix.py for reference
```

## Database ID Handling

The system now properly handles the member ID format differences between SQLite and PostgreSQL:

1. **SQLite Database**: Uses UUID strings for member IDs in the parliament_clips table
2. **PostgreSQL Database**: Requires integer member IDs in the parliament_member_clips table
3. **Conversion Process**: 
   - Member IDs are consistently handled as strings within the recognition system
   - During export to PostgreSQL, IDs are validated against the parliament_members table
   - No fallback mechanisms are used that might mask problems with fake data
   - Clear error reporting is provided for invalid member IDs

## Future Improvements

1. Add unit tests for the embedding and matcher modules
2. Implement periodic validation of the embedding cache
3. Add more detailed logging for production troubleshooting
4. Consider implementing a confidence score calibration system
5. Create a unified member ID management system across all databases
