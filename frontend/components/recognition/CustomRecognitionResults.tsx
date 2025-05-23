import React from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

interface Speaker {
  name: string;
  confidence: number;
  start_time: number;
  end_time: number;
  duration: number;
}

interface RecognitionResultsProps {
  videoId: number;
  speakerResults?: {
    speakers: Speaker[];
    [key: string]: any;
  };
  transcriptionText?: string;
  isLoading?: boolean;
  error?: string;
}

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const CustomRecognitionResults: React.FC<RecognitionResultsProps> = ({ 
  videoId, 
  speakerResults, 
  transcriptionText, 
  isLoading = false,
  error
}) => {
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="p-4 border border-gray-300 rounded-lg overflow-hidden bg-white shadow-md">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
          <p>Processing recognition results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border border-gray-300 rounded-lg overflow-hidden bg-white shadow-md">
        <div className="flex flex-col space-y-4">
          <h3 className="text-lg font-semibold text-red-500">Error Processing Recognition</h3>
          <p>{error}</p>
          <button 
            className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded"
            onClick={() => router.reload()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 border border-gray-300 rounded-lg overflow-hidden bg-white shadow-md">
      <div className="flex flex-col space-y-6">
        {speakerResults && speakerResults.speakers && speakerResults.speakers.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Speaker Identification Results</h3>
            <div className="flex flex-col space-y-3">
              {speakerResults.speakers.map((speaker, index) => (
                <div key={index} className="p-3 border border-gray-200 rounded-md bg-gray-50">
                  <div className="flex justify-between items-center">
                    <div className="flex flex-col space-y-1">
                      <div className="flex items-center space-x-2">
                        <p className="font-bold">{speaker.name}</p>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          speaker.confidence > 0.7 
                            ? "bg-green-100 text-green-800" 
                            : speaker.confidence > 0.5 
                              ? "bg-yellow-100 text-yellow-800" 
                              : "bg-red-100 text-red-800"
                        }`}>
                          {Math.round(speaker.confidence * 100)}% confidence
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">
                        {formatTime(speaker.start_time)} - {formatTime(speaker.end_time)} ({Math.round(speaker.duration)} seconds)
                      </p>
                    </div>
                    <Link href={`/parliament-tv/captures/${videoId}?t=${Math.floor(speaker.start_time)}`}>
                      <button className="bg-blue-500 hover:bg-blue-600 text-white text-sm py-1 px-3 rounded">
                        Jump to Timestamp
                      </button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {transcriptionText && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Transcription</h3>
            <div className="p-4 border border-gray-200 rounded-md bg-gray-50 max-h-96 overflow-y-auto">
              <p className="whitespace-pre-wrap">{transcriptionText}</p>
            </div>
          </div>
        )}

        {(!speakerResults || !speakerResults.speakers || speakerResults.speakers.length === 0) && !transcriptionText && (
          <div className="text-center py-6">
            <p className="text-lg">No recognition results available</p>
            <p className="mt-2 text-gray-600">
              Process this video for speaker identification and transcription to see results here.
            </p>
            <div className="flex space-x-4 mt-6 justify-center">
              <Link href={`/recognition/process/${videoId}`}>
                <button className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">
                  Process Recognition
                </button>
              </Link>
              <Link href={`/parliament-tv/captures/${videoId}`}>
                <button className="border border-gray-300 hover:bg-gray-100 py-2 px-4 rounded">
                  View Video
                </button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomRecognitionResults;
