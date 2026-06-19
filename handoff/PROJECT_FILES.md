# 项目文件位置

项目根目录：

`C:\Users\Administrator\Documents\Muv-LuvSeries汉化`

## 源 CSV

当前主要修正源文件：

- `outputs\tda_text\tda01_deepseek_full.csv`
- `outputs\tda_text\tda02_deepseek_full.csv`
- `outputs\tda_text\tda03_deepseek_full.csv`

这些 CSV 是后续修正优先写入的位置。不要只改缓存或只改 repack。

## 术语表

- `outputs\glossary\muvluv_lunatranslator_full_glossary.csv`
- `outputs\glossary\muvluv_lunatranslator_proper_nouns.tsv`
- `outputs\glossary\muvluv_world_glossary_sources.md`

新增固定术语时，优先同步到这些术语表。

## 当前最新 repack 基准

TDA01 当前另一个对话在迭代，接手前必须先确认那边最新版本。

TDA02 当前基准：

- `outputs\repack_tda02_xmlsafe_20260617o`
- 当前测试包：`dist\MuvLuv_TDA02_CN_Patch_beta0.1.zip`

TDA03 当前基准：

- `outputs\repack_tda03_xmlsafe_20260617o`

## 当前游戏缓存路径

TDA01：

`%LOCALAPPDATA%\ancr\tda01\data\root\assets\data_spec\adv\game\scr\localized`

TDA02：

`%LOCALAPPDATA%\ancr\tda02\data\root\assets\data_spec\adv\game\scr\localized`

TDA03：

`%LOCALAPPDATA%\ancr\tda03\data\root\assets\data_spec\adv\game\scr\localized`

如果用户要马上进游戏验证，除了 CSV / repack，还要同步当前缓存。

## 打包输出

- `dist\MuvLuv_TDA01_CN_Patch_beta0.1.zip`
- `dist\MuvLuv_TDA02_CN_Patch_beta0.1.zip`
- `dist\MuvLuv_TDA03_CN_Patch_beta0.1.zip`

注意：TDA02 的 beta0.1 是最新重新打过的包。TDA01 已由另一个对话继续迭代，打包前要先核对当前最新 TDA01 状态。

## 已归档旧脚本

旧脚本多数已移到：

`work_archive_20260617`

不要随便从归档目录恢复旧替换脚本。特别注意：旧的安全重建脚本曾出现会把新术语改坏的替换规则，已经删除，不要恢复。

