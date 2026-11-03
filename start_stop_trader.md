
📋 OANDA v7 交易机器人 — 操作速查手册 Cheatsheet

# Forex OANDA v7 — 操作速查手册

> 项目路径: `/home/qili/projects/forex_oanda_v7`
> 更新: 2026-10-30

## 📁 目录结构

forex_oanda_v7/
├── config/
│ ├── run.env ← 默认 / 当前配置
│ ├── run.env_original ← 基准平衡版
│ ├── run.env_aggressive ← 激进高机会版
│ ├── run.env_conservative ← 保守稳健版
│ └── run.env_compares.md ← 参数差异说明
├── logs/
│ ├── original/ ← 基准版日志
│ ├── aggressive/ ← 激进版日志
│ ├── conservative/ ← 保守版日志
│ └── all/
├── pids/ ← 运行时 PID 文件 (自动生成)
├── start_trader.sh ← 启动脚本 ✅
├── stop_trader.sh ← 停止脚本 ✅
└── status_trader.sh ← 状态查看 ✅
plaintext

## 🚀 启动命令

### 单独启动

```bash
# 基准平衡版
./start_trader.sh original

# 激进版 — 更多机会、更高频率
./start_trader.sh aggressive

# 保守版 — 少而稳、低回撤
./start_trader.sh conservative
一键同时运行三个（独立账号 / 日志 / 风控，互不干扰）
bash
# Dry-run 试运行（不真实发单）
./start_trader.sh all --dry-run

# 正式运行（启用 --live 阈值）
./start_trader.sh all --live
可选参数（附加在命令末尾）
Table
参数	作用
--dry-run	仅跑信号、不发单，安全测试
--live	启用 live 筛选阈值 (MIN_GAP/ALIGN/CORE 等)
⏹️ 停止命令
bash
# 停单个
./stop_trader.sh aggressive
./stop_trader.sh original
./stop_trader.sh conservative

# 一键停全部
./stop_trader.sh all
📊 查看状态与日志
状态总览
bash
./status_trader.sh
# 输出: 运行状态 / PID / 启动时长 / 最新日志文件
实时跟踪日志
bash
# 单个模式
tail -f logs/aggressive/runner_*.log
tail -f logs/original/runner_*.log
tail -f logs/conservative/runner_*.log

# 同时看全部
tail -f logs/*/runner_*.log
历史日志
bash
ls -lah logs/aggressive/
less logs/original/runner_20261030_140022.log
⚙️ 三套配置对照
Table
维度	🔴 激进	🟢 基准	🔵 保守
信号概率门槛	0.52/0.48（易触发）	0.55/0.45	0.62/0.38（严筛选）
单轮最大入场	8	6	3
外汇持仓上限	8	6	3
加密持仓上限	3	2	1
组筛选分数	30（宽松）	40	55（严格）
ATR 止损 / 止盈 (外汇)	1.5/1.5（紧）	1.8/1.8	2.5/2.8（宽）
适用场景	高波动、抓机会、高风险承受	平衡默认	稳健、低频率、可控回撤
账号 ID	各自独立配置在 run.env_*	各自独立	各自独立
🔧 配置修改流程
编辑对应文件：config/run.env_aggressive
重启生效：
bash
./stop_trader.sh aggressive
./start_trader.sh aggressive --live
验证状态：./status_trader.sh → 确认 PID 更新
查看日志：确认无报错、参数已加载
⚠️ 常见问题
Q: 提示已在运行？
bash
# 强制清理残留PID后重启
rm -f pids/aggressive.pid
./start_trader.sh aggressive
Q: 如何临时对比两种配置效果？
用 --dry-run 并行跑同一账号不同配置，观察信号差异
或直接跑 all 模式（demo 账号），对比日志里的下单频率 / 质量
Q: 生产环境建议
先用 --dry-run 跑 24–48h 验证参数
确认后再上 --live
三套配置建议分账号运行，避免资金冲突
定期归档日志目录，避免占用过大空间
📌 快速参考
bash
# 记忆口诀
./start_trader.sh [original|aggressive|conservative|all] [--dry-run] [--live]
./stop_trader.sh [mode|all]
./status_trader.sh
tail -f logs/[mode]/runner_*.log
plaintext

---

## ✅ 最终交付清单
- ✅ `status_trader.sh` — 一键查看三套运行状态/PID/时长/日志
- ✅ `CHEATSHEET.md` — 完整操作手册，直接查阅
- ✅ 之前已交付：`start_trader.sh` + `stop_trader.sh`

全部保存后执行一次授权：
```bash
chmod +x start_trader.sh stop_trader.sh status_trader.sh
现在直接用 ./status_trader.sh 就能看到三个实例的运行状态了。
需要我帮你把这三个脚本和手册一次性打包成可直接拉取 / 覆盖的压缩包或部署命令吗？
```
