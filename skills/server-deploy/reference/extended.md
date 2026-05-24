# server-deploy Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## 第八步：安全加固`.

## 第八步：安全加固

部署完成后，调用 `/server-security` skill 进行完整安全审计。

如果用户不想跑完整审计，至少执行**最小安全加固**：

### 8a. 防火墙

```bash
ssh $SSH_TARGET "ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw default deny incoming && ufw default allow outgoing && echo 'y' | ufw enable"
```

**关键**：先放通 22 端口再 enable。启用后立即验证 SSH 连通性。

### 8b. fail2ban

```bash
ssh $SSH_TARGET "apt-get install -y -qq fail2ban && cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = ssh
maxretry = 3
bantime = 86400
EOF
systemctl enable fail2ban && systemctl restart fail2ban"
```

### 8c. 文件权限

```bash
ssh $SSH_TARGET "find $REMOTE_DIR -name '.env*' -exec chmod 600 {} \; 2>/dev/null"
ssh $SSH_TARGET "find $REMOTE_DIR \( -name '*.db' -o -name '*.sqlite' \) -exec chmod 600 {} \; 2>/dev/null"
```

---

## 第九步：最终验证

并行验证所有组件：

```bash
# 应用响应
curl -s -o /dev/null -w '%{http_code}' https://$DOMAIN 2>/dev/null || curl -s -o /dev/null -w '%{http_code}' http://<IP>:$PORT

# 进程状态（按项目类型）
ssh $SSH_TARGET "pm2 list 2>/dev/null; systemctl status $PROJECT_NAME 2>/dev/null; docker compose ps 2>/dev/null"

# 安全
ssh $SSH_TARGET "ufw status && fail2ban-client status sshd 2>/dev/null"
```

全部通过后输出总结：

```
## 部署完成

| 项目 | 状态 |
|------|------|
| 项目 | $PROJECT_NAME ($PROJECT_TYPE) |
| 服务器 | $SSH_TARGET |
| 部署路径 | $REMOTE_DIR |
| 运行端口 | $PORT |
| 进程管理 | PM2 / systemd / docker（状态 online） |
| 开机自启 | 已配置 |
| 域名 | $DOMAIN（或"仅 IP"） |
| SSL | Cloudflare Origin / Let's Encrypt / 无 |
| 防火墙 | UFW 启用 |
| fail2ban | SSH 防护已启用 |
| 访问地址 | https://$DOMAIN 或 http://<IP>:$PORT |
```

---

## 踩坑总结

| # | 坑 | 原因 | 正确做法 |
|---|-----|------|----------|
| 1 | rsync 大文件传输 SSH 断连 | 服务器 SSH 默认超时短 | 调整 ClientAliveInterval=60，rsync 加 ServerAliveInterval=30 |
| 2 | rsync 断连不丢进度 | 增量传输 | 重试即可，自动跳过已传文件 |
| 3 | 构建超时断连 | SSH 会话中断终止前台进程 | 用 nohup 后台执行，日志写 /tmp |
| 4 | Cloudflare 521 错误 | 服务器只有 HTTP，CF 用 HTTPS 连 | 配 SSL 或 CF 改 Flexible |
| 5 | Cloudflare 526 错误 | Origin Certificate 无效 | 检查 SAN 包含域名 + Key Usage 包含 Server Auth |
| 6 | Origin Certificate 缺域名 | 创建时未填主机名 | 重新创建，包含 domain 和 *.domain |
| 7 | Full (Strict) 526 | 证书链不完整 | cert.pem + origin-ca-rsa-root.pem → fullchain.pem |
| 8 | UFW 启用后锁死 | 忘记先放通 22 端口 | 先 `ufw allow 22/tcp` 再 `ufw enable` |
| 9 | Nginx 多 server 块冲突 | 多配置监听同端口 | 删 default，每项目独立配置 |
| 10 | PM2 重启丢进程 | 未 save | `pm2 startup && pm2 save` |
| 11 | Rust 服务器编译 OOM | 小内存 VPS 编译大项目 | 本地交叉编译，仅上传二进制 |
| 12 | Go 二进制架构不匹配 | 本地 arm64 编译的放到 x86 服务器 | GOOS=linux GOARCH=amd64 交叉编译 |
| 13 | Python venv 路径硬编码 | 本地 venv 上传到服务器路径不同 | 远程重新创建 venv，不上传本地 venv |
| 14 | systemd 服务启动失败无日志 | 没看 journalctl | `journalctl -u $PROJECT_NAME -f` 排查 |
| 15 | Docker 端口映射冲突 | 主机端口已占用 | `lsof -i:$PORT` 先检查 |
| 16 | .env 权限 644 泄露密钥 | rsync 保留权限 | 部署后 chmod 600 |
| 17 | Nginx 暴露版本号 | 默认配置 | `server_tokens off` |
| 18 | 服务器连接频率限制 | 短时间多次 SSH 触发保护 | 等 30-60 秒后重试 |
| 19 | Cloudflare 缓存命中率低 | Next.js 默认不设 Cache-Control | next.config.ts 配置 headers：静态资源 immutable、uploads s-maxage=30d、API no-store |
| 20 | ISR 页面不被 CDN 缓存 | 页面没有 revalidate 导致每次回源 | 按变化频率设 revalidate：首页 1h、详情页 24h |
| 21 | CI/CD 构建缺环境变量 | NEXT_PUBLIC_* 变量需构建时注入 | GitHub Secrets 添加变量，workflow build 步骤 env 注入 |
| 22 | 外链图片在国内加载失败 | Steam CDN / SteamGridDB 被墙 | 批量下载到 public/uploads/，数据库改本地路径，rsync 同步到服务器 |
| 23 | 服务器无 sqlite3 CLI | 精简系统未安装 | 用 node + better-sqlite3 执行 SQL，或安装 sqlite3 |

---

## 注意事项

- 自动识别项目类型，不要假设是 Node.js
- Rust/Go 低配服务器优先本地交叉编译
- Python 不要上传本地 venv，远程重建
- 所有 SSH 长操作加 ServerAliveInterval 防断连
- 构建操作用 nohup 后台执行
- 每次改网络配置后立即验证 SSH 连通性
- 敏感文件部署后立即修正权限
- 使用中文输出所有信息
