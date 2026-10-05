/* Optional DEVELOPMENT-ONLY source comparison; never imported by Python.
 * Run from repository root with Node 24 after downloading the two public files
 * to tmp/phase1e-iztro/{location,majorStar}.ts from:
 * https://raw.githubusercontent.com/SylarLong/iztro/2c7ef9be669df7b19d1799f4dce335fed3794f78/src/star/
 * No npm install, network request, or runtime iztro dependency is needed.
 *
 * Execute the actual getStartIndex/getMajorStar function bodies with calendar,
 * bureau, translation, brightness and mutation dependencies stubbed. This is
 * a placement-kernel comparison, NOT an external full-calendar/chart check.
 * Stubs inject already-verified lunar day and bureau. dayDivide='current'.
 * Only TypeScript syntax/export syntax is removed, not calculation logic.
 */
const fs = require('node:fs');
const crypto = require('node:crypto');
const vm = require('node:vm');
const { stripTypeScriptTypes } = require('node:module');
const { spawnSync } = require('node:child_process');
const assert = require('node:assert/strict');

function source(file, hash, name) {
  const bytes = fs.readFileSync(`tmp/phase1e-iztro/${file}.ts`);
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), hash);
  const text = bytes.toString('utf8');
  const begin = text.indexOf(`export const ${name} =`);
  const end = text.indexOf('\n};', begin) + 3;
  assert(begin >= 0 && end > begin);
  const declaration = text.slice(begin, end).replace('export const', 'const');
  return stripTypeScriptTypes(declaration) + `\n${name};`;
}
const startSource = source('location', '082f2b5883e57e7f6858cc64573efd5916baecedd578a09fdefdbc291849caef', 'getStartIndex');
const majorSource = source('majorStar', '1bb69864538458df73871f62fd826e1180ba9a33a8db89da3e7d4983dbe418a2', 'getMajorStar');
const input = { day: 1, bureau: 2 };
const translated = {
  ziweiMaj: '紫微', tianjiMaj: '天機', taiyangMaj: '太陽', wuquMaj: '武曲',
  tiantongMaj: '天同', lianzhenMaj: '廉貞', tianfuMaj: '天府', taiyinMaj: '太陰',
  tanlangMaj: '貪狼', jumenMaj: '巨門', tianxiangMaj: '天相', tianliangMaj: '天梁',
  qishaMaj: '七殺', pojunMaj: '破軍',
};
const context = {
  getSoulAndBody: () => ({}),
  solar2lunar: () => ({ lunarDay: input.day }),
  getFiveElementsClass: () => 'supplied',
  FiveElementsClass: { get supplied() { return input.bureau; } },
  kot: value => value,
  getTotalDaysOfLunarMonth: () => 30,
  getConfig: () => ({ dayDivide: 'current', yearDivide: 'normal' }),
  fixIndex: value => ((value % 12) + 12) % 12,
  getHeavenlyStemAndEarthlyBranchBySolarDate: () => ({ yearly: ['unused'] }),
  initStars: () => Array.from({ length: 12 }, () => []),
  t: value => translated[value],
  getBrightness: () => undefined,
  getMutagen: () => undefined,
  FunctionalStar: class { constructor(value) { this.name = value.name; } },
};
context.getStartIndex = vm.runInNewContext(startSource, context);
const getMajorStar = vm.runInNewContext(majorSource, context);
const python = spawnSync('.venv311/Scripts/python.exe', ['-X', 'utf8', '-c', `
import json
from tests.major_star_reference import CLASSICAL_CASES, FULL_LAYOUTS, STAR_NAMES
from tests.test_main_stars import rule_chart
print(json.dumps([dict(bureau=b, day=d, expected=dict(zip(STAR_NAMES, FULL_LAYOUTS[z])),
                      actual=rule_chart(b, d).star_to_branch) for b,d,z in CLASSICAL_CASES]))
`], { encoding: 'utf8' });
assert.equal(python.status, 0, python.stderr);
const rows = JSON.parse(python.stdout);
const branches = '寅卯辰巳午未申酉戌亥子丑'; // iztro's local array coordinate only.
const visited = new Set();
for (const row of rows) {
  input.day = row.day;
  input.bureau = row.bureau;
  const param = { solarDate: 'injected-not-converted', timeIndex: 0, fixLeap: false };
  const starts = context.getStartIndex(param);
  visited.add(starts.ziweiIndex);
  const actual = {};
  getMajorStar(param).forEach((stars, index) => stars.forEach(star => {
    assert(!(star.name in actual));
    actual[star.name] = branches[index];
  }));
  assert.deepEqual(actual, row.expected, `iztro/classical bureau=${row.bureau} day=${row.day}`);
  assert.deepEqual(actual, row.actual, `iztro/Python bureau=${row.bureau} day=${row.day}`);
}
assert.equal(rows.length, 150);
assert.equal(visited.size, 12);
for (const [bureau, day, expected] of [[3, 27, '戌'], [6, 13, '亥'], [5, 6, '未']]) {
  input.day = day;
  input.bureau = bureau;
  const result = context.getStartIndex({ solarDate: 'injected', timeIndex: 0 });
  assert.equal(branches[result.ziweiIndex], expected);
  console.log(`published vector: bureau=${bureau}, day=${day}, ziwei=${expected}: MATCH`);
}
input.day = 30;
input.bureau = 3;
assert.equal(branches[context.getStartIndex({ solarDate: 'injected', timeIndex: 12 }).ziweiIndex], '亥');
console.log('150 full fourteen-star comparisons: MATCH; 0 mismatch; all 12 rotations; current-day late-Zi: MATCH');
