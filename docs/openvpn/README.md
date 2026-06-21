# OpenVPN 集成配置说明

本文档用于把 OpenVPN 服务器接入 OIM 系统，支持：

- 证书签发与配置下载
- 在线会话上报
- 连接日志上报
- 断开流量上报
- 按服务器/证书/部门做流量统计与告警

## 文件说明

- `local-development.env.example`：本地开发环境的后端环境变量模板。
- `production.env.example`：线上部署环境的后端环境变量模板。
- `openvpn-server-local.conf.template`：本地开发联调时追加到 OpenVPN 服务端配置的片段。
- `openvpn-server-production.conf.template`：线上部署时追加到 OpenVPN 服务端配置的片段。
- `openvpn-server-record.example.json`：系统“OpenVPN服务器管理”里的字段填写模板。
- `install-openvpn-oim-hooks.sh`：把事件脚本和配置片段安装到新 OpenVPN 服务器的参考脚本。

## 本地开发与线上部署隔离

本地开发通常使用 SSH 反向隧道把远端 OpenVPN 服务器回调转发到本机后端：

```bash
ssh -N -R 18080:127.0.0.1:8000 -i ~/.ssh/<ssh-key> root@<openvpn-server-ip>
```

本地 OpenVPN 回调地址使用：

```text
http://127.0.0.1:18080
```

线上部署不要使用这个地址，应使用后端线上服务在 OpenVPN 服务器可访问的内网或公网地址，例如：

```text
https://oim.example.com/api
```

## 必须保持一致的配置

`OPENVPN_EVENT_SECRET` 必须与 OpenVPN 服务端配置中的 `OIM_OPENVPN_EVENT_TOKEN` 完全一致。

不要把真实密钥提交到 Git。模板中的 `CHANGE_ME_*` 都需要在实际部署时替换。

## 新增 OpenVPN 服务器时的默认路径

以下字段可以不在页面手动填写，后端会根据环境变量和默认规则自动补齐：

| 页面字段 | 默认来源 |
| --- | --- |
| SSH私钥路径 | `OPENVPN_DEFAULT_SSH_KEY_PATH`。如果为空，则使用系统默认 SSH identity/agent |
| Easy-RSA目录 | `OPENVPN_DEFAULT_EASY_RSA_DIR`，默认 `/etc/openvpn/easy-rsa` |
| PKI目录 | `Easy-RSA目录/pki` |
| CA证书路径 | `PKI目录/ca.crt` |
| TLS密钥路径 | `OPENVPN_DEFAULT_TLS_CRYPT_KEY_PATH`，默认 `/etc/openvpn/tls-crypt.key` |
| CRL路径 | `PKI目录/crl.pem` |
| 证书输出目录 | `OPENVPN_CLIENT_CONFIG_ROOT` |

证书归档目录结构：

```text
OPENVPN_CLIENT_CONFIG_ROOT/服务器编码/部门编码/用户名/
```

客户端配置文件命名保持：

```text
部门编码-用户名-服务器IP.ovpn
```

仍建议用户填写或确认的字段：

- 服务器名称
- 服务器编码
- 区域
- 公网 IP / 域名
- 端口
- 协议
- 最大连接数
- 证书后端
- SSH 用户

如果某台 OpenVPN 服务器路径与默认值不同，再在页面高级字段中单独覆盖。

## 服务器端脚本路径建议

建议统一放在：

```text
/etc/openvpn/oim-client-connect.sh
/etc/openvpn/oim-client-disconnect.sh
```

安装后需要赋予执行权限：

```bash
chmod 0755 /etc/openvpn/oim-client-connect.sh /etc/openvpn/oim-client-disconnect.sh
```

## OpenVPN 服务端配置必须包含

```text
script-security 2
client-connect /etc/openvpn/oim-client-connect.sh
client-disconnect /etc/openvpn/oim-client-disconnect.sh
```

并根据环境选择本地或线上配置片段中的 `setenv`。

## 验证

在 OpenVPN 服务器上验证 OIM 后端连通性：

```bash
curl -fsS <OIM_OPENVPN_EVENT_URL>/ping
```

模拟连接事件：

```bash
common_name=test-client \
ifconfig_pool_remote_ip=10.8.0.10 \
trusted_ip=1.2.3.4 \
OIM_OPENVPN_EVENT_URL=<OIM_OPENVPN_EVENT_URL> \
OIM_OPENVPN_EVENT_TOKEN=<OPENVPN_EVENT_SECRET> \
OIM_OPENVPN_SERVER_CODE=<SERVER_CODE> \
/etc/openvpn/oim-client-connect.sh
```

模拟断开事件：

```bash
common_name=test-client \
ifconfig_pool_remote_ip=10.8.0.10 \
trusted_ip=1.2.3.4 \
bytes_received=1048576 \
bytes_sent=2097152 \
OIM_OPENVPN_EVENT_URL=<OIM_OPENVPN_EVENT_URL> \
OIM_OPENVPN_EVENT_TOKEN=<OPENVPN_EVENT_SECRET> \
OIM_OPENVPN_SERVER_CODE=<SERVER_CODE> \
/etc/openvpn/oim-client-disconnect.sh
```

验证通过后，系统里应出现在线会话、连接日志和断开流量记录。

## 生产环境证书签发排查

如果发布到线上后签发证书报错，请优先检查：

1. 后端容器/服务器是否安装了 `ssh` 和 `scp`

   ```bash
   which ssh
   which scp
   ```

2. `SSH私钥路径` 是否是后端生产环境内可访问的路径，而不是开发电脑路径。

   ```bash
   ls -l <OPENVPN_DEFAULT_SSH_KEY_PATH>
   ```

3. 后端运行用户是否能读取 SSH 私钥。

   ```bash
   chmod 600 <OPENVPN_DEFAULT_SSH_KEY_PATH>
   ```

4. 后端是否能免密登录 OpenVPN 服务器。

   ```bash
   ssh -i <OPENVPN_DEFAULT_SSH_KEY_PATH> -p 22 root@<openvpn-server-ip> 'cd /etc/openvpn/easy-rsa && ./easyrsa --version'
   ```

5. 证书归档根目录是否可写。

   ```bash
   mkdir -p <OPENVPN_CLIENT_CONFIG_ROOT>
   touch <OPENVPN_CLIENT_CONFIG_ROOT>/.write-test
   rm -f <OPENVPN_CLIENT_CONFIG_ROOT>/.write-test
   ```

6. 服务器管理中的路径是否存在：

   ```bash
   test -x /etc/openvpn/easy-rsa/easyrsa
   test -d /etc/openvpn/easy-rsa/pki
   test -f /etc/openvpn/easy-rsa/pki/ca.crt
   test -f /etc/openvpn/tls-crypt.key
   ```

生产镜像需要包含 `openssh-client`，否则远程 Easy-RSA 签发无法执行 SSH/SCP。
