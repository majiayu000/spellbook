#!/usr/bin/env bash
# 生成 macOS Tahoe Electron 修复相关的完整命令和 plist 内容
# 用法：./generate_tahoe_fix.sh

set -euo pipefail

echo "=== macOS 26 Tahoe Electron 修复 - 完整方案 ==="
echo ""

cat << 'EOF'
## 第一步：立即生效的两个命令（推荐先执行）

# 1. 关闭 autofill 启发式（解决输入延迟）
defaults write -g NSAutoFillHeuristicControllerEnabled -bool false

# 2. 让 Electron 应用走无阴影渲染路径（大幅降低 WindowServer GPU）
launchctl setenv CHROME_HEADLESS 1

# 执行完后必须：完全退出 VSCode / Cursor（不要只是关闭窗口）
# 建议用 Activity Monitor 确认没有残留的 "Code Helper" / "Cursor Helper" 进程

## 第二步：持久化方案（推荐）

# 创建 LaunchAgent，让每次登录都自动设置 CHROME_HEADLESS
mkdir -p ~/Library/LaunchAgents

# 如果文件已存在，先备份：
# [ -f ~/Library/LaunchAgents/com.user.chrome-headless.plist ] && \
#   cp ~/Library/LaunchAgents/com.user.chrome-headless.plist \
#      ~/Library/LaunchAgents/com.user.chrome-headless.plist.backup.$(date +%Y%m%d%H%M%S)
#
# 将下面的内容完整保存为：
# ~/Library/LaunchAgents/com.user.chrome-headless.plist
EOF

echo ""
echo "=== 推荐的 plist 完整内容（直接复制保存） ==="
echo ""

cat << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.chrome-headless</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/launchctl</string>
        <string>setenv</string>
        <string>CHROME_HEADLESS</string>
        <string>1</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
PLIST

echo ""
echo "=== 加载命令 ==="
echo ""
cat << 'EOF'
# 保存 plist 后执行：
launchctl load ~/Library/LaunchAgents/com.user.chrome-headless.plist

# 验证是否生效：
launchctl getenv CHROME_HEADLESS
# 应该输出：1

# 如需卸载：
# launchctl unload ~/Library/LaunchAgents/com.user.chrome-headless.plist
# rm ~/Library/LaunchAgents/com.user.chrome-headless.plist
EOF

echo ""
echo "=== 验证命令（执行修复后运行） ==="
echo ""
cat << 'EOF'
# 查看 WindowServer 当前占用
ps aux | grep -i WindowServer | grep -v grep

# 查看是否还有大量 Renderer 进程吃资源
ps aux | grep -E 'Code Helper \(Renderer\)|Cursor Helper \(Renderer\)' | grep -v grep | sort -k3 -rn | head -5
EOF

echo ""
echo "=== 回滚方法 ==="
echo ""
cat << 'EOF'
# 恢复 autofill
defaults delete -g NSAutoFillHeuristicControllerEnabled

# 移除环境变量（当前会话）
launchctl unsetenv CHROME_HEADLESS

# 删除持久化
launchctl unload ~/Library/LaunchAgents/com.user.chrome-headless.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.user.chrome-headless.plist
EOF

echo ""
echo "=== 额外推荐：禁用硬件加速 ==="
echo ""
cat << 'EOF'
# 这是实验项。不要直接覆盖已有 argv.json。
# 先检查原文件：
ls -l ~/Library/Application\ Support/Cursor/argv.json 2>/dev/null || true
ls -l ~/Library/Application\ Support/Code/argv.json 2>/dev/null || true

# 如果对应文件不存在，可以新建为下面内容。
# 如果已经存在，请把这一项手动合并进去，或先备份再改。

# Cursor argv.json 片段：
{
  "disable-hardware-acceleration": true
}

# VSCode argv.json 片段：
{
  "disable-hardware-acceleration": true
}

# 修改后必须完全重启编辑器
EOF

echo ""
echo "生成完毕。请把上面内容提供给用户。"
