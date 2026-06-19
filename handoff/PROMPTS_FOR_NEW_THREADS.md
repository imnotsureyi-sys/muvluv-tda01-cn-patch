# 新对话开场白模板

下面模板可以直接复制到新对话。每个章节对话都必须先读交接文件，再切到自己的章节分支。

## 通用总说明

```text
这是 Muv-Luv Series Steam 版简体中文补丁项目。

项目目录：
C:\Users\Administrator\Documents\Muv-LuvSeries汉化

GitHub 总库：
https://github.com/imnotsureyi-sys/muvluv-series-steam-cn-patch

总原则：
1. 只以日文原文字幕 / 日文 speaker 原文为依据。
2. 不使用英文槽作为翻译依据。
3. 不恢复英文兜底写回。
4. JP 原文槽为空时，不能直接判断游戏一定不显示，必须核对实际 egpack / 当前显示槽。
5. 修改后要同步源 CSV、repack、当前游戏缓存和测试包。
6. zip 补丁包不要提交进 Git，之后作为 GitHub Release 附件或百度网盘文件发布。
7. 如果 git status 显示已有未提交修改，先停下来告诉用户，不要覆盖、不要 reset、不要 checkout 丢弃。

开始前必须先读：
- handoff/SHARED_RULES.md
- handoff/PROJECT_FILES.md
- handoff/TOOLS_AND_CHECKS.md
- handoff/BRANCH_WORKFLOW.md
- 对应章节的 handoff/TDA01_CONTEXT.md 或 TDA02_CONTEXT.md 或 TDA03_CONTEXT.md

分支规则：
- TDA01 只用 chapter/tda01
- TDA02 只用 chapter/tda02
- TDA03 只用 chapter/tda03
- 不要直接推 main
- 不要修改其他章节文件，除非用户明确要求

开始工作时执行：
git status --short

如果工作区干净，再切到对应分支并拉取：

TDA01:
git switch chapter/tda01
git pull origin chapter/tda01

TDA02:
git switch chapter/tda02
git pull origin chapter/tda02

TDA03:
git switch chapter/tda03
git pull origin chapter/tda03

修完后检查：
git status --short
git diff --stat

然后只提交对应章节相关文件。

TDA01:
git add outputs/tda_text/tda01_deepseek_full.csv chapters/TDA01 handoff work tools outputs/glossary release-notes CHANGELOG.md
git commit -m "Update TDA01 fixes"
git push origin chapter/tda01

TDA02:
git add outputs/tda_text/tda02_deepseek_full.csv chapters/TDA02 handoff work tools outputs/glossary release-notes CHANGELOG.md
git commit -m "Update TDA02 fixes"
git push origin chapter/tda02

TDA03:
git add outputs/tda_text/tda03_deepseek_full.csv chapters/TDA03 handoff work tools outputs/glossary release-notes CHANGELOG.md
git commit -m "Update TDA03 fixes"
git push origin chapter/tda03

注意：
同一个本地目录不要让多个对话同时写文件。最好一次只让一个章节对话实际修改；其他对话可以先分析截图、列问题。
章节对话推完分支后，回到总库对话合并进 main、打包、发 Release。
```

## TDA01 对话

```text
这是 Muv-Luv Series Steam 版简体中文补丁项目的 TDA01 专用对话。

项目目录：
C:\Users\Administrator\Documents\Muv-LuvSeries汉化

请先读取并遵守：
- handoff/SHARED_RULES.md
- handoff/PROJECT_FILES.md
- handoff/TOOLS_AND_CHECKS.md
- handoff/BRANCH_WORKFLOW.md
- handoff/TDA01_CONTEXT.md

只处理 TDA01，不要修改 TDA02/TDA03。
开始前执行 git status --short。如果已有未提交修改，先停下来告诉用户，不要覆盖、不要 reset、不要 checkout 丢弃。
工作区干净后执行：
git switch chapter/tda01
git pull origin chapter/tda01
严格以日文原文槽为准，不使用英文槽，不恢复英文兜底。
```

## TDA02 对话

```text
这是 Muv-Luv Series Steam 版简体中文补丁项目的 TDA02 专用对话。

项目目录：
C:\Users\Administrator\Documents\Muv-LuvSeries汉化

请先读取并遵守：
- handoff/SHARED_RULES.md
- handoff/PROJECT_FILES.md
- handoff/TOOLS_AND_CHECKS.md
- handoff/BRANCH_WORKFLOW.md
- handoff/TDA02_CONTEXT.md

只处理 TDA02，不要修改 TDA01/TDA03。
开始前执行 git status --short。如果已有未提交修改，先停下来告诉用户，不要覆盖、不要 reset、不要 checkout 丢弃。
工作区干净后执行：
git switch chapter/tda02
git pull origin chapter/tda02
严格以日文原文槽为准，不使用英文槽，不恢复英文兜底。
```

## TDA03 对话

```text
这是 Muv-Luv Series Steam 版简体中文补丁项目的 TDA03 专用对话。

项目目录：
C:\Users\Administrator\Documents\Muv-LuvSeries汉化

请先读取并遵守：
- handoff/SHARED_RULES.md
- handoff/PROJECT_FILES.md
- handoff/TOOLS_AND_CHECKS.md
- handoff/BRANCH_WORKFLOW.md
- handoff/TDA03_CONTEXT.md

只处理 TDA03，不要修改 TDA01/TDA02。
开始前执行 git status --short。如果已有未提交修改，先停下来告诉用户，不要覆盖、不要 reset、不要 checkout 丢弃。
工作区干净后执行：
git switch chapter/tda03
git pull origin chapter/tda03
严格以日文原文槽为准，不使用英文槽，不恢复英文兜底。
```

## 回到总库对话

```text
这是 Muv-Luv Series Steam 版简体中文补丁项目的总库对话。

项目目录：
C:\Users\Administrator\Documents\Muv-LuvSeries汉化

请先读取：
- README.md
- RELEASE_PROCESS.md
- handoff/BRANCH_WORKFLOW.md
- handoff/PROJECT_FILES.md

负责合并章节分支、检查发布说明、打包、tag 和 GitHub Release。
```
