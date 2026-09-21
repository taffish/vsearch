vsearch 2.32.0-r1 — nucleotide sequence processing and global search

Start:
  taf-vsearch --help                       This task help
  taf-vsearch vsearch --help               Upstream options
  taf-vsearch vsearch --version            Runtime version
  taf-vsearch -- --version                 Default-command option forwarding
  taf-vsearch --compile                    Compile this wrapper

Run from a writable directory containing FASTA/FASTQ/SFF inputs. FASTA/FASTQ
gzip and bzip2 input works. Choose new output paths: upstream may overwrite them.

Common tasks:
  taf-vsearch vsearch --fastx_uniques reads.fa --fastaout unique.fa --sizeout
  taf-vsearch vsearch --cluster_fast unique.fa --id 0.97 --centroids otus.fa --uc clusters.uc
  taf-vsearch vsearch --usearch_global queries.fa --db reference.fa --id 0.97 --blast6out hits.tsv
  taf-vsearch vsearch --uchime_denovo unique.fa --nonchimeras clean.fa --chimeras chimera.fa
  taf-vsearch vsearch --fastq_filter reads.fq --fastq_maxee 1.0 --fastaout filtered.fa
  taf-vsearch vsearch --fastq_mergepairs R1.fq --reverse R2.fq --fastqout merged.fq
  taf-vsearch vsearch --fastx_syncpairs R1.fq --reverse R2.fq --fastqout paired1.fq --fastqout_rev paired2.fq
  taf-vsearch vsearch --scramble reads.fa --scramble_kmer 2 --randseed 42 --fastaout scrambled.fa

Outputs: sequence FASTA/FASTQ, centroid/UC/OTU tables, search BLAST6/SAM,
taxonomy TSV or logs according to selected flags. Inspect counts and warnings.
Use --threads N to limit CPU. Memory grows with dataset size and sequence length.
Nucleotide sequences only; not protein search/local alignment. Set thresholds,
masking and quality encoding deliberately; 2.32 rejects more invalid parameters.

Use a local reference (no automatic download or database choice):
  taf-vsearch vsearch --makeudb_usearch reference.fa --output reference.udb --dbmask none
  taf-vsearch vsearch --sintax queries.fa --db reference.udb --tabbedout taxonomy.tsv --randseed 42
SINTAX requires taxonomic headers such as ;tax=d:Bacteria,g:Example;.
UDB retains build-time masking; choose --dbmask explicitly. Raw provider headers
may need conversion before SINTAX. Never infer scientific validity from smoke.

Choose backend for ordinary commands (native amd64/arm64 images):
  export TAFFISH_CONTAINER_BACKEND=docker
Or: export TAFFISH_CONTAINER_BACKEND=podman
Or on native Linux: export TAFFISH_CONTAINER_BACKEND=apptainer
  taf-vsearch vsearch --version
Apptainer cannot run on macOS; use Docker/Podman there. No GPU/GUI service needed.

Prepare a reusable database once (reviewed fixed recipe; see README schema):
  DB_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/taffish/vsearch/db"
  mkdir -p "$DB_ROOT"; chmod 755 "$DB_ROOT"
Choose ONE backend and its actual writable bind; run install as directory owner:
  export TAFFISH_CONTAINER_BACKEND=docker
  export TAFFISH_DOCKER_RUN_ARGS="--user $(id -u):$(id -g) -v '$DB_ROOT:/db-install:rw'"
Podman alternative:
  export TAFFISH_CONTAINER_BACKEND=podman
  export TAFFISH_PODMAN_RUN_ARGS="--userns keep-id --user $(id -u):$(id -g) -v '$DB_ROOT:/db-install:rw'"
Linux Apptainer alternative:
  export TAFFISH_CONTAINER_BACKEND=apptainer
  export TAFFISH_APPTAINER_RUN_ARGS="--bind '$DB_ROOT:/db-install:rw'"
With your selected backend:
  taf-vsearch vsearch-db install --recipe recipe.json --db-root /db-install --rights-reviewed --dry-run
  taf-vsearch vsearch-db install --recipe recipe.json --db-root /db-install --rights-reviewed
Review download bytes and reserve (default 10 GiB extra; --reserve-gb overrides).
Offline import: append --source-dir acquired (exact recipe filenames in workdir).
Repeat to resume/verify; no overwrite. On corruption/lock errors stop and inspect.

Reuse read-only; replace the install bind for your chosen backend:
  export TAFFISH_DOCKER_RUN_ARGS="-v '$DB_ROOT:/db:ro'"
  export TAFFISH_PODMAN_RUN_ARGS="-v '$DB_ROOT:/db:ro'"
  export TAFFISH_APPTAINER_RUN_ARGS="--bind '$DB_ROOT:/db:ro'"
  taf-vsearch vsearch-db verify --db-root /db --id chosen-reference--fixed-release
  taf-vsearch vsearch --usearch_global queries.fa --db /db/chosen-reference--fixed-release/reference.udb --id 0.97 --blast6out hits.tsv
Set DB_ROOT to your administrator's /var/lib/taffish/vsearch/db for site reuse:
the administrator installs once; ordinary users need read access, never root.
No discovery/fallback: --db selects the exact member; no bind means no shared DB.
Disable mount policy after use (preserve other site settings if applicable):
  unset TAFFISH_DOCKER_RUN_ARGS TAFFISH_PODMAN_RUN_ARGS TAFFISH_APPTAINER_RUN_ARGS
Manual fallback on all backends: keep acquired files in workdir and --db local.fa.
Do not chmod 777 or write into the image; inputs/shared DB should stay read-only.
For spaced arguments retain inner quotes: --db "'references/my db.fa'".

Missing DB / permission errors: check actual bind, selected ID, file permissions
and writable output/temp space. Review provider license before sharing resources.
Details, recipe schema and provenance: https://github.com/taffish/vsearch
Upstream command manual: https://torognes.github.io/vsearch/
