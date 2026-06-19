# 工具和检查

## 保留工具目录

主要脚本在：

`work`

常用脚本：

- `work\build_split_patch_packages.py`：打包脚本。
- `work\audit_display_slots_against_csv.py`：检查当前 repack / 缓存中是否包含 CSV 期望显示文本，可抓 missing / mismatch / Text ID Not Found。
- `work\audit_called_text_ids_have_display_text.py`：检查调用到的文本 ID 是否有显示文本。
- `work\audit_reextracted_jp_slots_all_tda.py`：重新核对 JP 槽用。
- `work\check_tda_glossary.py`：术语检查。
- `work\verify_curated_terms_strict.py`：固定术语严格检查。
- `work\build_line_by_line_review_workbook_openpyxl.py`：生成逐条核对表。

## 常用审计命令

TDA02 / TDA03 当前缓存显示文本审计：

```powershell
$env:PYTHONIOENCODING='utf-8'
python work\audit_display_slots_against_csv.py --mode cache --titles tda02 tda03 --report outputs\qa\alignment_review\display_slot_audit_cache_tda02_03.csv
```

TDA02 / TDA03 当前 repack 显示文本审计：

```powershell
$env:PYTHONIOENCODING='utf-8'
python work\audit_display_slots_against_csv.py --mode repack --stamp xmlsafe_20260617o --titles tda02 tda03 --report outputs\qa\alignment_review\display_slot_audit_repack_tda02_03.csv
```

只审 TDA02：

```powershell
$env:PYTHONIOENCODING='utf-8'
python work\audit_display_slots_against_csv.py --mode repack --stamp xmlsafe_20260617o --titles tda02 --report outputs\qa\alignment_review\display_slot_audit_repack_tda02.csv
```

## 打包注意

`work\build_split_patch_packages.py` 默认会遍历多个标题。为了避免误打旧包，接手时必须确认脚本里的来源路径，尤其是 `STAMP` 和每章 `source`。

TDA02 最近一次打包时使用的是：

`outputs\repack_tda02_xmlsafe_20260617o`

打包后必须检查：

1. zip 自检 `testzip=None`。
2. 包内有 `font_payload\SourceHanSansSC-Bold.otf`。
3. 包内 README 对应章节名称正确。
4. payload 内没有旧术语残留和 `Text ID Not Found`。
5. speaker 表里 `・ = 0`、`& = 0`，多人分隔符应为 `·`。

## 重要提醒

PowerShell 直接写中文时有过编码变成 `????` 的事故。写入 CSV / egpack 时，优先用 UTF-8 明确读写；如果用临时代码，设置：

```powershell
$env:PYTHONIOENCODING='utf-8'
```

