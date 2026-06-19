# TDA01 新对话上下文

## 状态

TDA01 已经在另一个对话继续迭代。这个项目里有旧 beta0.1 包和新的候选输出，但接手 TDA01 前必须先向用户确认“另一个对话”的最新结果是否已经同步回本项目。

当前项目里可见文件：

- 源 CSV：`outputs\tda_text\tda01_deepseek_full.csv`
- 一个候选输出：`outputs\repack_tda01_xmlsafe_20260618_beta02fix_candidate`
- 旧包：`dist\MuvLuv_TDA01_CN_Patch_beta0.1.zip`

## 接手前必须做

1. 问用户另一个 TDA01 对话是否已经把最新修改写入本项目。
2. 如果已经写入，先读对应报告和最新 repack。
3. 不要用旧 beta0.1 覆盖新的 TDA01 工作。
4. 不要把 TDA02 / TDA03 的修正批量套到 TDA01，除非日文原文和上下文都确认。

## 已知原则

- 严格以日文 JP 槽为准。
- speaker 原文必须是日文 speaker，不使用英文 speaker。
- 说话人多人分隔符用 `·`。
- 空 JP 槽不能直接当空文本处理，先查游戏实际显示。

## 建议新对话开场

请先读：

- `handoff\SHARED_RULES.md`
- `handoff\PROJECT_FILES.md`
- `handoff\TOOLS_AND_CHECKS.md`
- `handoff\TDA01_CONTEXT.md`

然后只处理 TDA01，不动 TDA02 / TDA03。

