'use client';

import { MonitoringDashboard } from '@/components/MonitoringDashboard';
import { LayoutWrapper } from '@/components/LayoutWrapper';

export default function MonitoringPage() {
  return (
    <LayoutWrapper showSidebar={false}>
      <MonitoringDashboard />
    </LayoutWrapper>
  );
}