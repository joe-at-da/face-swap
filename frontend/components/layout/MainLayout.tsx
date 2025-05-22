import React, { ReactNode } from 'react';
import DarkLayout from './DarkLayout';

interface MainLayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
  showTitle?: boolean;
}

/**
 * MainLayout is a wrapper around DarkLayout that provides some default props.
 * It's used for consistency across the application and to avoid duplicating props.
 * 
 * @param children - The content to render inside the layout
 * @param title - The page title
 * @param description - The page description for meta tags
 * @param showTitle - Whether to show the title in the page (defaults to true)
 */
const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  title = 'Parliament Video Clip Manager',
  description = 'Capture, edit, and share video clips from Parliament TV',
  showTitle = true,
}) => {
  return (
    <DarkLayout 
      title={title} 
      description={description}
    >
      {showTitle && (
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-white">{title}</h1>
        </div>
      )}
      {children}
    </DarkLayout>
  );
};

export default MainLayout;
