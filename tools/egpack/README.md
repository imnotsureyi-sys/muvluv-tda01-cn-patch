# AGES / egpack / FPD 工具

这些工具主要服务于 TDA00-03 的补丁制作流程，用于提取、检查和回写 AGES egpack 风格资源中的文本载荷。

## 文件

- `extract_egpack_text.py`：从 egpack 风格资源中提取脚本文本。
- `repack_egpack_with_csv.py`：按审核后的 CSV 重建文本载荷。
- `extract_fpd_filtered.py`：按过滤条件从 FPD / 资源容器中提取内容。
- `probe_fpd.py`：探测 FPD / 资源容器结构和密钥。
- `diagnose_fpd_keys.py`：辅助诊断 FPD 密钥组合。

## 注意

- 修改前必须定位章节、CSV 行、`id`、`egpack`、`scene`、`speaker_jp`、`jp_text`、`cn_text`。
- 翻译和修订只参考 JP 原文，不使用英文槽或旧中文兜底。
- 写回后需要审计 Text ID Not Found、空文本、错位、重复、乱码、英文残留和控制符问题。
