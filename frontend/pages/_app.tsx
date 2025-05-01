import { AppProps } from 'next/app';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import '../styles/globals.css';
import { AuthProvider } from '../contexts/AuthContext';
import { ThemeProvider } from '../contexts/ThemeContext';

function MyApp({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: 1,
        staleTime: 5 * 60 * 1000, // 5 minutes
      },
    },
  }));

  // Check if the page has requested to skip the AuthProvider
  const skipAuth = (pageProps as any).noAuth === true;
  console.log('MyApp rendering, skipAuth:', skipAuth);

  // Render with or without AuthProvider based on the flag
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        {skipAuth ? (
          <Component {...pageProps} />
        ) : (
          <AuthProvider>
            <Component {...pageProps} />
          </AuthProvider>
        )}
        <ToastContainer 
          position="top-right"
          autoClose={5000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="colored"
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default MyApp;
