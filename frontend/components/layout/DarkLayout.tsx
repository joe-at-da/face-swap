import React, { ReactNode, useState } from 'react';
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Define navigation categories and items
  const navigationCategories = [
    {
      name: 'Main',
      items: [
        {
          name: 'Dashboard',
          href: '/dashboard',
          icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
        },
      ],
    },
    {
      name: 'Media',
      items: [
        {
          name: 'Video Gallery',
          href: '/gallery',
          icon: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
        },
        {
          name: 'Video Clips',
          href: '/clips',
          icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
        },
        {
          name: 'File Gallery',
          href: '/files',
          icon: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z',
        },
      ],
    },
    {
      name: 'Production',
      items: [
        {
          name: 'Capture',
          href: '/capture',
          icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
        },
        {
          name: 'Transcriptions',
          href: '/transcriptions',
          icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
        },
        {
          name: 'Parliament TV',
          href: '/parliament-tv/videos',
          icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
        },
      ],
    },
    {
      name: 'Publishing',
      items: [
        {
          name: 'Social Media',
          href: '/social',
          icon: 'M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z',
        },
      ],
    },
  ];

  // Admin-only navigation categories
  const adminCategories = [
    {
      name: 'Administration',
      items: [
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
          icon: 'M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4',
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
      ],
    },
  ];

  // Flatten navigation items for mobile view
  const navigationItems = navigationCategories.flatMap(category => category.items);
  const adminItems = adminCategories.flatMap(category => category.items);

  return (
    <div className="min-h-screen bg-gray-900 text-white" style={{ position: 'relative' }}>
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="flex h-screen overflow-hidden">
        {/* Sidebar for desktop */}
        {isAuthenticated && (
          <div className="hidden md:flex md:flex-shrink-0 z-50">
            <div className="flex flex-col w-64">
              <div className="flex flex-col flex-grow pt-5 pb-4 overflow-y-auto bg-gray-800">
                <div className="flex items-center flex-shrink-0 px-4">
                  <span className="text-xl font-bold text-white">The MP</span>
                </div>
                <div className="mt-5 flex-1 flex flex-col">
                  <nav className="flex-1 px-2 space-y-1">
                    {navigationCategories.map((category) => (
                      <div key={category.name} className="mb-4">
                        <h3 className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                          {category.name}
                        </h3>
                        <div className="mt-1 space-y-1">
                          {category.items.map((item) => {
                            const isActive = router.pathname === item.href || router.pathname.startsWith(`${item.href}/`);
                            return (
                              <div key={item.name} className="relative" style={{ zIndex: 60 }}>
                                <Link 
                                  href={item.href}
                                  className={`${
                                    isActive
                                      ? 'text-blue-400 bg-gray-700'
                                      : 'text-gray-300 hover:text-blue-400 hover:bg-gray-700'
                                  } group flex items-center px-2 py-2 text-sm font-medium rounded-md cursor-pointer transition-colors duration-200 block`}
                                >
                                  <svg
                                    className="mr-3 h-5 w-5"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                    xmlns="http://www.w3.org/2000/svg"
                                  >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                                  </svg>
                                  {item.name}
                                </Link>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </nav>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Mobile menu button */}
        {isAuthenticated && (
          <div className="fixed top-0 left-0 right-0 z-50 bg-gray-800 border-b border-gray-700">
            <div className="flex items-center justify-between h-16 px-4">
              <div className="flex items-center">
                <div className="relative" style={{ zIndex: 60 }}>
                  <Link href="/" className="flex items-center">
                    <svg className="h-8 w-8 text-blue-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M3 3v18h18V3H3zm16 16H5V5h14v14z" strokeWidth="1.5" />
                      <path d="M10 7v10M14 7v10" strokeWidth="1.5" />
                      <path d="M7 10h10M7 14h10" strokeWidth="1.5" />
                    </svg>
                    <span className="text-xl font-bold text-white ml-2">The MP</span>
                  </Link>
                </div>
              </div>
              <button
                type="button"
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                <span className="sr-only">Open main menu</span>
                {mobileMenuOpen ? (
                  <svg
                    className="block h-6 w-6"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : (
                  <svg
                    className="block h-6 w-6"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Mobile menu */}
        {isAuthenticated && (
          <div className="md:hidden" style={{ position: 'relative' }}>
            {/* Mobile navigation items */}
            {navigationItems.map((item) => {
              const isActive = router.pathname === item.href || router.pathname.startsWith(`${item.href}/`);
              return (
                <div key={item.name} className="relative" style={{ zIndex: 60 }}>
                  <Link 
                    href={item.href}
                    className={`${
                      isActive
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    } block px-3 py-2 rounded-md text-base font-medium`}
                    onClick={() => setMobileMenuOpen(false)}
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
                </div>
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
                  const isActive = router.pathname === item.href || router.pathname.startsWith(`${item.href}/`);
                  return (
                    <div key={item.name} className="relative" style={{ zIndex: 60 }}>
                      <Link 
                        href={item.href}
                        className={`${
                          isActive
                            ? 'bg-gray-900 text-white'
                            : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                        } block px-3 py-2 rounded-md text-base font-medium`}
                        onClick={() => setMobileMenuOpen(false)}
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
                    </div>
                  );
                })}
              </>
            )}

            {/* Mobile user info */}
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
        )}

        {/* Main content */}
        <div className="flex flex-col w-0 flex-1 overflow-hidden">
          <main className="flex-1 relative z-0 overflow-y-auto focus:outline-none" style={{ position: 'relative' }}>
            <div className="py-6">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                {title && (
                  <h1 className="text-2xl font-semibold text-white mb-6">{title}</h1>
                )}
              </div>
              <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
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
