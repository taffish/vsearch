#!/usr/bin/python3
"""独立离线 tiny 功能验证；不代表生产科学验收。"""
from collections import Counter
import bz2
import gzip
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile


def run(*args, bad=False):
    result = subprocess.run(['vsearch', *args], capture_output=True, text=True)
    if (result.returncode == 0) == bad:
        print(f'smoke-stage={args[0]} exit={result.returncode}', file=sys.stderr)
        print((result.stdout + result.stderr)[-32768:], file=sys.stderr)
        raise SystemExit(result.returncode or 1)
    return result.stdout + result.stderr


def fasta(path):
    records = []
    for line in Path(path).read_text().splitlines():
        if line.startswith('>'):
            records.append([line[1:], ''])
        else:
            records[-1][1] += line
    return records


def fq(path, rows):
    Path(path).write_text(''.join(f'@{name}\n{seq}\n+\n{qual}\n' for name, seq, qual in rows))


def fastq(path):
    lines = Path(path).read_text().splitlines()
    assert len(lines) % 4 == 0
    return [(lines[i][1:], lines[i+1], lines[i+3]) for i in range(0, len(lines), 4)]


def sequence(seed, length=160):
    rng = random.Random(seed)
    return ''.join(rng.choice('ACGT') for _ in range(length))


def seed():
    seq = sequence(232)
    altered = seq[:70] + ('C' if seq[70] != 'C' else 'A') + seq[71:]
    Path('reads.fa').write_text(f'>read1\n{seq}\n>read2\n{seq}\n>read3\n{altered}\n')
    Path('query.fa').write_text(f'>query1\n{seq}\n')
    Path('db.fa').write_text(f'>db1;tax=d:Bacteria,p:Test,g:Example,s:Example_species;\n{seq}\n>db2;tax=d:Bacteria,p:Other;\n{sequence(233)}\n')
    return seq


def identity():
    output = run('--version')
    assert re.search(r'^vsearch v2\.32\.0_(?:linux_x86_64|linux_aarch64),', output, re.M), output
    help_text = run('--help')
    for option in ('--usearch_global', '--fastq_mergepairs', '--uchime_denovo', '--sintax', '--scramble', '--fastx_syncpairs'):
        assert option in help_text, option
    result = subprocess.run(['ldd', '/opt/vsearch/bin/vsearch'], capture_output=True, text=True)
    assert result.returncode == 0 and 'not found' not in result.stdout + result.stderr, result
    for name in ('man/man1/vsearch.1', 'man/man1/vsearch-scramble.1', 'completion/vsearch'):
        assert (Path('/opt/vsearch/share') / name).is_file(), name
    print(output.strip())


def core():
    seq = seed()
    run('--fastx_uniques', 'reads.fa', '--fastaout', 'unique.fa', '--sizeout', '--threads', '1')
    assert sorted(re.findall(r';size=(\d+)', Path('unique.fa').read_text())) == ['1', '2']
    run('--usearch_global', 'query.fa', '--db', 'db.fa', '--id', '0.90', '--blast6out', 'hits.tsv', '--threads', '1', '--dbmask', 'none')
    assert Path('hits.tsv').read_text().startswith('query1\tdb1;')
    for ext, encode, command in [('gz', gzip.compress, '--sortbylength'), ('bz2', bz2.compress, '--fastx_revcomp')]:
        Path('reads.' + ext).write_bytes(encode(Path('reads.fa').read_bytes()))
        run(command, 'reads.' + ext, '--output' if ext == 'gz' else '--fastaout', ext + '.fa', '--threads', '1')
        records = fasta(ext + '.fa')
        assert len(records) == 3
        assert records[0][1] == (seq if ext == 'gz' else seq.translate(str.maketrans('ACGT', 'TGCA'))[::-1])
    run('--cluster_fast', 'reads.fa', '--id', '0.97', '--centroids', 'centroids.fa', '--uc', 'clusters.uc', '--threads', '1')
    assert len(fasta('centroids.fa')) == 1 and Path('clusters.uc').stat().st_size > 0
    run('--uchime_denovo', 'unique.fa', '--nonchimeras', 'clean.fa', '--chimeras', 'chimera.fa', '--threads', '1')
    assert len(fasta('clean.fa')) == 2


def fastq_paths():
    seq = seed()
    fq('reads.fq', [('read1', seq, 'I' * len(seq))])
    run('--fastq_filter', 'reads.fq', '--fastq_maxee', '1', '--fastaout', 'filtered.fa')
    assert fasta('filtered.fa') == [['read1', seq]]
    fragment = sequence(250, 220)
    rev = fragment[70:].translate(str.maketrans('ACGT', 'TGCA'))[::-1]
    fq('r1.fq', [('pair/1', fragment[:150], 'I' * 150)])
    fq('r2.fq', [('pair/2', rev, 'I' * 150)])
    run('--fastq_mergepairs', 'r1.fq', '--reverse', 'r2.fq', '--fastqout', 'merged.fq', '--threads', '1')
    assert fastq('merged.fq')[0][1] == fragment
    run('--fastq_stats', 'reads.fq', '--log', 'stats.log')
    assert Path('stats.log').stat().st_size > 0


def delta():
    seq = seed()
    for suffix in ('one', 'two'):
        run('--scramble', 'query.fa', '--scramble_kmer', '2', '--randseed', '42', '--fastaout', suffix + '.fa')
    one = fasta('one.fa')[0]
    assert Path('one.fa').read_bytes() == Path('two.fa').read_bytes()
    assert one[0] == 'query1' and len(one[1]) == len(seq)
    for k in (1, 2):
        assert Counter(seq[i:i+k] for i in range(len(seq)-k+1)) == Counter(one[1][i:i+k] for i in range(len(seq)-k+1))
    fq('r1.fq', [('a/1', seq, 'I' * len(seq)), ('b/1', seq, 'I' * len(seq)), ('orphan/1', seq, 'I' * len(seq))])
    fq('r2.fq', [('b/2', seq, 'I' * len(seq)), ('a/2', seq, 'I' * len(seq))])
    run('--fastx_syncpairs', 'r1.fq', '--reverse', 'r2.fq', '--fastqout', 'sync1.fq', '--fastqout_rev', 'sync2.fq', '--fastqout_orphans', 'orphan.fq')
    assert [n.split('/')[0] for n, _, _ in fastq('sync1.fq')] == [n.split('/')[0] for n, _, _ in fastq('sync2.fq')]
    assert len(fastq('sync1.fq')) == 2 and fastq('orphan.fq')[0][0] == 'orphan/1'
    run('--fastx_subsample', 'query.fa', '--sample_size', '10', '--allow_fewer', '--fastaout', 'sub.fa', '--randseed', '42')
    assert fasta('sub.fa')[0][1] == seq
    run('--fastx_subsample', 'query.fa', '--sample_size', '10', '--fastaout', 'badsub.fa', bad=True)
    fq('qual.fq', [('q1;size=1;', seq, '+' * len(seq)), ('q2;size=2;', seq, '+' * len(seq))])
    run('--fastx_uniques', 'qual.fq', '--fastqout', 'qual-out.fq', '--sizein', '--sizeout', '--threads', '1')
    assert fastq('qual-out.fq')[0][2] == '+' * len(seq)
    fq('solexa.fq', [('solexa', seq, ';' * len(seq))])
    run('--fastq_convert', 'solexa.fq', '--fastq_solexa', '--fastq_ascii', '64', '--fastqout', 'phred.fq')
    assert fastq('phred.fq')[0][2] == '"' * len(seq)
    run('--usearch_global', 'query.fa', '--db', 'db.fa', '--id', '1', '--qsegout', 'segment.fa', '--threads', '1')
    assert fasta('segment.fa')[0][1] == seq
    run('--usearch_global', 'query.fa', '--db', 'db.fa', '--id', 'nan', '--blast6out', 'invalid.tsv', bad=True)


def database():
    seed()
    run('--makeudb_usearch', 'db.fa', '--output', 'db.udb', '--dbmask', 'none')
    run('--udbinfo', 'db.udb')
    run('--udbstats', 'db.udb')
    run('--udb2fasta', 'db.udb', '--output', 'db-back.fa')
    assert fasta('db-back.fa') == fasta('db.fa')
    for db in ('db.fa', 'db.udb'):
        run('--sintax', 'query.fa', '--db', db, '--tabbedout', db + '.tsv', '--sintax_random', '--randseed', '42', '--threads', '1')
        assert 'd:Bacteria' in Path(db + '.tsv').read_text() and 'g:Example' in Path(db + '.tsv').read_text()
    assert Path('db.fa.tsv').read_bytes() == Path('db.udb.tsv').read_bytes()
    run('--usearch_global', 'query.fa', '--db', 'missing.udb', '--id', '1', '--blast6out', 'missing.tsv', bad=True)
    Path('invalid.udb').write_bytes(b'UDBF' + bytes(200))
    run('--udbinfo', 'invalid.udb', bad=True)
    Path('empty.fa').write_text('')
    run('--makeudb_usearch', 'empty.fa', '--output', 'empty.udb', bad=True)


if __name__ == '__main__':
    modes = {'identity': identity, 'core': core, 'fastq': fastq_paths, 'delta': delta, 'database': database}
    mode = sys.argv[1]
    assert mode in modes, mode
    with tempfile.TemporaryDirectory(prefix='taf-vsearch-' + mode + '-') as scratch:
        os.chdir(scratch)
        modes[mode]()
    print('PASS vsearch ' + mode)
