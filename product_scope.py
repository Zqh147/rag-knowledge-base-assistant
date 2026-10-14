"""Resolve explicit fields and identifiers in the question without guessing."""
import re
from dataclasses import dataclass, field

FIELDS = ("product_model", "hardware_version", "region")
LABELS = {"product_model": "设备型号", "hardware_version": "硬件版本（如 V1）", "region": "销售地区（如 US）"}
MODEL_RE = re.compile(r"(?<![A-Za-z0-9])(?:Archer\s*)?(AX\d+[A-Za-z]*|TL-[A-Za-z0-9-]+)(?![A-Za-z0-9])", re.I)
VERSION_RE = re.compile(r"(?<![A-Za-z0-9])V\d+(?:\.\d+)?(?![A-Za-z0-9])", re.I)
REGION_RE = re.compile(r"(?<![A-Za-z0-9])(US|EU|CN)(?![A-Za-z0-9])|美版|美国|欧版|欧洲|国行|中国大陆", re.I)


def normalize(field_name, value):
    value = value.strip()
    if field_name == "product_model":
        match = MODEL_RE.fullmatch(value)
        return f"Archer {match.group(1).upper()}" if match and match.group(1).upper().startswith("AX") else value.upper()
    if field_name == "hardware_version":
        value = value.upper()
        if not value.startswith("V"):
            value = "V" + value
        return re.sub(r"^(V\d+)\.0$", r"\1", value)
    return {"美版": "US", "美国": "US", "欧版": "EU", "欧洲": "EU", "国行": "CN", "中国大陆": "CN"}.get(value, value.upper())


@dataclass
class ScopeResult:
    status: str
    message: str = ""
    filters: dict = field(default_factory=dict)
    missing_fields: list = field(default_factory=list)
    query: str = ""


def resolve_scope(question, products, product_model=None, hardware_version=None, region=None):
    if re.search(r"华为|huawei|小米|xiaomi|华硕|asus", question, re.I):
        return ScopeResult("unsupported_product", "现有资料仅覆盖所列 TP-Link 设备，无法依据现有资料确定其他品牌的操作。")
    explicit = dict(zip(FIELDS, (product_model, hardware_version, region)))
    extracted = {
        "product_model": {normalize("product_model", m.group()) for m in MODEL_RE.finditer(question)},
        "hardware_version": {normalize("hardware_version", m.group()) for m in VERSION_RE.finditer(question)},
        "region": {normalize("region", m.group()) for m in REGION_RE.finditer(question)},
    }
    resolved = {}
    for key in FIELDS:
        values = extracted[key]
        if explicit[key] is not None:
            if not explicit[key].strip():
                raise ValueError(f"{key} must not be blank")
            values.add(normalize(key, explicit[key]))
        if len(values) > 1:
            return ScopeResult("parameter_conflict", f"{LABELS[key]}存在冲突或多个值，请明确本次要查询哪一台设备。")
        if values:
            resolved[key] = next(iter(values))
    candidates = [p for p in products if all(p[FIELDS.index(k)] == v for k, v in resolved.items())]
    if resolved and not candidates:
        return ScopeResult("unsupported_product", "现有资料未收录该型号、硬件版本与地区组合，无法依据现有资料确定。", resolved)
    missing = [k for k in FIELDS if k not in resolved]
    if missing:
        return ScopeResult("needs_clarification", "请补充" + "、".join(LABELS[k] for k in missing) + "，可查看设备底部标签。", resolved, missing)
    query = REGION_RE.sub(" ", VERSION_RE.sub(" ", MODEL_RE.sub(" ", question))).strip(" ，。？?：:()（）")
    if len(query) < 2:
        return ScopeResult("needs_clarification", "请说明需要查询的功能或故障现象。", resolved, ["question"])
    return ScopeResult("ok", filters=resolved, query=query)


def chroma_where(filters):
    if not filters:
        return None
    terms = [{k: v} for k, v in filters.items()]
    return terms[0] if len(terms) == 1 else {"$and": terms}


def matches(metadata, filters):
    return all(metadata.get(k) == v for k, v in filters.items())
