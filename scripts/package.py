"""Build a deterministic source ZIP, excluding caches and unrelated local files."""
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAMES = ['.gitignore', 'README.md', 'SKILL.md', 'SECURITY.md', 'CONTRIBUTING.md', 'LICENSE', 'RELEASE.md',
         'frameflow/__init__.py', 'frameflow/__main__.py', 'tests/test_workflow.py',
         'examples/demo/manifest.json', 'examples/demo/assets/story.txt',
         'examples/review/manifest.json', 'examples/review/card.svg',
         'templates/workflow.md', 'docs/architecture.md', 'docs/adapters.md', 'scripts/package.py']

def main():
    destination = pathlib.Path(sys.argv[1]) if len(sys.argv) == 2 else ROOT.parent / 'frameflow-skill.zip'
    records = []
    data = {}
    for name in sorted(NAMES):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit('Missing or unsafe source file: ' + name)
        content = path.read_bytes()
        data[name] = content
        records.append({'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    data['MANIFEST.json'] = (json.dumps({'format': 1, 'status': 'v0.1-source-public-mit',
        'files': records, 'note': 'Manifest excludes itself. Integrity inventory is not a quality or security certification.'}, indent=2) + '\n').encode()
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(data.items()):
            info = zipfile.ZipInfo('frameflow-skill/' + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise SystemExit('ZIP verification failed')
        manifest = json.loads(archive.read('frameflow-skill/MANIFEST.json'))
        for row in manifest['files']:
            assert hashlib.sha256(archive.read('frameflow-skill/' + row['path'])).hexdigest() == row['sha256']
    print(json.dumps({'zip': str(destination), 'bytes': destination.stat().st_size,
                      'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'files': len(data)}))

if __name__ == '__main__':
    main()
