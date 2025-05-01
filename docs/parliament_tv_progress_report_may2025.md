# Parliament TV Capture Enhancement Progress Report

## Date: May 1, 2025

## Overview
This document tracks the progress of the Parliament TV capture enhancement project as outlined in the [Parliament TV Roadmap](parliament_tv_roadmap.md). The project aims to create a more intelligent, automated system for capturing, identifying, and processing parliamentary video content.

## Phase 1: Speaker Identification (May-June 2025)

### Current Progress

#### Core Functionality Improvements
- ✅ Fixed metadata access issues in the backend API
- ✅ Implemented proper error handling for conflicts and invalid streams
- ✅ Integrated Parliament TV capture with main capture UI
- ✅ Added video management interface for viewing and deleting captures
- ✅ Created utilities for cleaning up temporary files
- ✅ Fixed duration handling to prevent excessive capture times

#### Video Management
- ✅ Created ParliamentTVVideoList component for listing captured videos
- ✅ Added video player page for viewing captured videos
- ✅ Implemented API endpoints for streaming video files
- ✅ Added functionality to delete videos and associated files
- ✅ Created command-line utility for managing videos (scripts/manage_parliament_videos.py)

### Next Steps

#### 1.1 Enhanced Facial Recognition (2 weeks)
- [ ] Implement more robust face detection algorithms
- [ ] Create a database of MP faces with multiple reference images per MP
- [ ] Add real-time speaker identification during capture
- [ ] Store speaker metadata with timestamps in the capture session

#### 1.2 Speaker Diarization (2 weeks)
- [ ] Implement voice recognition for speaker identification
- [ ] Combine facial and voice recognition for more accurate identification
- [ ] Create a system to timestamp speaker changes
- [ ] Develop an API endpoint for retrieving speaker segments

#### 1.3 MP Profile Management (1 week)
- [ ] Create an interface for managing MP profiles
- [ ] Build functionality to add/update reference images for MPs
- [ ] Implement batch import of MP data from parliamentary resources
- [ ] Add ability to correct misidentified speakers

## Technical Challenges & Solutions

### Metadata Access in SQLAlchemy
We encountered issues with accessing metadata in the Parliament TV API endpoints. The SQLAlchemy `MetaData` object doesn't support dictionary-like methods like `has_key()` or `get()`. We implemented a more robust approach that checks if metadata is a dictionary and uses proper dictionary access patterns.

### Video File Management
The system was accumulating numerous temporary files during testing and validation. We've implemented:
1. A cleanup endpoint in the API to remove temporary files
2. A command-line utility for managing video files
3. A UI component for viewing and deleting videos

### Capture Duration Control
We identified that captures were running longer than expected. We've improved the duration handling to ensure captures stop after the specified duration or when facial recognition detects the speaker is no longer present.

## Resources Needed for Next Phase

### Development Resources
- Access to a GPU server for facial recognition training and testing
- Additional storage for MP face database and reference images
- Test data with known speakers for accuracy evaluation

### External Dependencies
- Face recognition library with custom training capabilities
- Voice recognition system for speaker diarization
- Parliament MP database or API for profile information

## Timeline Update
We are on track with the roadmap timeline. Phase 1.1 (Enhanced Facial Recognition) will begin immediately and is expected to be completed by mid-May 2025.

## Conclusion
The foundation for the Parliament TV capture enhancement project has been successfully established. The core functionality is working correctly, and we've added tools for managing captured videos. The next phase will focus on implementing speaker identification and diarization capabilities.
