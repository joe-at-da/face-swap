import React from 'react';
import { 
  Box, 
  Container, 
  Heading, 
  Button, 
  VStack,
  FormControl,
  FormLabel,
  Input,
  FormErrorMessage,
  Textarea,
  Switch,
  useToast,
  Flex,
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { GetServerSideProps } from 'next';
import { ChevronRightIcon } from '@chakra-ui/icons';
import Link from 'next/link';
import { withAuth } from '../../../utils/auth';
import { api } from '../../../utils/api';

interface FormValues {
  name: string;
  parliament_id: string;
  party: string;
  constituency: string;
  photo_url: string;
  is_active: boolean;
}

const AddMPProfilePage: React.FC = () => {
  const { 
    handleSubmit, 
    register, 
    formState: { errors, isSubmitting } 
  } = useForm<FormValues>();
  const toast = useToast();

  const onSubmit = async (values: FormValues) => {
    try {
      const response = await api.post('/mp-profiles', values);
      
      toast({
        title: 'MP Profile Created',
        description: `Profile for ${values.name} has been created successfully.`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      // Redirect to profiles list
      window.location.href = '/recognition/profiles';
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create the MP profile. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  return (
    <Container maxW="container.lg" py={8}>
      <Breadcrumb separator={<ChevronRightIcon color="gray.500" />} mb={8}>
        <BreadcrumbItem>
          <BreadcrumbLink as={Link} href="/dashboard">
            Dashboard
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbItem>
          <BreadcrumbLink as={Link} href="/recognition/profiles">
            MP Profiles
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>
          <BreadcrumbLink>Add New MP</BreadcrumbLink>
        </BreadcrumbItem>
      </Breadcrumb>

      <Box bg="white" p={8} borderRadius="md" shadow="md">
        <Heading size="lg" mb={6}>Add New MP Profile</Heading>
        
        <form onSubmit={handleSubmit(onSubmit)}>
          <VStack spacing={4} align="stretch">
            <FormControl isInvalid={!!errors.name} isRequired>
              <FormLabel>MP Name</FormLabel>
              <Input 
                {...register('name', { 
                  required: 'Name is required',
                })}
                placeholder="Enter MP's full name"
              />
              <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
            </FormControl>
            
            <FormControl isInvalid={!!errors.parliament_id}>
              <FormLabel>Parliament ID</FormLabel>
              <Input 
                {...register('parliament_id')}
                placeholder="Enter Parliament ID (optional)"
              />
              <FormErrorMessage>{errors.parliament_id?.message}</FormErrorMessage>
            </FormControl>
            
            <FormControl isInvalid={!!errors.party}>
              <FormLabel>Political Party</FormLabel>
              <Input 
                {...register('party')}
                placeholder="Enter political party (optional)"
              />
              <FormErrorMessage>{errors.party?.message}</FormErrorMessage>
            </FormControl>
            
            <FormControl isInvalid={!!errors.constituency}>
              <FormLabel>Constituency</FormLabel>
              <Input 
                {...register('constituency')}
                placeholder="Enter constituency (optional)"
              />
              <FormErrorMessage>{errors.constituency?.message}</FormErrorMessage>
            </FormControl>
            
            <FormControl isInvalid={!!errors.photo_url}>
              <FormLabel>Photo URL</FormLabel>
              <Input 
                {...register('photo_url')}
                placeholder="Enter photo URL (optional)"
              />
              <FormErrorMessage>{errors.photo_url?.message}</FormErrorMessage>
            </FormControl>
            
            <FormControl display="flex" alignItems="center">
              <FormLabel htmlFor="is_active" mb="0">
                Active MP
              </FormLabel>
              <Switch 
                id="is_active" 
                {...register('is_active')} 
                defaultChecked 
              />
            </FormControl>
            
            <Flex justify="flex-end" mt={6}>
              <Button 
                as={Link} 
                href="/recognition/profiles" 
                variant="ghost" 
                mr={3}
              >
                Cancel
              </Button>
              <Button 
                colorScheme="blue" 
                type="submit" 
                isLoading={isSubmitting}
                loadingText="Creating..."
              >
                Create MP Profile
              </Button>
            </Flex>
          </VStack>
        </form>
      </Box>
    </Container>
  );
};

export const getServerSideProps: GetServerSideProps = withAuth(async (context) => {
  return {
    props: {}
  };
});

export default AddMPProfilePage;
