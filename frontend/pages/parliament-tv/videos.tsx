import React from 'react';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import DarkLayout from '../../components/layout/DarkLayout';
import ParliamentTVVideoList from '../../components/parliament-tv/ParliamentTVVideoList';
import { Button, Card } from '../../components/ui';

const ParliamentTVVideosPage: React.FC = () => {
  return (
    <DarkLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ParliamentTVVideoList />
      </div>
    </DarkLayout>
  );
};

export default withAuth(ParliamentTVVideosPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
