/**
 * src/routes/AppRoutes.jsx — Client Routing Configuration
 */
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { SchoolFeed } from '../features/feed/SchoolFeed';
import { AdminPendingRequests } from '../features/admin/AdminPendingRequests';

export function AppRoutes({ user }) {
  return (
    <Routes>
      <Route path="/" element={<SchoolFeed currentUser={user} />} />
      <Route path="/feed" element={<SchoolFeed currentUser={user} />} />
      {user?.role === 'SCHOOL_ADMIN' && (
        <Route 
          path="/admin/requests" 
          element={<AdminPendingRequests schoolId={user.schoolId || user.school_id} />} 
        />
      )}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
