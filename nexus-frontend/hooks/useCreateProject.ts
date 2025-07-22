'use client';

import { useState } from 'react';

/**
 * Hook to manage project creation modal state
 * This provides a consistent way to trigger project creation across components
 */
export function useCreateProject() {
  const [showCreateModal, setShowCreateModal] = useState(false);

  const openCreateModal = () => setShowCreateModal(true);
  const closeCreateModal = () => setShowCreateModal(false);

  return {
    showCreateModal,
    openCreateModal,
    closeCreateModal,
  };
}
