# AstrBot Muv-Luv Feedback Plugin

用于 QQ 群内收集 Muv-Luv 汉化反馈，并基于 TDA00-03 原始 JP/CN compare 表定位章节、id、egpack、scene、speaker、JP 原文和当前 CN。

## 触发方式

- `/反馈`：强制进入反馈流程，可附图或文本。
- `@机器人 + 图片`：自动 OCR 图片并尝试定位；普通未 @ 的图片不会触发。
- `@机器人 + 图片 + 文字`：图片为主，文字只用于聚焦图片中的某一句，例如“停车场对吗”。

## 模型分流

- 普通聊天建议在 AstrBot 全局配置中使用 `deepseek/deepseek-v4-flash`。
- 翻译反馈判定由插件的 `review_provider_id` 控制，默认使用 `deepseek/deepseek-v4-pro`。
- 图片 OCR 继续使用 AstrBot 的图片描述模型，或配置 `vision_provider_id`。

## 数据源

默认读取：

- `C:/Users/Administrator/Desktop/TDA00_03_latest_compare_tables/TDA00_JP_CN_COMPARE_utf8bom_2026.6.23.csv`
- `C:/Users/Administrator/Desktop/TDA00_03_latest_compare_tables/TDA01_JP_CN_COMPARE_utf8bom_2026.6.23.csv`
- `C:/Users/Administrator/Desktop/TDA00_03_latest_compare_tables/TDA02_JP_CN_COMPARE_utf8bom_2026.6.23.csv`
- `C:/Users/Administrator/Desktop/TDA00_03_latest_compare_tables/TDA03_JP_CN_COMPARE_utf8bom_2026.6.23.csv`

这些表包含 `call_order, id, egpack, scene, speaker_jp, jp_text, cn_text, review_status, audit_flags`。ParaTranz ID 按 `章节起点 + call_order - 1` 计算。

## 判定规则

模型判定时只使用 JP 原文和日文上下文作为语义依据，不使用英文槽或旧中文兜底。判定会额外参考：

- 发言人 `speaker_jp`
- 前后文 JP/CN
- scene / egpack
- 人物资料表
- 人物关系表
- 场景资料表
- 术语表

确定错误且建议 CN 明确时，插件会直接更新 compare 表的 `cn_text`，并把 `review_status` 标为 `FIXED_BY_FEEDBACK`。不确定时不改 CN，只把 `review_status` 标为 `QUESTION`。

## 工作表

插件会在 AstrBot 的 `plugin_data/astrbot_plugin_muvluv_feedback` 下维护：

- `line_catalog.csv`：台词主表，含 `paratranz_id`、QQ 反馈检查状态、ParaTranz 疑问检查状态。
- `feedback_queue.csv`：群友反馈队列。
- `feedback_resolution_table.csv`：已处理反馈记录表。若 key、文件、JP/CN 对上，机器人会返回“已处理过”或“疑问”及具体内容。
- `paratranz_sync_tasks.csv`：ParaTranz 同步任务表。确定修改生成 `update_translation`；不确定生成 `mark_question`。
- `speaker_profiles.csv`：人物资料表，可补充性格、语气、说话风格、翻译注意。
- `scene_contexts.csv`：场景资料表，可补充故事梗概、地点、氛围、当前情景。
- `speaker_relationships.csv`：人物关系表。

命令 `/反馈工作表` 可查看这些文件路径。
