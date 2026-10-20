// Computes the frontend coverage number EXACTLY the way CI does in the
// `check_frontend_coverage` job (.github/workflows/main.yml).
//
// CI reads the clover coverage.xml emitted by vitest, takes the top-level
// <project><metrics> element, computes statement / conditional / method /
// element coverage percentages, and averages the non-zero ones. This script
// mirrors that so a local `npm run coverage` reports the same figure the CI
// gate compares against.
//
// Run after vitest has produced the report:
//   npm run coverage          # runs vitest + this script
//   npm run coverage:report   # just re-parses the last report

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Must match `reportsDirectory` + clover `file` in vitest.config.mts.
const xmlPath = path.join(
    __dirname,
    '..',
    'coverage',
    'frontend',
    'coverage.xml',
);

if (!fs.existsSync(xmlPath)) {
    console.error(
        `Coverage report not found at ${xmlPath}\n` +
            `Run \`npm run coverage\` (or \`npm run vitest\`) first.`,
    );
    process.exit(1);
}

const xml = fs.readFileSync(xmlPath, 'utf-8');

// Grab the first <metrics .../> under <project>. Clover emits a file-level set
// of <metrics> too, so anchor on the project element to match CI's
// `$xml.coverage.project.metrics`.
const projectMatch = xml.match(/<project\b[^>]*>([\s\S]*?)<\/project>/);
const scope = projectMatch ? projectMatch[0] : xml;
const metricsMatch = scope.match(/<metrics\b([^>]*)\/?>/);

if (!metricsMatch) {
    console.error('Could not find <project><metrics> in coverage.xml');
    process.exit(1);
}

const attrs = metricsMatch[1];
const num = (name) => {
    const m = attrs.match(new RegExp(`${name}="([0-9.]+)"`));
    return m ? parseFloat(m[1]) : 0;
};

const pairs = [
    ['statements', 'coveredstatements'],
    ['conditionals', 'coveredconditionals'],
    ['methods', 'coveredmethods'],
    ['elements', 'coveredelements'],
];

let total = 0;
let nonZero = 0;
const rows = [];

for (const [totalKey, coveredKey] of pairs) {
    const t = num(totalKey);
    const c = num(coveredKey);
    const pct = t > 0 ? (c / t) * 100 : 0;
    if (t > 0) {
        total += pct;
        nonZero++;
    }
    rows.push({ metric: totalKey, covered: c, total: t, pct });
}

const coverage = nonZero > 0 ? total / nonZero : 0;

console.log('\nFrontend coverage (CI-equivalent — average of non-zero metrics):');
for (const r of rows) {
    console.log(
        `  ${r.metric.padEnd(13)} ${r.pct.toFixed(2).padStart(6)}%  (${r.covered}/${r.total})`,
    );
}
console.log(`  ${'='.repeat(28)}`);
console.log(`  TOTAL         ${coverage.toFixed(2).padStart(6)}%\n`);
