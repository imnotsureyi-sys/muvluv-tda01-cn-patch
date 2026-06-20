# 提交和版本规则

本项目采用：

```text
commit = 每次完成一个明确改动就记录
version = 准备发给玩家测试/公开发布时才升级
```

## Commit 规则

每次修完一组明确问题后都要提交。提交信息必须说明章节和改动内容。

推荐格式：

```text
TDA03: fix JFK HIVE terminology
TDA03: shorten overlong dialogue lines
TDA02: fix Tsukuyomi speaker rank
TDA00: audit batch 006 against JP baseline
Glossary: add Black Knives terminology
Tools: improve JP baseline audit
Docs: update patch workflow
```

不要使用含糊提交信息：

```text
fix
update
misc
改一下
```

## 每次章节修补的提交条件

提交前至少确认：

- 改动只属于当前章节或共通文档/工具。
- 没有误改其他章节正文。
- `git diff --stat` 范围合理。
- 如果修的是游戏文本，已经同步源 CSV。
- 如果用户正在实机测试，已经同步当前游戏缓存。
- 如果打包，zip 自检通过。
- 如果有审计脚本，已跑本轮对应审计。

## 版本规则

版本只在发包/给玩家测试/公开发布时升级。

每个章节独立版本，不强行使用全项目统一版本。

示例：

```text
tda00-beta0.1.0
tda01-beta0.2.2
tda02-beta0.1.0
tda03-beta0.1.0
```

## 版本号含义

```text
beta0.1.0 = 第一个公开测试版
beta0.1.1 = 小修补版，修错字、术语、少量台词、宽度问题
beta0.2.0 = 大范围更新，例如重校、重抽 JP、修大量错位、覆盖新段落
1.0.0 = 基本完整、通关验证、主要问题清完
```

## Release tag 规则

Git tag 使用：

```text
tda00-beta0.1.0
tda01-beta0.2.2
tda02-beta0.1.0
tda03-beta0.1.0
```

GitHub Release 附件放 zip，不把 zip 提交进 Git。

## 分支规则

章节对话只提交到自己的章节分支：

```text
chapter/tda00
chapter/tda01
chapter/tda02
chapter/tda03
```

main 负责合并和发布。
