// vite-shims/jquery-global.js
const g = typeof window !== 'undefined' ? window : globalThis;
const jq = g.jQuery || g.$;
if (!jq) throw new Error('Global jQuery not found on window');
export default jq;
