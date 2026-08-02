# environment_provider

`environment_provider` 是一个面向 Hermes Agent 的开源环境信息注入插件。它在每次调用大语言模型前，通过 `pre_llm_call` hook 注入简短、可本地化的现实环境信息，让 Agent 能感知当前时间、星期、手动配置的地点、天气、电量和充电状态。

插件不会修改 Agent 的 Prompt、Skill、Memory、工作区或会话历史。天气、电池或配置读取失败时采用 fail-open 策略，不会阻断 Hermes 对话。

## 功能

- 当前日期、时间、时区和星期几。
- 手动配置城市与国家，不使用 GPS 或 IP 自动定位。
- 通过 `wttr.in` 获取天气、温度、湿度和风速，无需 API Key。
- 获取设备电量及充电状态。
- 中文和英文输出，可自动选择或在配置中固定。
- 天气结果本地缓存，默认 30 分钟。
- 控制注入文本长度，默认最多 1600 个字符。
- Windows 与 macOS 支持。

典型中文注入内容如下：

```text
【现实环境信息】
当前时间：2026-08-02 21:30:00
时区：Asia/Shanghai
星期：星期日
地点：武汉 / 中国
天气：Clear
温度：34°C
湿度：45%
风速：12 km/h
电量：72%
充电状态：未充电
```

具体字段会随可用信息变化。某项信息不可用时，插件不会伪造结果。

## 依赖

- Python 3.10 或更高版本。
- `PyYAML`：读取插件配置。
- `psutil`：读取电池状态；缺少时其他功能仍可使用。
- 能访问 `wttr.in` 的网络环境：仅天气功能需要。

在 Hermes 使用的 Python 环境中安装依赖：

```bash
python -m pip install PyYAML psutil
```

## 安装

克隆仓库，并确保最终目录名和层级为 `plugins/environment_provider`：

```bash
git clone https://github.com/liqiming-whu/environment_provider.git environment_provider
```

将整个目录复制或克隆到目标 Hermes profile 的 `plugins` 目录。Windows Hermes Desktop 的 profile 通常形如：

```text
%LOCALAPPDATA%\hermes\profiles\<profile-name>\plugins\environment_provider
```

然后启用插件并重启对应 Hermes 进程：

```text
hermes plugins enable environment_provider
```

多个 Hermes profile 彼此隔离，需要分别安装、配置和启用。更详细的平台命令和排错说明见 [INSTALLATION.md](INSTALLATION.md)。

## 配置

编辑插件根目录中的 `config.yaml`：

```yaml
enabled: true

language:
  mode: auto       # auto、zh_CN 或 en_US

weather:
  enabled: true
  cache_minutes: 30
  timeout_seconds: 3

battery:
  enabled: true

location:
  mode: manual
  city: Wuhan
  country: China

max_injected_chars: 1600
```

当前版本只支持手动地点。`city` 和 `country` 会发送给 `wttr.in` 以查询天气，请勿填写不希望发送给该服务的精确地址或其他隐私信息。

## 测试

从仓库的上级目录运行，使仓库目录作为 `environment_provider` Python 包被导入：

Windows PowerShell：

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m unittest discover -s .\environment_provider\tests -v
```

macOS/Linux：

```bash
PYTHONPATH="$(pwd)" python3 -m unittest discover -s ./environment_provider/tests -v
```

测试覆盖星期字段、中英文格式、天气缓存与失败回退、电池读取、缺失配置以及 Hermes hook 注册。

## 设计边界

- 插件只提供环境事实，不负责规定 Agent 应如何回应这些信息。
- 不修改 Hermes 核心代码，也不持久化注入内容到 Memory 或工作区。
- 不提供 GPS、IP 定位或后台定位。
- 天气来自第三方服务，准确性和可用性取决于 `wttr.in`。
- Hermes 不同发行版的插件 API 可能变化；当前实现依赖 `pre_llm_call` 与 `register_hook` 接口。

## 开源许可

本项目采用 [MIT License](LICENSE)。
