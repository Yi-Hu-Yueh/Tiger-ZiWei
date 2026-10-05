/* Development-only FULL engine comparison; unlike Phase 1E, no dependencies
 * are stubbed. Run setup_iztro_basic_chart.cjs first. JSON only on stdout.
 * The production app and normal Python runtime do not import Node or iztro.
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
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
const configuration = { algorithm: 'default', yearDivide: 'normal', dayDivide: 'current' };
iztro.astro.config(configuration);
for (const [key, value] of Object.entries(configuration)) assert.equal(iztro.astro.getConfig()[key], value);
const branches = '子丑寅卯辰巳午未申酉戌亥';
const canonicalNames = ['命宮','兄弟宮','夫妻宮','子女宮','財帛宮','疾厄宮','遷移宮','交友宮','官祿宮','田宅宮','福德宮','父母宮'];
const majorNames = new Set(['紫微','天機','太陽','武曲','天同','廉貞','天府','太陰','貪狼','巨門','天相','天梁','七殺','破軍']);
const names = name => {
  const stem = name.replace(/宮$/, '');
  const canonical = ({ '僕役':'交友', '奴僕':'交友', '事業':'官祿' }[stem] || stem) + '宮';
  assert(canonicalNames.includes(canonical), `unknown palace ${name}`);
  return canonical;
};
function normalize(chart) {
  const lunar = chart.rawDates.lunarDate;
  const stars = {};
  const palaces = chart.palaces.map(p => {
    const major = p.majorStars.filter(s => majorNames.has(s.name));
    for (const s of major) {
      assert(!(s.name in stars), `duplicate star ${s.name}`);
      stars[s.name] = p.earthlyBranch;
    }
    return { branch:p.earthlyBranch, name:names(p.name), stem:p.heavenlyStem,
      ganzhi:p.heavenlyStem+p.earthlyBranch, body:p.isBodyPalace,
      stars:major.map(s=>s.name).sort() };
  }).sort((a,b)=>branches.indexOf(a.branch)-branches.indexOf(b.branch));
  assert.equal(palaces.length,12);
  assert.equal(new Set(palaces.map(p=>p.branch)).size,12);
  assert.equal(new Set(palaces.map(p=>p.name)).size,12);
  assert.equal(Object.keys(stars).length,14);
  const life = palaces.find(p=>p.name==='命宮');
  const body = palaces.filter(p=>p.body);
  assert.equal(body.length,1);
  assert.equal(life.branch,chart.earthlyBranchOfSoulPalace);
  assert.equal(body[0].branch,chart.earthlyBranchOfBodyPalace);
  return {
    lunar_date:{year:lunar.lunarYear,month:lunar.lunarMonth,day:lunar.lunarDay,is_leap_month:lunar.isLeap},
    year_ganzhi:chart.rawDates.chineseDate.yearly.join(''),
    life:life.branch,body:body[0].branch,body_name:body[0].name,life_ganzhi:life.ganzhi,
    bureau:{name:chart.fiveElementsClass,number:{'水二局':2,'木三局':3,'金四局':4,'土五局':5,'火六局':6}[chart.fiveElementsClass]},
    palaces,stars,
  };
}
const pythonPath = process.env.TIGER_PYTHON || path.resolve('.venv311/Scripts/python.exe');
const python = spawnSync(pythonPath, ['-X','utf8','-m','scripts.validate_basic_chart','--comparison-cases'], {encoding:'utf8'});
assert.equal(python.status,0,python.stderr);
const cases = JSON.parse(python.stdout);
const same = (a,b) => { try { assert.deepEqual(a,b); return true; } catch { return false; } };
const results = [];
for (const row of cases) {
  const b = row.input;
  const solar = `${b.birth_year}-${String(b.birth_month).padStart(2,'0')}-${String(b.birth_day).padStart(2,'0')}`;
  const timeIndex = b.birth_hour === 23 ? 12 : Math.floor((b.birth_hour+1)/2);
  const external = normalize(iztro.astro.bySolar(solar,timeIndex,b.gender==='female'?'女':'男',true,'zh-TW'));
  const tiger = row.chart;
  const checks = [
    ['lunar_date','CALENDAR_MISMATCH'], ['year_ganzhi','YEAR_BOUNDARY_MISMATCH'],
    ['life','LIFE_BODY_MISMATCH'], ['body','LIFE_BODY_MISMATCH'], ['body_name','LIFE_BODY_MISMATCH'],
    ['palace_names','PALACE_ORDER_MISMATCH'], ['palace_stems','PALACE_STEM_MISMATCH'],
    ['life_ganzhi','PALACE_STEM_MISMATCH'], ['bureau','BUREAU_MISMATCH'], ['stars','MAJOR_STAR_MISMATCH'],
    ['palaces','IMPLEMENTATION_BUG'],
  ];
  const field = (chart,key) => key==='palace_names' ? chart.palaces.map(p=>[p.branch,p.name])
    : key==='palace_stems' ? chart.palaces.map(p=>[p.branch,p.stem]) : chart[key];
  const differences = checks.filter(([key])=>!same(field(tiger,key),field(external,key)))
    .map(([field,category])=>({field,category}));
  const leap = tiger.lunar_date.is_leap_month;
  // A convention flag never excuses a calendar/year disagreement.
  const upstreamMatch = same(tiger.lunar_date,external.lunar_date) && tiger.year_ganzhi===external.year_ganzhi;
  const classification = differences.length===0 ? 'FULL MATCH'
    : leap && upstreamMatch ? 'DIFFERENT_CONVENTION' : 'MISMATCH';
  const result = {input:row.input, classification,
    earliest_divergence: differences.length ? { ...differences[0],
      cause:classification==='DIFFERENT_CONVENTION'?'LEAP_MONTH_CONVENTION':differences[0].category } : null,
    differences,tiger,external};
  results.push(result);
  if (classification==='MISMATCH') break; // Investigate before later cases.
}
const failed = results.some(r=>r.classification==='MISMATCH');
const report = {revision,configuration,fixLeap:true,language:'zh-TW',
  engine:'full compiled pinned source, actual lockfile-pinned lunar dependencies, no stubs',
  versions:receipt.versions,
  comparison_scope:'lunar date, primary year Ganzhi, Life/Body, twelve palace names/stems, Life Ganzhi, bureau, fourteen major stars',
  excluded:'month/day/hour Ganzhi external comparison and all unimplemented chart fields',
  results};
const serialized = JSON.stringify(report,null,2);
if (process.argv.includes('--save-report')) {
  const output = path.resolve('output/phase1f');
  fs.mkdirSync(output,{recursive:true});
  fs.writeFileSync(path.join(output,'iztro-comparison.json'),serialized+'\n');
}
console.log(serialized);
if (failed) process.exitCode=1;
