# Parliament TV Capture Enhancement Roadmap

## Overview
This roadmap outlines the planned enhancements for the Parliament TV capture functionality in the MP Video Clip Manager. The goal is to create a more intelligent, automated system for capturing, identifying, and processing parliamentary video content.

## Current Status (May 3, 2025)
- ✅ Basic Parliament TV capture functionality implemented
- ✅ Stream URL extraction and validation with support for both video and audio streams
- ✅ Active capture detection and management
- ✅ Integration with main capture UI
- ✅ Facial recognition-based capture termination
- ✅ Error handling for conflicts and invalid streams
- ✅ Fixed NoneType errors in capture process
- ✅ Improved video and audio stream handling
- ✅ Enhanced ffmpeg integration for combining video and audio
- ✅ Robust path handling with directory creation

## Phase 1: Speaker Identification (May-June 2025)

### 1.1 Enhanced Facial Recognition (2 weeks)
- [ ] Implement more robust face detection algorithms
- [ ] Create a database of MP faces with multiple reference images per MP
- [ ] Add real-time speaker identification during capture
- [ ] Store speaker metadata with timestamps in the capture session

### 1.2 Speaker Diarization (2 weeks)
- [ ] Implement voice recognition for speaker identification
- [ ] Combine facial and voice recognition for more accurate identification
- [ ] Create a system to timestamp speaker changes
- [ ] Develop an API endpoint for retrieving speaker segments

### 1.3 MP Profile Management (1 week)
- [ ] Create an interface for managing MP profiles
- [ ] Build functionality to add/update reference images for MPs
- [ ] Implement batch import of MP data from parliamentary resources
- [ ] Add ability to correct misidentified speakers

## Phase 2: Intelligent Video Processing (June-July 2025)

### 2.1 Automatic Clip Segmentation (2 weeks)
- [ ] Develop algorithms to detect natural segment boundaries (topic changes, speaker changes)
- [ ] Implement automatic clip creation based on speaker changes
- [ ] Create a "follow this speaker" feature to compile all segments of a specific MP
- [ ] Add intelligent clip naming based on speaker and content

### 2.2 Transcription Enhancement (2 weeks)
- [ ] Improve transcription accuracy with parliamentary-specific vocabulary
- [ ] Link transcription timestamps with video segments
- [ ] Add speaker attribution to transcription segments
- [ ] Implement searchable transcriptions with speaker filtering

### 2.3 Topic Detection (2 weeks)
- [ ] Implement NLP for topic detection in transcribed content
- [ ] Create automatic tagging of clips based on detected topics
- [ ] Develop a topic clustering system for related clips
- [ ] Add topic-based search and filtering

## Phase 3: User Experience & Integration (July-August 2025)

### 3.1 Enhanced Timeline UI (2 weeks)
- [ ] Develop a visual timeline with speaker markers
- [ ] Add color coding for different speakers
- [ ] Implement topic markers on the timeline
- [ ] Create an interactive timeline for clip selection

### 3.2 Parliamentary Data Integration (2 weeks)
- [ ] Connect with parliamentary APIs for session information
- [ ] Link clips to relevant parliamentary documents
- [ ] Add contextual information about debates or sessions
- [ ] Implement automatic tagging with bill numbers, debate topics

### 3.3 Batch Processing & Export (1 week)
- [ ] Add batch processing for multiple clips
- [ ] Implement export options for speaker-specific compilations
- [ ] Create automated reports of MP speaking time
- [ ] Develop scheduled capture and processing workflows

## Phase 4: Advanced Features (August-September 2025)

### 4.1 Sentiment Analysis (2 weeks)
- [ ] Implement sentiment analysis on transcribed content
- [ ] Add visual indicators for sentiment on the timeline
- [ ] Create reports on sentiment by speaker or topic
- [ ] Develop alerts for highly emotional segments

### 4.2 Automatic Highlights (2 weeks)
- [ ] Develop algorithms to detect important moments in debates
- [ ] Implement automatic highlight reel creation
- [ ] Add customizable criteria for highlight detection
- [ ] Create shareable highlight compilations

### 4.3 Performance Optimization (1 week)
- [ ] Optimize facial recognition for real-time processing
- [ ] Improve video processing speed
- [ ] Implement caching strategies for processed video
- [ ] Enhance resource management for concurrent captures

## Technical Requirements

### Infrastructure
- Dedicated GPU resources for facial recognition and video processing
- Increased storage capacity for reference images and processed video
- Optimized database schema for speaker and segment metadata

### Dependencies
- OpenCV for enhanced video processing
- face_recognition library with custom training
- Whisper or similar for improved transcription
- BERT/GPT for topic detection and sentiment analysis
- FFmpeg for advanced video manipulation

### Monitoring & Metrics
- Processing time per minute of video
- Facial recognition accuracy metrics
- Speaker identification success rate
- Transcription accuracy measurements

## Success Criteria
- 90%+ accuracy in speaker identification
- Reduction in manual clip creation time by 75%
- Searchable archive of parliamentary content by speaker, topic, and sentiment
- Seamless integration with existing clip editing and sharing workflows

## Risks & Mitigations
- **Risk**: High computational requirements for real-time processing
  - **Mitigation**: Implement asynchronous processing and optimize algorithms

- **Risk**: Accuracy challenges with similar-looking MPs or poor lighting conditions
  - **Mitigation**: Use multiple identification methods and allow manual corrections

- **Risk**: Integration complexity with parliamentary data sources
  - **Mitigation**: Create flexible adapters and fallback mechanisms

## Next Immediate Steps

### Immediate (1-2 weeks):
1. Enhance stream format detection to better identify and process various Parliament TV stream types
2. Implement automatic retry mechanisms for failed captures
3. Add stream quality selection options in the capture UI
4. Create more comprehensive logging for capture diagnostics

### Short-term (2-4 weeks):
1. Begin development of enhanced facial recognition system
2. Create database schema for MP profiles and reference images
3. Implement basic speaker identification during capture
4. Develop prototype of speaker timeline visualization

This roadmap will be reviewed and updated monthly based on progress and changing requirements.
