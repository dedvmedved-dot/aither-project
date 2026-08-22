# Qwen3.8 Download Verify N7 R1 (READ-ONLY)

## Task / Result
- task_id: `AITHER-URGENT-QWEN38-DOWNLOAD-VERIFY-N7-R1`
- executor: `hermes`
- mode: `READ_ONLY_MODEL_DOWNLOAD_VERIFY`
- baseline_sha: `bc90a740d1a5488e1720f1e310d443a637af2bb7`
- HEAD at verify: `f6e2d70e7d9cf8a2da163fb01b2b50b034aeea8f` (branch `aither-v2`)
- baseline is ancestor of HEAD: YES (diff baseline..HEAD = only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md`)
- result: **PASS**
- **DOWNLOAD_COMPLETE=YES**

## Timestamps
- measurement window: `2026-08-22 22:31` – `2026-08-22 22:35 MSK` (`19:31` – `19:35 UTC`)

## Node
- n7 (`bootsmam-k8s-clnt01-n7-gpu`, 10.129.13.77)

## Findings

### 1. Process `hf download Qwen/Qwen3.8-27B-FP8`
NOT RUNNING. `ps -eo pid,ppid,user,etime,args | grep -iE 'hf|huggingface|qwen|download|curl|wget|aria2|safetensors'`
→ no match (excluding grep). The orphaned download process recorded in the prior recovery audit
(PID 3291298) is gone. The only vLLM process on n7 is `qwen2.5-32b-instruct` (old model, unrelated).

### 2. Directory size
`/data/models/Qwen3.8-27B-FP8` = **29G** (`du -sh`). (Prior audit R1 measured 22 GiB at 15:46 MSK.)

### 3. Exact revision
commitHash (line 1) is uniform across all **81** `.cache/huggingface/download/*.metadata` files:
`017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`
(matches the `--revision` recorded in prior recovery audit R1).

### 4. Expected shard files (authoritative: `model.safetensors.index.json` → `weight_map`)
Count: **66**
- 64 × `layers-{0..63}.safetensors`
- `mtp.safetensors`
- `outside.safetensors`

### 5. Actual safetensors present on disk
- present: **66**
- missing: **0**
- extra: **0**

### 6. Download artifacts
- `*.incomplete`: **0**
- `*.partial`: **0**
- `*.tmp` / `*.temp`: **0**
- `*.lock`: **81** (residual, in `.cache/huggingface/download/`)
- `*.metadata`: **81** (normal hf_hub metadata: commitHash + etag + mtime)
- `safetensors-md5sum.txt`: **0 bytes** — etag `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`
  (SHA-1 of empty content) → empty file matches source; correct.

### 7. Config/tokenizer/index readability (valid JSON)
All OK: `config.json`, `tokenizer.json`, `tokenizer_config.json`, `generation_config.json`,
`preprocessor_config.json`, `video_preprocessor_config.json`, `model.safetensors.index.json`.

### 8. Shard integrity (safetensors header check)
Per file: expected size = 8 (header_len) + header JSON length + max `data_offsets[1]` == actual file size.
- checked: **66**
- size match: **66**
- mismatch: **0**
→ no truncated files, including the two non-layer shards:
  - `outside.safetensors` = 6 007 102 112 bytes (~5.6 GiB)
  - `mtp.safetensors` = 477 202 224 bytes (~455 MiB)
- `layers-*.safetensors` range 372 313 744 – 383 865 472 bytes each (~355–366 MiB)

## Conclusion
All 66 expected shard files are present and verified complete (safetensors header size check, 0 mismatches);
config/tokenizer/index files are readable. No `.incomplete` / `.partial` / `.tmp` artifacts exist.
The previously-missing 8 shards (`layers-6/7/8/9/61/63`, `mtp`, `outside`) are now present and complete,
and the orphaned `hf download` process has terminated.

Residual note: 81 stale `.lock` files remain in `.cache/huggingface/download/` — lock artifacts from the
orphaned (non-graceful) download. They do NOT indicate incomplete data, but a subsequent `hf download`
against the same local dir may block on them unless cleared.

**DOWNLOAD_COMPLETE=YES**

## SECRETS_EXPOSED: NO
