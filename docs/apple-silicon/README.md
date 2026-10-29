# Apple Silicon 适配候选版本

基础仓库：https://github.com/unoplatform/calculator
基础提交：c32d9b20ee49a394370afd5e73cd7d2f48507cc8
用户提供的 LuisFX/Uno.Calculator 是该仓库的旧分支。

状态：源码修改及构建流程已准备，尚未执行 macOS 编译和功能验收。

## 改动

- 使用已有的 Mac Catalyst 应用和 C++ 计算引擎，明确选择 maccatalyst-arm64。
- 原生引擎按架构隔离临时对象文件，使用正确的 Ratpack 目录大小写。
- 明确 Mac Catalyst 静态库入口及原生回调条件，保留静态库导出函数。
- CommunityBuild=true 使用独立 bundle ID 及 ad-hoc 签名，不需要上游证书。
- 自动生成 DMG、应用 ZIP、SHA256 和日志；打包前检查全部 Mach-O 架构及签名。
- 不发布 GitHub Release、不提交至应用商店；只产生 Actions 构建产物。

## GitHub 构建

1. 将改动放入自己拥有的上游 fork 的 community-arm64 分支。
2. 在 fork 中启用 Actions。将工作流合入默认分支后，可以在 Actions →
   Build Apple Silicon calculator → Run workflow 手动运行；
   community-arm64 分支后续的相关文件推送也会触发构建。
3. 等待结果。成功后下载 Uno-Calculator-arm64 产物；失败时查看步骤日志及
   Uno-Calculator-build-logs。首次构建仍可能需要解决上游依赖或工具链兼容问题。
4. 在自己的 M 芯片 Mac 上按 TESTING.md 验收。

固定初次构建基线：.NET SDK 9.0.302 / workload set 9.0.302.0 / Xcode 16.4。
匹配关系来自官方发布说明：
https://github.com/dotnet/macios/releases/tag/dotnet-9.0.1xx-xcode16.4-9207
GitHub macos-15 标签当前为 ARM64，流程会在开头验证实际架构。
若 GitHub 移除该 Xcode 镜像或依赖不再可用，需要配套升级工具链后再构建。

## 本机构建（备用）

在安装上述 Xcode、.NET SDK 和 Mac Catalyst workload 的 Mac 上运行：

```bash
bash scripts/build-apple-silicon.sh
```

构建输出在 artifacts/。发布给更多用户之前，应升级并复核受支持的依赖，
使用自己的 Developer ID 做正式签名及公证，并完成功能测试。
