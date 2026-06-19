# 分章节分支工作流

总库主分支：

- `main`

章节工作分支：

- `chapter/tda01`
- `chapter/tda02`
- `chapter/tda03`

## 总原则

1. `main` 只做总库、发布说明、最终确认。
2. 每个章节对话只在自己的章节分支工作。
3. 章节对话不要随便改其他章节的 CSV。
4. 章节对话完成一轮修正后提交 commit。
5. 回到总库对话合并、打 tag、发布 Release。

## 单工作目录注意

当前项目只有一个工作目录：

`C:\Users\Administrator\Documents\Muv-LuvSeries汉化`

如果三个对话同时写同一个目录，会互相影响。

最稳方式：

- 同一时间只让一个章节对话进行实际文件修改。
- 另两个对话可以先分析截图、列问题，但不要同时写文件。

如果之后确实要三个对话同时改文件，可以再建立 Git worktree 独立工作目录。

## 章节对话开始时

TDA01 对话：

```powershell
git switch chapter/tda01
```

TDA02 对话：

```powershell
git switch chapter/tda02
```

TDA03 对话：

```powershell
git switch chapter/tda03
```

切换分支前必须确认当前工作区没有未提交修改：

```powershell
git status --short
```

## 章节对话结束时

先查看修改：

```powershell
git status --short
git diff --stat
```

确认后提交：

```powershell
git add outputs/tda_text chapters handoff work tools outputs/glossary release-notes README.md CHANGELOG.md RELEASE_PROCESS.md
git commit -m "Update TDA02 fixes"
```

提交信息按章节改：

- `Update TDA01 fixes`
- `Update TDA02 fixes`
- `Update TDA03 fixes`

## 回到总库

总库对话合并章节分支：

```powershell
git switch main
git merge chapter/tda02
```

如果要上传 GitHub：

```powershell
git push origin main
git push origin chapter/tda02
```

## 发布 tag

示例：

```powershell
git tag tda02-beta0.1
git push origin tda02-beta0.1
```

zip 包仍然通过 GitHub Release 附件上传，不提交进 Git。

