#!/usr/bin/python3
"""合成资源安装与完整性测试；不下载生产数据库。"""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile


def run(stage, argv, bad=False, marker=None):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
    if (result.returncode == 0) == bad or (marker and marker not in result.stdout):
        print(f'resource-smoke stage={stage} exit={result.returncode}\n{result.stdout[-32768:]}', file=sys.stderr)
        raise SystemExit(result.returncode or 1)
    return result.stdout


def fixture(directory):
    directory.mkdir()
    rng = random.Random(232)
    seq = ''.join(rng.choice('ACGT') for _ in range(160))
    data = f'>reference;tax=d:Bacteria,g:Example;\n{seq}\n'.encode()
    (directory / 'reference.fa').write_bytes(data)
    (directory / 'query.fa').write_text(f'>query\n{seq}\n')
    recipe = dict(schema='taffish.vsearch.recipe.v1', id='synthetic', version='1',
        source='Wholly synthetic technical fixture. No production/scientific claim.',
        license='CC0-1.0; generated test sequence, no third-party data.',
        files=[dict(name='reference.fa', url='https://example.invalid/synthetic-1.fa',
                    sha256=hashlib.sha256(data).hexdigest(), size=len(data))],
        makeudb=dict(input='reference.fa', dbmask='none'))
    (directory / 'recipe.json').write_text(json.dumps(recipe))
    return recipe


def resources():
    source = Path.cwd() / 'source'
    recipe = fixture(source)
    root = Path.cwd() / 'resources'; root.mkdir(mode=0o755)
    install = ['vsearch-db', 'install', '--recipe', str(source / 'recipe.json'),
        '--db-root', str(root), '--source-dir', str(source), '--reserve-gb', '0', '--rights-reviewed']
    run('dry-run', install + ['--dry-run'], marker='synthetic--1')
    assert not list(root.iterdir())
    run('install', install, marker='installed:')
    member = root / 'synthetic--1'
    ready = (member / 'READY').read_bytes()
    run('idempotent', install, marker='already complete:')
    assert (member / 'READY').read_bytes() == ready
    verify = ['vsearch-db', 'verify', '--db-root', str(root), '--id', 'synthetic--1']
    record = json.loads(run('verify', verify))
    assert len(record['files']) == 4 and not list(root.glob('.*.stage-*'))
    run('use-db', ['vsearch', '--usearch_global', str(source / 'query.fa'), '--db',
        str(member / 'reference.udb'), '--id', '1', '--blast6out', 'hits.tsv', '--threads', '1'])
    assert Path('hits.tsv').read_text().startswith('query\treference;')
    for name, value in [('reference.fa', b'broken'), ('extra', b'x')]:
        path = member / name
        original = path.read_bytes() if path.exists() else None
        path.write_bytes(value)
        run('corruption-' + name, verify, bad=True)
        run('no-overwrite-' + name, install, bad=True)
        if original is None: path.unlink()
        else: path.write_bytes(original)
    (member / 'reference.fa').chmod(0o666)
    run('permission', verify, bad=True, marker='permission drift')
    (member / 'reference.fa').chmod(0o644)
    run('restore', verify)
    bad = copy.deepcopy(recipe); bad['id'] = 'bad'; bad['files'][0]['sha256'] = '0' * 64
    (source / 'bad.json').write_text(json.dumps(bad))
    wrong = install.copy(); wrong[wrong.index('--recipe')+1] = str(source / 'bad.json')
    run('checksum', wrong, bad=True, marker='checksum/size mismatch')
    assert not (root / 'bad--1').exists() and not (root / '.install.lock').exists()
    (root / '.install.lock').mkdir()
    run('lock', wrong, bad=True, marker='install lock exists')
    (root / '.install.lock').rmdir()
    for key, value in [('name', '../escape'), ('url', 'http://example.invalid/x'), ('size', -1)]:
        modified = copy.deepcopy(recipe); modified['files'][0][key] = value
        (source / 'bad.json').write_text(json.dumps(modified))
        run('recipe-' + key, wrong + ['--dry-run'], bad=True)
    second = copy.deepcopy(recipe); second['id'] = 'second'; second.pop('makeudb')
    (source / 'bad.json').write_text(json.dumps(second))
    run('second-selected-member', wrong, marker='installed:')
    assert (root / 'second--1/reference.fa').is_file()
    assert not (root / 'second--1/reference.udb').exists()
    run('missing-selected-member', ['vsearch-db', 'verify', '--db-root', str(root), '--id', 'absent--1'], bad=True)
    link = root / 'link--1'; link.symlink_to(member, target_is_directory=True)
    run('member-symlink', ['vsearch-db', 'verify', '--db-root', str(root), '--id', 'link--1'], bad=True)
    link.unlink()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'fixture':
        fixture(Path(sys.argv[2]))
    else:
        with tempfile.TemporaryDirectory(prefix='taf-vsearch-resource-') as scratch:
            os.chdir(scratch)
            resources()
        print('PASS vsearch resources')
