# environment_provider 安装与配置

该插件通过 Hermes 的 `llm_request` 中间件，在请求发送给模型前临时附加当前日期时间、时区、星期、手动地点、天气和电池状态。环境块不写入可见消息或 `api_content` 历史侧车；请求中若含旧版插件遗留的环境块，也会仅在出站副本中清理。它不修改 `SOUL.md`、Prompt、Skill、Memory、工作区或会话数据库；删除插件后不会影响 Agent 的其他功能。

## 1. 安装依赖

天气和时间功能只使用 Python 标准库。电池读取需要 `psutil`，读取 `config.yaml` 需要 `PyYAML`。请在对应 Hermes profile 的 Python 环境中安装：

Windows PowerShell：

```powershell
& "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe" -m pip install psutil PyYAML
```

macOS：

```bash
python3 -m pip install psutil PyYAML
```

如果没有 `psutil`，插件仍会加载，只会把电池显示为“不可用”。

## 2. 复制插件

把整个 `environment_provider` 目录复制到目标 profile 的 `plugins` 目录。必须保留目录层级，确保 `plugin.yaml` 与 `__init__.py` 位于同一级。

Windows 示例（xiaoling profile）：

```powershell
$src = ".\plugins\environment_provider"
$dst = "$env:LOCALAPPDATA\hermes\profiles\xiaoling\plugins\environment_provider"
Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
```

macOS 示例：

```bash
cp -R ./plugins/environment_provider ~/.hermes/plugins/environment_provider
```

若使用 Hermes Desktop 的独立 profile，请以该 profile 实际目录为准，不要把插件只复制到其他 profile。

## 3. 配置地点与语言

编辑安装后插件目录中的 `config.yaml`：

```yaml
language:
  mode: zh_CN      # 默认中文；也可设为 auto 或 en_US

location:
  mode: manual
  query:            # 发送给天气服务的稳定查询名称
    city: Wuhan
    country: China
  display:          # 仅用于注入文本的本地化名称
    zh_CN:
      city: 武汉
      country: 中国
    en_US:
      city: Wuhan
      country: China
```

V1 不使用 GPS 或 IP 定位。`query` 与 `display` 分离，因此不需要内置全球城市中英文对照表；没有对应语言的 `display` 时会回退到查询名称。旧版 `city`／`country` 顶层写法仍可读取，但不会自动翻译。

天气请求使用 `wttr.in`，不需要 API Key。中文模式优先读取服务返回的中文天气描述，缺失时使用覆盖 49 个天气代码的内置中文兜底（扩展天气码 `149` 为“烟霾”），再回退到英文。缓存有效期默认为 30 分钟，缓存格式升级时会自动绕过旧缓存。天气、网络或电池读取失败不会中断 Hermes。

## 4. 启用并重启

在目标 profile 对应的 Hermes 环境中执行：

```text
hermes plugins list
hermes plugins enable environment_provider
```

也可以在该 profile 的 `config.yaml` 中把 `environment_provider` 加入 `plugins.enabled`。若它同时出现在 `plugins.disabled`，必须先从禁用列表移除。完成后重启 Hermes CLI 或 Gateway。

## 5. 验证

```text
hermes plugins list
```

应看到 `environment_provider` 为 enabled。随后询问 Agent 当前日期、星期、天气或电量；模型收到的临时环境块应包含独立的“星期”字段，例如 `星期：星期日`。聊天记录正文中不应出现该环境块。

离线测试：

Windows PowerShell：

```powershell
$env:PYTHONPATH = (Resolve-Path .\plugins).Path
python -m unittest discover -s .\plugins\environment_provider\tests -v
```

macOS：

```bash
PYTHONPATH="$(pwd)/plugins" python3 -m unittest discover -s ./plugins/environment_provider/tests -v
```

排错时可临时设置 `HERMES_PLUGINS_DEBUG=1` 后运行 `hermes plugins list`。常见问题是目录层级过深、缺少 `__init__.py`、插件未加入允许列表，或修改后没有重启 Gateway。

## 6. 卸载

先执行：

```text
hermes plugins disable environment_provider
```

再删除目标 profile 下的 `plugins/environment_provider` 目录并重启 Hermes。插件没有修改核心代码、人格、Memory 或工作区，因此无需其他回滚步骤。
