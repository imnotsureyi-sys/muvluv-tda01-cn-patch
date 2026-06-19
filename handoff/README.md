# Muv-Luv TDA 汉化项目交接入口

这个目录用于新对话接手工作。新对话不要只依赖聊天记忆，先读这里的文件，再处理对应章节。

## 建议开三个新对话

1. TDA01 专用对话：只处理 TDA01 的玩家反馈、修正、重新打包。
2. TDA02 专用对话：只处理 TDA02 的玩家反馈、修正、重新打包。
3. TDA03 专用对话：只处理 TDA03 的逐条核对、玩家反馈、重新打包。

每个新对话开头建议直接贴对应文件内容：

- `handoff/TDA01_CONTEXT.md`
- `handoff/TDA02_CONTEXT.md`
- `handoff/TDA03_CONTEXT.md`

同时让新对话先读：

- `handoff/SHARED_RULES.md`
- `handoff/PROJECT_FILES.md`
- `handoff/TOOLS_AND_CHECKS.md`

## 当前项目根目录

`C:\Users\Administrator\Documents\Muv-LuvSeries汉化`

## 最重要原则

- 翻译、修正、说话人表都只能以日文原文槽为依据。
- 不要把英文槽当原文，不要恢复英文兜底。
- JP 原文槽为空时，不能简单判断“游戏一定不显示”；要先核对游戏实际显示槽 / egpack 当前内容。
- 修改后要同步到源 CSV、最新 repack 输出、当前游戏缓存、需要发布的压缩包。
- 打包前必须跑审计，至少确认没有 `Text ID Not Found`、旧术语、错说话人、明显空文本。

