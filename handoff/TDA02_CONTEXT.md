# TDA02 新对话上下文

## 当前状态

TDA02 用户已经自己游玩并修过一遍，当前项目已生成测试包：

`dist\MuvLuv_TDA02_CN_Patch_beta0.1.zip`

当前主要源文件：

`outputs\tda_text\tda02_deepseek_full.csv`

当前最新 repack：

`outputs\repack_tda02_xmlsafe_20260617o`

当前缓存路径：

`%LOCALAPPDATA%\ancr\tda02\data\root\assets\data_spec\adv\game\scr\localized`

## 已修复并确认的 TDA02 问题

- `game_s00069`：`月詠中尉` -> `月咏中尉`，修掉 `月咏少尉`。
- `game_t02127`：`对美关系值也会提升……`
- `game_t02211`：`你说……什么……！？`
- `game_t02216`：`突击光线级……！？`
- `game_t02226`：`支援第1中队对光线级的突击`
- `game_t00902`：`可怜是个什么样的人呢？`
- `game_t03151`：`大上中尉所认识的可怜`
- `game_t03657-03679`：接待会 / 合成食材段错位已按 JP 修正。
- `game_t05953`：`西北偏北15公里外，似乎正在交战――！`
- `game_t06100`：`那个大笨蛋！！！又让他干成了——！`
- `game_t06231`：`殿下赌上自身安危作出的英明决断`
- `game_t06286`：加拿大新自由党政治报告句已重写顺序。
- `ユズちゃん` 相关称呼统一为 `柚酱`。
- `ボクサー` 固定为 `拳师号`。
- `イーグル` 固定为 `鹰`。
- `フェザント` 固定为 `雉鸡`。
- `クレイン` 固定为 `鹤`。
- speaker 表多人分隔符用 `·`，不是 `・` 或 `&`。

## 最近一次验证

最终 TDA02 beta0.1 包检查结果：

- zip 自检通过，`testzip=None`。
- payload 内 `Text ID Not Found`：0。
- payload 内 `月咏少尉`：0。
- payload 内 `博克瑟 / Boxer / 拳击手`：0。
- payload 内 `伊格尔`：0。
- payload 内 `克莱因 / 克莱恩 / 克雷因`：0。
- payload 内 `小柚 / 小由 / 柚香酱 / 柚子酱`：0。
- payload 内 `北北西 / 混帐混蛋 / 自身的英断`：0。
- speaker 表 `・ = 0`、`& = 0`、`· = 20`。
- repack 审计：`missing=0 / mismatch=0 / text_id_not_found=0`。

## 后续处理建议

新对话只处理用户继续反馈的 TDA02 截图 / ID。

每次修正流程：

1. 用截图文本 / ID / 日文原文定位 CSV 行。
2. 对照 JP 原文和上下文决定中文。
3. 修改 `outputs\tda_text\tda02_deepseek_full.csv`。
4. 同步到 `outputs\repack_tda02_xmlsafe_20260617o`。
5. 如果用户要立刻游戏验证，同步到 TDA02 当前缓存。
6. 重新审计并打包。

