
# Forex OANDA Bot v7x

AI-powered automated trading bot for OANDA — LightGBM + TCN + GARCH + Drift Monitoring

## Quick Start

1. cp config/.env.example config/.env
2. nano config/.env  # Fill OANDA_TOKEN, ACCOUNT_ID
3. chmod +x deploy.sh
4. ./deploy.sh init
5. ./deploy.sh train
6. ./deploy.sh daemon

## 总控命令 (deploy.sh)

| 命令 | 说明 |
|---|---|
| `./deploy.sh init` | 完整安装（依赖 + 目录 + .env 模板） |
| `./deploy.sh deps` | 重装 Python 依赖 |
| `./deploy.sh train` | 前台训练全部货币对（耗时较长，Ctrl-C 可中断，已完成模型保留） |
| `./deploy.sh start` | 前台运行主循环 |
| `./deploy.sh daemon` | 后台同时启动：**主循环 + 周守护** |
| `./deploy.sh stop` | 同时停止两个进程 |
| `./deploy.sh restart` | 重启两个进程 |
| `./deploy.sh status` | 显示双进程状态 + 模型上次更新时间 |
| `./deploy.sh retrain-now` | 立即执行一次全量重训（应急） |

日/周训练分离：**主循环只做交易**（拉K线→特征→预测→风控→下单），**周守护**（`weekly_train_daemon.py`）独立进程按 `config/config.yaml` 的 `lgb.retrain_interval_days`（默认 7 天）增量更新模型，互不阻塞。

## 目录结构（按环境隔离）

```
data/
  practice/datasets/     # practice 拉取的 K 线
  live/datasets/         # live 拉取的 K 线（切换后自动生成）
  common/                # 跨环境通用参考数据（预留）
models/model_store/
  practice/              # practice 模型 lgb_*.pkl / tcn_*.pkl
  live/                  # live 模型
reports/
  bot.pid                # 主交易进程 PID
  weekly_train.pid       # 周守护进程 PID
  bot.log                # 交易日志
  weekly_train.log       # 训练日志
  .last_weekly_retrain   # 模型上次更新时间戳
```

## 启动参数 (main_loop_v2.py)

主循环通过命令行选择环境 / 账号 / 手数（`deploy.sh start|daemon|restart` 会透传参数）：

| 参数 | 说明 |
|---|---|
| `--live` | 切换到 live 实盘账号（无简写）；**不带则一律 demo** |
| `--account N` / `-a N` | 选择账号序号 N（1-based）：`--live` 对应 live 账号，否则对应 demo 账号 |
| `--lots N` | 下单手数 N（以 unit 计，非合约金额）；缺省读 `config/run.env` 的 `DEMO_LOT_SIZE`/`LIVE_LOT_SIZE`（demo 10000 / live 1） |
| `--dry-run` | 空跑模式：正常跑完整流程（拉K线→特征→预测→风控），但**不下单/平仓/改单**（不向 OANDA 发送任何订单） |

市场停牌（HALT）：主循环每轮会实时查询 OANDA 报价的 `tradeable` 状态；当市场停牌/休市
（周末、假期、HALT）时，该货币对当轮跳过并打 tag=`market_halt`，动作限制与 `--dry-run` 一致。

```bash
python main_loop_v2.py                        # demo 账号 1，手数取 DEMO_LOT_SIZE
python main_loop_v2.py -a 5                   # demo 账号 5
python main_loop_v2.py --live -a 2 --lots 1   # 实盘账号 2，手数 1
python main_loop_v2.py --dry-run              # 空跑（不下单/平仓）
./deploy.sh daemon --live -a 2                # 后台实盘账号 2
```

- live / demo 使用**各自独立**的 TOKEN（`OANDA_API_TOKEN_LIVE` / `OANDA_API_TOKEN`），
  由 `--live` 决定，不会错用。
- 环境同时决定数据/模型目录与日志：`data/<env>/datasets`、`models/model_store/<env>`、
  `logs/profile_<env>.jsonl`。

## 环境切换 (practice / live)

- **主循环**：由 `--live` 决定（见上），无需改配置文件。
- **周守护 `weekly_train_daemon.py`**：无 CLI 开关，仍读取 `config/run.env` 的 `OANDA_ENV`。
  若要让周守护按 live 训练，把 `config/run.env` 的 `OANDA_ENV` 改为 `live` 后 `./deploy.sh restart`。
- 目录随环境自动切换：
  - `practice` → `data/practice/datasets` + `models/model_store/practice`
  - `live` → `data/live/datasets` + `models/model_store/live`

> ⚠️ **首次切到 live 会缺数据**：`data/live/` 与 `models/model_store/live/` 初始为空，
> 属正常现象。两条路径任选其一：
> - **正常积累**：直接启动，主循环会自动拉取并补训缺失模型（见下方「首次启动」）
> - **冷启动迁移**：用迁移脚本把 practice 历史拷到 live（见下节）

## 迁移脚本 (practice → live 冷启动)

把 practice 的历史 K 线与模型复制到 live 目录，供实盘模型冷启动：

```bash
./tools/migrate_data_to_live.sh
```

- **作用**：复制 `data/practice/datasets/*` → `data/live/datasets/`，`models/model_store/practice/*` → `models/model_store/live/`，并把 `config.yaml` 的 `data.allow_practice_for_live` 置为 `true`
- **风险**：practice 数据 ≠ 实盘表现（点差 / 滑点 / 交易深度 / 更新延迟均不同）
- **确认机制**：执行前打印风险横幅，需手动输入大写 `YES` 才继续；取消则不做任何改动
- **边界处理**：拷贝前检查磁盘空间（不足即中止）；目标文件已存在时逐个询问 `[S]kip / [O]verwrite / [A]ll`
- **`data.allow_practice_for_live` 标志位含义**：是否允许 live 环境使用 practice 迁移来的数据。默认 `false`（严格隔离）；迁移脚本会自动置为 `true`。若想重新隔离，手动改回 `false`

> ⚠️ **迁移 ≠ 实盘效果**：迁移数据仅用于冷启动，不代表实盘表现。
> 上实盘前请先跑 **至少 2–4 周原生 live 数据**再评估模型是否可用。

## 首次启动

- 当前 `config/forex_pairs.yml` 共 **29 对**；若本地只有 **27 套**完整模型（`CAD_NZD`、`CHF_NZD` 缺失），
  首次启动会**自动补训**缺失的货币对，训练完成后才进入交易循环，无需手动干预
- **周守护**（`weekly_train_daemon.py`）默认每 **7 天**（`lgb.retrain_interval_days`）对全部货币对执行一次全量增量更新
- 日志位置：
  - `reports/bot.log` — 主交易日志（进程前台输出另见 `reports/bot_console.out`）
  - `reports/weekly_train.log` — 周度训练日志（进程前台输出另见 `reports/weekly_console.out`）
  - `reports/.last_weekly_retrain` — 模型上次更新时间戳

