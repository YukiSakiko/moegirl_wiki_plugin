"""moegirl_wiki_plugin 配置模型。

按 PluginConfigBase 拆分为多个 section,使用 maibot_sdk 强类型配置。
"""

from maibot_sdk import Field, PluginConfigBase


class PluginSection(PluginConfigBase):
    """插件基础信息"""

    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    # enabled 是宿主保留键（WebUI 顶部启停开关写同一个键），禁止在模型中声明；
    # 插件名称与版本以 _manifest.json 为准，此处不再重复
    config_version: str = Field(
        default="2.1.0",
        description="配置版本，请勿手动修改。",
        json_schema_extra={"disabled": True, "hidden": True, "label": "配置版本", "order": 99},
    )


class NetworkSection(PluginConfigBase):
    """网络访问配置"""

    __ui_label__ = "网络"
    __ui_icon__ = "globe"
    __ui_order__ = 1

    timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=120,
        description="请求超时时间(秒)",
        json_schema_extra={"label": "请求超时（秒）", "order": 0},
    )


class AuthSection(PluginConfigBase):
    """认证配置"""

    __ui_label__ = "认证"
    __ui_icon__ = "lock"
    __ui_order__ = 2

    cookie_string: str = Field(
        default="",
        description="萌娘百科登录 Cookie；当前搜索主路径不依赖 Cookie，留空即可",
        json_schema_extra={"label": "登录 Cookie", "order": 0, "hint": "一般无需填写，留空即可"},
    )


class SearchSection(PluginConfigBase):
    """搜索策略配置"""

    __ui_label__ = "搜索"
    __ui_icon__ = "search"
    __ui_order__ = 3

    prefer_generator_search: bool = Field(
        default=True,
        description="优先使用 generator=search 搜索接口，失败时回退 opensearch",
        json_schema_extra={"label": "优先使用高级搜索", "order": 0},
    )


class CacheSection(PluginConfigBase):
    """本地缓存配置"""

    __ui_label__ = "缓存"
    __ui_icon__ = "database"
    __ui_order__ = 4

    ttl_seconds: int = Field(
        default=300,
        ge=0,
        le=86400,
        description="缓存生存时间(秒)，0 表示禁用缓存",
        json_schema_extra={"label": "缓存生存时间（秒）", "order": 0},
    )


class ResultSection(PluginConfigBase):
    """结果返回配置"""

    __ui_label__ = "结果"
    __ui_icon__ = "list"
    __ui_order__ = 5

    max_candidates: int = Field(
        default=5,
        ge=1,
        le=20,
        description="候选词条数量上限",
        json_schema_extra={"label": "候选词条上限", "order": 0},
    )


class ToolSection(PluginConfigBase):
    """工具行为配置"""

    __ui_label__ = "工具"
    __ui_icon__ = "tool"
    __ui_order__ = 6

    prefer_exact_title: bool = Field(
        default=True,
        description="是否优先精确标题匹配；关闭后只要有候选即返回候选列表",
        json_schema_extra={"label": "优先精确标题匹配", "order": 0},
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
