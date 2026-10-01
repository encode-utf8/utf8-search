# `scripts/recall_ab.py` 使用说明（受控回放）

- 脚本：`scripts/recall_ab.py`（2026-10-01 从 `data/measure/p7-recall-20260930/recall_ab.py` 移入仓库；
  `data/` 被 gitignore，放在那里脚本会丢）
- 用途：P7 轮为量化「`drop_stale=True`（P5）会不会伤召回」而写的对照工具；
  现在同时作为**受控回放**模板 —— 同一批 20 条 2-9 查询、单并发、强制禁缓存，输出逐条**返回结果条数**的 before/after 对照。
- 用法（仓库根目录）：

  ```bash
  .venv/bin/python scripts/recall_ab.py
  ```

- 前提与代价：需要 `.env` 里 `UTF8SEARCH_SEARXNG_URL` 指向的 SearXNG 可达；
  共 **40 次上游请求**（20 查询 × before/after 两遍），单并发、`cache_enabled=False`；只读、不改配置、不写产品数据。
- 输出：stdout 对照表（`# / 是否命中时间意图 / before / after / delta / 查询`）+ 汇总行；
  明细 JSON 落在 `data/recall-ab.json`（gitignored 的工作副本，报告引用 stdout 表）。
- 首次运行结果引用：`docs/reports/20260930-p7-ranking-followups.md`（P7 轮：命中时间意图 8 条、条数下降 0 条、合计 100 → 100）。
- 注意：本脚本是"条数"维度的回放；"相关性"维度的采样用 `scripts/relevance.py`，
  采样次数与摆动区间见 `docs/reports/m2-9-sampling-variance-20261001.md`。
