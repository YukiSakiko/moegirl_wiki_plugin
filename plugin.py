"""moegirl_wiki_plugin 主入口 — 适配 maibot_sdk 2.x

提供 ``moegirl_lookup`` Tool,用于查询萌娘百科词条摘要、主词条信息以及相关语境。
"""

from __future__ import annotations

from typing import Any

from maibot_sdk import MaiBotPlugin, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType

from .client import MoegirlApiClient
from .config import MoegirlWikiPluginConfig
from .services.query_service import MoegirlQueryService

PLUGIN_VERSION = "2.1.2"

# 与 config.ResultSection.max_candidates 的 le=20 保持一致
MAX_CANDIDATES_CEILING = 20


class MoegirlWikiPlugin(MaiBotPlugin):
    """萌娘百科查询插件主类。"""

    config_model = MoegirlWikiPluginConfig

    def __init__(self) -> None:
        super().__init__()
        self._service: MoegirlQueryService | None = None

    # ===== 生命周期 =====

    async def on_load(self) -> None:
        cfg = self.config
        self.ctx.logger.info(
            "moegirl_wiki_plugin v%s 已加载 (timeout=%ds, cache_ttl=%ds, "
            "prefer_generator=%s, prefer_exact_title=%s, max_candidates=%d)",
            PLUGIN_VERSION,
            cfg.network.timeout_seconds,
            cfg.cache.ttl_seconds,
            cfg.search.prefer_generator_search,
            cfg.tool.prefer_exact_title,
            cfg.result.max_candidates,
        )

    async def on_unload(self) -> None:
        self._service = None
        self.ctx.logger.info("moegirl_wiki_plugin 已卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        del config_data
        # 丢弃旧服务实例，下次 Tool 调用按新配置重建（缓存与客户端参数随之刷新）
        self._service = None
        self.ctx.logger.info("配置更新事件: scope=%s version=%s，查询服务将在下次调用时重建", scope, version)

    # ===== 内部辅助 =====

    def _build_service(self) -> MoegirlQueryService:
        cfg = self.config
        client = MoegirlApiClient(
            timeout_seconds=cfg.network.timeout_seconds,
            cookie_string=cfg.auth.cookie_string,
        )
        return MoegirlQueryService(
            client=client,
            prefer_exact_title=cfg.tool.prefer_exact_title,
            cache_ttl_seconds=cfg.cache.ttl_seconds,
            enable_generator_search=cfg.search.prefer_generator_search,
        )

    def _get_service(self) -> MoegirlQueryService:
        if self._service is None:
            self._service = self._build_service()
        return self._service

    @staticmethod
    def _format_result(result: Any) -> str:
        if result.status == "ok" and result.page is not None:
            lines = [
                f"词条:{result.page.title}",
                f"简介:{result.page.summary}",
                f"链接:{result.page.url}",
            ]
            if result.page.categories:
                lines.append("分类:" + "、".join(result.page.categories[:3]))
            if result.page.thumbnail_url:
                lines.append(f"缩略图:{result.page.thumbnail_url}")
            if result.candidates:
                lines.append("")
                lines.append("相关语境:")
                for index, item in enumerate(result.candidates, start=1):
                    lines.append(f"{index}. {item.title}")
                    if item.description:
                        lines.append(f"简介:{item.description}")
                    lines.append(f"链接:{item.url}")
            return "\n".join(lines)

        if result.status == "ambiguous":
            lines = [result.message or "以下词条可能相关:"]
            for index, item in enumerate(result.candidates, start=1):
                lines.append(f"{index}. {item.title}")
                if item.description:
                    lines.append(f"简介:{item.description}")
                lines.append(f"链接:{item.url}")
            return "\n".join(lines)

        if result.status == "not_found":
            return result.message or "未找到明显匹配词条。"

        return result.message or "萌娘百科查询暂时不可用。"

    # ===== Tool: moegirl_lookup =====

    @Tool(
        "moegirl_lookup",
        description="查询萌娘百科词条摘要与链接,用于角色、作品、设定和术语知识补充",
        parameters=[
            ToolParameterInfo(
                name="query",
                param_type=ToolParamType.STRING,
                description="要查询的词条或关键词",
                required=True,
            ),
            ToolParameterInfo(
                name="mode",
                param_type=ToolParamType.STRING,
                description="查询模式: summary(返回主词条详细信息) 或 candidates(返回候选列表)",
                required=False,
                enum_values=["summary", "candidates"],
                default="summary",
            ),
            ToolParameterInfo(
                name="max_candidates",
                param_type=ToolParamType.INTEGER,
                description="候选数量上限,留空时使用配置默认值",
                required=False,
            ),
        ],
    )
    async def handle_moegirl_lookup(
        self,
        query: str = "",
        mode: str = "summary",
        max_candidates: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        del kwargs
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return {"success": False, "content": "查询词不能为空。", "error": "empty_query"}

        normalized_mode = str(mode or "summary").strip() or "summary"
        if normalized_mode not in ("summary", "candidates"):
            normalized_mode = "summary"

        default_max_candidates = self.config.result.max_candidates
        try:
            resolved_max_candidates = int(max_candidates) if max_candidates is not None else default_max_candidates
        except (TypeError, ValueError):
            resolved_max_candidates = default_max_candidates
        if resolved_max_candidates <= 0:
            resolved_max_candidates = default_max_candidates
        # 钳制到配置模型的合法区间，防止模型传入超大值撑爆 API 与返回正文
        resolved_max_candidates = max(1, min(resolved_max_candidates, MAX_CANDIDATES_CEILING))

        service = self._get_service()
        try:
            result = await service.lookup(
                normalized_query,
                mode=normalized_mode,
                max_candidates=resolved_max_candidates,
            )
        except Exception as exc:  # noqa: BLE001
            self.ctx.logger.error("moegirl_lookup 执行异常: %s", exc, exc_info=True)
            return {
                "success": False,
                "content": f"萌娘百科查询失败: {exc}",
                "error": str(exc),
            }

        # not_found / ambiguous 属于正常的业务结果，对 LLM 而言调用本身是成功的
        return {"success": True, "content": self._format_result(result)}


def create_plugin() -> MoegirlWikiPlugin:
    """Runner 通过此工厂函数实例化插件。"""
    return MoegirlWikiPlugin()
