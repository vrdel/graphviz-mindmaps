import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

try {
  let rough;
  try { rough = createRequire(import.meta.url)('roughjs'); }
  catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') throw error;
    rough = createRequire(resolve(process.cwd(), 'package.json'))('roughjs');
  }
  const { shapes, roughness, strokeWidth } = JSON.parse(readFileSync(0, 'utf8'));
  const generator = rough.generator();
  const results = shapes.map((shape, index) => {
    const options = { seed: 17 + index, roughness, strokeWidth: shape.strokeWidth ?? strokeWidth, preserveVertices: true, fill: 'none' };
    const drawable = shape.kind === 'ellipse'
      ? generator.ellipse(...shape.coordinates, options)
      : generator.path(shape.path, options);
    const coordinates = drawable.sets.flatMap(set => set.ops.flatMap(op => {
      const points = [];
      for (let i = 0; i + 1 < op.data.length; i += 2) points.push([op.data[i], op.data[i+1]]);
      return points;
    }));
    return {
      paths: generator.toPaths(drawable).map(path => path.d),
      bounds: coordinates.length ? [
        Math.min(...coordinates.map(p => p[0])), Math.min(...coordinates.map(p => p[1])),
        Math.max(...coordinates.map(p => p[0])), Math.max(...coordinates.map(p => p[1]))
      ] : null
    };
  });
  process.stdout.write(JSON.stringify(results));
} catch (error) {
  console.error(error.code === 'MODULE_NOT_FOUND'
    ? 'Rough.js is not installed; run npm ci in the repository or npm install roughjs@4.6.6 in the working directory.'
    : error.message);
  process.exitCode = 1;
}
