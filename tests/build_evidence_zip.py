"""E3-12 evidence ZIP packaging: complete and portable variants.

Complete: everything needed to reproduce (code, tests, reports, contracts,
manifests, run evidence), referencing the already-published frozen input
ZIPs.  Portable: evidence only (no generator-compat dependencies beyond
what evidence cites).  Manifests with SHA-256 are generated inside each
archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'

COMPLETE_INCLUDE = [
    'contracts/', 'reports/', 'implementations/', 'oracles/', 'tests/',
    'models/', '.github/workflows/', 'runs/actions/', 'runs/domain_audit/',
    'runs/e3_04/', 'runs/e3_10/', 'baseline_readonly/inputs/',
]
PORTABLE_INCLUDE = [
    'contracts/', 'reports/', 'runs/actions/', 'runs/domain_audit/',
    'runs/e3_04/', 'runs/e3_10/', 'tests/accept_e3.py',
    'tests/verify_authority_manifest.py', 'oracles/independent/tina_raw_replay.py',
    'implementations/subject/r604_replay.py', 'implementations/subject/reachability.py',
]


def _iter_files(prefixes):
    for prefix in prefixes:
        base = ROOT / prefix
        if base.is_file():
            yield base
        elif base.is_dir():
            for path in sorted(base.rglob('*')):
                if path.is_file():
                    yield path


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build(variant, prefixes):
    OUT.mkdir(exist_ok=True)
    seen = set()
    files = []
    for path in _iter_files(prefixes):
        rel = path.relative_to(ROOT).as_posix()
        if rel in seen or '.DS_Store' in rel:
            continue
        seen.add(rel)
        files.append(path)
    zip_path = OUT / f'R6_E3_{variant}_evidence.zip'
    manifest = {}
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            rel = path.relative_to(ROOT).as_posix()
            archive.write(path, rel)
            manifest[rel] = _sha256(path)
        archive.writestr('MANIFEST.json', json.dumps({
            'variant': variant, 'files': len(files), 'sha256_by_path': manifest,
            'frozen_inputs': {
                'R6_E2_complete_workspace.zip': 'bb72a68af34c852213e96588b4e29ecc602b0de428d406bbd30e8300a8656715',
                'tex': 'a4196145c95812ff19376a5985b6a6f2cf469d432c80836071cad1c8ac174c5a'},
            'note': 'RAW_NOT_SHIPPED: pyscrew raw JSON available at release pyscrew-raw-v1 '
                    '(sha256 de161758a6918bc70e3b24a0327b5d719b882395df81b5d481071b5abf22d545); '
                    'FULL_RAW_REPRODUCIBLE=false for this archive alone.'}, indent=2))
    outer = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (OUT / f'R6_E3_{variant}_evidence.sha256.txt').write_text(f'{outer}  {zip_path.name}\n')
    return {'variant': variant, 'files': len(files), 'zip': zip_path.name,
            'zip_sha256': outer, 'bytes': zip_path.stat().st_size}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['complete', 'portable'], default='complete')
    args = parser.parse_args()
    prefixes = COMPLETE_INCLUDE if args.variant == 'complete' else PORTABLE_INCLUDE
    print(json.dumps(build(args.variant, prefixes), indent=2))
