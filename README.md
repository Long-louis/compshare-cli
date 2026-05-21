# compshare-cli

面向 [CompShare](https://www.compshare.cn/) 云 GPU 租用平台的 Python 命令行工具，覆盖智能体和人工终端常用的租用闭环：查询资源、查价、容量检查、创建前 dry-run、实例列表/详情、启动/停止/重启/删除。

English documentation: [`README.en.md`](README.en.md)

## 安装

公开仓库用户可以直接从 Git 仓库安装：

```bash
uv tool install git+https://github.com/Long-louis/compshare-cli.git
```

本地开发：

```bash
git clone https://github.com/Long-louis/compshare-cli.git
cd compshare-cli
uv sync
uv run compshare --help
```

如果你使用 fork 或其他镜像仓库，把上面的 Git URL 替换成对应仓库地址即可。

## 给 Code Agent 安装配套 Skill

本仓库包含 `compshare-cli` skill，用来提醒 Claude Code、OpenCode、Cursor 等 code agent 按安全流程使用本 CLI。

交互式安装：

```bash
npx skills add Long-louis/compshare-cli
```

运行后按提示选择安装范围、目标 agent 和 `compshare-cli` skill。

如果要先查看仓库内可安装的 skills：

```bash
npx skills add Long-louis/compshare-cli --list
```

安装后，当你让 code agent 准备或控制 CompShare GPU 实例时，它应优先从 `compshare doctor --agent` 开始，再执行查价、容量检查、dry-run 和需要确认的创建/删除操作。

## 获取 Public Key 和 Private Key

CLI 调用 CompShare API 需要平台账号的 `Public Key` 和 `Private Key`。

获取方式：

1. 登录 [CompShare 网页控制台](https://www.compshare.cn/)。
2. 进入账号/API 密钥管理相关页面。
3. 找到平台提供的 `Public Key` 和 `Private Key`。
4. 将它们配置到本机环境变量或 CLI 本地配置中。

安全注意事项：

- 不要把 `Private Key` 粘贴到聊天记录、Issue、日志或 README 示例里。
- `compshare config get` 默认会掩码显示密钥。
- 如果要给智能体使用，建议先在本机配置好密钥，再让智能体运行只读命令。

## 配置凭据

方式一：使用环境变量，适合自动化和临时会话。

```bash
export COMPSHARE_PUBLIC_KEY=...
export COMPSHARE_PRIVATE_KEY=...
```

方式二：写入 CLI 本地配置，适合日常使用。

```bash
compshare config set public-key ...
compshare config set private-key ...
```

环境变量优先级高于本地配置文件。

检查配置：

```bash
compshare config get
compshare doctor --agent
```

## 输出模式

默认输出面向人类终端，尽量用摘要和表格。

`--json` 输出面向脚本，只输出可解析 JSON，不应该混入 SDK 日志、自然语言解释或表格。

`--agent` 输出面向 code agent，返回稳定 JSON envelope，包含：

- `ok`：命令是否成功。
- `summary`：一句话结论。
- `data`：结构化事实数据。
- `warnings`：风险或注意事项。
- `next_actions`：下一步建议。
- `commands`：可复制的后续命令，每条都带 `risk` 和 `requires_confirmation`。
- `cost_risk`：整体风险，例如 `read-only`、`cost-incurring`、`destructive`。

`--agent --debug` 保留给调试场景，诊断信息不能泄露密钥。

## 版本发布

仓库使用 `CHANGELOG.md` 作为 GitHub Release 文案的唯一来源。

推荐发版流程：

1. 更新 `pyproject.toml` 和 `src/compshare_cli/__init__.py` 里的版本号。
2. 把 `CHANGELOG.md` 里的 `Unreleased` 整理成版本段落，例如 `## [0.3.0] - 2026-05-22`。
3. 提交并推送代码到 `master`。
4. 创建并推送 tag：

```bash
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0
```

5. GitHub Actions 会自动：
   - 运行 `uv run pytest -v`
   - 从 `CHANGELOG.md` 提取对应版本段落
   - 创建 GitHub Release

如果 `CHANGELOG.md` 没有对应版本段落，自动发布会失败，这样可以避免发布出没有说明的版本。

## 智能体推荐入口

让 code agent 使用这个 CLI 时，第一条命令应该是：

```bash
compshare doctor --agent
```

它会检查：

- CLI 是否可运行。
- 凭据是否存在以及来源。
- API 是否可访问。
- 支持的区域/可用区。
- 当前账号下已有实例摘要。

## 常用只读流程

这些命令不会创建或删除资源，适合先让智能体执行：

```bash
compshare doctor --agent
compshare resource zones --agent
compshare resource images --type platform --json
compshare resource images --type community --json
compshare instance list --agent
```

## 查价

```bash
compshare price create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200 \
  --agent
```

## 容量检查

```bash
compshare resource capacity \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200 \
  --json
```

## 创建前 dry-run

创建前先 dry-run，检查请求体，不产生费用：

```bash
compshare instance create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200 \
  --name my-gpu \
  --dry-run \
  --agent
```

## 创建实例

真实创建实例会产生费用，必须显式加 `--yes`：

```bash
compshare instance create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200 \
  --name my-gpu \
  --agent \
  --yes
```

建议让智能体执行真实创建前先完成：

1. `doctor --agent`
2. `resource zones --agent`
3. `price create --agent`
4. `resource capacity --json`
5. `instance create --dry-run --agent`
6. 获得用户明确确认后，再执行 `instance create --agent --yes`

## 管理实例

```bash
compshare instance list --agent
compshare instance show <INSTANCE_ID> --agent
compshare instance start <INSTANCE_ID> --agent
compshare instance stop <INSTANCE_ID> --agent
compshare instance reboot <INSTANCE_ID> --agent
compshare instance delete <INSTANCE_ID> --agent --yes
```

风险规则：

- `start` 可能导致计费，智能体执行前应获得用户确认。
- `delete` 是破坏性操作，必须显式确认并加 `--yes`。
- `stop` 后是否仍计费取决于平台计费规则，执行前应结合实例状态和平台说明判断。

## 参考资料

- [CompShare 操作示例文档](https://www.compshare.cn/docs/gpus/operationexample)
- [CompShare Python SDK 示例](https://github.com/ucloud/compshare-developer-examples/tree/main/python-sdk/compshare)

## 开源协议

[MIT](LICENSE)
