import { useEffect } from 'react';
import { useRouter } from 'next/router';

const ParliamentTVRedirect = () => {
  const router = useRouter();
  
  useEffect(() => {
    router.push('/parliament-tv/videos');
  }, [router]);

  return null;
};

export default ParliamentTVRedirect;
