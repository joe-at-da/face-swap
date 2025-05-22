import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme] = useState<Theme>('dark');

  // Always use dark mode
  useEffect(() => {
    if (typeof window === 'undefined') return;
    localStorage.setItem('theme', 'dark');
  }, []);

  // Apply dark mode styles
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const htmlElement = document.documentElement;
    
    // Always use dark mode
    htmlElement.setAttribute('data-theme', 'parliamentDark');
    htmlElement.classList.add('dark');
    document.body.classList.add('dark-mode');
    document.body.style.backgroundColor = '#111827'; // Dark gray
    document.body.style.color = '#ffffff';
    
    // Force a repaint to ensure styles are applied
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    localStorage.setItem('theme', 'dark');
  }, []);

  // Keep the toggleTheme function for compatibility, but it does nothing now
  const toggleTheme = () => {
    console.log('Theme toggle disabled - always using dark mode');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
};
