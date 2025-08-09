'use client';

import { useAppStore } from '@/lib/store';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { ToastContainer } from './Toast';
import { usePathname } from 'next/navigation';

interface LayoutWrapperProps {
  children: React.ReactNode;
  showSidebar?: boolean;
}

export function LayoutWrapper({ children, showSidebar }: LayoutWrapperProps) {
  const { sidebarCollapsed, toasts, removeToast } = useAppStore();
  const pathname = usePathname();
  
  // Show sidebar by default on home page, hide on monitoring page unless explicitly requested
  const shouldShowSidebar = showSidebar !== undefined ? showSidebar : pathname === '/';
  
  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex pt-20">
        {shouldShowSidebar && <Sidebar />}
        <main className={`flex-1 ${
          shouldShowSidebar 
            ? (sidebarCollapsed ? 'ml-16' : 'ml-80') 
            : 'ml-0'
        } transition-all duration-300 overflow-hidden min-w-0`}>
          <div className="h-full w-full overflow-hidden">
            {children}
          </div>
        </main>
      </div>
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
    </div>
  );
}
