from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

from src.plugin_system import (
    BasePlugin,
    BaseTool,
    ComponentInfo,
    ConfigField,
    ToolParamType,
    register_plugin,
    get_logger,
)

from .client import MoegirlApiClient
from .services.query_service import MoegirlQueryService

logger = get_logger("moegirl_wiki")
_MISSING = object()


def _nested_config_get(data: Any, key: str, default: Any = None) -> Any:
    """读取嵌套配置值。"""
    if not data:
        return default
    current = data
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _load_plugin_config_from_disk(config_path: Path) -> Dict[str, Any]:
    """从磁盘读取插件配置文件,作为兼容层尚未注入配置时的回退。"""
    if not config_path.exists():
        return {}
    try:
        with config_path.open("rb") as file:
            loaded = tomllib.load(file)
    except Exception as exc:
        logger.warning(f"读取插件配置失败 {config_path}: {exc}")
        return {}
    return loaded if isinstance(loaded, dict) else {}


class MoegirlLookupTool(BaseTool):
    name = "moegirl_lookup"
    description = "查询萌娘百科词条摘要与链接，用于角色、作品、设定和术语知识补充"
    parameters = [
        ("query", ToolParamType.STRING, "要查询的词条或关键词", True, None),
        ("mode", ToolParamType.STRING, "summary 或 candidates", False, ["summary", "candidates"]),
        ("max_candidates", ToolParamType.INTEGER, "候选数量上限", False, None),
    ]
    available_for_llm = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # 兼容层会在每次调用前重新设置 plugin_config，这里仅作占位。
        self._disk_config_cache: Optional[Dict[str, Any]] = None

    def _resolve_config(self, key: str, default: Any = None) -> Any:
        """优先读取注入配置，缺失时回退到磁盘 config.toml。"""
        runtime_value = _nested_config_get(self.plugin_config, key, _MISSING)
        if runtime_value is not _MISSING:
            return runtime_value

        if self._disk_config_cache is None:
            config_path = Path(__file__).with_name("config.toml")
            self._disk_config_cache = _load_plugin_config_from_disk(config_path)
        return _nested_config_get(self._disk_config_cache, key, default)

    def _build_service(self) -> MoegirlQueryService:
        timeout_seconds = int(self._resolve_config("network.timeout_seconds", 10))
        prefer_exact_title = bool(self._resolve_config("tool.prefer_exact_title", True))
        cache_ttl_seconds = int(self._resolve_config("cache.ttl_seconds", 0))
        cookie_string = str(self._resolve_config("auth.cookie_string", "") or "").strip()

        raw_search_config = self.plugin_config.get("search", {}) if isinstance(self.plugin_config, dict) else {}
        if isinstance(raw_search_config, dict) and "prefer_generator_search" in raw_search_config:
            prefer_generator_search = bool(raw_search_config.get("prefer_generator_search", True))
        elif isinstance(raw_search_config, dict) and "prefer_authenticated_search" in raw_search_config:
            prefer_generator_search = bool(raw_search_config.get("prefer_authenticated_search", True))
        else:
            prefer_generator_search = bool(self._resolve_config("search.prefer_generator_search", True))

        client = MoegirlApiClient(timeout_seconds=timeout_seconds, cookie_string=cookie_string)
        return MoegirlQueryService(
            client=client,
            prefer_exact_title=prefer_exact_title,
            cache_ttl_seconds=cache_ttl_seconds,
            enable_generator_search=prefer_generator_search,
        )

    def _format_result(self, result: Any) -> str:
        if result.status == "ok" and result.page is not None:
            lines = [
                f"词条：{result.page.title}",
                f"简介：{result.page.summary}",
                f"链接：{result.page.url}",
            ]
            if result.page.categories:
                lines.append("分类：" + "、".join(result.page.categories[:3]))
            if result.page.thumbnail_url:
                lines.append(f"缩略图：{result.page.thumbnail_url}")
            if result.candidates:
                lines.append("")
                lines.append("相关语境：")
                for index, item in enumerate(result.candidates, start=1):
                    lines.append(f"{index}. {item.title}")
                    if item.description:
                        lines.append(f"简介：{item.description}")
                    lines.append(f"链接：{item.url}")
            return "\n".join(lines)

        if result.status == "ambiguous":
            lines = [result.message or "以下词条可能相关："]
            for index, item in enumerate(result.candidates, start=1):
                lines.append(f"{index}. {item.title}")
                if item.description:
                    lines.append(f"简介：{item.description}")
                lines.append(f"链接：{item.url}")
            return "\n".join(lines)

        if result.status == "not_found":
            return result.message or "未找到明显匹配词条。"

        return result.message or "萌娘百科查询暂时不可用。"

    async def execute(self, function_args: dict[str, Any]) -> dict[str, Any]:
        query = str(function_args.get("query", "")).strip()
        if not query:
            return {"name": self.name, "content": "查询词不能为空。"}

        mode = str(function_args.get("mode", "summary") or "summary")
        max_candidates = int(
            function_args.get("max_candidates", self._resolve_config("result.max_candidates", 5))
        )
        service = self._build_service()
        result = await service.lookup(query, mode=mode, max_candidates=max_candidates)
        return {"name": self.name, "content": self._format_result(result)}


@register_plugin
class MoegirlWikiPlugin(BasePlugin):
    plugin_name = "moegirl_wiki_plugin"
    enable_plugin = True
    dependencies: List[str] = []
    python_dependencies: List[str] = ["aiohttp>=3.8.0"]
    config_file_name = "config.toml"
    log_prefix = "[moegirl_wiki_plugin]"
    plugin_config: Dict[str, Any] = {}

    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "config_version": ConfigField(type=str, default="1.1.0", description="配置文件版本"),
        },
        "network": {
            "timeout_seconds": ConfigField(type=int, default=10, description="请求超时时间（秒）"),
        },
        "auth": {
            "mode": ConfigField(
                type=str,
                default="anonymous",
                description="认证模式",
                choices=["anonymous", "cookie"],
            ),
            "cookie_string": ConfigField(
                type=str,
                default="",
                description="萌娘百科登录 Cookie",
                input_type="textarea",
                rows=4,
                placeholder="例如：session=...; token=...",
                hint="可选。当前搜索主路径不依赖 Cookie，但保留登录态配置用于后续扩展；建议仅保存在本地配置中。",
            ),
        },
        "search": {
            "prefer_generator_search": ConfigField(
                type=bool,
                default=True,
                description="优先使用 generator=search 搜索接口",
            ),
        },
        "cache": {
            "ttl_seconds": ConfigField(type=int, default=300, description="缓存生存时间（秒）"),
        },
        "result": {
            "max_candidates": ConfigField(type=int, default=5, description="候选词条数量上限"),
        },
        "tool": {
            "prefer_exact_title": ConfigField(type=bool, default=True, description="是否优先精确标题匹配"),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        return [(MoegirlLookupTool.get_tool_info(), MoegirlLookupTool)]

    # ── 兼容层最小配置访问 ─────────────────────────────────────
    def set_plugin_config(self, config: Optional[Dict[str, Any]]) -> None:
        """兼容层注入插件配置。"""
        self.plugin_config = config or {}

    def get_config(self, key: str, default: Any = None) -> Any:
        """在兼容层下读取插件配置，缺失时回退到磁盘。"""
        runtime_value = _nested_config_get(self.plugin_config, key, _MISSING)
        if runtime_value is not _MISSING:
            return runtime_value

        config_path = Path(__file__).with_name(self.config_file_name)
        disk_config = _load_plugin_config_from_disk(config_path)
        return _nested_config_get(disk_config, key, default)

    def _load_plugin_config(self) -> None:
        """兼容旧调用路径：从当前插件目录重新载入配置。"""
        config_path = Path(__file__).with_name(self.config_file_name)
        self.set_plugin_config(_load_plugin_config_from_disk(config_path))
