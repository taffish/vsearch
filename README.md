# vsearch

TAFFISH tool app for [VSEARCH](https://github.com/torognes/vsearch), a
versatile open-source command-line toolkit for amplicon and metagenomic
sequence processing.

## Package Identity

- App name: `vsearch`
- Command: `taf-vsearch`
- TAFFISH version: `2.31.0-r1`
- App kind: `tool`
- Container image: `ghcr.io/taffish/vsearch:2.31.0-r1`
- Upstream: `torognes/vsearch` tag `v2.31.0`
- Runtime source: official VSEARCH GitHub release binaries
- Upstream runtime version: `vsearch v2.31.0`
- Upstream license: `GPL-3.0-or-later OR BSD-2-Clause`
- TAFFISH wrapper license: `Apache-2.0`

## What Is Packaged

- `vsearch`: upstream command-line executable from the official `v2.31.0`
  release.
- Upstream README, man page, PDF manual, and license files under
  `/opt/vsearch/share`.
- Standard shell utilities used by smoke tests and common compressed-input
  workflows: `gzip`, `bzip2`, `grep`, `sed`, and `bash`.
- A tiny offline smoke fixture at
  `/opt/vsearch/share/testdata/vsearch-smoke.sh`.

The image chooses the official upstream binary by target architecture:

- `linux/amd64`: `vsearch-2.31.0-linux-x86_64.tar.gz`
- `linux/arm64`: `vsearch-2.31.0-linux-aarch64.tar.gz`

Both downloads are checksum-verified during image build using the SHA256
digests published in the GitHub release metadata.

## Scope

This app exposes the VSEARCH CLI, including the main command families documented
by upstream:

- chimera detection: `--uchime_denovo`, `--uchime2_denovo`,
  `--uchime3_denovo`, `--uchime_ref`
- clustering: `--cluster_fast`, `--cluster_size`, `--cluster_smallmem`,
  `--cluster_unoise`
- dereplication and rereplication: `--fastx_uniques`,
  `--derep_fulllength`, `--derep_id`, `--derep_prefix`, `--derep_smallmem`,
  `--rereplicate`
- FASTA/FASTQ/SFF processing: filtering, conversion, stats, merging, reverse
  complementation, sorting, shuffling, masking, and subsampling
- searching and alignment: `--search_exact`, `--usearch_global`,
  `--allpairs_global`
- UDB database handling: `--makeudb_usearch`, `--udb2fasta`, `--udbinfo`,
  `--udbstats`
- taxonomic classification with `--sintax`

This app does not bundle reference databases, taxonomy databases, QIIME/Galaxy
wrappers, biom conversion tools, downstream reports, or the experimental
libvsearch developer API. It is a CLI runtime, not a C/C++ development SDK.

## Basic Usage

Show upstream version and help:

```bash
taf-vsearch vsearch --version
taf-vsearch vsearch --help
```

Global search against a user-provided FASTA database:

```bash
taf-vsearch vsearch \
  --usearch_global queries.fa \
  --db database.fa \
  --id 0.97 \
  --blast6out hits.tsv
```

Dereplicate FASTA/FASTQ sequences:

```bash
taf-vsearch vsearch \
  --fastx_uniques reads.fa \
  --fastaout uniques.fa \
  --sizeout
```

Cluster sequences into OTU-like centroids:

```bash
taf-vsearch vsearch \
  --cluster_fast reads.fa \
  --id 0.97 \
  --centroids otus.fa \
  --uc clusters.uc
```

Run de novo chimera detection:

```bash
taf-vsearch vsearch \
  --uchime_denovo reads.fa \
  --nonchimeras clean.fa \
  --chimeras chimera.fa
```

Filter FASTQ reads:

```bash
taf-vsearch vsearch \
  --fastq_filter reads.fq \
  --fastq_maxee 1.0 \
  --fastaout filtered.fa
```

Merge paired-end FASTQ reads:

```bash
taf-vsearch vsearch \
  --fastq_mergepairs R1.fq \
  --reverse R2.fq \
  --fastqout merged.fq
```

## Command-Mode Notes

This is a thin TAFFISH wrapper:

```taf
<taf-app:container:ghcr.io/taffish/vsearch:2.31.0-r1>
vsearch ::*ARGV*::
```

Use explicit command-mode calls for clarity:

```bash
taf-vsearch vsearch --usearch_global queries.fa --db database.fa --id 0.97 --blast6out hits.tsv
```

Option-leading shorthand also works for the default upstream command:

```bash
taf-vsearch -- --help
taf-vsearch -- --version
```

## Inputs And Outputs

Common inputs:

- FASTA, FASTQ, and SFF sequence files.
- gzip-compressed `.gz` and bzip2-compressed `.bz2` FASTA/FASTQ files.
- User-provided reference FASTA databases through `--db`.
- VSEARCH UDB databases created with `--makeudb_usearch`.

Common outputs:

- FASTA/FASTQ sequence files from filtering, merging, dereplication, sorting,
  masking, reverse-complementing, or clustering.
- UC clustering output, BIOM/mothur/OTU-style tables, BLAST6, SAM, alignment,
  and user-defined tabular output depending on selected command family.
- Logs and statistics tables for FASTQ and search workflows.

## Runtime Boundaries

No external database, reference bundle, network service, GPU, MPI runtime, or
license server is required. VSEARCH workflows that use `--db`, `--sintax`, or
UDB commands expect the user to provide the relevant reference FASTA or UDB
files.

VSEARCH is for nucleotide sequences. Upstream states that it does not support
amino acid sequences or local alignments. Large all-vs-all alignment and
clustering tasks can require substantial RAM, CPU, and temporary disk; memory
usage grows with sequence lengths, identity thresholds, and thread counts.

The smoke test validates a tiny offline path only. It does not replace
scientific validation of a production microbiome pipeline, reference database,
taxonomy assignment, or OTU/ASV interpretation.

## Platforms

The official VSEARCH release provides Linux binaries for multiple 64-bit
architectures. This TAFFISH app requests native `linux/amd64` and `linux/arm64`
container images:

- `linux/amd64` uses the upstream `linux-x86_64` binary.
- `linux/arm64` uses the upstream `linux-aarch64` binary.

## Testing

The smoke coverage checks:

- command existence
- upstream version string `vsearch v2.31.0`
- core help entries for search, FASTQ merging, and chimera detection
- dynamic library resolution with `ldd`
- a small real workflow covering `--fastx_uniques`, `--usearch_global`,
  gzip input, bzip2 input, `--sortbylength`, and `--fastx_revcomp`

## License And Citation

The TAFFISH wrapper metadata and documentation are distributed under
`Apache-2.0`.

Upstream VSEARCH is dual-licensed under either `GPL-3.0-or-later` or
`BSD-2-Clause`. The upstream distribution also includes third-party license
notices for bundled or optional components such as CityHash, DUST-derived code,
MD5/SHA1 code, zlib, bzip2, and Autoconf-generated files. The upstream license
files are preserved under `/opt/vsearch/share/licenses/vsearch`.

Please cite:

Rognes T, Flouri T, Nichols B, Quince C, Mahe F. VSEARCH: a versatile open
source tool for metagenomics. PeerJ. 2016;4:e2584. DOI:
`10.7717/peerj.2584`.

## Upstream Resources

- Source and releases: <https://github.com/torognes/vsearch>
- Tagged release: <https://github.com/torognes/vsearch/releases/tag/v2.31.0>
- Online documentation: <https://torognes.github.io/vsearch/>
- Manual PDF: <https://github.com/torognes/vsearch/releases/download/v2.31.0/vsearch_manual.pdf>
- Bioconda recipe: <https://bioconda.github.io/recipes/vsearch/README.html>
