# Speaker Diarization Improvements for Long Audio Files

## Current Issues with One-Hour Files

The current speaker diarization system works well for short clips (1-5 minutes) but fails with longer files (60+ minutes) due to:

1. **Too Many Segments**: Creates excessive speaker segments that don't properly group similar voices
2. **Memory Usage**: Processing entire files at once leads to memory and computational inefficiency
3. **Feature Scaling**: Fixed window and step sizes don't scale well to longer durations
4. **Threshold Adaptation**: Dynamic thresholding becomes less effective across long files

## Proposed Improvements

### 1. Chunked Processing (HIGH PRIORITY)

Process long files in manageable chunks (5-10 minutes each) and then merge results:

```python
def process_in_chunks(audio_path, chunk_duration=300):  # 5-minute chunks
    """Process a long audio file in chunks"""
    y, sr = librosa.load(audio_path, sr=None)
    audio_duration = len(y) / sr
    
    all_segments = []
    
    # Process in chunks
    chunk_samples = int(chunk_duration * sr)
    for i in range(0, len(y), chunk_samples):
        chunk = y[i:i+chunk_samples]
        chunk_offset = i / sr
        
        # Process this chunk
        chunk_segments = process_chunk(chunk, sr)
        
        # Adjust timestamps
        for segment in chunk_segments:
            segment["start_time"] += chunk_offset
            segment["end_time"] += chunk_offset
        
        all_segments.extend(chunk_segments)
    
    # Merge adjacent segments from the same speaker
    merged_segments = merge_adjacent_segments(all_segments)
    
    return merged_segments
```

### 2. Speaker Clustering (HIGH PRIORITY)

Instead of assigning unique speaker IDs sequentially, cluster segments by acoustic similarity:

```python
def cluster_speakers(segments, audio_data, sr, max_speakers=8):
    """Cluster segments by speaker similarity"""
    # Extract features for each segment
    segment_features = []
    for segment in segments:
        start_sample = int(segment["start_time"] * sr)
        end_sample = int(segment["end_time"] * sr)
        segment_audio = audio_data[start_sample:end_sample]
        
        # Extract i-vector or d-vector features
        features = extract_speaker_embedding(segment_audio, sr)
        segment_features.append(features)
    
    # Cluster features
    from sklearn.cluster import AgglomerativeClustering
    clustering = AgglomerativeClustering(
        n_clusters=min(max_speakers, len(segments)),
        affinity='cosine',
        linkage='average'
    )
    labels = clustering.fit_predict(segment_features)
    
    # Assign cluster labels as speaker IDs
    for i, segment in enumerate(segments):
        segment["speaker"] = f"SPEAKER_{labels[i]+1}"
        segment["speech_group_id"] = labels[i]+1
    
    return segments
```

### 3. Adaptive Window Sizing (MEDIUM PRIORITY)

Adjust window and step sizes based on file duration:

```python
def calculate_window_parameters(audio_duration):
    """Calculate appropriate window and step sizes based on audio duration"""
    # For longer files, use larger windows
    if audio_duration > 1800:  # > 30 minutes
        window_size = 2.0
        step_size = 1.0
    elif audio_duration > 600:  # > 10 minutes
        window_size = 1.5
        step_size = 0.75
    else:
        window_size = 1.0
        step_size = 0.5
        
    return window_size, step_size
```

### 4. Segment Merging (MEDIUM PRIORITY)

Merge adjacent segments from the same speaker to reduce fragmentation:

```python
def merge_adjacent_segments(segments, max_gap=1.0, similarity_threshold=0.8):
    """Merge adjacent segments that likely belong to the same speaker"""
    if not segments:
        return []
        
    merged = [segments[0]]
    
    for current in segments[1:]:
        previous = merged[-1]
        
        # Check if segments are close enough in time
        time_gap = current["start_time"] - previous["end_time"]
        
        # If segments are from the same speaker or very similar and the gap is small
        if (previous["speaker"] == current["speaker"] or 
            are_segments_similar(previous, current, similarity_threshold)) and time_gap < max_gap:
            # Merge segments
            previous["end_time"] = current["end_time"]
            previous["duration"] = previous["end_time"] - previous["start_time"]
        else:
            merged.append(current)
            
    return merged
```

### 5. Global Normalization (LOW PRIORITY)

Normalize features across the entire file for more consistent similarity calculations:

```python
def normalize_features_globally(window_features):
    """Apply global normalization to features"""
    # Calculate global mean and std
    global_mean = np.mean(window_features, axis=0)
    global_std = np.std(window_features, axis=0)
    global_std[global_std == 0] = 1.0  # Avoid division by zero
    
    # Normalize
    normalized_features = (window_features - global_mean) / global_std
    
    return normalized_features
```

## Implementation Plan

1. **Phase 1**: Implement chunked processing and adaptive window sizing
   - Modify `_create_diarization_results` to process in chunks
   - Add adaptive window/step size calculation

2. **Phase 2**: Implement speaker clustering
   - Add feature extraction for speaker embeddings
   - Implement clustering algorithm
   - Replace sequential speaker ID assignment

3. **Phase 3**: Add segment merging and refinement
   - Implement segment similarity calculation
   - Add post-processing to merge similar adjacent segments

4. **Testing**:
   - Test with various file durations (1min, 5min, 15min, 30min, 60min)
   - Compare segment counts and speaker consistency
   - Measure processing time and memory usage

## Expected Outcomes

- **Reduced Processing Time**: 30-50% faster processing for long files
- **Better Speaker Grouping**: Fewer unique speakers, more consistent grouping
- **Lower Memory Usage**: Processing in chunks reduces peak memory consumption
- **Scalability**: System works consistently across different file durations
