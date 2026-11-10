// Keep the diagram engine optional and resolve it for source and wheel installs.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

try {
  let engine;
  try {
    engine = await import('pele');
  } catch (error) {
    if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error;
    const require = createRequire(resolve(process.cwd(), 'package.json'));
    engine = await import(pathToFileURL(require.resolve('pele')).href);
  }
  const { source, width, face, size } = JSON.parse(readFileSync(0, 'utf8'));
  const { svg } = engine.render(source, {
    fontFamily: face,
    fontFamilyMono: face,
    fontSize: size,
    responsive: false,
    maxWidth: width ?? undefined,
    autoDirection: false,
    images: false,
    links: false,
  });
  process.stdout.write(svg);
} catch (error) {
  const missing = ['ERR_MODULE_NOT_FOUND', 'MODULE_NOT_FOUND'].includes(error.code);
  console.error(missing ? 'Pele is not installed; run npm install pele in the working directory (or npm ci in the repository).' : error.message);
  process.exitCode = 1;
}
