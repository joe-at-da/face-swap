import React from 'react';

// Format duration in seconds to HH:MM:SS
const formatDuration = (seconds: number): string => {
  if (!seconds && seconds !== 0) return '00:00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

interface FacesViewProps {
  recognitionResults: any;
}

const FacesView: React.FC<FacesViewProps> = ({ recognitionResults }) => {
  console.log('FacesView received recognition results:', recognitionResults);
  
  if (!recognitionResults) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-400">No facial recognition data available.</p>
      </div>
    );
  }
  
  try {
    // Parse the results if they're a string
    const results = typeof recognitionResults === 'string' 
      ? JSON.parse(recognitionResults) 
      : recognitionResults;
    
    console.log('Parsed recognition results:', results);
    
    // Extract faces from various possible data structures
    let faces = [];
    
    if (results.facial_recognition && Array.isArray(results.facial_recognition.faces)) {
      faces = results.facial_recognition.faces;
    } else if (results.faces && Array.isArray(results.faces)) {
      faces = results.faces;
    } else if (results.speakers && Array.isArray(results.speakers)) {
      faces = results.speakers.map((speaker: any) => ({
        name: speaker.name || 'Unknown',
        confidence: speaker.confidence || 0,
        timestamp: speaker.timestamp || 0,
        image_path: speaker.image_path || null
      }));
    } else if (results.speaker_identification && results.speaker_identification.speakers) {
      faces = results.speaker_identification.speakers.map((speaker: any) => ({
        name: speaker.name || 'Unknown',
        confidence: speaker.confidence || 0,
        timestamp: speaker.timestamp || 0,
        image_path: speaker.image_path || null
      }));
    }
    
    console.log('Extracted faces:', faces);
    
    if (faces.length === 0) {
      return (
        <div className="p-6 text-center">
          <p className="text-gray-400">No facial recognition data available.</p>
        </div>
      );
    }
    
    return (
      <div className="mt-4">
        <h3 className="text-lg font-medium mb-4 text-white">Detected Faces</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {faces.map((face: any, index: number) => (
            <div key={`face-${index}`} className="border border-gray-700 rounded-lg p-4 bg-gray-800">
              {face.image_path && (
                <div className="mb-3">
                  <img 
                    src={face.image_path} 
                    alt={`${face.name || 'Unknown'}`}
                    className="w-full h-40 object-cover rounded"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = '/placeholder-face.png';
                    }}
                  />
                </div>
              )}
              <div>
                <h4 className="font-medium text-white">{face.name || 'Unknown'}</h4>
                <p className="text-sm text-gray-400">Confidence: {Math.round((face.confidence || 0) * 100)}%</p>
                <p className="text-sm text-gray-400">Time: {formatDuration(face.timestamp || 0)}</p>
                {face.bbox && (
                  <p className="text-sm text-gray-400">Bounding Box: [{face.bbox.map((v: number) => Math.round(v)).join(', ')}]</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  } catch (err) {
    console.error('Error parsing facial recognition data:', err);
    return (
      <div className="p-6 text-center">
        <p className="text-red-400">Error parsing facial recognition data.</p>
        <pre className="mt-2 text-xs text-left bg-gray-900 p-2 rounded overflow-auto">
          {JSON.stringify(recognitionResults, null, 2)}
        </pre>
      </div>
    );
  }
};

export default FacesView;
