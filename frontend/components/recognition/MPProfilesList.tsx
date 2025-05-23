import React, { useState } from 'react';
import {
  Box,
  Text,
  Button,
  Image,
  Badge,
  Flex,
  HStack,
  IconButton,
  useDisclosure,
  Heading,
  useToast,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Tooltip
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon, RepeatIcon } from '@chakra-ui/icons';
import { api } from '../../utils/api';
import EditMPProfileModal from './EditMPProfileModal';

interface MPProfile {
  id: number;
  name: string;
  parliament_id?: string;
  party?: string;
  constituency?: string;
  photo_url?: string;
  has_face_encoding: boolean;
  is_active: boolean;
  created_at: string;
}

interface MPProfilesListProps {
  profiles: MPProfile[];
  error?: string;
}

const MPProfilesList: React.FC<MPProfilesListProps> = ({ profiles, error }) => {
  const [selectedProfile, setSelectedProfile] = useState<MPProfile | null>(null);
  const [isRegenerating, setIsRegenerating] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState<number | null>(null);
  const editDisclosure = useDisclosure();
  const deleteDisclosure = useDisclosure();
  const cancelRef = React.useRef<HTMLButtonElement>(null);
  const toast = useToast();

  const handleEdit = (profile: MPProfile) => {
    setSelectedProfile(profile);
    editDisclosure.onOpen();
  };

  const handleDelete = (profile: MPProfile) => {
    setSelectedProfile(profile);
    deleteDisclosure.onOpen();
  };

  const confirmDelete = async () => {
    if (!selectedProfile) return;
    
    setIsDeleting(selectedProfile.id);
    try {
      await api.delete(`/mp-profiles/${selectedProfile.id}`);
      toast({
        title: 'Profile Deleted',
        description: `${selectedProfile.name}'s profile has been deleted.`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      deleteDisclosure.onClose();
      // Reload the page to refresh the list
      window.location.reload();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete the profile. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsDeleting(null);
    }
  };

  const regenerateFaceEncoding = async (profileId: number) => {
    setIsRegenerating(profileId);
    try {
      const response = await api.post(`/mp-profiles/${profileId}/regenerate-encoding`);
      toast({
        title: 'Face Encoding Regenerated',
        description: response.message || 'Face encoding has been regenerated successfully.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      // Reload the page to refresh the list
      window.location.reload();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to regenerate face encoding. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsRegenerating(null);
    }
  };

  if (error) {
    return (
      <Alert status="error" mb={6}>
        <AlertIcon />
        <AlertTitle>Error!</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (profiles.length === 0) {
    return (
      <Alert status="info" mb={6}>
        <AlertIcon />
        <AlertTitle>No MP Profiles</AlertTitle>
        <AlertDescription>
          No MP profiles have been created yet. Click the "Add New MP" button to create your first profile.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Box>
      <Box overflowX="auto">
        <Table variant="simple">
          <Thead>
            <Tr>
              <Th>Photo</Th>
              <Th>Name</Th>
              <Th>Parliament ID</Th>
              <Th>Party</Th>
              <Th>Constituency</Th>
              <Th>Face Encoding</Th>
              <Th>Status</Th>
              <Th>Actions</Th>
            </Tr>
          </Thead>
          <Tbody>
            {profiles.map(profile => (
              <Tr key={profile.id}>
                <Td>
                  {profile.photo_url ? (
                    <Image 
                      src={profile.photo_url} 
                      alt={profile.name} 
                      boxSize="50px" 
                      objectFit="cover" 
                      borderRadius="md"
                    />
                  ) : (
                    <Box 
                      width="50px" 
                      height="50px" 
                      bg="gray.200" 
                      borderRadius="md" 
                      display="flex" 
                      alignItems="center" 
                      justifyContent="center"
                    >
                      <Text fontSize="xs" color="gray.500">No photo</Text>
                    </Box>
                  )}
                </Td>
                <Td fontWeight="medium">{profile.name}</Td>
                <Td>{profile.parliament_id || '-'}</Td>
                <Td>{profile.party || '-'}</Td>
                <Td>{profile.constituency || '-'}</Td>
                <Td>
                  <Badge 
                    colorScheme={profile.has_face_encoding ? 'green' : 'red'}
                    variant="subtle"
                    px={2}
                    py={1}
                    borderRadius="full"
                  >
                    {profile.has_face_encoding ? 'Available' : 'Missing'}
                  </Badge>
                </Td>
                <Td>
                  <Badge 
                    colorScheme={profile.is_active ? 'blue' : 'gray'}
                    variant="subtle"
                    px={2}
                    py={1}
                    borderRadius="full"
                  >
                    {profile.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </Td>
                <Td>
                  <HStack>
                    <Tooltip label="Edit Profile">
                      <IconButton
                        aria-label="Edit profile"
                        _icon={{ as: EditIcon }}
                        size="sm"
                        colorScheme="blue"
                        variant="ghost"
                        onClick={() => handleEdit(profile)}
                      />
                    </Tooltip>
                    
                    <Tooltip label="Regenerate Face Encoding">
                      <IconButton
                        aria-label="Regenerate face encoding"
                        _icon={{ as: RepeatIcon }}
                        size="sm"
                        colorScheme="green"
                        variant="ghost"
                        disabled={!profile.photo_url}
                        onClick={() => regenerateFaceEncoding(profile.id)}
                      />
                    </Tooltip>
                    
                    <Tooltip label="Delete Profile">
                      <IconButton
                        aria-label="Delete profile"
                        _icon={{ as: DeleteIcon }}
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => handleDelete(profile)}
                      />
                    </Tooltip>
                  </HStack>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {/* Edit Profile Modal */}
      {selectedProfile && (
        <Modal isOpen={editDisclosure.isOpen} onClose={editDisclosure.onClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Edit MP Profile</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Text>Edit profile for {selectedProfile.name}</Text>
            </ModalBody>
            <ModalFooter>
              <Button onClick={editDisclosure.onClose}>Close</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      )}

      {/* Delete Confirmation Dialog */}
      <Modal isOpen={deleteDisclosure.isOpen} onClose={deleteDisclosure.onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Delete MP Profile</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            Are you sure you want to delete {selectedProfile?.name}'s profile? This action cannot be undone.
          </ModalBody>
          <ModalFooter>
            <Button ref={cancelRef} onClick={deleteDisclosure.onClose}>
              Cancel
            </Button>
            <Button 
              colorScheme="red" 
              onClick={confirmDelete} 
              ml={3}
            >
              Delete
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default MPProfilesList;
