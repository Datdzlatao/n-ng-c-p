// app/js/core/state.js — Global State Store
import { getValidSchoolId } from './config.js';

export const state = {
  schoolId: getValidSchoolId(),
  currentUser: null,
  ws: null,
  statsCache: {},
  classesCache: [],
  allSchoolsCache: []
};

// Expose to window for seamless backwards-compatibility
if (typeof window !== 'undefined') {
  window.schoolId = state.schoolId;
  window.currentUser = state.currentUser;
  window.ws = state.ws;
  window.statsCache = state.statsCache;
  window.classesCache = state.classesCache;
  window.allSchoolsCache = state.allSchoolsCache;
}
