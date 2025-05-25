export const formatTime = (seconds: number): string => {
  if (seconds === undefined || seconds === null || isNaN(seconds)) {
    return '0:00'; // Return a default value for invalid inputs
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};
