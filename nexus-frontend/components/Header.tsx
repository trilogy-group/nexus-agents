'use client';

import { Search, Settings, Activity } from 'lucide-react';
import ThemeSwitcher from './ThemeSwitcher';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function Header() {
  const pathname = usePathname();

  return (
    <header className="fixed top-0 left-0 right-0 h-20 bg-black border-b border-gray-800 z-40">
      <div className="flex items-center justify-between h-full px-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Image
                src="/nexus-agents-logo.png"
                alt="Nexus Agents Logo"
                width={106}
                height={80}
                className="w-[106px] h-20 cursor-pointer"
              />
            </Link>
            <Link href="/">
              <h1 className="text-2xl font-semibold text-white cursor-pointer hover:text-gray-200">
                Nexus Agents
              </h1>
            </Link>
          </div>
          
          {/* Navigation Links */}
          <nav className="flex items-center gap-6 ml-8">
            <Link 
              href="/"
              className={`text-sm font-medium transition-colors ${
                pathname === '/' 
                  ? 'text-white' 
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              Projects
            </Link>
            <Link 
              href="/monitoring"
              className={`flex items-center gap-2 text-sm font-medium transition-colors ${
                pathname === '/monitoring' 
                  ? 'text-white' 
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              <Activity className="w-4 h-4" />
              Monitoring
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="search"
              placeholder="Search tasks..."
              className="pl-10 pr-4 py-2 w-64 border border-gray-600 rounded-lg bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <ThemeSwitcher />
          
          <button className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
            <Settings className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>
    </header>
  );
}
