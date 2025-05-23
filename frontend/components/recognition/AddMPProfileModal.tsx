import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  FormErrorMessage,
  useToast,
  VStack,
  Switch,
  HStack,
  Box,
  Image,
  Text,
  Flex,
  Spinner
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import api from '../../lib/api';

interface AddMPProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface FormValues {
  name: string;
  parliament_id: string;
  party: string;
  constituency: string;
  is_active: boolean;
  photo_url: string;
}

const AddMPProfileModal: React.FC<AddMPProfileModalProps> = ({ isOpen, onClose }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const toast = useToast();
  
  const {
    handleSubmit,
    register,
    formState: { errors },
    reset,
    setValue,
    watch
  } = useForm<FormValues>({
    defaultValues: {
      name: '',
      parliament_id: '',
      party: '',
      constituency: '',
      is_active: true,
      photo_url: ''
    }
  });

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    if (file) {
      setPhotoFile(file);
      
      // Create a preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setPhotoFile(null);
      setPhotoPreview(null);
    }
  };

  const uploadPhoto = async (): Promise<string> => {
    if (!photoFile) return '';
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('photo', photoFile);
      
      const response = await api.post('/recognition/upload-mp-photo', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return response.photo_url || '';
    } catch (error) {
      console.error('Error uploading photo:', error);
      throw new Error('Failed to upload photo');
    } finally {
      setIsUploading(false);
    }
  };

  const onSubmit = async (data: FormValues) => {
    setIsSubmitting(true);
    try {
      // Upload photo if provided
      let photoUrl = data.photo_url;
      if (photoFile) {
        photoUrl = await uploadPhoto();
        if (!photoUrl) {
          throw new Error('Failed to upload photo');
        }
      }
      
      // Create MP profile
      const response = await api.post('/recognition/mp-profiles', {
        ...data,
        photo_url: photoUrl
      });
      
      toast({
        title: 'Profile Created',
        description: `${data.name}'s profile has been created successfully.`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      // Reset form and close modal
      reset();
      setPhotoFile(null);
      setPhotoPreview(null);
      onClose();
      
      // Reload the page to refresh the list
      window.location.reload();
    } catch (error) {
      console.error('Error creating profile:', error);
      toast({
        title: 'Error',
        description: 'Failed to create MP profile. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    reset();
    setPhotoFile(null);
    setPhotoPreview(null);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <ModalHeader>Add New MP Profile</ModalHeader>
          <ModalCloseButton />
          
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <FormControl isInvalid={!!errors.name} isRequired>
                <FormLabel>Name</FormLabel>
                <Input 
                  {...register('name', { 
                    required: 'Name is required',
                    minLength: { value: 2, message: 'Name must be at least 2 characters' }
                  })}
                />
                <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
              </FormControl>
              
              <FormControl isInvalid={!!errors.parliament_id}>
                <FormLabel>Parliament ID</FormLabel>
                <Input {...register('parliament_id')} />
                <FormErrorMessage>{errors.parliament_id?.message}</FormErrorMessage>
              </FormControl>
              
              <FormControl isInvalid={!!errors.party}>
                <FormLabel>Party</FormLabel>
                <Input {...register('party')} />
                <FormErrorMessage>{errors.party?.message}</FormErrorMessage>
              </FormControl>
              
              <FormControl isInvalid={!!errors.constituency}>
                <FormLabel>Constituency</FormLabel>
                <Input {...register('constituency')} />
                <FormErrorMessage>{errors.constituency?.message}</FormErrorMessage>
              </FormControl>
              
              <FormControl>
                <FormLabel>Photo</FormLabel>
                <Input 
                  type="file" 
                  accept="image/*"
                  onChange={handlePhotoChange}
                  p={1}
                />
                
                {photoPreview && (
                  <Box mt={2}>
                    <Image 
                      src={photoPreview} 
                      alt="MP Photo Preview" 
                      maxH="150px" 
                      borderRadius="md"
                    />
                  </Box>
                )}
              </FormControl>
              
              <FormControl isInvalid={!!errors.photo_url}>
                <FormLabel>Photo URL (Optional if uploading a photo)</FormLabel>
                <Input 
                  {...register('photo_url')}
                  placeholder="https://example.com/mp-photo.jpg"
                  disabled={!!photoFile}
                />
                <FormErrorMessage>{errors.photo_url?.message}</FormErrorMessage>
              </FormControl>
              
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="is-active" mb="0">
                  Active
                </FormLabel>
                <Switch 
                  id="is-active" 
                  {...register('is_active')}
                  defaultChecked
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={handleClose} isDisabled={isSubmitting}>
              Cancel
            </Button>
            <Button 
              colorScheme="blue" 
              type="submit"
              isLoading={isSubmitting || isUploading}
              loadingText={isUploading ? "Uploading Photo..." : "Saving..."}
            >
              Save
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default AddMPProfileModal;
