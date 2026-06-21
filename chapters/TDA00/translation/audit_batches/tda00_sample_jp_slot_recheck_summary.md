# TDA00 sample JP slot recheck

- rows checked: 200
- unique ids: 200
- duplicate ids: 0
- call_order increasing: no
- issue rows: 22
- manual fixes applied after JP-slot reading: 27
- sample vs full JP baseline mismatches: 0

## Issue counts
- call_order_not_increasing: 1
- duplicate_cn_suspect: 21

## Resolution Notes
- `call_order_not_increasing` is expected for this sample: the sample combines separate ranges, so row order crosses from call order 269 back to 20.
- `duplicate_cn_suspect` rows are normal silent/ellipsis lines where JP itself is repeated punctuation/control timing.
- No remaining sample issues were found for empty CN, old `マム -> 妈妈`, `ゴルフセット` old wording, speaker-name leakage, JSON garbage, English full-sentence residue, kana residue, or control-code damage.
- Manual JP-slot fixes are listed in `tda00_sample_jp_slot_manual_fixes.csv`.
- Exact sample-to-baseline alignment is listed in `tda00_sample_vs_full_jp_baseline.csv`.

## Important notes
- This audits the current 200-row sample only. The full 3713-row JP baseline is present, but the full CN final file is not present in this worktree.
- Model comparison raw files are not treated as final translation.
