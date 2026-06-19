# TDA03 新对话上下文

## 当前状态

TDA03 还没有像 TDA02 一样完整玩家实机通关反馈。之前做过一轮逐条核对和术语同步，但后续仍需要重点处理。

当前主要源文件：

`outputs\tda_text\tda03_deepseek_full.csv`

当前最新 repack：

`outputs\repack_tda03_xmlsafe_20260617o`

当前缓存路径：

`%LOCALAPPDATA%\ancr\tda03\data\root\assets\data_spec\adv\game\scr\localized`

旧测试包：

`dist\MuvLuv_TDA03_CN_Patch_beta0.1.zip`

注意：这个包不是当前优先发布对象，接手时应重新审计后再决定是否打新包。

## 已同步的重要修正

- `ユズちゃん` 相关称呼统一为 `柚酱`。
- 光线级相关语序已修：
  - `tda03_t05454`
  - `tda03_t05456`
  - `tda03_t05800`
  - `tda03_t05809`
- `ボクサー` 固定为 `拳师号`。
- `クレイン` 固定为 `鹤`。
- 多人 speaker 分隔符应使用 `·`。

## 接手重点

1. 先跑 TDA03 当前 repack / 缓存审计。
2. 优先处理玩家截图反馈。
3. 如果继续逐条核对，直接从当前 CSV 和 JP 原文对照，不要参考英文槽。
4. 检查 speaker 原文必须来自日文 speaker，不要让英文 speaker 混入。
5. 检查是否仍有旧专名、繁体字、日文汉字残留。

## 建议新对话开场

请先读：

- `handoff\SHARED_RULES.md`
- `handoff\PROJECT_FILES.md`
- `handoff\TOOLS_AND_CHECKS.md`
- `handoff\TDA03_CONTEXT.md`

然后只处理 TDA03，不动 TDA01 / TDA02。

