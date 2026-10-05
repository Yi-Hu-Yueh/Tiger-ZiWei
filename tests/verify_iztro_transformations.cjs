/* Optional development-only Phase 2B comparison against pinned full iztro.
 * Production Python never imports Node or iztro.
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
for (const [relative, hash] of Object.entries(receipt.source_hashes)) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'src', relative))).digest('hex'), hash);
}
const iztro = require(path.join(root, 'lib'));
const configuration = {algorithm:'default', yearDivide:'normal', dayDivide:'current'};
iztro.astro.config(configuration);

const pythonPath = process.env.TIGER_PYTHON || path.resolve('.venv311/Scripts/python.exe');
const python = spawnSync(pythonPath, ['-X','utf8','-m','scripts.validate_transformations','--comparison-cases'], {encoding:'utf8'});
assert.equal(python.status, 0, python.stderr);
const tiger = JSON.parse(python.stdout);

const types = ['化祿','化權','化科','化忌'];
const mutagenToType = {'祿':'化祿','權':'化權','科':'化科','忌':'化忌'};
const canonicalPalaces = ['命宮','兄弟宮','夫妻宮','子女宮','財帛宮','疾厄宮','遷移宮','交友宮','官祿宮','田宅宮','福德宮','父母宮'];
const canonicalPalace = name => {
  const stem = name.replace(/宮$/, '');
  const value = ({'僕役':'交友','奴僕':'交友','事業':'官祿'}[stem] || stem) + '宮';
  assert(canonicalPalaces.includes(value), `unknown palace ${name}`);
  return value;
};
const timeIndex = hour => hour === 23 ? 12 : Math.floor((hour + 1) / 2);
function chartFor(solar, hour, gender='female') {
  return iztro.astro.bySolar(solar, timeIndex(hour), gender === 'female' ? '女' : '男', true, 'zh-TW');
}
function transformations(chart) {
  const found = [];
  for (const palace of chart.palaces) {
    for (const star of [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars]) {
      if (!star.mutagen) continue;
      const transformation = mutagenToType[star.mutagen];
      assert(transformation, `unknown mutagen ${star.mutagen}`);
      found.push({transformation, star_name:star.name,
        earthly_branch:palace.earthlyBranch, palace_name:canonicalPalace(palace.name)});
    }
  }
  found.sort((a,b)=>types.indexOf(a.transformation)-types.indexOf(b.transformation));
  assert.equal(found.length, 4);
  assert.equal(new Set(found.map(row=>row.transformation)).size, 4);
  return found;
}

// One safely post-Lunar-New-Year civil date for each 2014..2023 stem.
const vectors = {
  '甲':['2014-02-10',12], '乙':['2015-02-20',12], '丙':['2016-02-10',12],
  '丁':['2017-02-01',12], '戊':['2018-02-20',12], '己':['2019-02-10',12],
  '庚':['2020-02-01',12], '辛':['2021-02-20',12], '壬':['2022-02-10',12],
  '癸':['2023-02-01',12],
};
const externalTable = {};
for (const [stem,[solar,hour]] of Object.entries(vectors)) {
  const chart = chartFor(solar,hour);
  assert.equal(chart.rawDates.chineseDate.yearly[0], stem);
  externalTable[stem] = transformations(chart).map(row=>row.star_name);
}
const differences = [];
for (const stem of Object.keys(tiger.table)) {
  types.forEach((transformation,index) => {
    if (tiger.table[stem][index] !== externalTable[stem][index]) {
      differences.push({stem, transformation, tiger:tiger.table[stem][index], external:externalTable[stem][index]});
    }
  });
}
const classification = differences.length === 1 &&
  JSON.stringify(differences[0]) === JSON.stringify({stem:'壬',transformation:'化科',tiger:'天府',external:'左輔'})
  ? 'EDITION_VARIANT' : differences.length ? 'FAIL' : 'MATCH';

const cases = [];
for (const row of tiger.cases) {
  const b = row.input;
  const solar = `${b.birth_year}-${String(b.birth_month).padStart(2,'0')}-${String(b.birth_day).padStart(2,'0')}`;
  const external = transformations(chartFor(solar,b.birth_hour,b.gender));
  const local = row.chart.transformations.map(item => ({
    transformation:item.transformation, star_name:item.star_name,
    earthly_branch:item.earthly_branch, palace_name:item.palace_name,
  }));
  const targetNamesMatch = local.every((item,index)=>item.star_name===external[index].star_name);
  const recordDifferences = local.map((item,index)=>({tiger:item,external:external[index]}))
    .filter(item=>JSON.stringify(item.tiger)!==JSON.stringify(item.external));
  const caseClassification = recordDifferences.length === 0 ? 'MATCH'
    : row.case === 'L' && targetNamesMatch ? 'DIFFERENT_CONVENTION' : 'FAIL';
  cases.push({case:row.case, classification:caseClassification,
    target_names_match:targetNamesMatch, differences:recordDifferences,
    tiger:local, external});
}
const report = {revision, configuration, fixLeap:true, language:'zh-TW',
  engine:'full compiled pinned source and lockfile dependencies; no stubs',
  compared_assignments:40, classification, differences,
  tiger_table:tiger.table, external_table:externalTable, cases};
const serialized = JSON.stringify(report,null,2);
if (process.argv.includes('--save-report')) {
  const output = path.resolve('output/phase2b');
  fs.mkdirSync(output,{recursive:true});
  fs.writeFileSync(path.join(output,'iztro-comparison.json'),serialized+'\n');
}
console.log(serialized);
if (classification === 'FAIL' || cases.some(row=>row.classification==='FAIL')) process.exitCode = 1;
