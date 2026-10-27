
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
| `./deploy.sh train` | 前台训练**全部品种**（8 外汇 + 2 加密，读 `config/forex_pairs.yml`）；耗时较长，Ctrl-C 可中断，已完成的模型保留 |
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
| `--forex` / `-f` | **只**交易外汇（默认） |
| `--crypto` / `-c` | **只**交易加密货币（`BTC_USD`/`ETH_USD`） |
| `--forex-crypto` / `-b` | 外汇与加密**同时**交易 |
| `--crypto-lots N` | 加密下单手数 N（unit 计，支持小数）；缺省读 `config/run.env` 的 `DEMO_LOT_SIZE_CRYPTO`/`LIVE_LOT_SIZE_CRYPTO`（demo 1 / live 0.01） |
| `--dry-run` | 空跑模式：正常跑完整流程（拉K线→特征→预测→风控），但**不下单/平仓/改单**（不向 OANDA 发送任何订单） |

交易品种模式优先级：CLI（`-f`/`-c`/`-b`，三者互斥）> `run.env` 的 `TRADE_MODE` > 代码默认 `forex`。

市场停牌（HALT）：主循环每轮会实时查询 OANDA 报价的 `tradeable` 状态；当市场停牌/休市
（周末、假期、HALT）时，该货币对当轮跳过并打 tag=`market_halt`，动作限制与 `--dry-run` 一致。

```bash
python main_loop_v2.py                        # demo 账号 1，手数取 DEMO_LOT_SIZE
python main_loop_v2.py -a 5                   # demo 账号 5
python main_loop_v2.py --live -a 2 --lots 1   # 实盘账号 2，手数 1
python main_loop_v2.py --crypto               # 只交易加密（BTC_USD/ETH_USD）
python main_loop_v2.py --forex-crypto         # 外汇 + 加密
python main_loop_v2.py -c --crypto-lots 0.01  # 只交易加密，手数覆盖为 0.01
python main_loop_v2.py --dry-run              # 空跑（不下单/平仓）
./deploy.sh daemon --live -a 2                # 后台实盘账号 2
```

### 通过 deploy.sh 后台切换交易模式

`start` / `daemon` / `restart` 会把后面的参数**原样透传**给 `main_loop_v2.py`，无需改脚本：

| 目标 | 命令 |
|---|---|
| 只跑外汇（默认） | `./deploy.sh daemon -f` |
| 只跑加密 | `./deploy.sh daemon -c` |
| 外汇 + 加密 | `./deploy.sh daemon -b` |
| 加密 + 自定义手数 | `./deploy.sh daemon -c --crypto-lots 0.5` |
| 实盘 + 加密 | `./deploy.sh daemon --live -c` |
| 空跑测试（不下单） | `./deploy.sh daemon -b --dry-run` |
| **已在运行要换模式** | `./deploy.sh restart -b` |

注意事项：

- **换模式必须走 `restart`**：主循环已在运行时，`daemon` 检测到 PID 存活会**直接跳过**（仅打印 warning），新参数不生效。
- **`daemon` / `restart` 会连带拉起周守护**（`weekly_train_daemon.py`），它与 `TRADE_MODE` **无关**，
  始终按 `config/forex_pairs.yml` 对**外汇 + 加密**全部品种做增量更新（因此 `daemon -c` ≠ 只碰加密）。
- **长期固定模式**：改 `config/run.env` 的 `TRADE_MODE`（`forex` / `crypto` / `forex-crypto`）后 `./deploy.sh restart`，
  之后裸跑 `./deploy.sh daemon` 即生效；CLI 参数始终可临时覆盖。
- 实时看日志：`tail -f reports/bot_console.out`（主循环）/ `reports/weekly_console.out`（周守护）。
- 不要用 `nohup python main_loop_v2.py ... &` 手动拉起：不会写 `reports/bot.pid`，`./deploy.sh status/stop` 将无法管理。

## 加密货币 (BTC_USD / ETH_USD)

加密品种在 `config/forex_pairs.yml` 的 `crypto:` 段统一管理（当前启用 `BTC_USD`、`ETH_USD`；
`LTC_USD`/`BCH_USD` 暂注释、不参与）。与外汇的区别通过独立配置隔离：

- **启用方式**：`--forex/-f`（默认）、`--crypto/-c`、`--forex-crypto/-b` 三选一；未指定时以 `run.env` 的 `TRADE_MODE` 为准，均无则默认 `forex`。
- **手数**：按 unit 计且支持小数，优先级 `--crypto-lots` > `run.env` 的 `DEMO_LOT_SIZE_CRYPTO`/`LIVE_LOT_SIZE_CRYPTO` > 缺省（demo 1 / live 0.01）。
  OANDA 最小可交易单位：BTC 0.001、ETH 0.01。
- **价格精度**：下单 SL/TP 精度改为**实时查询** OANDA 品种 `displayPrecision` 并缓存（BTC=1、ETH=2、日元=3、其余=5），
  避免 `TAKE_PROFIT_ON_FILL_PRICE_PRECISION_EXCEEDED`。
- **信号概率阈值**：默认**沿用外汇**的 `PROB_LONG_THRESHOLD` / `PROB_SHORT_THRESHOLD`（0.65 / 0.35）；
  若需加密单独收紧或放宽，在 `run.env` 设 `CRYPTO_PROB_LONG_THRESHOLD` / `CRYPTO_PROB_SHORT_THRESHOLD`（留空即继承外汇）。
  注意它与风控侧的波动率阈值是**两套独立参数**：概率阈值决定「开不开仓」，波动率阈值决定「风控放不放行」。
- **风控波动率**：加密使用独立阈值 —— `run.env` 的 `CRYPTO_VOL_THRESHOLD`（或 `config.yaml` 的 `crypto.vol_threshold_annual`，默认 1.0），
  外汇仍用 `risk.vol_threshold_annual`（0.15）；优先级同样 `run.env` > `config.yaml` > 内置默认。
- **ATR 止损/止盈倍率**：加密使用**独立倍率**以适配更高波动 —— `run.env` 的 `CRYPTO_ATR_SL_MULTIPLIER` / `CRYPTO_ATR_TP_MULTIPLIER`
  （或 `config.yaml` 的 `crypto.atr_sl_multiplier` / `crypto.atr_tp_multiplier`），默认 **2.0 / 2.5**；
  外汇沿用 `STOP_LOSS_ATR_MULTIPLIER` / `TAKE_PROFIT_ATR_MULTIPLIER`（1.5 / 1.8），行为完全不变。
  解析优先级同为 `run.env` > `config.yaml` > 内置默认；启动日志会分别标注归属（加密模式下显示 `SL=2.0(加密) | TP=2.5(加密)`）。
- **训练标签**：加密使用 `crypto.label_threshold_pct`（默认 0.01），外汇沿用 `make_label` 默认 0.002。

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

- 当前 `config/forex_pairs.yml` 启用 **8 对外汇** + **2 对加密**（`BTC_USD`、`ETH_USD`，其余注释未启用）；若本地模型缺失，
  首次启动会**自动补训**缺失的品种，训练完成后才进入交易循环，无需手动干预
- **周守护**（`weekly_train_daemon.py`）默认每 **7 天**（`lgb.retrain_interval_days`）对外汇 + 加密全部品种执行一次全量增量更新
- **K 线 CSV 自愈**：`data/<env>/datasets/*.csv` 若为空或损坏（例如上次训练被中断写坏），
  `update_csv` 会自动按全量重建并打印 warning；写盘采用「临时文件 + 原子替换」，不会留下 0 字节 CSV 导致整批训练中止。
- 日志位置：
  - `reports/bot.log` — 主交易日志（进程前台输出另见 `reports/bot_console.out`）
  - `reports/weekly_train.log` — 周度训练日志（进程前台输出另见 `reports/weekly_console.out`）
  - `reports/.last_weekly_retrain` — 模型上次更新时间戳

