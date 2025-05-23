import React from 'react';
import { GetServerSideProps } from 'next';
import { 
  Container, 
  Box, 
  Heading, 
  Breadcrumb, 
  BreadcrumbItem, 
  BreadcrumbLink,
  Button,
  Flex,
  useDisclosure
} from '@chakra-ui/react';
import { ChevronRightIcon, AddIcon } from '@chakra-ui/icons';
import Layout from '../../../components/Layout';
import { withAuth } from '../../../utils/auth';
import { api } from '../../../utils/api';
import MPProfilesList from '../../../components/recognition/MPProfilesList';
import AddMPProfileModal from '../../../components/recognition/AddMPProfileModal';

interface MPProfilesPageProps {
  profiles?: any[];
  error?: string;
}

const MPProfilesPage: React.FC<MPProfilesPageProps> = ({ profiles = [], error }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  return (
    <Layout title="MP Profiles Management">
      <Container maxW="container.xl" py={6}>
        <Box mb={6}>
          <Breadcrumb separator={<ChevronRightIcon color="gray.500" />} fontSize="sm">
            <BreadcrumbItem>
              <BreadcrumbLink href="/dashboard">Dashboard</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem>
              <BreadcrumbLink href="/recognition">Recognition</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem isCurrentPage>
              <BreadcrumbLink>MP Profiles</BreadcrumbLink>
            </BreadcrumbItem>
          </Breadcrumb>
        </Box>
        
        <Flex justify="space-between" align="center" mb={6}>
          <Heading size="lg">MP Profiles Management</Heading>
          <Button 
            leftIcon={<AddIcon />} 
            colorScheme="blue" 
            onClick={onOpen}
          >
            Add New MP
          </Button>
        </Flex>
        
        <MPProfilesList profiles={profiles} error={error} />
        
        <AddMPProfileModal isOpen={isOpen} onClose={onClose} />
      </Container>
    </Layout>
  );
};

export const getServerSideProps: GetServerSideProps = withAuth(async (context) => {
  try {
    // Fetch MP profiles
    const response = await api.get('/mp-profiles', {
      headers: {
        Cookie: context.req.headers.cookie || ''
      }
    });
    
    return {
      props: {
        profiles: response.profiles || []
      }
    };
  } catch (error) {
    console.error('Error fetching MP profiles:', error);
    
    return {
      props: {
        profiles: [],
        error: 'Failed to fetch MP profiles'
      }
    };
  }
});

export default MPProfilesPage;
