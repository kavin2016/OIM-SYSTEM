# WireGuard VPN 配置模式

OIM 的 VPN 管理支持两种模式：

- OpenVPN：使用 Easy-RSA 签发证书，下载 `.ovpn`。
- WireGuard：系统生成客户端密钥，通过 SSH 在服务器上添加 peer，下载 `.conf`。

## 生产服务器准备

WireGuard 服务器需要先完成基础安装，并确保后端能 SSH 登录该服务器。

服务器上建议使用接口：

```text
wg0
```

常见服务器端配置：

```ini
[Interface]
Address = 10.66.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key>
```

启动服务：

```bash
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0
wg show wg0
```

## OIM 页面新增服务器

进入：

```text
运维管理 / VPN管理 / 服务器管理
```

选择：

```text
VPN类型 = WireGuard
```

通常只需要填写：

- 区域
- 公网 IP / 域名
- 最大连接
- SSH 用户
- SSH 私钥内容

系统会自动补齐：

- 端口：`51820`
- 协议：`udp`
- WG接口：`wg0`
- 客户端网段：`10.66.0.0/24`
- DNS：`1.1.1.1,1.0.0.1`
- AllowedIPs：`0.0.0.0/0,::/0`
- Keepalive：`25`
- SSH私钥路径：`/data/oim/ssh/<服务器编码>.key`

保存后点击“测试配置”，系统会通过 SSH 执行：

```bash
wg show wg0 public-key
```

测试通过后即可给用户开通账号。

## 用户开通流程

1. 在“用户管理”里开通 VPN 账号。
2. 选择 WireGuard 服务器。
3. 点击“签发凭据”。
4. 系统自动生成客户端密钥和客户端地址。
5. 系统通过 SSH 执行 `wg set` 添加 peer。
6. 点击“下载配置”，得到 `.conf` 文件。

吊销凭据或吊销账号时，系统会从 WireGuard 服务器上移除 peer。
