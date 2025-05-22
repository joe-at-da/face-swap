import React, { useEffect, useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

interface ThemeToggleProps {}

const ThemeToggle: React.FC<ThemeToggleProps> = () => {
  // We're now enforcing dark mode, so don't render the toggle
  return null;
};

export default ThemeToggle;
