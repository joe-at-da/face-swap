import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  VStack, 
  Heading, 
  Text, 
  HStack, 
  useToast, 
  Spinner,
  Checkbox,
  Divider,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Progress
} from '@chakra-ui/react';
import { useRouter } from 'next/router';
import api from '../../lib/api';

interface RecognitionProcessorProps {
  videoId: number;
  videoPath?: string;
  audioPath?: string;
}

const RecognitionProcessor: React.FC<RecognitionProcessorProps> = ({ 
  videoId, 
  videoPath, 
  audioPath 
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTask, setCurrentTask] = useState<string>('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [options, setOptions] = useState({
    facialRecognition: true,
    speakerIdentification: true,
    transcription: true,
    saveOutput: true
  });
  
  const toast = useToast();
  const router = useRouter();

  const handleOptionChange = (option: keyof typeof options) => {
    setOptions({
      ...options,
      [option]: !options[option]
    });
  };

  const processFacialRecognition = async () => {
    setCurrentTask('Detecting faces in video...');
    setProgress(20);
    
    try {
      const response = await api.post('/recognition/facial-recognition', {
        video_id: videoId,
        save_output: options.saveOutput
      });
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to process facial recognition');
      }
      
      return response;
    } catch (err: any) {
      console.error('Facial recognition error:', err);
      throw new Error(`Facial recognition failed: ${err.message}`);
    }
  };

  const processSpeakerIdentification = async () => {
    setCurrentTask('Identifying speakers in video...');
    setProgress(40);
    
    try {
      const response = await api.post('/recognition/speaker-identification', {
        video_id: videoId,
        save_output: options.saveOutput
      });
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to process speaker identification');
      }
      
      return response;
    } catch (err: any) {
      console.error('Speaker identification error:', err);
      throw new Error(`Speaker identification failed: ${err.message}`);
    }
  };

  const processTranscription = async () => {
    setCurrentTask('Transcribing audio...');
    setProgress(70);
    
    try {
      const response = await api.post('/recognition/transcription', {
        audio_id: videoId,
        save_output: options.saveOutput
      });
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to process transcription');
      }
      
      return response;
    } catch (err: any) {
      console.error('Transcription error:', err);
      throw new Error(`Transcription failed: ${err.message}`);
    }
  };

  const processCombinedRecognition = async () => {
    setCurrentTask('Processing combined recognition...');
    setProgress(30);
    
    try {
      const response = await api.post('/recognition/combined-recognition', {
        video_id: videoId,
        save_output: options.saveOutput
      });
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to process combined recognition');
      }
      
      setProgress(90);
      return response;
    } catch (err: any) {
      console.error('Combined recognition error:', err);
      throw new Error(`Combined recognition failed: ${err.message}`);
    }
  };

  const handleStartProcessing = async () => {
    setIsProcessing(true);
    setError(null);
    setSuccess(null);
    setProgress(10);
    
    try {
      let result;
      
      // Check which options are selected
      if (options.facialRecognition && options.speakerIdentification && options.transcription) {
        // If all options are selected, use the combined endpoint
        result = await processCombinedRecognition();
      } else {
        // Otherwise, process each selected option individually
        if (options.facialRecognition) {
          await processFacialRecognition();
        }
        
        if (options.speakerIdentification) {
          await processSpeakerIdentification();
        }
        
        if (options.transcription) {
          await processTranscription();
        }
      }
      
      setProgress(100);
      setCurrentTask('Processing complete!');
      setSuccess('Recognition processing completed successfully!');
      
      toast({
        title: 'Processing Complete',
        description: 'The recognition processing has been completed successfully.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      // Redirect to the video page after a short delay
      setTimeout(() => {
        router.push(`/parliament-tv/captures/${videoId}`);
      }, 2000);
      
    } catch (err: any) {
      setError(err.message);
      toast({
        title: 'Processing Failed',
        description: err.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Box p={6} borderWidth="1px" borderRadius="lg" overflow="hidden" bg="white" shadow="md">
      <VStack spacing={6} align="stretch">
        <Heading size="md">Process Recognition for Video #{videoId}</Heading>
        
        {!videoPath && !audioPath && (
          <Alert status="warning">
            <AlertIcon />
            <AlertTitle>Missing Media Files</AlertTitle>
            <AlertDescription>
              This video does not have associated video or audio files. Recognition processing may fail.
            </AlertDescription>
          </Alert>
        )}
        
        <Box>
          <Text fontWeight="bold" mb={3}>Recognition Options</Text>
          <VStack align="start" spacing={2}>
            <Checkbox 
              isChecked={options.facialRecognition} 
              onChange={() => handleOptionChange('facialRecognition')}
              isDisabled={isProcessing}
            >
              Facial Recognition
            </Checkbox>
            <Checkbox 
              isChecked={options.speakerIdentification} 
              onChange={() => handleOptionChange('speakerIdentification')}
              isDisabled={isProcessing}
            >
              Speaker Identification
            </Checkbox>
            <Checkbox 
              isChecked={options.transcription} 
              onChange={() => handleOptionChange('transcription')}
              isDisabled={isProcessing || !audioPath}
            >
              Audio Transcription {!audioPath && '(No audio file available)'}
            </Checkbox>
            <Divider my={2} />
            <Checkbox 
              isChecked={options.saveOutput} 
              onChange={() => handleOptionChange('saveOutput')}
              isDisabled={isProcessing}
            >
              Save Output Files
            </Checkbox>
          </VStack>
        </Box>
        
        {isProcessing && (
          <Box>
            <Text mb={2}>{currentTask}</Text>
            <Progress value={progress} size="sm" colorScheme="blue" borderRadius="md" />
          </Box>
        )}
        
        {error && (
          <Alert status="error">
            <AlertIcon />
            <AlertTitle>Processing Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert status="success">
            <AlertIcon />
            <AlertTitle>Success</AlertTitle>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}
        
        <HStack spacing={4} justify="flex-end">
          <Button 
            onClick={() => router.back()} 
            variant="outline"
            isDisabled={isProcessing}
          >
            Cancel
          </Button>
          <Button 
            colorScheme="blue" 
            onClick={handleStartProcessing}
            isLoading={isProcessing}
            loadingText={currentTask}
            isDisabled={isProcessing || (!options.facialRecognition && !options.speakerIdentification && !options.transcription)}
          >
            {isProcessing ? <Spinner size="sm" /> : 'Start Processing'}
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
};

export default RecognitionProcessor;
