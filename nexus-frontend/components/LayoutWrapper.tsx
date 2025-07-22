'use client';

import { useAppStore } from '@/lib/store';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed } = useAppStore();
  
  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex pt-20">
        <Sidebar />
        <main className={`flex-1 ${sidebarCollapsed ? 'ml-16' : 'ml-80'} transition-all duration-300`}>
          {children}
        </main>
      </div>
    </div>
  );
}
