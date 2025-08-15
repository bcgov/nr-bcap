// vite-shims/underscore-global.js
const g = typeof window !== 'undefined' ? window : globalThis;
if (!g._) throw new Error('Global underscore (_) not found on window');
export default g._;
