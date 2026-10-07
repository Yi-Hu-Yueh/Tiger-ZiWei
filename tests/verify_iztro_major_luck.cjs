/* Development-only Phase 6A comparison against the existing pinned full engine. */
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
const branches = '子丑寅卯辰巳午未申酉戌亥';
const canonicalNames = ['命宮','兄弟宮','夫妻宮','子女宮','財帛宮','疾厄宮','遷移宮','交友宮','官祿宮','田宅宮','福德宮','父母宮'];
function palaceName(value) {
  const stem = value.replace(/宮$/, '');
  const normalized = ({ '僕役':'交友', '奴僕':'交友', '事業':'官祿' }[stem] || stem) + '宮';
  assert(canonicalNames.includes(normalized), `unknown palace ${value}`);
  return normalized;
}
function normalize(label, solar, timeIndex, gender) {
  const chart = iztro.astro.bySolar(solar, timeIndex, gender === 'female' ? '女' : '男', true, 'zh-TW');
  const periods = chart.decadalList().map(decadal => ({
    range: [...decadal.ageRange],
    stem: decadal.heavenlyStem,
    branch: decadal.earthlyBranch,
    palace: palaceName(decadal.palaceName),
    ganzhi: decadal.heavenlyStem + decadal.earthlyBranch,
    targets: [...decadal.mutagen],
  }));
  assert.equal(periods.length, 12);
  assert.equal(new Set(periods.map(item => item.branch)).size, 12);
  assert.equal(periods[0].palace, '命宮');
  const first = branches.indexOf(periods[0].branch);
  const second = branches.indexOf(periods[1].branch);
  const direction = second === (first + 1) % 12 ? '順行' : '逆行';
  return { case: label, gender, direction, periods };
}
const results = [
  normalize('A-FEMALE', '2025-01-29', 0, 'female'),
  normalize('A-MALE', '2025-01-29', 0, 'male'),
  normalize('C-FEMALE', '2024-02-29', 6, 'female'),
];
console.log(JSON.stringify({
  revision, configuration, fixLeap: true, language: 'zh-TW',
  scope: 'direction, nominal-age ranges, host branches, palace names, palace Ganzhi',
  excluded: 'decadal transformations, decadal stars, annual luck and interpretation',
  results,
}, null, 2));
