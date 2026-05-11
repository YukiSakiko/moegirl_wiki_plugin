"""moegirl_wiki_plugin 配置模型。

按 PluginConfigBase 拆分为多个 section,使用 maibot_sdk 强类型配置。
"""

from maibot_sdk import Field, PluginConfigBase


class PluginSection(PluginConfigBase):
    """插件基础信息"""

    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    name: str = Field(default="moegirl_wiki_plugin", description="插件名称")
    version: str = Field(default="2.0.0", description="插件版本")
    config_version: str = Field(default="2.0.0", description="配置版本(Runner 用于兼容性校验)")
    enabled: bool = Field(default=True, description="是否启用插件")


class NetworkSection(PluginConfigBase):
    """网络访问配置"""

    __ui_label__ = "网络"
    __ui_icon__ = "globe"
    __ui_order__ = 1

    timeout_seconds: int = Field(default=10, ge=1, le=120, description="请求超时时间(秒)")


class AuthSection(PluginConfigBase):
    """认证配置"""

    __ui_label__ = "认证"
    __ui_icon__ = "lock"
    __ui_order__ = 2

    cookie_string: str = Field(
        default="",
        description="萌娘百科登录 Cookie；当前搜索主路径不依赖 Cookie，留空即可",
    )


class SearchSection(PluginConfigBase):
    """搜索策略配置"""

    __ui_label__ = "搜索"
    __ui_icon__ = "search"
    __ui_order__ = 3

    prefer_generator_search: bool = Field(
        default=True,
        description="优先使用 generator=search 搜索接口，失败时回退 opensearch",
    )


class CacheSection(PluginConfigBase):
    """本地缓存配置"""

    __ui_label__ = "缓存"
    __ui_icon__ = "database"
    __ui_order__ = 4

    ttl_seconds: int = Field(default=300, ge=0, le=86400, description="缓存生存时间(秒)，0 表示禁用缓存")


class ResultSection(PluginConfigBase):
    """结果返回配置"""

    __ui_label__ = "结果"
    __ui_icon__ = "list"
    __ui_order__ = 5

    max_candidates: int = Field(default=5, ge=1, le=20, description="候选词条数量上限")


class ToolSection(PluginConfigBase):
    """工具行为配置"""

    __ui_label__ = "工具"
    __ui_icon__ = "tool"
    __ui_order__ = 6

    prefer_exact_title: bool = Field(
        default=True,
        description="是否优先精确标题匹配；关闭后只要有候选即返回候选列表",
    )


class MoegirlWikiPluginConfig(PluginConfigBase):
    """moegirl_wiki_plugin 顶层配置"""

    plugin: PluginSection = Field(default_factory=PluginSection)
    network: NetworkSection = Field(default_factory=NetworkSection)
    auth: AuthSection = Field(default_factory=AuthSection)
    search: SearchSection = Field(default_factory=SearchSection)
    cache: CacheSection = Field(default_factory=CacheSection)
    result: ResultSection = Field(default_factory=ResultSection)
    tool: ToolSection = Field(default_factory=ToolSection)
