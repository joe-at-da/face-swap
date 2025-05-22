import React, { ReactNode } from 'react';
import DarkLayout from './DarkLayout';

interface MainLayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
}

const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  title = 'Parliament Video Clip Manager',
  description = 'Capture, edit, and share video clips from Parliament TV',
}) => {
  // Use the new DarkLayout component
  return (
    <DarkLayout title={title} description={description}>
      {children}
    </DarkLayout>
  );
};

export default MainLayout;
