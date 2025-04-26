import React, { useEffect, useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

interface ThemeToggleProps {}

const ThemeToggle: React.FC<ThemeToggleProps> = () => {
  const { theme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Only render the toggle on the client side to avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  // Determine the actual current theme (could be from localStorage or system preference)
  const currentTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';

  return (
    <button
      className="p-2 rounded-full bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors shadow-md"
      onClick={toggleTheme}
      aria-label={`Switch to ${currentTheme === 'dark' ? 'light' : 'dark'} mode`}
    >
      <div className="relative w-6 h-6">
        {/* If we're in dark mode, show sun icon (to switch TO light mode) */}
        {currentTheme === 'dark' ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6 text-yellow-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-label="Switch to light mode"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
            />
          </svg>
        ) : (
          /* If we're in light mode, show moon icon (to switch TO dark mode) */
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6 text-gray-700"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-label="Switch to dark mode"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
            />
          </svg>
        )}
      </div>
      <span className="sr-only">{currentTheme === 'dark' ? 'Light' : 'Dark'} Mode</span>
    </button>
  );
};

export default ThemeToggle;
