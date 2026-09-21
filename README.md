# VSEARCH

TAFFISH tool app for [VSEARCH](https://github.com/torognes/vsearch), an open-source
nucleotide sequence processing and global-search CLI.

## Identity and installation

- Package: `vsearch 2.32.0-r1`; command: `taf-vsearch`.
- Image: `ghcr.io/taffish/vsearch:2.32.0-r1`.
- Upstream: `torognes/vsearch` tag `v2.32.0`, commit
  `d44d6da51f7fe0b4281f02af76d04923f2075e61`.
- Native platforms: `linux/amd64` and `linux/arm64`.
- Runtime: unmodified official, SHA256-verified release binaries; no algorithm patches.
- Wrapper: Apache-2.0; upstream: GPL-3.0-or-later OR BSD-2-Clause.

Once this candidate is published and indexed, install the pinned app:

```sh
taf update
taf install vsearch 2.32.0-r1
taf-vsearch-v2.32.0-r1 --version
taf-vsearch vsearch --version
```

During local development, `taf check` and `taf build` create
`target/taf-vsearch-v2.32.0-r1`; building the wrapper does not build the image.
The unversioned alias follows the latest installed local version; use the
versioned command when this exact package is required. For an argument containing
spaces preserve an inner quote, for example `--db "'references/my db.fa'"`.

## Scope and upstream changes

The complete upstream CLI is exposed: clustering, dereplication, chimera detection,
FASTA/FASTQ/SFF processing, paired-read merging, global/exact search, SINTAX and UDB.
VSEARCH is nucleotide-only; it is not a protein search or local alignment tool.

[2.32.0](https://github.com/torognes/vsearch/releases/tag/v2.32.0) adds
`--scramble` (k-mer-preserving randomization), `--fastx_syncpairs` (paired-read
synchronization), `--allow_fewer` for subsampling, and Solexa-to-Phred conversion.
It also fixes quality aggregation, SINTAX reproducibility and UDB validation.
Invalid values and output failures are rejected more strictly. FASTQ maximum
quality defaults changed; set quality encoding/ranges explicitly when appropriate.
`--search_exact --lcaout` was never implemented and is now rejected; use the
documented `--usearch_global` route for LCA output. See upstream release notes for
the complete change list; old pipeline outputs are not guaranteed byte-identical.

The image retains man sections 1/5/7, README, NEWS, licenses, binary provenance,
package inventory and upstream Bash/Zsh/Fish completion files under
`/opt/vsearch/share`. Completion files describe the **upstream `vsearch` executable**,
not the host `taf-vsearch` wrapper; no host shell configuration is installed.
The old PDF manual is not in these binary assets; use the packaged man sources or
[online documentation](https://torognes.github.io/vsearch/).

Officially linked Galaxy IUC and QIIME 2 integrations are independent host
environments/plugins, not a VSEARCH GUI/service or executable bundled with this
release. They remain separately installed integrations. GPU, browser ports and
GUI lifecycle handling are N/A. The experimental C++ API/development SDK, BIOM
conversion tools and downstream reports are outside this CLI runtime.

## Usage and outputs

```sh
taf-vsearch --help                  # installed wrapper task help
taf-vsearch vsearch --help          # upstream options
taf-vsearch -- --version            # default-command option forwarding
taf-vsearch vsearch --fastx_uniques reads.fa --fastaout unique.fa --sizeout
taf-vsearch vsearch --cluster_fast unique.fa --id 0.97 --centroids otus.fa --uc clusters.uc
taf-vsearch vsearch --usearch_global queries.fa --db reference.fa --id 0.97 --blast6out hits.tsv
taf-vsearch vsearch --fastq_mergepairs R1.fq --reverse R2.fq --fastqout merged.fq
taf-vsearch vsearch --scramble reads.fa --scramble_kmer 2 --randseed 42 --fastaout shuffled.fa
```

Run from a writable working directory containing your inputs; normal commands do
not download resources. FASTA/FASTQ gzip and bzip2 input is supported. Search gives
BLAST6/SAM/alignment or selected tabular outputs; clustering gives centroids/UC/
OTU tables; filters/merges give sequence files. Explicitly select thresholds,
masking, strand, thread count and output names. Existing output paths can be
overwritten by upstream: use a new output directory. Large comparisons require
substantial RAM; tiny smoke is not scientific or production-scale qualification.

## Reference and taxonomy resources

Project-specific FASTA is user input. Reusable public reference/taxonomy releases
are selectable resources, not a mandatory universal database. Nothing is bundled
or selected automatically. `--db` is the authoritative resource override: choosing
a different reference silently would change the scientific meaning of a run.
There is consequently no implicit discovery/fallback, download-on-analysis, model
cache, or magic mounted marker. Omit the explicit bind to disable shared access.

`vsearch-db` prepares **one explicitly selected, fixed recipe** from HTTPS or
already downloaded local files. It validates exact size/SHA256, preserves source
and permission notices, resumes downloads, locks concurrent installation, verifies
existing members and atomically promotes a complete member without overwriting.
Directories/files become 0755/0644 for ordinary-user read-only reuse; installer
cache is 0700. It does not unpack archives or convert taxonomy formats. gzip/bzip2
FASTA can be retained as such. SINTAX needs appropriately formatted `;tax=...;`
headers; raw SILVA headers must not be assumed SINTAX-compatible.

Create a reviewed JSON recipe using actual immutable URLs, exact byte counts and
independently checked SHA256 values; the following is a **schema illustration**,
not a downloadable catalog entry:

```json
{
  "schema": "taffish.vsearch.recipe.v1",
  "id": "chosen-reference",
  "version": "fixed-release",
  "source": "Provider, release, provenance URL and any formatting steps",
  "license": "Exact license, attribution and permitted local/shared use",
  "files": [{"name": "reference.fa.gz", "url": "https://provider.example/fixed/reference.fa.gz",
    "sha256": "REPLACE_WITH_64_LOWERCASE_HEX_DIGITS", "size": 123456}],
  "makeudb": {"input": "reference.fa.gz", "dbmask": "none"}
}
```

Omit `makeudb` to retain only the selected original files. If present, it generates
`reference.udb`; `dbmask` must explicitly be `none`, `soft` or `dust`. Masking is a
scientific choice, and UDB preserves the build-time mask: use `none` if requiring
unmasked SINTAX FASTA/UDB equivalence. No entire catalog/family is downloaded.

Recommended host roots: personal `${XDG_DATA_HOME:-$HOME/.local/share}/taffish/vsearch/db`,
or administrator-owned `/var/lib/taffish/vsearch/db` (a site may instead choose
`/usr/local/share/taffish/vsearch/db`). `--db-root` is the container
path of the actual bind, not a host-path discovery mechanism. A root must already
exist, be owned by the installer, and not be group/world writable. A site
administrator can prepare it once with an authorized installation account;
ordinary users then bind it read-only and never need root. Do not use `chmod 777`.

### Prepare once, then reuse

Place `recipe.json` in the current working directory. Use a physical absolute host
path without symlink components and with permissions allowing intended readers:

```sh
DB_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/taffish/vsearch/db"
mkdir -p "$DB_ROOT"
chmod 755 "$DB_ROOT"
# Choose exactly one backend; Apptainer requires native Linux.
export TAFFISH_CONTAINER_BACKEND=docker
export TAFFISH_DOCKER_RUN_ARGS="--user $(id -u):$(id -g) -v '$DB_ROOT:/db-install:rw'"
# Podman alternative:
# export TAFFISH_CONTAINER_BACKEND=podman
# export TAFFISH_PODMAN_RUN_ARGS="--userns keep-id --user $(id -u):$(id -g) -v '$DB_ROOT:/db-install:rw'"
# Apptainer alternative:
# export TAFFISH_CONTAINER_BACKEND=apptainer
# export TAFFISH_APPTAINER_RUN_ARGS="--bind '$DB_ROOT:/db-install:rw'"
taf-vsearch vsearch-db install --recipe recipe.json --db-root /db-install --rights-reviewed --dry-run
taf-vsearch vsearch-db install --recipe recipe.json --db-root /db-install --rights-reviewed
```

Review the displayed URLs, member inventory, download size and disk reserve before
installation. `--reserve-gb` defaults to 10 GiB in addition to downloads; increase
it for large UDB generation. Network access is needed only for explicit acquisition.
For offline import, put exact named files in `acquired/` and append
`--source-dir acquired`. Repeating the same command resumes network transfer or
verifies an already-complete identical recipe. A different recipe needs a new
version. On damage, stop and inspect the exact member/cache/lock; do not delete an
active lock or overwrite a shared release. No `--force` repair is provided.

For analysis replace the install bind with a read-only bind using the same backend:

```sh
export TAFFISH_DOCKER_RUN_ARGS="-v '$DB_ROOT:/db:ro'"
export TAFFISH_PODMAN_RUN_ARGS="-v '$DB_ROOT:/db:ro'"
export TAFFISH_APPTAINER_RUN_ARGS="--bind '$DB_ROOT:/db:ro'"
taf-vsearch vsearch-db verify --db-root /db --id chosen-reference--fixed-release
taf-vsearch vsearch --sintax queries.fa --db /db/chosen-reference--fixed-release/reference.udb --tabbedout taxonomy.tsv --randseed 42
unset TAFFISH_DOCKER_RUN_ARGS TAFFISH_PODMAN_RUN_ARGS TAFFISH_APPTAINER_RUN_ARGS
```

These environment variables are explicit local/site mount policy, not mandatory
app-specific runtime settings. Preserve any other necessary site options when
setting them. No automatic mount is claimed. Manual fallback for every backend:
put a legally acquired FASTA/UDB in the working directory and pass `--db local.fa`;
optionally run `vsearch --makeudb_usearch local.fa --output local.udb --dbmask none`.
Keep the source release/checksum/license alongside it even without the helper.

SILVA data/taxonomy is one possible source, not a selected default. Its
[license information](https://www.arb-silva.de/silva-license-information/) specifies
CC BY 4.0 attribution and additional DSI notices; review the exact selected file's
terms and intended sharing. Other providers may impose different conditions.
`--rights-reviewed` records an explicit operator acknowledgement, not legal advice
or automatic permission. Software and database licenses are separate.

## Backend, write map and validation

Docker/Podman execute native Linux images; on macOS they use Linux VMs. Apptainer
runs on native Linux with an actual read-only SIF. All three use the same thin
`<taf-app:container:...>` entry and explicit command mode. No backend-specific
algorithm, privilege, GPU or network service options are required.

Image paths `/opt`, `/usr` and `/var` are read-only at runtime. Temporary files use
unique `/tmp` directories; outputs use the working directory; only explicit
installation writes to the bound resource root. Analysis binds resources read-only.
Apptainer must have writable private temporary/work directories and sufficient
space. Linux arm64 Apptainer is conceptually supported but not a separate validation
claim unless recorded below; it is not a macOS runtime.

Current native validation:

| Platform / backend | Exact offline smoke | Wrapper / actual resource bind |
| --- | --- | --- |
| xjp Linux amd64 / Docker | normal + read-only PASS | ordinary user PASS |
| xjp Linux amd64 / Podman | normal + read-only PASS | ordinary user PASS |
| xjp Linux amd64 / Apptainer | actual read-only SIF PASS | ordinary user PASS |
| Linux VM arm64 / Podman | normal + read-only PASS | ordinary user PASS |
| Linux VM arm64 / Docker | read-only PASS | interrupted by Docker Desktop failure |
| Linux arm64 / Apptainer | not separately validated | not separately validated |

Both native platforms were built using the canonical app-root Docker context.
The Docker Desktop failure occurred after the successful arm64 build/direct smoke;
the same arm64 OCI was loaded into Podman for complete validation. Docker's backend
gate is independently covered on native amd64. No app-specific runtime arguments,
architecture-specific resource format or observed coupling requires ARM SIF as an
additional gate; it remains an untested combination, not a native ARM failure.
No QEMU result is reported as native evidence and no backend exception is used.

The 18 manifest checks passed in eight fresh-container matrices (144 commands).
Actual wrapper tests additionally cover read-only roots, spaced paths, host-owned
outputs, installation, idempotence, missing members, fake-mount rejection and
read-only analysis. On xjp, one container-root-owned synthetic installation was
reused by ordinary users across all three backends and by a second numeric UID;
writes were denied, including with a writable bind. The private fixture was cleaned.
HTTPS interruption/Range resumption and visible original exit-37 diagnostics passed
on all three backends. These are tiny mechanism tests: no full production reference,
real system-directory installation or production scientific compatibility is claimed.

Image sizes are 136,721,997 bytes (amd64) and 165,900,313 bytes (arm64), uncompressed.
VSEARCH/docs use about 3 MiB; Python standard library about 27–28 MiB. The base,
shared libraries and Python/curl support explicit resource acquisition. APT lists,
package/download archives, build sources, headers and compiler are absent. Runtime
Python standard-library bytecode is retained for imports; no app-generated bytecode
is written. Copyright notices and upstream manuals/completions are retained.

Build-time checks are deliberately small: version, ordinary help, libraries and
tiny sequence operations, with no rendered manual, terminal-width dependency,
GUI/browser, network acquisition, CPU-feature assumption or benchmark threshold.
Runtime smoke additionally checks FASTQ merging/filtering, new 2.32 paths, UDB/
SINTAX equivalence, corrupt input rejection and resource integrity. Synthetic
fixtures do not validate a production database or ecological interpretation.

## License and citation

Upstream license files are retained in `/opt/vsearch/share/licenses`; Debian
dependency notices remain under `/usr/share/doc`. No license notices are stripped.
Reference providers retain their own license and citation requirements.

Rognes T, Flouri T, Nichols B, Quince C, Mahé F. VSEARCH: a versatile open source
tool for metagenomics. PeerJ 4:e2584 (2016), [doi:10.7717/peerj.2584](https://doi.org/10.7717/peerj.2584).
