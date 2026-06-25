vsearch 2.31.0-r1

Purpose:
  VSEARCH is a command-line toolkit for amplicon and metagenomic sequence
  processing. It supports chimera detection, clustering, dereplication,
  rereplication, global search/alignment, FASTA/FASTQ processing, masking,
  sorting, subsampling, SINTAX classification, and UDB handling.

Usage:
  taf-vsearch vsearch --version
  taf-vsearch vsearch --help
  taf-vsearch vsearch --usearch_global queries.fa --db db.fa --id 0.97 --blast6out hits.tsv
  taf-vsearch vsearch --fastx_uniques reads.fa --fastaout uniques.fa --sizeout
  taf-vsearch vsearch --cluster_fast reads.fa --id 0.97 --centroids otus.fa --uc clusters.uc
  taf-vsearch vsearch --uchime_denovo reads.fa --nonchimeras clean.fa --chimeras chimera.fa

Common FASTQ paths:
  taf-vsearch vsearch --fastq_filter reads.fq --fastq_maxee 1.0 --fastaout filtered.fa
  taf-vsearch vsearch --fastq_mergepairs R1.fq --reverse R2.fq --fastqout merged.fq
  taf-vsearch vsearch --fastq_stats reads.fq --log fastq_stats.log

Packaged command:
  vsearch   Upstream VSEARCH CLI from the official GitHub release binary.

Command-mode note:
  Prefer explicit command-mode calls such as:
    taf-vsearch vsearch --usearch_global queries.fa --db db.fa --id 0.97 --blast6out hits.tsv
  Option-leading shorthand also works for the default command:
    taf-vsearch -- --help

Inputs:
  FASTA/FASTQ/SFF     Sequence inputs. FASTA/FASTQ can be gzip or bzip2
                      compressed when the upstream binary supports it.
  reference FASTA     User-provided database/reference for --db workflows.
  UDB                 VSEARCH database created with --makeudb_usearch.

Key outputs:
  FASTA/FASTQ         Filtered, merged, dereplicated, sorted, masked, or
                      clustered sequences.
  UC/BIOM/OTU table   Clustering and OTU table outputs.
  BLAST6/SAM/ALN      Search and alignment outputs.
  logs/stat tables    FASTQ statistics and command logs.

Common command families:
  --usearch_global, --search_exact      Global and exact sequence search.
  --cluster_fast, --cluster_size        OTU clustering.
  --fastx_uniques, --derep_fulllength   Dereplication.
  --uchime_denovo, --uchime_ref         Chimera detection.
  --fastq_filter, --fastq_mergepairs    FASTQ filtering and read merging.
  --fastx_revcomp, --sortbylength       FASTA/FASTQ utilities.
  --sintax                              Taxonomic classification with a user DB.

Platform and resources:
  This app uses official VSEARCH Linux release binaries for linux/amd64 and
  linux/arm64. No external database, network service, GPU, or license server is
  required. Runtime memory can grow quickly for long sequence comparisons and
  multi-threaded alignments.

Boundaries:
  This app packages the VSEARCH CLI and upstream documentation. It does not
  bundle reference databases, taxonomy databases, QIIME/Galaxy wrappers, biom,
  downstream reports, or the experimental libvsearch developer API. VSEARCH is
  for nucleotide sequences; upstream does not support amino acid sequences or
  local alignments.

Detailed documentation:
  https://github.com/torognes/vsearch
  https://torognes.github.io/vsearch/
  https://github.com/torognes/vsearch/releases/tag/v2.31.0

Wrapper options:
  taf-vsearch --help       Show this TAFFISH help.
  taf-vsearch --version    Show TAFFISH wrapper version.
  taf-vsearch --compile    Compile the TAFFISH wrapper.
  taf-vsearch vsearch      Run the upstream command.
