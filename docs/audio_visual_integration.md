# Audio-Visual Recognition Integration Plan

## Overview

This document outlines the plan to integrate our existing facial recognition and voice recognition systems to create a comprehensive audio-visual recognition solution. The goal is to synchronize face detections with speaker segments to provide a unified view of who is speaking and when they appear in the video.

## Current State

### Facial Recognition System
- ✅ Face detection in video frames
- ✅ Face recognition against known profiles
- ✅ Unidentified face display and management
- ✅ Timestamp information for each face detection
- ✅ UI for viewing and managing face detections

### Voice Recognition System
- ✅ Speaker diarization (segmenting audio by speaker)
- ✅ Voice profile matching
- ✅ Speaker identification with timestamps
- ✅ UI for viewing speaker segments in transcriptions

## Integration Plan

### 1. Data Structure Alignment (Backend)

#### 1.1 Unified Results Schema
Create a unified schema that combines facial and voice recognition results:

```json
{
  "video_id": "123",
  "duration": 600,
  "faces": [
    {
      "id": "face_1",
      "person_id": "mp_1",
      "name": "John Smith",
      "confidence": 0.92,
      "timestamps": [
        {"start": 10.5, "end": 15.2, "frame_path": "/path/to/frame.jpg"},
        {"start": 45.8, "end": 52.3, "frame_path": "/path/to/frame2.jpg"}
      ]
    }
  ],
  "speakers": [
    {
      "id": "speaker_1",
      "person_id": "mp_1",
      "name": "John Smith",
      "confidence": 0.87,
      "segments": [
        {"start": 9.8, "end": 16.5, "text": "Thank you, Mr. Speaker."},
        {"start": 45.2, "end": 53.1, "text": "I would like to address the concerns raised."}
      ]
    }
  ],
  "correlations": [
    {
      "face_id": "face_1",
      "speaker_id": "speaker_1",
      "confidence": 0.95,
      "segments": [
        {"start": 10.5, "end": 15.2, "type": "synchronized"}
      ]
    }
  ]
}
```

#### 1.2 Database Model Updates
Extend existing models to support correlations:

- Add `MultimodalCorrelation` model to link face detections with speaker segments
- Add correlation confidence scores
- Add correlation metadata (method used, timestamp overlap)

### 2. Correlation Algorithm (Backend)

#### 2.1 Timestamp-Based Matching
Implement an algorithm to match faces and voices based on temporal proximity:

```python
def correlate_faces_and_voices(faces, speakers, max_gap=0.5):
    correlations = []
    
    for face in faces:
        for face_timestamp in face["timestamps"]:
            face_start, face_end = face_timestamp["start"], face_timestamp["end"]
            
            for speaker in speakers:
                for segment in speaker["segments"]:
                    speaker_start, speaker_end = segment["start"], segment["end"]
                    
                    # Check for overlap
                    if (face_start <= speaker_end + max_gap and 
                        face_end + max_gap >= speaker_start):
                        
                        # Calculate overlap duration
                        overlap_start = max(face_start, speaker_start)
                        overlap_end = min(face_end, speaker_end)
                        overlap_duration = max(0, overlap_end - overlap_start)
                        
                        # Calculate confidence based on overlap
                        face_duration = face_end - face_start
                        segment_duration = speaker_end - speaker_start
                        overlap_ratio = overlap_duration / min(face_duration, segment_duration)
                        
                        # Only add if significant overlap
                        if overlap_ratio > 0.3:
                            correlations.append({
                                "face_id": face["id"],
                                "speaker_id": speaker["id"],
                                "confidence": overlap_ratio,
                                "segments": [{
                                    "start": overlap_start,
                                    "end": overlap_end,
                                    "type": "synchronized"
                                }]
                            })
    
    return correlations
```

#### 2.2 Identity-Based Correlation
Enhance matching when both systems identify the same person:

```python
def enhance_correlations_with_identity(correlations, faces, speakers):
    for correlation in correlations:
        face = next(f for f in faces if f["id"] == correlation["face_id"])
        speaker = next(s for s in speakers if s["id"] == correlation["speaker_id"])
        
        # If both systems identified the same person, boost confidence
        if (face.get("person_id") and speaker.get("person_id") and 
            face["person_id"] == speaker["person_id"]):
            
            # Combine confidence scores
            face_conf = face.get("confidence", 0.5)
            speaker_conf = speaker.get("confidence", 0.5)
            time_conf = correlation["confidence"]
            
            # Weighted average with higher weight for temporal match
            correlation["confidence"] = (
                0.6 * time_conf + 
                0.2 * face_conf + 
                0.2 * speaker_conf
            )
            
            correlation["match_type"] = "identity_confirmed"
        else:
            correlation["match_type"] = "temporal_only"
    
    return correlations
```

#### 2.3 Conflict Resolution
Implement logic to resolve conflicts when multiple faces or speakers overlap:

- Prioritize matches with higher confidence scores
- Consider speaker continuity (prefer matching the same speaker across segments)
- Use face tracking data to maintain consistent identity

### 3. API Endpoints (Backend)

#### 3.1 Unified Recognition Results
Create a new endpoint to retrieve combined results:

```python
@router.get("/recognition/multimodal/{capture_id}")
async def get_multimodal_recognition(
    capture_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get facial recognition results
    face_results = await get_facial_recognition_results(capture_id, db)
    
    # Get voice recognition results
    voice_results = await get_voice_recognition_results(capture_id, db)
    
    # Correlate results
    correlations = correlate_faces_and_voices(
        face_results.get("faces", []),
        voice_results.get("speakers", [])
    )
    
    # Enhance with identity information
    correlations = enhance_correlations_with_identity(
        correlations, 
        face_results.get("faces", []),
        voice_results.get("speakers", [])
    )
    
    # Return unified results
    return {
        "video_id": capture_id,
        "faces": face_results.get("faces", []),
        "speakers": voice_results.get("speakers", []),
        "correlations": correlations
    }
```

#### 3.2 Timeline Data
Create an endpoint to provide timeline data for visualization:

```python
@router.get("/recognition/timeline/{capture_id}")
async def get_recognition_timeline(
    capture_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get multimodal results
    results = await get_multimodal_recognition(capture_id, db, current_user)
    
    # Format for timeline visualization
    timeline_data = []
    
    # Add face detections to timeline
    for face in results.get("faces", []):
        for timestamp in face.get("timestamps", []):
            timeline_data.append({
                "type": "face",
                "id": face["id"],
                "person_id": face.get("person_id"),
                "name": face.get("name", "Unknown"),
                "start": timestamp["start"],
                "end": timestamp["end"],
                "confidence": face.get("confidence", 0),
                "image_path": timestamp.get("frame_path")
            })
    
    # Add speaker segments to timeline
    for speaker in results.get("speakers", []):
        for segment in speaker.get("segments", []):
            timeline_data.append({
                "type": "speaker",
                "id": speaker["id"],
                "person_id": speaker.get("person_id"),
                "name": speaker.get("name", "Unknown"),
                "start": segment["start"],
                "end": segment["end"],
                "confidence": speaker.get("confidence", 0),
                "text": segment.get("text", "")
            })
    
    # Sort by start time
    timeline_data.sort(key=lambda x: x["start"])
    
    return {
        "video_id": capture_id,
        "timeline": timeline_data
    }
```

### 4. Frontend Implementation

#### 4.1 Unified Recognition Results Component
Create a new React component to display the integrated results:

```tsx
// components/recognition/UnifiedRecognitionResults.tsx
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { formatTime } from '../../utils/formatTime';

interface TimelineItem {
  type: 'face' | 'speaker';
  id: string;
  person_id?: string;
  name: string;
  start: number;
  end: number;
  confidence: number;
  image_path?: string;
  text?: string;
}

interface UnifiedResultsProps {
  videoId: string;
}

const UnifiedRecognitionResults: React.FC<UnifiedResultsProps> = ({ videoId }) => {
  const [timelineData, setTimelineData] = useState<TimelineItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const router = useRouter();
  
  useEffect(() => {
    const fetchTimelineData = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/recognition/timeline/${videoId}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch timeline data');
        }
        
        const data = await response.json();
        setTimelineData(data.timeline);
      } catch (err) {
        setError('Error loading recognition data');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    
    if (videoId) {
      fetchTimelineData();
    }
  }, [videoId]);
  
  // Group timeline items by person
  const personGroups = timelineData.reduce((groups, item) => {
    const personId = item.person_id || item.id;
    if (!groups[personId]) {
      groups[personId] = {
        personId,
        name: item.name,
        items: []
      };
    }
    groups[personId].items.push(item);
    return groups;
  }, {});
  
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4 dark:text-white">Unified Recognition Results</h2>
      
      {isLoading && <p className="text-gray-500 dark:text-gray-400">Loading recognition data...</p>}
      {error && <p className="text-red-500">{error}</p>}
      
      {!isLoading && !error && (
        <div className="space-y-6">
          {Object.values(personGroups).map((group) => (
            <div key={group.personId} className="border border-gray-200 dark:border-gray-700 rounded-md p-4">
              <h3 className="text-lg font-medium mb-2 dark:text-white">{group.name}</h3>
              
              <div className="space-y-4">
                {/* Face appearances */}
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Appearances</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {group.items.filter(item => item.type === 'face').map((item, index) => (
                      <div key={`${item.id}-${index}`} className="border border-gray-200 dark:border-gray-700 rounded p-2">
                        {item.image_path && (
                          <div className="mb-2">
                            <img 
                              src={item.image_path} 
                              alt={`${item.name} at ${formatTime(item.start)}`}
                              className="w-full h-32 object-contain rounded cursor-pointer"
                              onClick={() => {/* Open full image modal */}}
                            />
                          </div>
                        )}
                        <div className="text-sm">
                          <p className="text-gray-700 dark:text-gray-300">
                            Time: {formatTime(item.start)} - {formatTime(item.end)}
                          </p>
                          <p className="text-gray-500 dark:text-gray-400">
                            Confidence: {Math.round(item.confidence * 100)}%
                          </p>
                          <button
                            onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(item.start)}`)}
                            className="mt-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-sm py-1 px-3 rounded transition-colors"
                          >
                            Jump to {formatTime(item.start)}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* Speaker segments */}
                <div>
                  <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Speech Segments</h4>
                  <div className="space-y-2">
                    {group.items.filter(item => item.type === 'speaker').map((item, index) => (
                      <div key={`${item.id}-${index}`} className="border border-gray-200 dark:border-gray-700 rounded p-3">
                        <p className="text-gray-700 dark:text-gray-300 mb-1">
                          {item.text}
                        </p>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500 dark:text-gray-400">
                            {formatTime(item.start)} - {formatTime(item.end)}
                          </span>
                          <span className="text-gray-500 dark:text-gray-400">
                            Confidence: {Math.round(item.confidence * 100)}%
                          </span>
                        </div>
                        <button
                          onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(item.start)}`)}
                          className="mt-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-sm py-1 px-3 rounded transition-colors"
                        >
                          Jump to {formatTime(item.start)}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UnifiedRecognitionResults;
```

#### 4.2 Timeline Visualization Component
Create a visual timeline component to show speaker and face detections:

```tsx
// components/recognition/RecognitionTimeline.tsx
import React, { useState, useRef, useEffect } from 'react';
import { formatTime } from '../../utils/formatTime';

interface TimelineItem {
  type: 'face' | 'speaker';
  id: string;
  person_id?: string;
  name: string;
  start: number;
  end: number;
  confidence: number;
  image_path?: string;
  text?: string;
}

interface TimelineProps {
  data: TimelineItem[];
  duration: number;
  currentTime: number;
  onSeek: (time: number) => void;
}

const RecognitionTimeline: React.FC<TimelineProps> = ({ 
  data, 
  duration, 
  currentTime, 
  onSeek 
}) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(100); // pixels per second
  const [hoveredItem, setHoveredItem] = useState<TimelineItem | null>(null);
  
  // Group items by person
  const personGroups = data.reduce((groups, item) => {
    const personId = item.person_id || item.id;
    if (!groups[personId]) {
      groups[personId] = {
        personId,
        name: item.name,
        items: []
      };
    }
    groups[personId].items.push(item);
    return groups;
  }, {});
  
  // Calculate timeline width
  const timelineWidth = duration * scale;
  
  // Handle timeline click
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickedTime = (clickX / timelineWidth) * duration;
    
    onSeek(clickedTime);
  };
  
  // Convert time to position
  const timeToPosition = (time: number) => {
    return (time / duration) * timelineWidth;
  };
  
  return (
    <div className="mt-4">
      <h3 className="text-lg font-medium mb-2 dark:text-white">Recognition Timeline</h3>
      
      <div className="relative overflow-x-auto" style={{ height: Object.keys(personGroups).length * 60 + 40 }}>
        {/* Timeline header */}
        <div className="sticky top-0 bg-white dark:bg-gray-900 z-10 border-b border-gray-200 dark:border-gray-700 pb-2">
          <div className="flex">
            <div className="w-32 flex-shrink-0 pr-2 font-medium dark:text-white">Person</div>
            <div 
              ref={timelineRef}
              className="relative flex-grow" 
              style={{ width: timelineWidth }}
              onClick={handleTimelineClick}
            >
              {/* Time markers */}
              {Array.from({ length: Math.ceil(duration / 60) + 1 }).map((_, i) => (
                <div 
                  key={i} 
                  className="absolute top-0 bottom-0 border-l border-gray-300 dark:border-gray-700"
                  style={{ left: timeToPosition(i * 60) }}
                >
                  <div className="text-xs text-gray-500 dark:text-gray-400 ml-1">
                    {formatTime(i * 60)}
                  </div>
                </div>
              ))}
              
              {/* Current time indicator */}
              <div 
                className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20"
                style={{ left: timeToPosition(currentTime) }}
              />
            </div>
          </div>
        </div>
        
        {/* Timeline rows */}
        <div className="mt-2">
          {Object.values(personGroups).map((group) => (
            <div key={group.personId} className="flex mb-2">
              <div className="w-32 flex-shrink-0 pr-2 text-sm font-medium dark:text-white truncate">
                {group.name}
              </div>
              <div 
                className="relative flex-grow" 
                style={{ height: 40, width: timelineWidth }}
              >
                {/* Face items */}
                {group.items.filter(item => item.type === 'face').map((item, index) => (
                  <div
                    key={`face-${item.id}-${index}`}
                    className="absolute h-4 bg-blue-400 dark:bg-blue-600 rounded-sm cursor-pointer z-10 top-0"
                    style={{ 
                      left: timeToPosition(item.start),
                      width: timeToPosition(item.end - item.start),
                      opacity: 0.7 + (item.confidence * 0.3)
                    }}
                    onClick={() => onSeek(item.start)}
                    onMouseEnter={() => setHoveredItem(item)}
                    onMouseLeave={() => setHoveredItem(null)}
                  />
                ))}
                
                {/* Speaker items */}
                {group.items.filter(item => item.type === 'speaker').map((item, index) => (
                  <div
                    key={`speaker-${item.id}-${index}`}
                    className="absolute h-4 bg-green-400 dark:bg-green-600 rounded-sm cursor-pointer z-10 bottom-0"
                    style={{ 
                      left: timeToPosition(item.start),
                      width: timeToPosition(item.end - item.start),
                      opacity: 0.7 + (item.confidence * 0.3)
                    }}
                    onClick={() => onSeek(item.start)}
                    onMouseEnter={() => setHoveredItem(item)}
                    onMouseLeave={() => setHoveredItem(null)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Tooltip */}
      {hoveredItem && (
        <div className="fixed bg-white dark:bg-gray-800 shadow-lg rounded p-2 z-50 max-w-xs">
          <div className="font-medium dark:text-white">{hoveredItem.name}</div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {formatTime(hoveredItem.start)} - {formatTime(hoveredItem.end)}
          </div>
          {hoveredItem.type === 'speaker' && hoveredItem.text && (
            <div className="text-sm mt-1 dark:text-gray-300">"{hoveredItem.text}"</div>
          )}
          {hoveredItem.type === 'face' && hoveredItem.image_path && (
            <div className="mt-1">
              <img 
                src={hoveredItem.image_path} 
                alt={hoveredItem.name} 
                className="w-24 h-24 object-contain"
              />
            </div>
          )}
        </div>
      )}
      
      <div className="flex items-center mt-2">
        <div className="flex items-center mr-4">
          <div className="w-4 h-4 bg-blue-400 dark:bg-blue-600 rounded-sm mr-1"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">Face Detection</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-green-400 dark:bg-green-600 rounded-sm mr-1"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">Voice Detection</span>
        </div>
      </div>
    </div>
  );
};

export default RecognitionTimeline;
```

#### 4.3 Integration with Existing Pages
Update the recognition results page to include the new components:

```tsx
// pages/recognition/results/[id].tsx
// Add to imports
import UnifiedRecognitionResults from '../../../components/recognition/UnifiedRecognitionResults';
import RecognitionTimeline from '../../../components/recognition/RecognitionTimeline';

// Add to the component
const [activeTab, setActiveTab] = useState('unified'); // Add this state

// Add to the tabs section
<div className="mb-4 border-b border-gray-200 dark:border-gray-700">
  <ul className="flex flex-wrap -mb-px">
    <li className="mr-2">
      <button
        className={`inline-block p-4 ${
          activeTab === 'unified'
            ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-500 dark:border-blue-500'
            : 'text-gray-500 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-300'
        }`}
        onClick={() => setActiveTab('unified')}
      >
        Unified Results
      </button>
    </li>
    <li className="mr-2">
      <button
        className={`inline-block p-4 ${
          activeTab === 'faces'
            ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-500 dark:border-blue-500'
            : 'text-gray-500 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-300'
        }`}
        onClick={() => setActiveTab('faces')}
      >
        Faces
      </button>
    </li>
    <li className="mr-2">
      <button
        className={`inline-block p-4 ${
          activeTab === 'speakers'
            ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-500 dark:border-blue-500'
            : 'text-gray-500 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-300'
        }`}
        onClick={() => setActiveTab('speakers')}
      >
        Speakers
      </button>
    </li>
  </ul>
</div>

{/* Tab content */}
{activeTab === 'unified' && (
  <>
    <RecognitionTimeline
      data={timelineData}
      duration={videoDuration}
      currentTime={currentTime}
      onSeek={handleSeek}
    />
    <UnifiedRecognitionResults videoId={id} />
  </>
)}
{activeTab === 'faces' && (
  <CustomRecognitionResults
    videoId={id}
    speakerResults={recognitionResults}
    transcriptionText={transcriptionText}
  />
)}
{activeTab === 'speakers' && (
  <SpeakerResults
    videoId={id}
    speakerResults={recognitionResults}
  />
)}
```

### 5. Testing Plan

#### 5.1 Unit Tests
- Test correlation algorithm with various scenarios
- Test timeline data formatting
- Test API endpoints with mock data

#### 5.2 Integration Tests
- Test combined facial and voice recognition processing
- Test data flow from backend to frontend
- Test timeline visualization with real data

#### 5.3 End-to-End Tests
- Test complete workflow from video upload to unified results
- Test with various video types and durations
- Test with known and unknown faces/voices

### 6. Implementation Timeline

#### Week 1: Backend Development
- Day 1-2: Create unified data schema and database models
- Day 3-4: Implement correlation algorithm
- Day 5: Develop and test API endpoints

#### Week 2: Frontend Development
- Day 1-2: Create unified recognition results component
- Day 3-4: Implement timeline visualization
- Day 5: Integrate with existing pages and test

#### Week 3: Testing and Refinement
- Day 1-2: Unit and integration testing
- Day 3-4: End-to-end testing and bug fixes
- Day 5: Documentation and final review

## Success Criteria

1. **Technical Success**
   - Successful correlation of face and voice data with >80% accuracy
   - Timeline visualization showing synchronized data
   - Unified UI for viewing multimodal recognition results

2. **User Experience Success**
   - Users can easily identify who is speaking and when they appear
   - Navigation between video, faces, and transcription is seamless
   - Performance remains smooth even with large videos

3. **Business Success**
   - Improved accuracy in speaker identification
   - Reduced manual effort in identifying speakers
   - Enhanced value proposition for parliamentary video analysis

## Future Enhancements

1. **Advanced Correlation**
   - Use lip movement detection to improve synchronization
   - Implement machine learning for correlation confidence scoring
   - Add support for multiple faces in the same frame

2. **Enhanced Visualization**
   - Add heat map view of speaker activity
   - Implement side-by-side comparison of face and voice matches
   - Create exportable reports with synchronized data

3. **Performance Optimization**
   - Implement caching for correlation results
   - Optimize timeline rendering for very long videos
   - Add pagination for large result sets
