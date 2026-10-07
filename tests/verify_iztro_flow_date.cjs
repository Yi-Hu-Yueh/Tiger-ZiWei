/* Development-only Phase 8B comparison against the existing pinned engine. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const revision = '2c7ef9be669df7b19d1799f4dce335fed3794f78';
const base = path.resolve('tmp/phase1f-iztro');
const root = path.join(base, 'source', `iztro-${revision}`);
const receipt = JSON.parse(fs.readFileSync(path.join(base, 'build-receipt.json'), 'utf8'));
assert.equal(receipt.revision, revision);

const iztro = require(path.join(root, 'lib'));
const configuration = { algorithm: 'default', yearDivide: 'normal', dayDivide: 'current' };
iztro.astro.config(configuration);
const chart = iztro.astro.bySolar('2025-01-29', 0, '女', true, 'zh-TW');

function compare(date) {
  const horoscope = chart.horoscope(date, 6);
  const branchAt = (index) => chart.palaces[index].earthlyBranch;
  return {
    date,
    lunarDate: horoscope.lunarDate,
    flowYearBranch: branchAt(horoscope.yearly.index),
    flowMonthLifeBranch: branchAt(horoscope.monthly.index),
    flowDayLifeBranch: branchAt(horoscope.daily.index),
    monthGanzhi: horoscope.monthly.heavenlyStem + horoscope.monthly.earthlyBranch,
    dayGanzhi: horoscope.daily.heavenlyStem + horoscope.daily.earthlyBranch,
  };
}

console.log(JSON.stringify({
  revision,
  configuration,
  scope: 'representative non-leap Flow-Year/Month/Day Life branches and month/day Ganzhi',
  differentConvention: [
    'Tiger whole leap month N uses effective month N+1; iztro may split leap month around day 15',
    'Tiger late-Zi keeps the supplied civil/lunar date; comparison excludes late-Zi defaults',
  ],
  results: ['2029-02-13', '2029-02-14'].map(compare),
}, null, 2));
