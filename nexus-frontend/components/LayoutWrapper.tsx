'use client';

import { useAppStore } from '@/lib/store';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { ToastContainer } from './Toast';

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed, toasts, removeToast } = useAppStore();
  
  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex pt-20">
        <Sidebar />
        <main className={`flex-1 ${sidebarCollapsed ? 'ml-16' : 'ml-80'} transition-all duration-300 overflow-hidden min-w-0`}>
          <div className="h-full w-full overflow-hidden">
            {children}
          </div>
        </main>
      </div>
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
    </div>
  );
}
