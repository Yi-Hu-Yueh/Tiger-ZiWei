/* Development-only setup. Source archive must first be downloaded/extracted to
 * tmp/phase1f-iztro/source from the exact codeload commit URL in README.
 * Installs only yarn.lock-pinned packages into that ignored checkout, verifies
 * tarball integrity, runs no lifecycle scripts, and transpiles the FULL engine.
 * No package or Node dependency is added to the Python application.
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const assert = require('node:assert/strict');
const revision = '2c7ef9be669df7b19d1799f4dce335fed3794f78';
const base = path.resolve('tmp/phase1f-iztro');
const root = path.join(base, 'source', `iztro-${revision}`);
const sha256 = data => crypto.createHash('sha256').update(data).digest('hex');
assert.equal(sha256(fs.readFileSync(path.join(base, 'source.zip'))),
  '794938fbc17331b3cbf66040c39ceb1a82aa21ad31cf7f35f3324e685379da68');
const lock = fs.readFileSync(path.join(root, 'yarn.lock'), 'utf8');
const packages = [
  ['dayjs@^1.11.10', 'dayjs'], ['i18next@^23.5.1', 'i18next'],
  ['lunar-lite@^0.2.8', 'lunar-lite'], ['lunar-typescript@^1.7.8', 'lunar-typescript'],
  ['lunar-typescript@^1.8.6', 'lunar-lite/node_modules/lunar-typescript'],
  ['"@babel/runtime@^7.22.5"', '@babel/runtime'],
  ['regenerator-runtime@^0.14.0', 'regenerator-runtime'], ['typescript@^5.2.2', 'typescript'],
];
(async () => {
  const versions = {};
  for (const [key, destination] of packages) {
    const section = lock.split(/\r?\n\r?\n/).find(s => s.startsWith(key));
    assert(section, `missing lock entry ${key}`);
    const version = section.match(/\n  version "([^"]+)"/)[1];
    const url = section.match(/\n  resolved "([^"#]+)/)[1];
    const integrity = section.match(/\n  integrity (\S+)/)[1];
    const response = await fetch(url);
    assert(response.ok, `download ${url}: ${response.status}`);
    const data = Buffer.from(await response.arrayBuffer());
    const [algorithm, expected] = integrity.split('-');
    assert.equal(crypto.createHash(algorithm).update(data).digest('base64'), expected);
    const archive = path.join(base, destination.replaceAll('/', '_') + '.tgz');
    fs.writeFileSync(archive, data); // Verified dependency archive, not project source.
    const target = path.join(root, 'node_modules', destination);
    fs.mkdirSync(target, { recursive: true });
    execFileSync('tar', ['-xzf', archive, '-C', target, '--strip-components=1']);
    versions[destination] = version;
  }
  const ts = require(path.join(root, 'node_modules/typescript'));
  const hashes = {};
  function build(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (entry.name === '__tests__') continue;
      const source = path.join(directory, entry.name);
      if (entry.isDirectory()) { build(source); continue; }
      const relative = path.relative(path.join(root, 'src'), source);
      hashes[relative.replaceAll('\\', '/')] = sha256(fs.readFileSync(source));
      const target = path.join(root, 'lib', relative.replace(/\.ts$/, '.js'));
      fs.mkdirSync(path.dirname(target), { recursive: true });
      if (entry.name.endsWith('.ts')) {
        const result = ts.transpileModule(fs.readFileSync(source, 'utf8'), {
          compilerOptions: { target: ts.ScriptTarget.ES5, module: ts.ModuleKind.CommonJS, esModuleInterop: true },
          fileName: source,
        });
        fs.writeFileSync(target, result.outputText); // Compiler output only.
      } else fs.copyFileSync(source, target);
    }
  }
  build(path.join(root, 'src'));
  const receipt = { revision, source_archive_sha256: sha256(fs.readFileSync(path.join(base, 'source.zip'))),
    versions, source_hashes: hashes };
  fs.writeFileSync(path.join(base, 'build-receipt.json'), JSON.stringify(receipt, null, 2));
  console.log(JSON.stringify({ revision, versions, compiled_source_files: Object.keys(hashes).length }));
})().catch(error => { console.error(error); process.exitCode = 1; });
