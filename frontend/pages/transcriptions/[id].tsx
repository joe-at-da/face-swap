import React, { useState } from 'react';
import { GetServerSideProps } from 'next';
import { useRouter } from 'next/router';
import { 
  Container, 
  Box, 
  Heading, 
  Text, 
  Button, 
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel,
  HStack,
  VStack,
  Badge,
  Divider,
  useToast,
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  Flex,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem
} from '@chakra-ui/react';
import { ChevronRightIcon, DownloadIcon, TimeIcon, ChevronDownIcon } from '@chakra-ui/icons';
import Layout from '../../components/layout/Layout';
import { withAuth } from '../../lib/auth';
import api from '../../lib/api';
import RecognitionResults from '../../components/recognition/RecognitionResults';

interface TranscriptionDetailPageProps {
  transcriptionData: {
    id: number;
    capture_session_id: number;
    transcription_path?: string;
    status?: string;
    content?: string;
    created_at?: string;
    source?: string;
    capture?: {
      id: number;
      title?: string;
      video_path?: string;
      audio_path?: string;
      status?: string;
      created_at?: string;
      duration?: number;
      speaker_identification_results?: string;
    };
  };
  error?: string;
}

const TranscriptionDetailPage: React.FC<TranscriptionDetailPageProps> = ({ transcriptionData, error }) => {
  const router = useRouter();
  const toast = useToast();
  const [isProcessing, setIsProcessing] = useState(false);
  const [tabIndex, setTabIndex] = useState(0);
  
  // Get timestamp from URL query if present
  const { t } = router.query;
  const startTime = t ? parseInt(t as string, 10) : 0;
  
  const handleStartProcessing = async () => {
    if (!transcriptionData.capture_session_id) {
      toast({
        title: 'Processing Failed',
        description: 'No capture session associated with this transcription.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      return;
    }
    
    setIsProcessing(true);
    
    try {
      // Start combined recognition processing
      await api.post('/recognition/combined-recognition', {
        video_id: transcriptionData.capture_session_id,
        save_output: true
      });
      
      toast({
        title: 'Processing Started',
        description: 'Recognition processing has been started. This may take a few minutes.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      // Refresh the page after a short delay
      setTimeout(() => {
        router.reload();
      }, 3000);
      
    } catch (error) {
      console.error('Error starting recognition processing:', error);
      toast({
        title: 'Processing Failed',
        description: 'Failed to start recognition processing. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Load speaker identification results if available
  const speakerResults = transcriptionData.capture?.speaker_identification_results 
    ? JSON.parse(transcriptionData.capture.speaker_identification_results)
    : null;
  
  // Load transcription content
  const transcriptionText = transcriptionData.content || '';
  
  // Format date
  const formattedDate = transcriptionData.created_at 
    ? new Date(transcriptionData.created_at).toLocaleString()
    : 'Unknown date';
  
  // Format duration
  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  const handleExport = async (format: string) => {
    try {
      const response = await api.get(`/transcription/export/${transcriptionData.id}?format=${format}`, {
        responseType: 'blob'
      });
      
      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `transcription_${transcriptionData.id}.${format.toLowerCase()}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast({
        title: 'Export Successful',
        description: `Transcription exported as ${format.toUpperCase()} successfully.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error exporting transcription:', error);
      toast({
        title: 'Export Failed',
        description: 'Failed to export transcription. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };
  
  return (
    <Layout title={`Transcription #${transcriptionData.id}`}>
      <Container maxW="container.xl" py={6}>
        <Box mb={6}>
          <Breadcrumb separator={<ChevronRightIcon color="gray.500" />} fontSize="sm">
            <BreadcrumbItem>
              <BreadcrumbLink href="/dashboard">Dashboard</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem>
              <BreadcrumbLink href="/transcriptions">Transcriptions</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem isCurrentPage>
              <BreadcrumbLink>Transcription #{transcriptionData.id}</BreadcrumbLink>
            </BreadcrumbItem>
          </Breadcrumb>
        </Box>
        
        <Box mb={6}>
          <Flex justify="space-between" align="center" wrap="wrap">
            <Heading size="lg">
              {transcriptionData.capture?.title || `Transcription #${transcriptionData.id}`}
            </Heading>
            <HStack spacing={4}>
              <Menu>
                <MenuButton as={Button} rightIcon={<ChevronDownIcon />} colorScheme="teal" variant="outline">
                  Export
                </MenuButton>
                <MenuList>
                  <MenuItem onClick={() => handleExport('txt')}>Export as TXT</MenuItem>
                  <MenuItem onClick={() => handleExport('srt')}>Export as SRT</MenuItem>
                  <MenuItem onClick={() => handleExport('json')}>Export as JSON</MenuItem>
                  <MenuItem onClick={() => handleExport('docx')}>Export as DOCX</MenuItem>
                </MenuList>
              </Menu>
              
              {transcriptionData.capture_session_id && (
                <Button 
                  colorScheme="blue" 
                  onClick={handleStartProcessing}
                  isLoading={isProcessing}
                  loadingText="Starting..."
                  isDisabled={isProcessing || !transcriptionData.capture?.video_path}
                >
                  Process Recognition
                </Button>
              )}
            </HStack>
          </Flex>
          
          <HStack mt={2} spacing={4}>
            <Badge colorScheme={transcriptionData.status === 'completed' ? 'green' : 'yellow'}>
              {transcriptionData.status || 'Unknown'}
            </Badge>
            <Text color="gray.600" fontSize="sm">
              <TimeIcon mr={1} />
              {formattedDate}
            </Text>
            {transcriptionData.capture?.duration && (
              <Text color="gray.600" fontSize="sm">
                Duration: {formatDuration(transcriptionData.capture.duration)}
              </Text>
            )}
            {transcriptionData.source && (
              <Badge colorScheme="purple">
                Source: {transcriptionData.source}
              </Badge>
            )}
          </HStack>
        </Box>
        
        <Divider mb={6} />
        
        <Tabs isFitted variant="enclosed" index={tabIndex} onChange={setTabIndex}>
          <TabList mb="1em">
            <Tab>Transcription</Tab>
            <Tab>Recognition Results</Tab>
            {transcriptionData.capture_session_id && <Tab>Media</Tab>}
            <Tab>Details</Tab>
          </TabList>
          <TabPanels>
            <TabPanel>
              <Box p={4} borderWidth="1px" borderRadius="lg" bg="white" shadow="sm">
                <Heading size="md" mb={4}>Transcription Content</Heading>
                <Box p={4} borderWidth="1px" borderRadius="md" bg="gray.50" maxHeight="70vh" overflowY="auto">
                  <Text whiteSpace="pre-wrap">{transcriptionText || 'No transcription content available.'}</Text>
                </Box>
              </Box>
            </TabPanel>
            
            <TabPanel>
              <RecognitionResults 
                videoId={transcriptionData.capture_session_id || 0}
                speakerResults={speakerResults}
                transcriptionText={transcriptionText}
                error={error}
              />
            </TabPanel>
            
            {transcriptionData.capture_session_id && (
              <TabPanel>
                {transcriptionData.capture?.video_path ? (
                  <Box borderRadius="md" overflow="hidden" bg="black">
                    <video 
                      controls 
                      width="100%" 
                      style={{ maxHeight: '70vh' }}
                      src={`/api/v1/parliament-tv/stream/${transcriptionData.capture_session_id}`}
                      poster="/images/parliament-tv-poster.jpg"
                      preload="metadata"
                    >
                      Your browser does not support the video tag.
                    </video>
                  </Box>
                ) : (
                  <Box p={6} textAlign="center" bg="gray.100" borderRadius="md">
                    <Text>No video available for this transcription.</Text>
                  </Box>
                )}
                
                {transcriptionData.capture?.audio_path && (
                  <Box mt={4}>
                    <Heading size="sm" mb={2}>Audio Track</Heading>
                    <audio 
                      controls 
                      width="100%" 
                      src={`/api/v1/parliament-tv/stream-audio/${transcriptionData.capture_session_id}`}
                    >
                      Your browser does not support the audio tag.
                    </audio>
                  </Box>
                )}
              </TabPanel>
            )}
            
            <TabPanel>
              <Box p={4} borderWidth="1px" borderRadius="lg" bg="white" shadow="sm">
                <VStack align="stretch" spacing={4}>
                  <Box>
                    <Text fontWeight="bold">Transcription ID:</Text>
                    <Text>{transcriptionData.id}</Text>
                  </Box>
                  
                  <Box>
                    <Text fontWeight="bold">Status:</Text>
                    <Text>{transcriptionData.status || 'Unknown'}</Text>
                  </Box>
                  
                  <Box>
                    <Text fontWeight="bold">Created At:</Text>
                    <Text>{formattedDate}</Text>
                  </Box>
                  
                  <Box>
                    <Text fontWeight="bold">Source:</Text>
                    <Text>{transcriptionData.source || 'Unknown'}</Text>
                  </Box>
                  
                  {transcriptionData.capture_session_id && (
                    <Box>
                      <Text fontWeight="bold">Capture Session ID:</Text>
                      <Text>{transcriptionData.capture_session_id}</Text>
                    </Box>
                  )}
                  
                  {transcriptionData.transcription_path && (
                    <Box>
                      <Text fontWeight="bold">Transcription Path:</Text>
                      <Text fontSize="sm" fontFamily="monospace">{transcriptionData.transcription_path}</Text>
                    </Box>
                  )}
                </VStack>
              </Box>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Container>
    </Layout>
  );
};

export const getServerSideProps: GetServerSideProps = withAuth(async (context) => {
  const { id } = context.params as { id: string };
  const transcriptionId = parseInt(id, 10);
  
  if (isNaN(transcriptionId)) {
    return {
      notFound: true
    };
  }
  
  try {
    // Fetch the transcription data
    const transcriptionData = await api.get(`/transcription/${transcriptionId}`, {
      headers: {
        Cookie: context.req.headers.cookie || ''
      }
    });
    
    // If there's a capture session, fetch its details
    if (transcriptionData.capture_session_id) {
      try {
        const captureData = await api.get(`/parliament-tv/captures/${transcriptionData.capture_session_id}`, {
          headers: {
            Cookie: context.req.headers.cookie || ''
          }
        });
        
        transcriptionData.capture = captureData;
      } catch (error) {
        console.error('Error fetching capture data:', error);
      }
    }
    
    return {
      props: {
        transcriptionData
      }
    };
  } catch (error) {
    console.error('Error fetching transcription data:', error);
    
    return {
      props: {
        transcriptionData: { id: transcriptionId },
        error: 'Failed to fetch transcription data'
      }
    };
  }
});

export default TranscriptionDetailPage;
