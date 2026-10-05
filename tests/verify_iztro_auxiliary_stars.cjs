/* Optional development-only full-engine comparison. No Node production use.
 * Reuses the Phase 1F pinned source + lockfile build without npm/install hooks.
 * Only fourteen auxiliary positions are projected; no brightness or 四化.
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const assert = require('node:assert/strict');
const revision = '2c7ef9be669df7b19d1799f4dce335fed3794f78';
const base = path.resolve('tmp/phase1f-iztro');
const root = path.join(base, 'source', `iztro-${revision}`);
const receipt = JSON.parse(fs.readFileSync(path.join(base, 'build-receipt.json'), 'utf8'));
assert.equal(receipt.revision, revision);
assert.equal(receipt.source_archive_sha256, '794938fbc17331b3cbf66040c39ceb1a82aa21ad31cf7f35f3324e685379da68');
for (const [relative, hash] of Object.entries(receipt.source_hashes)) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'src', relative))).digest('hex'), hash);
}
const iztro = require(path.join(root, 'lib'));
const configuration = {algorithm:'default', yearDivide:'normal', dayDivide:'current'};
iztro.astro.config(configuration);
for (const [key, value] of Object.entries(configuration)) assert.equal(iztro.astro.getConfig()[key], value);
const names = ['左輔','右弼','文昌','文曲','天魁','天鉞','祿存','擎羊','陀羅','天馬','火星','鈴星','地空','地劫'];
const pythonPath = process.env.TIGER_PYTHON || path.resolve('.venv311/Scripts/python.exe');
const python = spawnSync(pythonPath, ['-X','utf8','-m','scripts.validate_auxiliary_stars','--comparison-cases'], {encoding:'utf8'});
assert.equal(python.status, 0, python.stderr);
const cases = JSON.parse(python.stdout);
const results = [];
for (const row of cases) {
  const b = row.input;
  const solar = `${b.birth_year}-${String(b.birth_month).padStart(2,'0')}-${String(b.birth_day).padStart(2,'0')}`;
  const timeIndex = b.birth_hour === 23 ? 12 : Math.floor((b.birth_hour + 1) / 2);
  const full = iztro.astro.bySolar(solar, timeIndex, b.gender === 'female' ? '女' : '男', true, 'zh-TW');
  const lunar = full.rawDates.lunarDate;
  assert.deepEqual(row.chart.lunar_date, {year:lunar.lunarYear, month:lunar.lunarMonth,
    day:lunar.lunarDay, is_leap_month:lunar.isLeap});
  assert.equal(row.chart.year_ganzhi, full.rawDates.chineseDate.yearly.join(''));
  const external = {};
  for (const palace of full.palaces) {
    // Some iztro builds put 祿存/天馬 in majorStars; select by name, not category.
    for (const star of [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars]) {
      if (!names.includes(star.name)) continue;
      assert(!(star.name in external), `duplicate ${star.name}`);
      external[star.name] = palace.earthlyBranch;
    }
  }
  assert.equal(Object.keys(external).length, 14);
  assert(Object.values(external).every(b => '子丑寅卯辰巳午未申酉戌亥'.includes(b)));
  const differences = Object.entries(row.chart.stars)
    .filter(([name, branch]) => external[name] !== branch)
    .map(([name, tiger]) => ({name, tiger, external:external[name]}));
  assert.equal(row.chart.status, 'PASS');
  assert.equal(Object.keys(row.chart.stars).length, 14);
  const yearHourMatch = names.slice(2).every(name => row.chart.stars[name] === external[name]);
  let status = differences.length ? 'FAIL' : 'PASS';
  if (row.case === 'L') {
    assert.equal(row.chart.lunar_date.is_leap_month, true);
    assert.equal(row.chart.lunar_date.month, 6);
    assert.equal(row.chart.lunar_date.day, 1);
    assert.equal(row.chart.auxiliary_effective_month, 7);
    assert.equal(row.chart.stars['左輔'], '戌');
    assert.equal(row.chart.stars['右弼'], '辰');
    assert.equal(external['左輔'], '酉');
    assert.equal(external['右弼'], '巳');
    // Only these exact month-star differences qualify; never excuse a year/hour bug.
    if (yearHourMatch && differences.length === 2 &&
        differences.every(d => ['左輔','右弼'].includes(d.name))) status = 'DIFFERENT_CONVENTION';
  }
  results.push({case:row.case, input:b, status,
    compared_count:Object.keys(row.chart.stars).length, year_hour_stars_match:yearHourMatch,
    differences, tiger:row.chart.stars, external,
    convention:row.case === 'L' ? 'Tiger whole leap month uses next month; iztro fixLeap=true splits at day 15/16 and uses month 6 on leap day 1. Left/right DIFFERENT_CONVENTION; twelve year/hour stars MATCH.' : null});
}
const report = {revision, configuration, fixLeap:true, language:'zh-TW', versions:receipt.versions,
  engine:'full compiled pinned source and actual pinned lunar dependencies; no stubs',
  scope:'auxiliary star branches only; unchanged Phase 1 fields validated by their existing suite', results};
const serialized = JSON.stringify(report, null, 2);
if (process.argv.includes('--save-report')) {
  const output = path.resolve('output/phase2a');
  fs.mkdirSync(output, {recursive:true});
  fs.writeFileSync(path.join(output, 'iztro-comparison.json'), serialized + '\n');
}
console.log(serialized);
if (results.some(r => r.status==='FAIL')) process.exitCode = 1;
