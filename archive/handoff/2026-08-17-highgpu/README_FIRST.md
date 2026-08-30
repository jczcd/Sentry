# Sentinel Work Handoff ZIP

推荐使用顺序：

## 新 Work 会话
把整个 ZIP 上传到新的 Work 会话。
第一条复制：
WORK_FIRST_PROMPT.txt

## 新电脑 Codex
把真正的 Sentinel 工程复制到新电脑后，
在仓库根目录启动 Codex，
粘贴：
CODEX_RESUME_PROMPT_HIGH_GPU.txt

## 如果还没有真正的当前源码 ZIP
在旧电脑运行：
make_real_full_project_zip.sh

详见：
HOW_TO_CREATE_REAL_PROJECT_ZIP.md

## 本包内容
- PROJECT_HANDOFF.md：完整项目交接
- CURRENT_TASK.md：当前短期任务
- NEW_HIGH_GPU_PC_PLAN.md：高性能电脑重新 benchmark 原则
- WORK_FIRST_PROMPT.txt：新 Work 会话首条提示词
- CODEX_RESUME_PROMPT_HIGH_GPU.txt：Codex 续接提示词
- make_real_full_project_zip.sh：从真实旧电脑打包当前工程
- references/：最近阶段日志、Mid-360官方手册、GUI截图

注意：
本包本身不是 Ubuntu 当前实时源码仓库镜像。
实际源码请运行 make_real_full_project_zip.sh。
