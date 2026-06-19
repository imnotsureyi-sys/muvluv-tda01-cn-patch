# Muv-Luv Series Steam 版简体中文补丁

这是一个非官方、非商业的 Muv-Luv Series Steam 版简体中文补丁总项目。

当前目标是把各章节 / 各作品的汉化补丁、术语表、检查工具、发布说明集中管理，方便测试、回滚、发布和收集反馈。

## 当前范围

计划纳入：

- Muv-Luv Unlimited: THE DAY AFTER TDA00
- Muv-Luv Unlimited: THE DAY AFTER TDA01
- Muv-Luv Unlimited: THE DAY AFTER TDA02
- Muv-Luv Unlimited: THE DAY AFTER TDA03
- Muv-Luv photonflowers
- Muv-Luv photonmelodies
- 帝都燃烧篇

## 当前状态

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| TDA01 | 迭代中 | 已在其他对话继续修正，发布前需同步最新成果 |
| TDA02 | 测试中 | 已生成 `beta0.1` 测试包 |
| TDA03 | 制作 / 核对中 | 仍需继续逐条核对和实机反馈 |
| 其他作品 | 计划中 | 等 TDA 工作稳定后再展开 |

## 下载方式

正式面向玩家的 zip 补丁不要直接放进 Git 仓库本体，建议放在 GitHub Releases 和百度网盘镜像。

当前本地测试包位于：

- `dist/MuvLuv_TDA02_CN_Patch_beta0.1.zip`

## 项目结构

- `handoff/`：给新对话接手使用的规则、路径、章节上下文。
- `chapters/`：每个章节 / 作品的状态、已知问题、发布记录。
- `release-notes/`：每次发布用的说明文本。
- `outputs/tda_text/*_deepseek_full.csv`：当前修正源 CSV。
- `outputs/glossary/`：术语表和专有名词表。
- `work/`：审计、打包、核对脚本。
- `tools/`：egpack / fpd / 字体相关辅助工具。

## 工作原则

- 只以日文原文字幕 / 日文 speaker 原文为依据。
- 不使用英文槽作为翻译依据。
- 不恢复英文兜底写回。
- JP 原文槽为空时，不能直接判定游戏一定不显示，必须核对实际显示槽 / egpack。
- 修改后要同步源 CSV、repack、当前游戏缓存和需要发布的压缩包。
- 每次发布前必须做残留扫描和显示文本审计。

更多规则见：

- `handoff/SHARED_RULES.md`
- `handoff/PROJECT_FILES.md`
- `handoff/TOOLS_AND_CHECKS.md`

## 致谢

特别感谢“主任保护协会”提供 AGES 引擎汉化思路，并允许在发布时注明感谢。

也感谢所有提供截图、术语建议、错字反馈和实机测试的玩家。

## 免责声明

本项目不包含游戏本体，不提供破解，不修改 exe，不修改 Steam 原始游戏文件，不操作存档。

制作者本人不懂日语，当前版本未经过完整日中人工校对，可能仍存在错译、错字、术语不统一、说话人错位、空字幕、缺字或 Text ID Not Found 类问题。欢迎带截图和上下文反馈。
