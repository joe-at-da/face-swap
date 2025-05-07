import React from 'react';
import { GetServerSideProps } from 'next';
import { useRouter } from 'next/router';
import { Container, Box, Heading, Breadcrumb, BreadcrumbItem, BreadcrumbLink } from '@chakra-ui/react';
import { ChevronRightIcon } from '@chakra-ui/icons';
import Layout from '../../../components/layout/Layout';
import RecognitionProcessor from '../../../components/recognition/RecognitionProcessor';
import { withAuth } from '../../../lib/auth';
import api from '../../../lib/api';

interface ProcessRecognitionPageProps {
  videoId: number;
  videoData?: {
    id: number;
    title?: string;
    description?: string;
    video_path?: string;
    audio_path?: string;
    status?: string;
    created_at?: string;
  };
  error?: string;
}

const ProcessRecognitionPage: React.FC<ProcessRecognitionPageProps> = ({ 
  videoId, 
  videoData,
  error 
}) => {
  const router = useRouter();
  
  return (
    <Layout title={`Process Recognition - Video #${videoId}`}>
      <Container maxW="container.xl" py={6}>
        <Box mb={6}>
          <Breadcrumb separator={<ChevronRightIcon color="gray.500" />} fontSize="sm">
            <BreadcrumbItem>
              <BreadcrumbLink href="/dashboard">Dashboard</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem>
              <BreadcrumbLink href="/parliament-tv/captures">Parliament TV Captures</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/parliament-tv/captures/${videoId}`}>Video #{videoId}</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem isCurrentPage>
              <BreadcrumbLink>Process Recognition</BreadcrumbLink>
            </BreadcrumbItem>
          </Breadcrumb>
        </Box>
        
        <Heading size="lg" mb={6}>Process Recognition</Heading>
        
        <RecognitionProcessor 
          videoId={videoId} 
          videoPath={videoData?.video_path} 
          audioPath={videoData?.audio_path} 
        />
      </Container>
    </Layout>
  );
};

export const getServerSideProps: GetServerSideProps = withAuth(async (context) => {
  const { id } = context.params as { id: string };
  const videoId = parseInt(id, 10);
  
  if (isNaN(videoId)) {
    return {
      notFound: true
    };
  }
  
  try {
    // Fetch the video data
    const response = await api.get(`/parliament-tv/captures/${videoId}`, {
      headers: {
        Cookie: context.req.headers.cookie || ''
      }
    });
    
    return {
      props: {
        videoId,
        videoData: response
      }
    };
  } catch (error) {
    console.error('Error fetching video data:', error);
    
    return {
      props: {
        videoId,
        error: 'Failed to fetch video data'
      }
    };
  }
});

export default ProcessRecognitionPage;
