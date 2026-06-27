# RIO / CRsa 工具

这些工具来自 photonflowers / photonmelodies 工作流沉淀，用于分析和处理 AGES 7.0 / rUGP / RIO / CRsa 技术路线下的脚本文本。

## 文件

- `extract_native_rio_crsa_text.py`：提取 native RIO / CRsa 文本。
- `extract_native_rio_crsa_text_wide.py`：宽扫描提取，用于漏网文本审计。
- `rio_crypto_probe.py`：探测 RIO / CRsa 解密和 payload 结构。
- `rio_reencrypt_one_line.py`：单行解密、重加密、写回验证。
- `rio_apply_batch_slots_v2.py`：批量槽位写回。
- `rio_apply_choice_slots.py`：选择项和特殊槽位写回。
- `make_byte_patch.py`：生成 byte patch 差分补丁。
- `verify_extraction_artifacts.py`：校验提取产物。

## 注意

- 不要直接假设不同平台或不同游戏的 `.rio` 结构完全相同。
- 新资源第一阶段只读分析：扫描 magic、CRsa offset、payload 范围、解密结果和 UTF-16LE 解码证据。
- 写回时必须按 stable id / 原 payload offset 定位，保留控制符，重新加密后再制作差分补丁。
