import React from 'react';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import MainLayout from '../../components/layout/MainLayout';
import ParliamentTVVideoList from '../../components/parliament-tv/ParliamentTVVideoList';

const ParliamentTVVideosPage: React.FC = () => {
  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ParliamentTVVideoList />
      </div>
    </MainLayout>
  );
};

export default withAuth(ParliamentTVVideosPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
