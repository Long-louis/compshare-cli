# Changelog

本文档记录 `compshare-cli` 的版本变更历史。

格式参考 Keep a Changelog，版本号遵循 Semantic Versioning。

## [Unreleased]

### Changed
- 占位：下次发版前，把这里的内容整理成新的版本段落。

## [0.2.0] - 2026-05-21

### Added
- 新增 `image` 命令组，支持 `create`、`list`、`show-progress`、`delete`，覆盖自定义镜像流程。
- 新增 `disk` 命令组，支持 `attach`、`detach`、`resize`、`delete`，覆盖云硬盘管理。
- 新增实例运维命令：`rename`、`reinstall`、`resize`、`set-stop-scheduler`、`attach-us3`。
- 新增 `resource gpu-inventory`，支持按可用区和可选 GPU 型号查看库存。
- 新增 `resource images --type custom`，用于查询自定义镜像。
- 新增配套 skill 与 `AGENTS.md` 指引，覆盖扩展后的 agent 工作流。

### Changed
- 扩展测试用 fake client 与测试集，覆盖镜像、云硬盘、实例运维、GPU 库存相关 API。
- 为会产生费用或变更资源状态的命令增加显式确认：`image delete`、`instance reinstall`、`instance resize`、`instance attach-us3`、所有 `disk` 写操作。
- 改进新命令的错误处理，保证 `--json` 与 `--agent` 输出在失败时仍然可解析。
- 为 `resource gpu-inventory` 增加空 zone 返回时的安全处理。

## [0.1.0] - 2026-05-10

### Added
- 初始版 `compshare` CLI，覆盖 CompShare GPU 租用的基础闭环。
- 新增凭据管理命令：`config set`、`config get`、`config unset`、`config path`。
- 新增资源发现命令：`resource zones`、`resource instance-types`、`resource images`、`resource machine-families`、`resource capacity`。
- 新增查价命令：`price create`。
- 新增实例生命周期命令：`instance create`、`list`、`show`、`start`、`stop`、`reboot`、`delete`。
- 新增默认人类可读输出和结构化 `--json` 输出。
- 新增配置、请求构建、SDK 包装、输出辅助和 CLI 流程测试。
