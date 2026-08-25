import React from 'react';
import { Sidebar } from '@/components/Sidebar';
import { Outlet } from 'react-router-dom';

export const AppLayout = () => {
  return (
    <div className="flex w-full min-h-screen bg-[var(--bg-main)]">
      <Sidebar />
      <main className="flex flex-col h-[100vh] p-[2.5rem] overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};