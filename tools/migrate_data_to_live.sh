#!/bin/bash
# tools/migrate_data_to_live.sh
# 将 practice 环境的历史数据 / 模型复制到 live 目录，供实盘模型冷启动使用。
# ⚠️ 这是「手动确认」入口：脚本执行后会把 config.yaml 的
#    data.allow_practice_for_live 置为 true。
set -euo pipefail
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log_info() { echo -e "${GREEN}✅ $*${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
log_err() { echo -e "${RED}❌ $*${NC}"; }

cd "$(dirname "$0")/.."

SRC_DATA="data/practice/datasets"
SRC_MODEL="models/model_store/practice"
DST_DATA="data/live/datasets"
DST_MODEL="models/model_store/live"

echo ""
echo -e "${RED}══════════════════════════════════════════════════════════════${NC}"
echo -e "${RED}  ⚠️  数据迁移风险提示 / DATA MIGRATION RISK${NC}"
echo -e "${RED}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  即将把 practice 的历史数据与模型复制到 live 环境。${NC}"
echo -e "${YELLOW}  迁移数据 ≠ 实盘表现：点差 / 滑点 / 交易深度 / 更新延迟都有差异。${NC}"
echo -e "${YELLOW}  上实盘前请先跑 至少 2–4 周原生 live 数据，再评估模型是否可用。${NC}"
echo -e "${RED}══════════════════════════════════════════════════════════════${NC}"
echo ""
read -r -p "确认迁移 practice → live ？(输入大写 YES 继续): " ans
if [[ "$ans" != "YES" ]]; then
    log_warn "已取消，未做任何改动"
    exit 1
fi

mkdir -p "$DST_DATA" "$DST_MODEL"

# ── 拷贝前磁盘空间检查 ────────────────────────────────────────────
check_disk_space() {
    local need_kb=0 avail_kb dirs=()
    if [[ -d "$SRC_DATA" ]]; then dirs+=("$SRC_DATA"); fi
    if [[ -d "$SRC_MODEL" ]]; then dirs+=("$SRC_MODEL"); fi
    if [[ ${#dirs[@]} -gt 0 ]]; then
        need_kb=$(du -ck "${dirs[@]}" 2>/dev/null | tail -n1 | awk '{print $1}') || need_kb=0
    fi
    [[ -n "${need_kb:-}" ]] || need_kb=0
    avail_kb=$(df -Pk data/live | awk 'NR==2 {print $4}')
    [[ -n "${avail_kb:-}" ]] || avail_kb=0
    log_info "磁盘检查：需要约 $(( need_kb / 1024 )) MB，可用 $(( avail_kb / 1024 )) MB"
    if [[ "$avail_kb" -lt "$need_kb" ]]; then
        log_err "磁盘空间不足，已中止迁移（未复制任何文件）"
        return 1
    fi
    return 0
}

# ── 逐个文件复制；已存在时询问 [S]kip / [O]verwrite / [A]ll ────────
copy_files() {
    local src_dir="$1" dst_dir="$2" label="$3"
    local overwrite_all=0 copied=0 skipped=0 f base target ans
    local files=()
    shopt -s nullglob
    files=("$src_dir"/*)
    shopt -u nullglob
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "$label：$src_dir 下无可迁移文件，跳过"
        return 0
    fi
    for f in "${files[@]}"; do
        base=$(basename "$f")
        target="$dst_dir/$base"
        if [[ -e "$target" && $overwrite_all -eq 0 ]]; then
            ans=""
            if [[ -t 0 ]]; then
                read -r -p "  [$label] 已存在 $base → [S]kip/[O]verwrite/[A]ll ? " ans || ans="S"
            fi
            case "${ans:-S}" in
                o|O) : ;;
                a|A) overwrite_all=1 ;;
                *) log_warn "跳过 $base"; skipped=$((skipped + 1)); continue ;;
            esac
        fi
        cp -f "$f" "$target"
        copied=$((copied + 1))
    done
    log_info "$label：复制 $copied 个，跳过 $skipped 个"
}

if ! check_disk_space; then
    exit 1
fi

copy_files "$SRC_DATA" "$DST_DATA" "数据"
copy_files "$SRC_MODEL" "$DST_MODEL" "模型"

python3 - <<'PY'
import pathlib
import yaml

p = pathlib.Path("config/config.yaml")
cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
cfg.setdefault("data", {})["allow_practice_for_live"] = True
p.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
print("config.yaml: data.allow_practice_for_live -> true")
PY

log_info "迁移完成：$DST_DATA 与 $DST_MODEL"
log_warn "⚠️ 迁移数据 ≠ 实盘表现 —— 上实盘前请先跑至少 2–4 周原生 live 数据！"
