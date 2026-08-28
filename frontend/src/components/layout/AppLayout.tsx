import { Sidebar } from '@/components/Sidebar';
import UnifiedNavBar from '@/components/UnifiedNavBar';
import ContextPanel from '@/components/ContextPanel';
import { Outlet } from 'react-router-dom';
import CommandPaletteTrigger from '@/components/CommandPaletteTrigger';

export const AppLayout = () => {
  return (
    <div className="flex w-full min-h-screen bg-[var(--bg-main)]">
      <Sidebar />
      <div className="hidden md:block"><UnifiedNavBar /></div>
      <main className="flex flex-col h-[100vh] p-[2.5rem] overflow-auto">
        <CommandPaletteTrigger />
        <Outlet />
        <ContextPanel />
      </main>
    </div>
  );
}