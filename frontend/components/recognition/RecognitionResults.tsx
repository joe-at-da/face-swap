import React from 'react';
import { Box, Text, Heading, VStack, HStack, Badge, Spinner, Button, Link } from '@chakra-ui/react';
import { useRouter } from 'next/router';
import NextLink from 'next/link';

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

const RecognitionResults: React.FC<RecognitionResultsProps> = ({ 
  videoId, 
  speakerResults, 
  transcriptionText, 
  isLoading = false,
  error
}) => {
  const router = useRouter();

  if (isLoading) {
    return (
      <Box p={4} borderWidth="1px" borderRadius="lg" overflow="hidden" bg="white" shadow="md">
        <VStack spacing={4} align="center">
          <Spinner size="xl" />
          <Text>Processing recognition results...</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={4} borderWidth="1px" borderRadius="lg" overflow="hidden" bg="white" shadow="md">
        <VStack spacing={4} align="stretch">
          <Heading size="md" color="red.500">Error Processing Recognition</Heading>
          <Text>{error}</Text>
          <Button 
            colorScheme="blue" 
            onClick={() => router.reload()}
          >
            Try Again
          </Button>
        </VStack>
      </Box>
    );
  }

  return (
    <Box p={4} borderWidth="1px" borderRadius="lg" overflow="hidden" bg="white" shadow="md">
      <VStack spacing={6} align="stretch">
        {speakerResults && speakerResults.speakers && speakerResults.speakers.length > 0 && (
          <Box>
            <Heading size="md" mb={4}>Speaker Identification Results</Heading>
            <VStack spacing={3} align="stretch">
              {speakerResults.speakers.map((speaker, index) => (
                <Box key={index} p={3} borderWidth="1px" borderRadius="md" bg="gray.50">
                  <HStack justify="space-between">
                    <VStack align="start" spacing={1}>
                      <HStack>
                        <Text fontWeight="bold">{speaker.name}</Text>
                        <Badge colorScheme={speaker.confidence > 0.7 ? "green" : speaker.confidence > 0.5 ? "yellow" : "red"}>
                          {Math.round(speaker.confidence * 100)}% confidence
                        </Badge>
                      </HStack>
                      <Text fontSize="sm" color="gray.600">
                        {formatTime(speaker.start_time)} - {formatTime(speaker.end_time)} ({Math.round(speaker.duration)} seconds)
                      </Text>
                    </VStack>
                    <NextLink href={`/parliament-tv/captures/${videoId}?t=${Math.floor(speaker.start_time)}`} passHref>
                      <Button as="a" size="sm" colorScheme="blue">
                        Jump to Timestamp
                      </Button>
                    </NextLink>
                  </HStack>
                </Box>
              ))}
            </VStack>
          </Box>
        )}

        {transcriptionText && (
          <Box>
            <Heading size="md" mb={4}>Transcription</Heading>
            <Box p={4} borderWidth="1px" borderRadius="md" bg="gray.50" maxHeight="400px" overflowY="auto">
              <Text whiteSpace="pre-wrap">{transcriptionText}</Text>
            </Box>
          </Box>
        )}

        {(!speakerResults || !speakerResults.speakers || speakerResults.speakers.length === 0) && !transcriptionText && (
          <Box textAlign="center" py={6}>
            <Text fontSize="lg">No recognition results available</Text>
            <Text mt={2} color="gray.600">
              Process this video for speaker identification and transcription to see results here.
            </Text>
            <HStack spacing={4} mt={6} justify="center">
              <NextLink href={`/recognition/process/${videoId}`} passHref>
                <Button as="a" colorScheme="blue">
                  Process Recognition
                </Button>
              </NextLink>
              <NextLink href={`/parliament-tv/captures/${videoId}`} passHref>
                <Button as="a" variant="outline">
                  View Video
                </Button>
              </NextLink>
            </HStack>
          </Box>
        )}
      </VStack>
    </Box>
  );
};

export default RecognitionResults;
