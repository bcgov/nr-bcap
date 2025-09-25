// Import Underscore's ESM build via a deep path to bypass the alias.
// Works in modern Underscore (1.13+). If your install lacks this file,
// try the alternative path noted below.
import _, * as underscoreNS from 'underscore/modules/index.js';

const g: any = typeof window !== 'undefined' ? window : globalThis;
if (!g._) g._ = _;

export default _;
export * from 'underscore/modules/index.js';