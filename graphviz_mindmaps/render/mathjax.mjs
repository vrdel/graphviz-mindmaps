// Typeset locally with self-contained SVG paths; no browser is needed.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

let MathJax;
try {
  let entry;
  try { entry = createRequire(import.meta.url).resolve('@mathjax/src'); }
  catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') throw error;
    entry = createRequire(resolve(process.cwd(), 'package.json')).resolve('@mathjax/src');
  }
  const engine = (await import(pathToFileURL(entry).href)).default;
  MathJax = await engine.init({
    loader: { load: ['input/tex-base', '[tex]/ams', '[tex]/newcommand', 'output/svg', 'adaptors/liteDOM'] },
    startup: { typeset: false },
    tex: {
      packages: ['base', 'ams', 'newcommand'],
      formatError: (_jax, error) => { throw new Error(error.message); },
    },
    svg: { fontCache: 'none', linebreaks: { inline: false } },
  });
  const { source, display, size, color } = JSON.parse(readFileSync(0, 'utf8'));
  const adaptor = MathJax.startup.adaptor;
  const container = await MathJax.tex2svgPromise(source, { display, em: size, ex: size / 2, containerWidth: 100000 });
  const svg = adaptor.firstChild(container);
  const viewBox = adaptor.getAttribute(svg, 'viewBox').split(/\s+/).map(Number);
  // MathJax uses 1000 units per em. Graphviz treats raster images as 96 dpi,
  // while node text sizes are points (72/inch), so convert points to pixels.
  adaptor.setAttribute(svg, 'width', String(Math.max(1, viewBox[2] * size * (96 / 72) / 1000)));
  adaptor.setAttribute(svg, 'height', String(Math.max(1, viewBox[3] * size * (96 / 72) / 1000)));
  adaptor.setAttribute(svg, 'color', color);
  adaptor.setAttribute(svg, 'style', `color:${color}`);
  process.stdout.write(adaptor.outerHTML(svg));
} catch (error) {
  console.error(['ERR_MODULE_NOT_FOUND', 'MODULE_NOT_FOUND'].includes(error.code)
    ? 'MathJax is not installed; run npm ci in the repository or npm install @mathjax/src@4.1.3 in the working directory.'
    : error.message);
  process.exitCode = 1;
} finally {
  MathJax?.done();
}
