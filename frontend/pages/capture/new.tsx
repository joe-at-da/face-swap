import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';

// This page now redirects to /capture
const NewCapturePage: React.FC = () => {
  const router = useRouter();
  
  useEffect(() => {
    // Redirect to the main capture page
    router.push('/capture');
  }, [router]);
  
  return <div>Redirecting to capture page...</div>;
};

export default withAuth(NewCapturePage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
