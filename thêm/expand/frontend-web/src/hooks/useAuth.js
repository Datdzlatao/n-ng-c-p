/**
 * src/hooks/useAuth.js — Authentication State & User Session
 */
import { useState, useEffect } from 'react';
import { authService } from '../services/authService';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('stem_auth_token');
    if (!token) {
      setLoading(false);
      return;
    }

    authService.getProfile()
      .then((data) => {
        if (data?.user) {
          const u = data.user;
          setUser({
            ...u,
            fullName: u.full_name || u.fullName || u.username,
            memberCode: u.user_code || u.student_code || u.memberCode || `ID-${u.id}`,
            schoolId: u.school_id || u.schoolId,
          });
        }
      })
      .catch(() => authService.logout())
      .finally(() => setLoading(false));
  }, []);

  return {
    user,
    isAuthenticated: !!user,
    role: user?.role || 'STUDENT',
    memberCode: user?.memberCode || '',
    loading,
    logout: authService.logout,
  };
}
