# 发布流程

这个项目采用“总库 + 分章节工作对话”的方式。

## 分工

总库对话负责：

- 总 README
- 共通规则
- 术语表
- 工具脚本
- Git / GitHub / Release 管理
- 最终打包前审计

章节对话负责：

- 只处理自己的章节
- 修改对应源 CSV
- 同步对应 repack / 缓存
- 生成测试包
- 提交修改到对应分支

建议分支名：

- `chapter/tda01`
- `chapter/tda02`
- `chapter/tda03`
- `chapter/photonflowers`
- `chapter/photonmelodies`
- `chapter/teito`

## 每次修正流程

1. 根据截图 / ID / 显示文本定位 JP 原文。
2. 严格参考 JP 原文和上下文修改中文。
3. 修改 `outputs/tda_text/*_deepseek_full.csv`。
4. 同步到对应 `outputs/repack_*`。
5. 如果用户要立即实机验证，同步到 `%LOCALAPPDATA%\ancr\...` 当前缓存。
6. 跑审计脚本。
7. 打测试包。
8. 记录改动到对应 `chapters/*/changelog.md`。
9. 提交到对应分支。

## Release tag 命名

- `tda01-beta0.2`
- `tda02-beta0.1`
- `tda03-beta0.1`
- `photonflowers-beta0.1`
- `photonmelodies-beta0.1`
- `teito-beta0.1`

## GitHub Release 附件

zip 补丁包作为 Release 附件上传，不提交进 Git 仓库本体。

示例：

- `MuvLuv_TDA02_CN_Patch_beta0.1.zip`

## 发布前必须检查

- zip 自检通过。
- README 章节名正确。
- 包内有字体 payload。
- payload 内无旧术语残留。
- payload 内无 `Text ID Not Found`。
- speaker 表多人分隔符正确。
- 审计结果为 `missing=0 / mismatch=0 / text_id_not_found=0`，或明确列出未解决风险。

