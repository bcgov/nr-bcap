import { defineConfig } from 'vite';
import path from "path";
import vue from '@vitejs/plugin-vue';
import fs from 'fs';
import type { ResolvedConfig } from 'vite';

// Absolute roots inside your containers
const ROOTS = {
  bcap: '/web_root/bcap',
  common: '/web_root/bcgov-arches-common',
  arches: '/web_root/arches',
};

// Where code/templates live under each root
const MEDIA_JS = {
  bcap:   path.join(ROOTS.bcap,   'bcap',                  'media', 'js'),
  common: path.join(ROOTS.common, 'bcgov_arches_common',   'media', 'js'),
  arches: path.join(ROOTS.arches, 'arches', 'app',         'media', 'js'),
};
const TMPL_DIR = {
  bcap:   path.join(ROOTS.bcap,   'bcap',                'templates'),
  common: path.join(ROOTS.common, 'bcgov_arches_common','templates'),
  arches: path.join(ROOTS.arches, 'arches', 'app',      'templates'),
};

const CODE_EXTS  = ['.js','.mjs','.cjs','.ts','.jsx','.tsx','.vue','.json','.css'];
const TMPL_EXTS  = ['.htm','.html'];
const isUrl = (s:string) => /^[a-z]+:\/\//i.test(s);

function exists(p:string){ try { return fs.statSync(p).isFile(); } catch { return false; }}

// Prefer the ESM build regardless of which repo (bcap or arches) is providing node_modules
const jsCookieCandidates = [
  path.resolve('/web_root/bcap/node_modules/js-cookie/dist/js.cookie.mjs'),
  path.resolve('/web_root/arches/node_modules/js-cookie/dist/js.cookie.mjs'),
  path.resolve(process.cwd(), 'node_modules/js-cookie/dist/js.cookie.mjs'),
];
const jsCookieMjs = jsCookieCandidates.find(exists) || 'js-cookie/dist/js.cookie.mjs';

// Consider an import "reports/map-header" a *bare* import:
function isBare(id: string) {
  return !id.startsWith('.') && !id.startsWith('/') && !/^[a-zA-Z]+:/.test(id);
}

// Builds candidates like <base>/<rel>, <base>/<rel>.js, <base>/<rel>/index.js, etc.
function candidates(base:string, rel:string, exts:string[]) {
  const core = path.resolve(base, rel);
  return [
    core,
    ...exts.map(e => core + e),
    ...CODE_EXTS.map(e => path.join(core, 'index' + e)), // index.* makes sense for code dirs
  ];
}

/**
 * Resolve *bare* imports by checking media/js across the three roots
 * in priority order: bcap -> bcgov_arches_common -> arches.
 */
function MultiRootBareJsResolver() {
  // TOP-LEVEL: proves the plugin factory is executed
  // (this should print once when Vite starts)
  console.error('[multi-root] factory created');

  // Anything matching these is handled by Vite or other plugins – do not resolve or stat.
  const VITE_INTERNAL = /^(?:\0|virtual:|\/@id\/|\/@vite\/|\/@fs\/)/;
  const HAS_QUERY = /\?/; // e.g. ?vue&type=style, ?import, ?raw
  // priority: bcap -> common -> arches
  const ROOTS = [
    '/web_root/bcap/bcap',
    '/web_root/bcgov-arches-common/bcgov_arches_common',
    '/web_root/arches/arches/app',
  ];
  const BASES = ROOTS.map(r => path.join(r, 'media', 'js'));
  const exts  = ['.js', '.mjs', '.cjs', '.ts'];

  const logger: ResolvedConfig['logger'] | null = null;
  const out = (...a: any[]) => {
    const line = `[multi-root] ${a.join(' ')}`;
    if (logger) logger.info(line);
    else console.error(line);              // fallback until configResolved
  };
  const tryResolve = (spec: string) => {
    for (const base of BASES) {
      const stem = path.join(base, spec);
      const candidates = [
        ...exts.map(e => stem + e),
        ...exts.map(e => path.join(stem, 'index' + e)),
      ];
      out(`Trying to resolve bare import ${spec} as ${candidates.join(',')}`);
      for (const p of candidates) {
        try { if (fs.statSync(p).isFile()) return p; } catch {}
      }
    }
    return null;
  };

  return {
    name: 'multi-root-bare-js-resolver',
    enforce: 'pre' as const,
    async resolveId(source: string, importer?: string) {
      // 1) Skip Vite internal/virtual ids and virtual importers
      if (VITE_INTERNAL.test(source) || (importer && VITE_INTERNAL.test(importer)) || HAS_QUERY.test(source)) {
        out('skip internal/virtual', { source, importer });
        return null; // let Vite/plugin-vue handle it
      }
      // let Vite/aliases try first
      out(`In resolveId: source ${source}`);
      const prior = await (this as any).resolve(source, importer, { skipSelf: true });
      out(`prior? ${prior}`);
      console.error(prior);
      if (prior && fs.statSync(prior.id).isFile()) return prior;

      out(`isBare(${source}) = ${isBare(source)}`);
      if (!isBare(source)) return null;

      const file = tryResolve(source);
      if (file) {
        // Force Vite to emit a proper @fs URL with an extension
        return '/@fs' + file;
      }
      return null;
    },
  };
}

function MultiRootFailoverResolver() {
  const logger: ResolvedConfig['logger'] | null = null;
  const out = (...a: any[]) => {
    const line = `[multi-root-failover] ${a.join(' ')}`;
    if (logger) logger.info(line);
    else console.error(line);              // fallback until configResolved
  };
  return {
    name: 'multi-root-failover-resolver',
    enforce: 'pre' as const,

    resolveId(id: string, importer?: string) {
      if (isUrl(id)) return null;                    // leave URLs alone
      if (id.startsWith('.') || id.startsWith('/')) return null; // let Vite handle relative/absolute

      // Preserve npm packages (jquery, underscore, vue, etc.)
      // We only intercept our legacy namespaces + the special "arches" entry.
      const isArchesSymbol = id === 'arches' || id === 'arches.js';
      const isLegacyNs = /^(viewmodels|reports|models|views|bindings|utils|plugins|templates)\//.test(id);
      const isLibrary = /^(js-cookie)\/.*$/.test(id);
      out(`resolveId(${id} ? library? ${isLibrary})`);
      if ((!isArchesSymbol && !isLegacyNs) || isLibrary) return null;

      // keep ?query (e.g., template imports that Vite appends)
      const qpos = id.indexOf('?');
      const bare = qpos >= 0 ? id.slice(0, qpos) : id;
      const tail = qpos >= 0 ? id.slice(qpos) : '';

      // arches -> arches.js under media/js with failover
      if (isArchesSymbol) {
        for (const key of ['bcap','common','arches'] as const) {
          const p = path.join(MEDIA_JS[key], 'arches.js');
          if (exists(p)) return p + tail;
        }
        return null;
      }

      // legacy namespaces
      const seg = bare.split('/')[0]; // viewmodels|bindings|utils|plugins|templates
      const rest = bare.slice(seg.length + 1); // path after the namespace

      // choose bases per namespace
      const basesPerRoot = (seg === 'templates')
        ? TMPL_DIR
        : MEDIA_JS;

      // search in priority order: bcap -> common -> arches
      for (const key of ['bcap','common','arches'] as const) {
        const base = basesPerRoot[key];
        const exts = (seg === 'templates') ? TMPL_EXTS : CODE_EXTS;
        for (const cand of candidates(base, seg === 'templates' ? rest : path.join(seg, rest), exts)) {
          if (exists(cand)) return cand + tail;
        }
      }
      return null; // let Vite error normally if nothing found
    },
  };
}

// Optional: load raw .htm/.html as strings when imported
function HtmAsString() {
  return {
    name: 'htm-as-string',
    enforce: 'pre' as const,
    load(id: string) {
      const clean = id.split('?')[0];
      if (clean.endsWith('.htm') || clean.endsWith('.html')) {
        const txt = fs.readFileSync(clean, 'utf8').replace(/`/g, '\\`');
        return `export default \`${txt}\`;`;
      }
      return null;
    },
  };
}


export default defineConfig({
  appType: 'custom',                 // <- critical: no SPA HTML fallback
  // Vite-only URLs live under this prefix; Django serves everything else.
  base: '/bcap/@vite/',
  // root: path.resolve(__dirname, 'bcap'),

  plugins: [
    MultiRootBareJsResolver(),
    vue(),
    MultiRootFailoverResolver(),
    HtmAsString(),
],

  resolve: {
    preserveSymlinks: true,
    dedupe: ['vue'], // safe to keep; has no effect if you’re not using Vue
    alias: [
    // Force ESM entry
    { find: /^js-cookie$/, replacement: jsCookieMjs },
    // Also catch direct “src/js.cookie(.js)” imports that some Arches code may use
    { find: /^js-cookie\/src\/js\.cookie(?:\.js)?$/, replacement: jsCookieMjs },
    // point bare imports to the window-backed shims
    { find: /^uuid$/,              replacement: '/@fs/web_root/bcap/vite-shims/uuid-default.js' },
    { find: /^jquery$/,              replacement: '/@fs/web_root/bcap/vite-shims/jquery-global.js' },
    { find: /^underscore$/,          replacement: '/@fs/web_root/bcap/vite-shims/underscore-global.js' },
    { find: /^backbone$/,            replacement: '/@fs/web_root/bcap/vite-shims/backbone-global.js' },
    { find: /^knockout$/,            replacement: '/@fs/web_root/bcap/vite-shims/knockout-global.js' },
    { find: /^knockout-mapping$/,    replacement: '/@fs/web_root/bcap/vite-shims/knockout-mapping-global.js' },

    // neutralize accidental module imports for libs the page already provides
    { find: /^bootstrap$/,           replacement: '/@fs/web_root/bcap/vite-shims/noop.js' },
    { find: /^jqueryui(\/.*)?$/,     replacement: '/@fs/web_root/bcap/vite-shims/noop.js' },
    { find: /^jquery-ui(\/.*)?$/,    replacement: '/@fs/web_root/bcap/vite-shims/noop.js' },
    { find: /^datatables\.net(-.*)?$/, replacement: '/@fs/web_root/bcap/vite-shims/noop.js' },
      // Point the bare 'arches' import at the browser file in the Arches repo
    { find: /^arches$/, replacement: "/@fs/web_root/arches/arches/app/media/js/arches.js" },
    { find: /^vue$/, replacement: '/@fs/web_root/bcap/node_modules/vue/dist/vue.runtime.esm-bundler.js' },


      // // Minimal Arches media helpers so imports like "viewmodels/..." resolve
      // { find: /^viewmodels\//, replacement: "/@fs/web_root/arches/arches/app/media/js/viewmodels/" },
      // { find: /^bindings\//, replacement: "/@fs/web_root/arches/arches/app/media/js/bindings/" },
      // { find: /^utils\//, replacement: "/@fs/web_root/arches/arches/app/media/js/utils/" },
      //
      // (optional) if templates are imported as strings anywhere
      // { find: /^templates\//, replacement: "/@fs/web_root/arches/arches/app/templates/" },

      // If your code imports 'slick', map it to slick-carousel’s browser build
      // (install if needed: npm i slick-carousel)
      { find: /^slick$/, replacement: "/@fs/web_root/arches/arches/app/media/plugins/slick/slick.js" },
      { find: /^chosen$/, replacement: "/@fs/web_root/bcap/node_modules/chosen-js/chosen.jquery.js" },
      { find: /^geojson-extent$/, replacement: "/@fs/web_root/bcap/node_modules/@mapbox/geojson-extent/geojson-extent.js" },
      { find: /^mapbox-gl-geocoder$/, replacement: "/@fs/web_root/bcap/node_modules/@mapbox/mapbox-gl-geocoder/dist/mapbox-gl-geocoder.min.js" },

      {
        find: '@/bcap',
        replacement: path.resolve(path.join(__dirname, './bcap/src/bcap')),
      },
    ],
  },

  // optimizeDeps: {
  //   // Don’t prebundle libs we are sourcing from Django globals
  //   exclude: [
  //     'jquery',
  //     'underscore',
  //     'backbone',
  //     'bootstrap',
  //     'knockout',
  //     'knockout-mapping',
  //     'jqueryui',
  //     'jquery-ui',
  //     'datatables.net',
  //     'datatables.net-bs',
  //     'datatables.net-buttons',
  //     'datatables.net-buttons-bs',
  //     'datatables.net-buttons-html5',
  //     'datatables.net-buttons-print',
  //     'datatables.net-responsive',
  //     'datatables.net-responsive-bs',
  //   ],
  //   entries: [
  //     path.resolve(__dirname, 'bcap/vite-entries/bcap-site.entry.ts'),
  //     path.resolve(__dirname, 'bcap/vite-entries/map.entry.js'),
  //   ],
  //   force: true,
  //   esbuildOptions: { preserveSymlinks: true },
  // },

  optimizeDeps: {
    noDiscovery: true,   // <-- don’t even crawl for candidates
    entries: [],         // <-- explicit: nothing to warm/scan
    include: [],
    exclude: ['vue'],
    esbuildOptions: { preserveSymlinks: true },
  },
  server: {
    host: '0.0.0.0',
    port: 5175,               // you asked to keep this
    strictPort: true,
    origin: 'http://localhost:82',
    hmr: {
      protocol: 'ws',
      host: 'localhost',      // browser reaches Vite through nginx on :82
      port: 82,
      path: '/@vite',
      clientPort: 82,
    },
    fs: {
      allow: ["/web_root", "/web_root/bcap", "/web_root/arches",
        path.join(ROOTS.bcap, "bcap"),
        path.join(ROOTS.common, "bcgov_arches_common"),
        path.join(ROOTS.arches, "arches", "app")]
    },
    // warmup: {
    //   clientFiles: [
    //     '/bcap/@vite/bcap/vite-entries/bcap-site.entry.ts',
    //     '/bcap/@vite/bcap/vite-entries/map.entry.js',
    //   ],
    // },
  },
});