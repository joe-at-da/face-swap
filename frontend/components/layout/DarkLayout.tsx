import React, { ReactNode } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';

interface DarkLayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
}

const DarkLayout: React.FC<DarkLayoutProps> = ({
  children,
  title = 'Parliament Video Clip Manager',
  description = 'Capture, edit, and share video clips from Parliament TV',
}) => {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuth();

  // Navigation items for the sidebar
  const navigationItems = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
    },
    {
      name: 'Video Gallery',
      href: '/videos',
      icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
    },
    {
      name: 'Video Clips',
      href: '/clips',
      icon: 'M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z',
    },
    {
      name: 'Capture',
      href: '/capture',
      icon: 'M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z',
    },
    {
      name: 'Transcriptions',
      href: '/transcriptions',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    },
    {
      name: 'File Gallery',
      href: '/files',
      icon: 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4',
    },
    {
      name: 'Parliament TV',
      href: '/parliament-tv/videos',
      icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
    },
    {
      name: 'Social Media',
      href: '/social',
      icon: 'M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z',
    },
  ];

  // Admin-only navigation items
  const adminItems = [
    {
      name: 'Admin Dashboard',
      href: '/admin',
      icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
    },
    {
      name: 'Users',
      href: '/admin/users',
      icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    },
    {
      name: 'Storage',
      href: '/admin/storage',
      icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4',
    },
    {
      name: 'Settings',
      href: '/admin/system',
      icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
    },
    {
      name: 'Voice Profiles',
      href: '/admin/voice-profiles',
      icon: 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z',
    },
    {
      name: 'System Logs',
      href: '/admin/logs',
      icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        {isAuthenticated && (
          <div className="hidden md:flex md:flex-shrink-0">
            <div className="flex flex-col w-64">
              <div className="flex flex-col h-0 flex-1 bg-gray-800">
                <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
                  <div className="flex items-center flex-shrink-0 px-4">
                    <Link href="/dashboard">
                      <div className="flex items-center cursor-pointer">
                        <img
                          src="/logo.svg"
                          alt="Parliament Video Clip Manager"
                          className="h-8 w-auto"
                        />
                        <span className="ml-2 text-xl font-semibold text-white">
                          The MP
                        </span>
                      </div>
                    </Link>
                  </div>
                  <nav className="mt-5 flex-1 px-2 space-y-1">
                    {navigationItems.map((item) => {
                      const isActive = router.pathname === item.href || 
                                      (item.href !== '/dashboard' && router.pathname.startsWith(item.href));
                      return (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={`${
                            isActive
                              ? 'bg-gray-900 text-white'
                              : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                          } group flex items-center px-2 py-2 text-sm font-medium rounded-md`}
                        >
                          <svg
                            className="mr-3 h-6 w-6 text-gray-400 group-hover:text-gray-300"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            aria-hidden="true"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                          </svg>
                          {item.name}
                        </Link>
                      );
                    })}

                    {/* Admin section */}
                    {user?.role === UserRole.ADMIN && (
                      <div className="pt-6">
                        <div className="px-3 mb-2">
                          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                            Administration
                          </h3>
                        </div>
                        {adminItems.map((item) => {
                          const isActive = router.pathname === item.href || 
                                          (item.href !== '/admin' && router.pathname.startsWith(item.href));
                          return (
                            <Link
                              key={item.name}
                              href={item.href}
                              className={`${
                                isActive
                                  ? 'bg-gray-900 text-white'
                                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                              } group flex items-center px-2 py-2 text-sm font-medium rounded-md`}
                            >
                              <svg
                                className="mr-3 h-6 w-6 text-gray-400 group-hover:text-gray-300"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                aria-hidden="true"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                              </svg>
                              {item.name}
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </nav>
                </div>
                <div className="flex-shrink-0 flex border-t border-gray-700 p-4">
                  <div className="flex-shrink-0 w-full group block">
                    <div className="flex items-center">
                      <div>
                        <div className="h-8 w-8 rounded-full bg-blue-600 text-white flex items-center justify-center">
                          {user?.name?.charAt(0) || 'U'}
                        </div>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-white">{user?.name}</p>
                        <button
                          onClick={logout}
                          className="text-xs font-medium text-gray-300 hover:text-gray-200"
                        >
                          Logout
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Mobile menu button */}
        {isAuthenticated && (
          <div className="md:hidden fixed top-0 left-0 right-0 z-10 bg-gray-800 border-b border-gray-700">
            <div className="flex items-center justify-between h-16 px-4">
              <div className="flex items-center">
                <img
                  src="/logo.svg"
                  alt="Parliament Video Clip Manager"
                  className="h-8 w-auto"
                />
                <span className="ml-2 text-lg font-semibold text-white">
                  The MP
                </span>
              </div>
              <button
                type="button"
                className="text-gray-300 hover:text-white focus:outline-none"
                onClick={() => {
                  // Toggle mobile menu
                  const mobileMenu = document.getElementById('mobile-menu');
                  if (mobileMenu) {
                    mobileMenu.classList.toggle('hidden');
                  }
                }}
              >
                <svg
                  className="h-6 w-6"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Mobile menu */}
        {isAuthenticated && (
          <div id="mobile-menu" className="md:hidden fixed inset-0 z-20 bg-gray-900 bg-opacity-90 hidden">
            <div className="pt-16 pb-3 px-2 space-y-1 sm:px-3">
              <div className="flex justify-end p-2">
                <button
                  type="button"
                  className="text-gray-300 hover:text-white focus:outline-none"
                  onClick={() => {
                    const mobileMenu = document.getElementById('mobile-menu');
                    if (mobileMenu) {
                      mobileMenu.classList.add('hidden');
                    }
                  }}
                >
                  <svg
                    className="h-6 w-6"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              {navigationItems.map((item) => {
                const isActive = router.pathname === item.href || 
                                (item.href !== '/dashboard' && router.pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`${
                      isActive
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    } block px-3 py-2 rounded-md text-base font-medium`}
                  >
                    <div className="flex items-center">
                      <svg
                        className="mr-3 h-6 w-6"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        aria-hidden="true"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                      </svg>
                      {item.name}
                    </div>
                  </Link>
                );
              })}

              {/* Admin section for mobile */}
              {user?.role === UserRole.ADMIN && (
                <>
                  <div className="pt-4 pb-2">
                    <div className="px-3">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                        Administration
                      </h3>
                    </div>
                  </div>
                  {adminItems.map((item) => {
                    const isActive = router.pathname === item.href || 
                                    (item.href !== '/admin' && router.pathname.startsWith(item.href));
                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        className={`${
                          isActive
                            ? 'bg-gray-900 text-white'
                            : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                        } block px-3 py-2 rounded-md text-base font-medium`}
                      >
                        <div className="flex items-center">
                          <svg
                            className="mr-3 h-6 w-6"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            aria-hidden="true"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                          </svg>
                          {item.name}
                        </div>
                      </Link>
                    );
                  })}
                </>
              )}

              <div className="pt-4 mt-4 border-t border-gray-700">
                <div className="flex items-center px-3 py-2">
                  <div className="h-8 w-8 rounded-full bg-blue-600 text-white flex items-center justify-center">
                    {user?.name?.charAt(0) || 'U'}
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-white">{user?.name}</p>
                    <button
                      onClick={logout}
                      className="text-xs font-medium text-gray-300 hover:text-gray-200"
                    >
                      Logout
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main content */}
        <div className="flex flex-col w-0 flex-1 overflow-hidden">
          <main className={`flex-1 relative z-0 overflow-y-auto focus:outline-none ${isAuthenticated ? 'md:pt-0 pt-16' : ''}`}>
            <div className="py-6">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                {isAuthenticated && (
                  <h1 className="text-2xl font-semibold text-white mb-4">{title}</h1>
                )}
                <div className="py-4">{children}</div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default DarkLayout;
