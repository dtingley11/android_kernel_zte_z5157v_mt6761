import { build, version } from 'esbuild';
import fs from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(process.argv[2]);
const assets = path.join(root, 'assets');
const mainName = 'index-BS9hEn4H.js';
let source = await fs.readFile(path.join(assets, mainName), 'utf8');
const oldVersionQuery = "be=await e(`grep version= ${K}/module.prop | cut -d '=' -f 2`)";
if (!source.includes(oldVersionQuery)) throw new Error('Kernel version query changed');
source = source.replace(oldVersionQuery, 'be=await e(`${k} show version`)');
const start = source.indexOf('(function(){');
const imports = source.slice(0, start);
if (start < 0 || !/^(?:import[^;]+;)+$/.test(imports)) {
  throw new Error('The pinned R28 WebUI entry point changed');
}
// Keep all original bindings together while replacing unsupported top-level await.
const contents = imports + '(async function(){"use strict";\n' + source.slice(start) +
  '\n})().catch(function(error){console.error("SUSFS WebUI startup failed",error);});';
await build({
  stdin: { contents, resolveDir: assets, sourcefile: mainName },
  bundle: true,
  format: 'iife',
  platform: 'browser',
  target: 'chrome74',
  outfile: path.join(assets, 'susfs-compat.js'),
  minify: true,
  legalComments: 'eof',
});
const oldScripts = ['fade-4ApaDT9x.js', 'i18n-CuIujUHf.js', mainName];
for (const file of await fs.readdir(root)) {
  if (!file.endsWith('.html')) continue;
  const target = path.join(root, file);
  let html = await fs.readFile(target, 'utf8');
  if (!html.includes(mainName)) continue;
  for (const name of oldScripts) {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const tag = new RegExp('<script[^>]*src=["\']/assets/' + escaped + '["\'][^>]*><\\/script>');
    if (!tag.test(html)) throw new Error('Missing WebUI script ' + name + ' in ' + file);
    html = html.replace(tag, name === mainName ? '<script defer src="/assets/susfs-compat.js"></script>' : '');
  }
  await fs.writeFile(target, html);
}
await fs.writeFile(path.join(root, 'COMPAT-BUILD.json'), JSON.stringify({
  esbuild: version,
  target: 'chrome74',
  original_entry: mainName,
  output: 'assets/susfs-compat.js',
}, null, 2) + '\n');
