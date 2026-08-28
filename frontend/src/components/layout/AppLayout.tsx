import { Sidebar } from '@/components/Sidebar';
import { Outlet } from 'react-router-dom';
import CommandPaletteTrigger from '@/components/CommandPaletteTrigger';

export const AppLayout = () => {
  return (
    <div className="flex w-full min-h-screen bg-[var(--bg-main)]">
      <Sidebar />
      <main className="flex flex-col h-[100vh] p-[2.5rem] overflow-auto">
        <CommandPaletteTrigger />
        <Outlet />
      </main>
    </div>
  );
}