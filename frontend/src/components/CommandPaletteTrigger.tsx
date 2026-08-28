import { useEffect, useState } from 'react';
import CommandPalette from './CommandPalette';

export default function CommandPaletteTrigger() {
  const [isOpen, setIsOpen] = useState(false);

  const handleKeyDown = (e: KeyboardEvent) => {
    // Check for Ctrl+K (Meta+K on Mac, Ctrl+K on Windows/Linux)
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault(); // Prevent the browser's default action
      setIsOpen(true);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return (
    <>
      {/* The command palette will be rendered here when open */}
      {isOpen && <CommandPalette isOpen={isOpen} onClose={handleClose} />}
    </>
  );
}