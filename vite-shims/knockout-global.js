// vite-shims/knockout-global.js
const g = typeof window !== 'undefined' ? window : globalThis;
const ko = g.ko;
if (!ko) throw new Error('Global Knockout (ko) not found on window');
export default ko;
