#!/usr/bin/python3
"""Explicit immutable resource recipes; never intercept VSEARCH analysis."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

SCHEMA = 'taffish.vsearch.recipe.v1'
RESERVED = {'manifest.json', 'READY', 'recipe.json', 'RESOURCE_LICENSE.txt', 'reference.udb'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode()


def safe_name(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value)
            and '..' not in value, 'unsafe resource ID, version or filename')
    return value


def regular(path):
    require(not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode), 'not a regular non-symlink file: ' + str(path))


def directory(path, writable=False):
    require(path.is_absolute() and path.is_dir() and not path.is_symlink() and path.resolve() == path,
            'root must be an existing absolute physical directory: ' + str(path))
    require(not path.stat().st_mode & 0o022, 'root must not be group/world writable')
    if writable:
        require(path.stat().st_uid == os.geteuid() and os.access(path, os.W_OK),
                'installer must own and be able to write root')


def recipe_load(path):
    regular(path)
    recipe = json.loads(path.read_text())
    require(isinstance(recipe, dict), 'recipe must be a JSON object')
    require(recipe.get('schema') == SCHEMA, 'unsupported recipe schema')
    require(set(recipe).issubset({'schema', 'id', 'version', 'source', 'license', 'files', 'makeudb'}), 'unknown recipe field')
    safe_name(recipe['id']); safe_name(recipe['version'])
    safe_name(recipe['id'] + '--' + recipe['version'])
    require(recipe['id'].lower() != 'all', 'select one fixed resource, not all')
    for field in ('source', 'license'):
        require(isinstance(recipe.get(field), str) and recipe[field].strip()
                and len(recipe[field]) <= 1024**2, 'source and license/permission notice required')
    require(isinstance(recipe.get('files'), list) and recipe['files'], 'explicit files required')
    outputs = set()
    for item in recipe['files']:
        require(isinstance(item, dict), 'recipe file must be a JSON object')
        require(set(item).issubset({'name', 'url', 'sha256', 'size'}), 'unknown recipe file field')
        filename = safe_name(item['name'])
        require(filename not in outputs | RESERVED, 'duplicate/reserved output filename')
        url = urlsplit(item['url'])
        require(url.scheme == 'https' and url.hostname and not url.username and not url.password and not url.fragment,
                'public HTTPS URL without credentials or fragments required')
        require(isinstance(item.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', item['sha256']), 'SHA256 required')
        require(type(item.get('size')) is int and item['size'] > 0, 'positive exact file size required')
        outputs.add(filename)
    if 'makeudb' in recipe:
        build = recipe['makeudb']
        require(isinstance(build, dict) and set(build) == {'input', 'dbmask'}, 'makeudb requires input and explicit dbmask')
        require(build['input'] in outputs, 'makeudb input missing')
        require(build['dbmask'] in ('none', 'soft', 'dust'), 'invalid explicit dbmask')
    return recipe


def verify(member, unit, recipe_hash=None):
    directory(member)
    require(stat.S_IMODE(member.stat().st_mode) == 0o755, 'member directory permission drift')
    for name in ('manifest.json', 'READY'):
        regular(member / name)
        require(stat.S_IMODE((member / name).stat().st_mode) == 0o644, 'manifest/READY permission drift')
    require((member / 'READY').read_text().strip() == sha(member / 'manifest.json'), 'READY/manifest mismatch')
    record = json.loads((member / 'manifest.json').read_text())
    require(isinstance(record, dict), 'manifest must be a JSON object')
    require(record.get('schema') == 'taffish.vsearch.db.v1' and record.get('resource') == unit, 'member schema/ID mismatch')
    require(recipe_hash is None or record.get('recipe_sha256') == recipe_hash, 'existing ID has a different recipe; use a new version')
    expected = {'manifest.json', 'READY'}
    require(isinstance(record.get('files'), list) and record['files'], 'empty inventory')
    for item in record['files']:
        require(isinstance(item, dict), 'inventory entry must be a JSON object')
        name = safe_name(item['name'])
        require(name not in expected, 'duplicate inventory entry')
        path = member / name
        regular(path)
        require(stat.S_IMODE(path.stat().st_mode) == 0o644, 'member file permission drift: ' + name)
        require(path.stat().st_size == item['size'] and sha(path) == item['sha256'], 'checksum/size mismatch: ' + name)
        expected.add(name)
    require({'recipe.json', 'RESOURCE_LICENSE.txt'}.issubset(expected), 'recipe/license inventory missing')
    require({p.name for p in member.iterdir()} == expected, 'unexpected/missing member files')
    recipe = recipe_load(member / 'recipe.json')
    require(hashlib.sha256(canonical(recipe)).hexdigest() == record['recipe_sha256'], 'recipe identity mismatch')
    require(recipe['id'] + '--' + recipe['version'] == unit, 'recipe/member ID mismatch')
    return record


def command(stage, argv, cwd=None):
    # A disk-backed bounded diagnostic tail avoids storing large progress logs in RAM.
    with tempfile.TemporaryFile() as log:
        result = subprocess.run(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            log.seek(max(0, log.tell() - 32768))
            print(f'vsearch-db: stage={stage} exit={result.returncode}', file=sys.stderr)
            print('\n'.join(log.read().decode(errors='replace').splitlines()[-100:]), file=sys.stderr)
            raise SystemExit(result.returncode if result.returncode > 0 else 128 - result.returncode)


def obtain(item, cache, source_dir):
    blob = cache / item['sha256']
    partial = cache / (item['sha256'] + '.part')
    for path in (blob, partial):
        if os.path.lexists(path):
            regular(path)
    if blob.exists():
        require(blob.stat().st_size == item['size'] and sha(blob) == item['sha256'], 'corrupt cache; inspect exact file: ' + str(blob))
        return blob
    if source_dir is not None:
        source = source_dir / item['name']
        regular(source)
        require(not partial.exists(), 'partial cache exists; inspect exact file before local import: ' + str(partial))
        with source.open('rb') as inp, partial.open('xb') as out:
            shutil.copyfileobj(inp, out, 8 * 1024**2)
    else:
        require(not partial.exists() or partial.stat().st_size <= item['size'], 'oversize partial cache')
        if not partial.exists() or partial.stat().st_size < item['size']:
            command('download', ['curl', '--fail', '--location', '--proto', '=https', '--proto-redir', '=https',
                                '--connect-timeout', '30', '--speed-limit', '1024', '--speed-time', '120',
                                '--retry', '3', '--retry-delay', '3', '--continue-at', '-',
                                '--max-filesize', str(item['size']), '--output', str(partial), item['url']])
    regular(partial)
    require(partial.stat().st_size == item['size'] and sha(partial) == item['sha256'],
            'download checksum/size mismatch; private partial retained: ' + str(partial))
    partial.chmod(0o600)
    partial.rename(blob)
    return blob


def install(root, recipe, source_dir, reserve, threads):
    directory(root, writable=True)
    unit = recipe['id'] + '--' + recipe['version']
    identity = hashlib.sha256(canonical(recipe)).hexdigest()
    destination = root / unit
    if os.path.lexists(destination):
        verify(destination, unit, identity)
        print('already complete: ' + str(destination))
        return
    lock = root / '.install.lock'
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        raise ValueError('install lock exists; do not remove an active lock: ' + str(lock))
    stage = None
    try:
        require(not os.path.lexists(destination), 'destination appeared; verify before retry')
        cache = root / '.downloads'
        if not cache.exists():
            cache.mkdir(mode=0o700)
        directory(cache, writable=True)
        require(stat.S_IMODE(cache.stat().st_mode) == 0o700, 'cache must have mode 0700')
        pending = {}
        for item in recipe['files']:
            if not (cache / item['sha256']).exists():
                pending[item['sha256']] = item['size']
        # Downloads are hardlinked into the member; reserve covers UDB workspace.
        required = sum(pending.values()) + reserve
        require(shutil.disk_usage(root).free >= required, f'insufficient space: need {required} free bytes')
        blobs = [(item, obtain(item, cache, source_dir)) for item in recipe['files']]
        stage = Path(tempfile.mkdtemp(prefix='.' + unit + '.stage-', dir=root))
        for item, blob in blobs:
            os.link(blob, stage / item['name'])
        if 'makeudb' in recipe:
            build = recipe['makeudb']
            command('makeudb', ['vsearch', '--makeudb_usearch', build['input'], '--output', 'reference.udb',
                               '--dbmask', build['dbmask'], '--threads', str(threads)], stage)
            require((stage / 'reference.udb').stat().st_size > 0, 'makeudb produced no database')
            command('udbinfo', ['vsearch', '--udbinfo', 'reference.udb'], stage)
        (stage / 'recipe.json').write_bytes(canonical(recipe) + b'\n')
        (stage / 'RESOURCE_LICENSE.txt').write_text(recipe['source'] + '\n\n' + recipe['license'] + '\n')
        inventory = [dict(name=p.name, size=p.stat().st_size, sha256=sha(p)) for p in sorted(stage.iterdir())]
        record = dict(schema='taffish.vsearch.db.v1', app_release='2.32.0-r1', resource=unit,
                      recipe_sha256=identity, files=inventory)
        (stage / 'manifest.json').write_bytes(canonical(record) + b'\n')
        (stage / 'READY').write_text(sha(stage / 'manifest.json') + '\n')
        for path in stage.iterdir():
            path.chmod(0o644)
        stage.chmod(0o755)
        verify(stage, unit, identity)
        command('promote', ['mv', '-T', '-n', '--', str(stage), str(destination)])
        require(not stage.exists(), 'destination appeared; refusing overwrite')
        stage = None
        # Only this recipe's verified blobs. Data was hardlinked into the member.
        for blob in {blob for _, blob in blobs}:
            blob.unlink()
        print('installed: ' + str(destination))
    finally:
        if stage is not None:
            shutil.rmtree(stage)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description='Prepare one fixed database/taxonomy recipe. Analysis never downloads.',
        epilog='Use an existing installer-owned private/site root. Members: 0755/0644. No --force; '
        'quarantine exact damaged members only after confirming no installer is running. '
        'Repeat network installation to resume. Always use actual writable/read-only backend binds.')
    parser.add_argument('--version', action='version', version='vsearch-db 2.32.0-r1')
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('install')
    prepare.add_argument('--recipe', required=True, type=Path)
    prepare.add_argument('--db-root', required=True, type=Path)
    prepare.add_argument('--source-dir', type=Path, help='already acquired recipe members, no network')
    prepare.add_argument('--rights-reviewed', action='store_true', required=True,
                         help='confirm acquisition and intended sharing rights for every recipe member')
    prepare.add_argument('--dry-run', action='store_true')
    prepare.add_argument('--reserve-gb', type=float, default=10, help='extra extraction/build reserve, default 10 GiB')
    prepare.add_argument('--threads', type=int, default=1)
    check = sub.add_parser('verify')
    check.add_argument('--db-root', required=True, type=Path)
    check.add_argument('--id', required=True, help='exact prepared member ID: recipe-id--version')
    args = parser.parse_args()
    require(args.db_root.is_absolute(), '--db-root must be absolute')
    if args.command == 'verify':
        directory(args.db_root)
        print(json.dumps(verify(args.db_root / safe_name(args.id), args.id), indent=2))
        return
    require(0 <= args.reserve_gb < 1000000 and args.threads > 0, 'invalid reserve/threads')
    recipe = recipe_load(args.recipe)
    if args.dry_run:
        print(json.dumps(dict(resource=recipe['id'] + '--' + recipe['version'], recipe=recipe,
            recipe_sha256=hashlib.sha256(canonical(recipe)).hexdigest(),
            download_bytes=sum(f['size'] for f in recipe['files']), reserve_bytes=int(args.reserve_gb * 1024**3),
            destination=str(args.db_root / (recipe['id'] + '--' + recipe['version'])),
            network=args.source_dir is None), indent=2))
        return
    install(args.db_root, recipe, args.source_dir, int(args.reserve_gb * 1024**3), args.threads)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('vsearch-db: stage=prepare-or-verify exit=1: ' + str(error), file=sys.stderr)
        sys.exit(1)
