/* Development-only Phase 6C comparison against the existing pinned full engine. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const revision = '2c7ef9be669df7b19d1799f4dce335fed3794f78';
const base = path.resolve('tmp/phase1f-iztro');
const root = path.join(base, 'source', `iztro-${revision}`);
const receipt = JSON.parse(fs.readFileSync(path.join(base, 'build-receipt.json'), 'utf8'));
assert.equal(receipt.revision, revision);
for (const [relative, hash] of Object.entries(receipt.source_hashes)) {
  const actual = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'src', relative))).digest('hex');
  assert.equal(actual, hash, `source hash mismatch: ${relative}`);
}

const iztro = require(path.join(root, 'lib'));
const configuration = { algorithm: 'default', yearDivide: 'normal', dayDivide: 'current' };
iztro.astro.config(configuration);
const aliases = { '僕役': '交友宮', '奴僕': '交友宮', '事業': '官祿宮' };
function palaceName(value) {
  const stem = value.replace(/宮$/, '');
  return aliases[stem] || `${stem}宮`;
}
function normalize(targetYear) {
  const chart = iztro.astro.bySolar('2025-01-29', 0, '女', true, 'zh-TW');
  // July is unambiguously inside the requested Chinese lunar year. Only the
  // yearly result is compared; no monthly, daily, star or mutagen data is used.
  const yearly = chart.horoscope(`${targetYear}-07-01`, 0).yearly;
  const palaces = chart.palaces.map((palace, index) => ({
    flowPalace: palaceName(yearly.palaceNames[index]),
    branch: palace.earthlyBranch,
  }));
  return {
    targetYear,
    stem: yearly.heavenlyStem,
    branch: yearly.earthlyBranch,
    lifeIndex: yearly.index,
    palaces,
    targets: [...yearly.mutagen],
  };
}
console.log(JSON.stringify({
  revision,
  configuration,
  scope: 'yearly stem/branch, yearly Life-Palace index, annual palace-name rotation and mutagen targets',
  excluded: 'yearly stars, childhood limits and interpretation',
  results: [2026, 2029, 2032, 2039].map(normalize),
}, null, 2));
