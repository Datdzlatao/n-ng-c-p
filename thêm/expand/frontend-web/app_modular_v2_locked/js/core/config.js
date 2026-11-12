// app/js/core/config.js — Central Configuration & Keys
export const AUTH_KEY = 'stem_auth_token';
export const REFRESH_KEY = 'stem_refresh_token';
export const SCHOOL_KEY = 'stem_school_id';
export const ROLE_KEY = 'stem_user_role';
export const ADMIN_TOKEN_KEY = 'stem_admin_token';

export function getValidSchoolId() {
  const urlParam = new URLSearchParams(location.search).get('school_id');
  const stored = localStorage.getItem(SCHOOL_KEY);
  let id = parseInt(urlParam);
  if (isNaN(id) || id <= 0) {
    id = parseInt(stored);
  }
  return (isNaN(id) || id <= 0) ? null : id;
}
