"""Core 品种筛选（Core Scoring）— v2.0（组级门禁）

打分对象是「关联组」（correlation group），不是组内单个品种：

    阶段1  关联组反向冲突检查（原有逻辑，完全保留、不修改）
    阶段2  组级门禁：按关联组计算「组波动分」（新增）
    阶段3  门禁判定：组波动分低于阈值 → 整组放弃本轮（新增）
    阶段4  择优开仓：通过门禁的候选按概率排序取前 N → 不超 max_open（原有逻辑）

为什么不再对品种打分（v1.0 → v2.0）：
    v1.0 用「组内 min-max 归一化」给品种打分，本质是组内相对排名、没有绝对尺度。
    组内两个品种波动率 0.190% 与 0.188% 几乎相同时，归一化会放大成 1.00 与 0.00，
    使「值相差无几」的品种被强行分出胜负、其中一个被阈值误杀。
    v2.0 改为：波动率只回答「这个组值不值得交易」（绝对口径）；
    组内/全池选谁，则交给概率（signal_strength）决定。

组波动分：
    group_vol   = 组内全部可见品种的最大相对波动率（ATR / 收盘价）
    group_score = min(group_vol / CORE_GROUP_VOL_REF, 1) × 100      （0~100）
    默认 ref = 0.0020（20bp/H1）→ 正常时段活跃组约 80~100 分。
    门槛：group_score < CORE_SCORE_THRESHOLD → 整组放弃，本轮不考虑该组。

品种级（不打分）：
    通过门禁的关联组，其候选按概率（signal_strength：多头=prob，空头=1-prob）排序；
    外汇池取前 CORE_MAX_PER_GROUP 个（默认 1，可调 1~3）；Crypto 单列独立名额。

打分范围（打分不跨组）：
    每个关联组独立计算组波动分，互不影响（例：jpy_cross 的 JPY 波动不影响 usd_foreign）。
    未列入任何关联组的品种自成一组；Crypto 组不参与本门禁（保持其原有行为不变）。

安全开关（CORE_MODE）：
    observe : 只打日志、不拦截（默认）——向后兼容，不改变任何下单行为；
    filter  : 正式门禁——组波动分不足的组，其全部候选本轮不开仓。

注意：本模块只做「组级门禁」，不改变 ATR 计算方式、SL/TP 参数、
关联冲突逻辑与分组控仓上限。
"""
import os

from config.correlation_groups import group_of
from config.pairs import is_crypto

# ── 默认配置（可被 config/run.env 的同名环境变量覆盖） ─────────────
DEFAULT_SCORE_THRESHOLD = 40.0        # 组波动分门槛（0~100），低于则整组放弃
DEFAULT_GROUP_VOL_REF = 0.0020        # 组波动分基准：组内最大相对波动率 20bp/H1 → 100 分
DEFAULT_MAX_PER_GROUP = 1             # 每轮外汇池最多开仓数（1~3）
DEFAULT_MODE = "observe"              # observe=仅日志 / filter=正式门禁

VALID_MODES = ("observe", "filter")

# 外汇池每轮开仓数硬上限（防止配置误填导致一次开太多）
MAX_PER_GROUP_CAP = 3

# 组外品种（未列入任何关联组）在日志中的显示前缀
UNGROUPED_LABEL = "未分组"

_EPSILON = 1e-12


class CoreConfig:
    """Core 组级门禁配置容器（config/run.env → 本对象）。"""

    def __init__(
        self,
        score_threshold=DEFAULT_SCORE_THRESHOLD,
        group_vol_ref=DEFAULT_GROUP_VOL_REF,
        max_per_group=DEFAULT_MAX_PER_GROUP,
        mode=DEFAULT_MODE,
    ):
        self.score_threshold = float(score_threshold)
        ref = float(group_vol_ref)
        self.group_vol_ref = ref if ref > _EPSILON else DEFAULT_GROUP_VOL_REF
        try:
            n = int(float(max_per_group))
        except (TypeError, ValueError):
            n = DEFAULT_MAX_PER_GROUP
        self.max_per_group = min(max(n, 1), MAX_PER_GROUP_CAP)
        mode = str(mode).strip().lower() or DEFAULT_MODE
        self.mode = mode if mode in VALID_MODES else DEFAULT_MODE

    @property
    def filter_enabled(self):
        """True = filter 模式（真正拦截）；False = observe 模式（仅日志）。"""
        return self.mode == "filter"

    @property
    def vol_gate(self):
        """与分数门槛等效的绝对波动率门槛 = 阈值/100 × 基准（日志展示用）。"""
        return self.score_threshold / 100.0 * self.group_vol_ref

    @classmethod
    def from_env(cls, env=None):
        """从环境变量读取配置（run.env 由 config.config_oanda 载入 os.environ）。

        缺失或非法值一律回退到默认值，保证向后兼容。
        """
        src = os.environ if env is None else env

        def _num(key, default):
            raw = (src.get(key) or "").strip()
            if not raw:
                return default
            try:
                return float(raw)
            except ValueError:
                return default

        return cls(
            score_threshold=_num("CORE_SCORE_THRESHOLD", DEFAULT_SCORE_THRESHOLD),
            group_vol_ref=_num("CORE_GROUP_VOL_REF", DEFAULT_GROUP_VOL_REF),
            max_per_group=_num("CORE_MAX_PER_GROUP", DEFAULT_MAX_PER_GROUP),
            mode=(src.get("CORE_MODE") or "").strip() or DEFAULT_MODE,
        )


def rel_volatility(atr, close):
    """相对波动率 = ATR / 收盘价；输入非法或收盘价非正时返回 None。"""
    try:
        a, c = float(atr), float(close)
    except (TypeError, ValueError):
        return None
    if c <= 0.0 or a < 0.0:
        return None
    return a / c


def group_key(instrument):
    """关联组槽位 key：组内品种用组名；组外品种用其自身名（自成一组）。"""
    return group_of(instrument) or str(instrument)


def group_label(instrument):
    """关联组显示名：组内品种用组名；组外品种显示为「未分组(<品种>)」。"""
    grp = group_of(instrument)
    return grp if grp else f"{UNGROUPED_LABEL}({instrument})"


def build_group_vols(pool_metrics):
    """按关联组汇总「可见品种」的相对波动率。

    :param pool_metrics: {inst: {"atr":..., "close":...}}，应为该轮全部可见品种
                         （不是当轮候选池）；Crypto 不参与
    :return: {group_key: {"label","insts","vols","max_vol","vol_inst"}}
             组外品种自成一组（key = 品种名），保证互不干扰。
    """
    pools = {}
    for inst, m in (pool_metrics or {}).items():
        if is_crypto(inst):
            continue  # Crypto 不参与本门禁
        v = rel_volatility((m or {}).get("atr"), (m or {}).get("close"))
        if v is None or v <= 0.0:
            continue
        pools.setdefault(group_key(inst), {})[inst] = v

    result = {}
    for key, vols in pools.items():
        max_inst = max(vols, key=lambda i: vols[i])
        result[key] = {
            "label": group_label(max_inst),
            "insts": sorted(vols),
            "vols": vols,
            "max_vol": vols[max_inst],
            "vol_inst": max_inst,
        }
    return result


def compute_group_scores(pool_metrics, cfg=None):
    """计算各关联组的「组波动分」，返回按分数降序的列表（打分对象是组）。

    :param pool_metrics: {inst: {"atr":..., "close":...}}，应为该轮「全部可见品种」
    :param cfg         : CoreConfig；缺省使用默认基准
    :return: [{"group","label","insts","n","vols","max_vol","vol_inst","score"}, ...]
    """
    cfg = cfg or CoreConfig()
    result = []
    for key, pool in build_group_vols(pool_metrics).items():
        score = int(round(min(pool["max_vol"] / cfg.group_vol_ref, 1.0) * 100.0))
        result.append(
            {
                "group": key,
                "label": pool["label"],
                "insts": pool["insts"],
                "n": len(pool["insts"]),
                "vols": pool["vols"],
                "max_vol": pool["max_vol"],
                "vol_inst": pool["vol_inst"],
                "score": score,
            }
        )
    result.sort(key=lambda e: e["score"], reverse=True)
    return result


def evaluate_group(entry, cfg=None):
    """组级门禁判定：组波动分 ≥ 阈值 → 该组本轮可交易。

    :param entry: compute_group_scores() 返回的单条结果
    :param cfg  : CoreConfig；缺省使用默认门槛
    :return: (keep: bool, reason: str)
             observe 模式下由调用方忽略 keep（仅日志），filter 模式下据此整组拦截。
             keep=False 表示「本轮放弃该组」，与组内个股信号好坏无关。
    """
    cfg = cfg or CoreConfig()
    score = entry.get("score")
    if score is None:
        return False, "缺少波动数据 → 本轮放弃该组"
    if score < cfg.score_threshold:
        return False, (
            f"组波动分 {score} < {cfg.score_threshold:.0f}"
            f"（组内最大波动 {entry['max_vol']:.3%} < 等效门槛 {cfg.vol_gate:.3%}）"
            f" → 本轮放弃该组"
        )
    return True, "保留"


def format_group(entry, cfg=None):
    """把单条组级门禁结果格式化成统一日志行。"""
    cfg = cfg or CoreConfig()
    _, reason = evaluate_group(entry, cfg)
    return (
        f"组门禁 {entry['label']}（{entry['n']}个品种） | 组波动分={entry['score']} | "
        f"组内最大波动={entry['max_vol']:.3%}（{entry['vol_inst']}） | "
        f"MODE={cfg.mode} → {reason}"
    )
