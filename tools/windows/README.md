# Windows 使用

Windows 侧主要负责编辑、Git、压缩和可选的 ROS 2 可视化：

```powershell
.\Set-RosNetwork.ps1
.\Build-RosInterfaces.ps1
.\Pack-Workspace.ps1
```

目标位置默认是 `E:\RoboMaster\Sentinel\workspace`。PowerShell 脚本不会删除已有目标；
`Install-Workspace.ps1` 遇到已有目录会停止，只有显式 `-Force` 才覆盖同名文件。

压缩脚本默认排除 ROS 构建产物和导入的旧 Isaac-RM 大体积资产，因此包可以在
Windows 与 Ubuntu 之间稳定传输。原始 `Isaac-RM.zip` 在 Ubuntu 上再用
`tools/common/import_isaac_rm.py` 导入。
