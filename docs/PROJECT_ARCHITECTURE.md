# Muv-Luv Series 汉化项目架构

本项目采用“总库 main + 分章节 worktree”的结构。

## 目标

`main` 不直接承载某一章的日常修补工作。它负责保存共通知识、共通工具、共通流程和发布入口。

各章节只在自己的分支和工作区里处理自己的文本、截图反馈、缓存、测试包和审计报告。章节之间只有在需要同步术语、工具或发布结果时才联动。

## main 总库负责

- Muv-Luv 世界观专有名词表
- 术语确认记录
- ATE 补丁分析总结
- 从零制作汉化补丁的方法
- JP baseline 审计方法
- DeepSeek / Codex 翻译校对流程
- 共通工具脚本
- Git / GitHub / Release 规则
- README、发布入口和下载链接

main 不负责某一章的日常截图修 bug，也不长期保存某一章的大量 repack 缓存、测试包和临时输出。

## 章节分支负责

每个章节只管理自己的内容：

- `chapter/tda00`
- `chapter/tda01`
- `chapter/tda02`
- `chapter/tda03`

以后可以增加：

- `chapter/photonflowers`
- `chapter/photonmelodies`
- `chapter/teito`

章节分支负责本章 JP baseline、翻译表、截图反馈、审计报告、测试包说明和 release notes。

## 推荐 worktree 布局

主目录只做总控：

```text
C:\Users\Administrator\Documents\Muv-LuvSeries汉化
```

章节工作建议放在独立 worktree：

```text
C:\Users\Administrator\Documents\Muv-LuvSeries汉化-worktrees\tda00
C:\Users\Administrator\Documents\Muv-LuvSeries汉化-worktrees\tda01
C:\Users\Administrator\Documents\Muv-LuvSeries汉化-worktrees\tda02
C:\Users\Administrator\Documents\Muv-LuvSeries汉化-worktrees\tda03
```

每个 Codex 对话只绑定自己的章节 worktree。不要让多个章节对话同时写同一个 checkout。

## 术语同步规则

1. 章节对话发现新专有名词时，先写入本章的待确认表。
2. 用户确认译法后，更新 main 的共通术语表。
3. 其他章节需要时，从 main 同步术语表。
4. 章节对话不得为了统一术语直接修改其他章节正文。

## 互相联动的正确方式

可以做：

- TDA01 发现“黑刃”，去查 TDA02/TDA03 是否一致。
- TDA03 发现新舰名，提交到 main 术语表。
- main 更新流程后，各章节同步工具和规则。

不要做：

- TDA01 对话直接改 TDA02 的 CSV。
- TDA03 修 bug 时顺手重写 TDA00 翻译表。
- 多个对话同时在主目录生成大量输出文件。

## 内存风险规则

为避免 Codex/Git 状态轮询反复扫盘：

- 主目录不要同时承载多个章节的未跟踪大文件。
- `dist/`、`outputs/repack_*`、`workspace_full_copy_*`、zip 解包目录不进入 Git。
- 大量翻译中间产物只保留在对应章节 worktree。
- 一个章节在跑全量翻译/打包时，不要让另一个章节在同一个 checkout 里改文件。
