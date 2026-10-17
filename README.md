# 萌娘百科知识补全插件

为 MaiBot / 麦麦提供一个 `moegirl_lookup` Tool，用于在聊天过程中查询萌娘百科词条、补充主词条信息，并附带相关语境条目。

## 功能特性

- 基于萌娘百科 Action API 查询词条
- 优先使用 `generator=search`，失败时自动回退 `opensearch`
- 支持常见问句归一化
  - `初音未来是谁`
  - `东方Project是什么`
  - `博丽灵梦是哪个作品的`
- 当主词条足够可信时：
  - 返回主词条**详细结果**
  - 默认附带 2~4 个**相关语境**中等详细结果
- 当主词条不够可信时：
  - 返回多条中等详细候选结果
- 支持本地缓存与可选 Cookie 配置

---

## 目录结构

```text
moegirl_wiki_plugin/
├─ __init__.py
├─ _manifest.json
├─ client.py
├─ config.py
├─ models.py
├─ plugin.py
├─ services/
│  └─ query_service.py
├─ requirements.txt
├─ README.md
├─ LICENSE
└─ .gitignore
```

---

## 安装方式

将本仓库克隆到 MaiBot 的 `plugins/` 目录下，例如：

```bash
cd /path/to/MaiBot/plugins
git clone https://github.com/ValleyWinds/Moegirl-Wiki.git moegirl_wiki_plugin
```

建议最终目录名保持为 `moegirl_wiki_plugin`。

插件依赖只有 `aiohttp`，已通过 `_manifest.json` 的 `python_package` 依赖声明，安装/更新插件时由依赖管道自动安装，无需手动 `pip install`。

---

## 配置说明

> 插件加载或热重载时会根据配置模型自动生成 `config.toml`。修改配置后在 WebUI「插件管理」点重新加载即可生效，**无需重启 MaiBot**。

### 最小配置

```toml
[plugin]
config_version = "2.1.0"

[network]
timeout_seconds = 10

[auth]
cookie_string = ""

[search]
prefer_generator_search = true

[cache]
ttl_seconds = 300

[result]
max_candidates = 5

[tool]
prefer_exact_title = true
```

多数场景直接留空使用默认值即可，大部分配置也可以在 WebUI 插件设置页里修改。

### Cookie 配置（可选）

当前搜索主路径**不依赖 Cookie**，但你仍然可以保留登录态配置，方便后续扩展或站点策略变化时使用：

```toml
[auth]
cookie_string = "完整 Cookie 头"
```

---

## Tool 说明

### Tool 名称

`moegirl_lookup`

### 输入参数

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `query` | `string` | 要查询的词条、关键词或自然语言问句 |
| `mode` | `string` | `summary` 或 `candidates` |
| `max_candidates` | `int` | 候选数量上限 |

### 输出策略

#### 1. 主词条足够可信

返回：

- 主词条详细结果
  - 标题
  - 完整简介
  - 链接
  - 分类
  - 缩略图
- 相关语境中等详细结果
  - 标题
  - 简短简介
  - 链接

#### 2. 主词条不够可信

返回：

- 多条中等详细候选结果
  - 标题
  - 简短简介
  - 链接

---

## 示例

### 示例 1：主词条 + 相关语境

输入：

```text
初音未来是谁
```

输出形态：

```text
词条：初音未来
简介：……
链接：……
分类：……
缩略图：……

相关语境：
1. 初音未来/现实事件
简介：……
链接：……
2. 初音未来 -歌姬计划-
简介：……
链接：……
```

### 示例 2：候选结果

输入：

```text
某个歧义较大的关键词
```

输出形态：

```text
未找到足够可信的主词条，以下词条可能相关：
1. 词条A
简介：……
链接：……
2. 词条B
简介：……
链接：……
```

---

## License

MIT License. 详见 [LICENSE](./LICENSE)。
