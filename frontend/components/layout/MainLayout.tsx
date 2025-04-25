import React, { ReactNode } from 'react';
import Head from 'next/head';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import { useAuth } from '../../contexts/AuthContext';

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
  const { isAuthenticated } = useAuth();

  return (
    <>
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {isAuthenticated && <Navbar />}
        
        <div className="flex min-h-screen">
          {isAuthenticated && (
            <div className="w-64 hidden md:block">
              <Sidebar />
            </div>
          )}
          
          <main className={`flex-1 ${isAuthenticated ? 'p-6' : 'p-0'}`}>
            {children}
          </main>
        </div>
      </div>
    </>
  );
};

export default MainLayout;
