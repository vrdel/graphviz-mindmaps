"""Content-addressed montage planning and lazy execution.

Planning consumes settings and source checksums, never decoded image pixels.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import PIL
from PIL import features

from graphviz_mindmaps.render.image_transform import ParseImageTransformSpec
from graphviz_mindmaps.render.montage_cache import file_digest, recipe_digest


class SourceChanged(ValueError):
    pass


def stat_signature(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def stable_digest(path):
    before = path.stat()
    digest = file_digest(path)
    after = path.stat()
    if stat_signature(before) != stat_signature(after):
        raise SourceChanged(f'source changed while being checked: {path}; retry the montage')
    return digest, after


@dataclass
class Source:
    path: Path
    key: str
    stat: os.stat_result
    kind: str = field(default='source', init=False)


@dataclass
class Operation:
    kind: str
    children: tuple
    parameters: dict
    profile: str
    descriptor: dict = field(init=False)
    key: str = field(init=False)

    def __post_init__(self):
        self.descriptor = {
            'key_schema': 1, 'operation': self.kind, 'profile': self.profile,
            'inputs': [{'kind': 'source' if c.kind == 'source' else 'node', 'key': c.key}
                       for c in self.children],
            'parameters': self.parameters,
        }
        self.key = recipe_digest(self.descriptor)


class MontagePlan:
    def __init__(self, renderer, transforms):
        self.renderer = renderer
        self.transforms = transforms
        self.sources = {}
        self.outputs = []
        self.profiles = {}
        self.started = time.monotonic()
        self.started_ns = time.time_ns()
        self.spec_digest = None
        self.hash_seconds = 0.0

    def profile(self, kind):
        if kind in self.profiles:
            return self.profiles[kind]
        from graphviz_mindmaps.render import image_transform
        from graphviz_mindmaps.tools import montage_title
        # Local implementation files and native library versions are conservative
        # fingerprints, independent from temporary and output pathnames.
        data = {'planner': file_digest(Path(__file__)),
                'renderer': file_digest(Path(sys.modules[self.renderer.__class__.__module__].__file__))}
        if kind in ('compose', 'export'):
            executable = shutil.which('gm')
            if executable is None:
                raise ValueError('GraphicsMagick (gm) is required for montage rendering')
            data['gm'] = file_digest(Path(executable))
            data['gm_version'] = subprocess.run([executable, 'version'], check=True,
                capture_output=True, text=True).stdout
            # Include explicit overrides and installed XML configuration.
            data['environment'] = {k: v for k, v in os.environ.items()
                                   if k.startswith(('MAGICK_', 'OMP_', 'LC_')) or k in ('LANG', 'TZ')}
            roots = [Path('/etc/GraphicsMagick'), Path('/usr/share/GraphicsMagick')]
            roots += list(Path('/etc').glob('GraphicsMagick-*'))
            roots += list(Path('/usr/lib').glob('GraphicsMagick-*'))
            roots += [Path(p) for p in os.environ.get('MAGICK_CONFIGURE_PATH', '').split(os.pathsep) if p]
            configuration = {}
            for root in roots:
                if root.is_dir():
                    for path in sorted(root.rglob('*.xml')):
                        if path.is_file():
                            configuration[str(path)] = file_digest(path)
            data['configuration'] = configuration
        else:
            data['pillow'] = PIL.__version__
            data['pillow_features'] = {f: features.version(f) for f in features.get_supported()}
            if kind == 'transform':
                data['implementation'] = file_digest(Path(image_transform.__file__))
            if kind == 'title':
                data['implementation'] = file_digest(Path(montage_title.__file__))
                data['font'] = file_digest(Path(montage_title.TITLE_FONT))
        self.profiles[kind] = recipe_digest(data)
        return self.profiles[kind]

    def source(self, filename):
        path = (self.renderer.curdir / filename).resolve()
        if path not in self.sources:
            started = time.monotonic()
            digest, stat = stable_digest(path)
            self.hash_seconds += time.monotonic() - started
            self.sources[path] = Source(path, digest, stat)
        return self.sources[path]

    def operation(self, kind, children, **parameters):
        profile_kind = 'compose' if kind in ('group', 'row', 'stack') else kind
        return Operation(kind, tuple(children), parameters, self.profile(profile_kind))

    def compose(self, kind, children, background, tile):
        if not children:
            raise ValueError('montage rows and image groups must not be empty')
        if len(children) == 1:
            return children[0]
        return self.operation(kind, children, background=background, tile=tile, geometry='+0+0', format='PNG')

    def item(self, item, background):
        if isinstance(item, str):
            return self.source(item)
        if isinstance(item, list):
            return self.compose('group', [self.source(str(name)) for name in item], background, '1x')
        if isinstance(item, dict):
            transform = next((key for key in self.transforms if key in item), None)
            if transform:
                path, scale = ParseImageTransformSpec(str(item[transform]))
                if scale is not None and not math.isfinite(scale):
                    raise ValueError('image scale must be a positive finite percentage')
                return self.operation('transform', [self.source(path)],
                                      options=self.transforms[transform], scale=scale)
            return self.spec(item, nested=True, inherited_background=background)[0]
        raise ValueError(f'unsupported row item: {item!r}')

    def spec(self, spec, nested=False, inherited_background=None):
        r = self.renderer
        if self.spec_digest is None:
            self.spec_digest = file_digest(r.spec_path) if r.spec_path.is_file() else recipe_digest(spec)
        output = r.resolve_output(spec, nested)
        title = r.resolve_title(spec, output)
        size = r.resolve_size(spec, nested)
        if title and size not in ('xs', 's', 'm', 'b'):
            raise ValueError(f'unsupported title size: {size}')
        background = r.background_for(spec, title, nested, inherited_background or r.background)
        rows = []
        for row in spec['rows']:
            children = [self.item(item, background) for item in row]
            rows.append(self.compose('row', children, background, f'{len(children)}x'))
        canvas = self.compose('stack', rows, background, '1x')
        if title:
            canvas = self.operation('title', [canvas], title=title, size=size, background=background)
        suffix = output.suffix.lower()
        if not suffix:
            raise ValueError('montage output must have an image extension')
        # Canonicalize equivalent format aliases and scale spellings.
        suffix = {'.jpeg': '.jpg', '.tif': '.tiff'}.get(suffix, suffix)
        scale = float(r.scale) if not nested and r.scale is not None else None
        if scale == 100:
            scale = None
        export = self.operation('export', [canvas], suffix=suffix, scale=scale, jpeg_limit=65500)
        if nested:
            self.outputs.append((export, output))
            r.intermediate_outputs.append(output)
        return export, output


class MontageExecutor:
    def __init__(self, renderer, plan, cache):
        self.renderer = renderer
        self.plan = plan
        self.cache = cache
        self.results = {}
        self.source_snapshots = {}
        self.stats = {'rendered': 0, 'hits': 0, 'memo_hits': 0, 'hash_seconds': plan.hash_seconds,
                      'operations': {}, 'render_seconds': 0.0}

    def explain(self, node, state):
        if self.renderer.cache_explain:
            print(f'montage cache: {node.kind} {node.key[:12]} {state}', file=sys.stderr)

    def snapshot(self, source):
        # Distinct files with the same bytes can share a read-only snapshot.
        if source.key not in self.source_snapshots:
            destination = self.renderer.temp_root / f'source-{source.key}{source.path.suffix}'
            before = source.path.stat()
            shutil.copyfile(source.path, destination)
            after = source.path.stat()
            if stat_signature(before) != stat_signature(after) or file_digest(destination) != source.key:
                destination.unlink(missing_ok=True)
                raise SourceChanged(f'source changed before rendering: {source.path}; retry the montage')
            self.source_snapshots[source.key] = destination
        return self.source_snapshots[source.key]

    def evaluate(self, node):
        if node.kind == 'source':
            return self.snapshot(node)
        if node.key in self.results:
            self.stats['memo_hits'] += 1
            self.explain(node, 'memory hit')
            return self.results[node.key]
        hit = self.cache.lookup(node.key)
        if hit is not None:
            self.stats['hits'] += 1
            self.explain(node, 'hit')
            self.results[node.key] = hit
            return hit
        children = [self.evaluate(child) for child in node.children]
        with self.cache.recipe_lock(node.key):
            hit = self.cache.lookup(node.key)
            if hit is not None:
                self.stats['hits'] += 1
                self.explain(node, 'hit after lock')
                self.results[node.key] = hit
                return hit
            self.explain(node, 'miss; rendering')
            started = time.monotonic()
            suffix = node.parameters.get('suffix', '.png')
            destination = self.renderer.temp_root / f'rendered-{node.key}{suffix}'
            self.renderer.render_operation(node, children, destination)
            elapsed = time.monotonic() - started
            self.stats['rendered'] += 1
            self.stats['render_seconds'] += elapsed
            counts = self.stats['operations']
            counts[node.kind] = counts.get(node.kind, 0) + 1
            self.cache.store(node, destination, elapsed * 1000)
            self.results[node.key] = destination
            return destination

    def publish(self, source, destination):
        # Always copy: a writable project output must never share a cache inode.
        import tempfile
        destination = Path(destination)
        fd, name = tempfile.mkstemp(prefix='.' + destination.stem + '-', suffix=destination.suffix,
                                    dir=destination.parent)
        os.close(fd)
        pending = Path(name)
        try:
            shutil.copyfile(source, pending)
            pending.replace(destination)
        finally:
            pending.unlink(missing_ok=True)

    def run(self, root, destination):
        if self.renderer.cache_explain:
            previous = self.cache.previous_sources(self.renderer.spec_path, destination)
            for source in self.plan.sources.values():
                state = 'first observation' if previous is None else (
                    'unchanged' if previous.get(str(source.path)) == source.key else 'content changed or newly referenced')
                print(f'montage cache: source {source.path}: {state}', file=sys.stderr)
        self.cache.observe_sources(self.plan.sources.values())
        result = self.evaluate(root)
        # Preserve legacy nested output side effects even on a root hit. When
        # cleanup is enabled, a warm root needs no intermediate publication.
        for node, path in self.plan.outputs:
            if self.renderer.no_clean or node.key in self.results:
                self.publish(self.evaluate(node), path)
        self.publish(result, destination)
        self.stats['total_seconds'] = time.monotonic() - self.plan.started
        self.cache.record_run(self.renderer.spec_path, self.plan.spec_digest, destination, root.key,
                              self.plan.sources.values(), self.stats, self.plan.started_ns)
        if self.renderer.cache_stats:
            print('montage cache: ' + str(self.stats), file=sys.stderr)
        return destination
