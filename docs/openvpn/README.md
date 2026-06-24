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
- `WIREGUARD.md`：WireGuard VPN 配置模式说明。
- `openvpn-server-local.conf.template`：本地开发联调时追加到 OpenVPN 服务端配置的片段。
- `openvpn-server-production.conf.template`：线上部署时追加到 OpenVPN 服务端配置的片段。
- `openvpn-server-record.example.json`：系统“OpenVPN服务器管理”里的字段填写模板。
- `prepare-oim-openvpn-storage.sh`：在 OIM 生产宿主机上准备 OpenVPN 持久化目录和 SSH 私钥权限。
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
| SSH私钥路径 | 默认使用 `OPENVPN_SSH_KEY_DIR/服务器编码.key`；`OPENVPN_DEFAULT_SSH_KEY_PATH` 仅作为无服务器编码时的兜底 |
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

创建或编辑 OpenVPN 服务器时，也可以在“高级路径配置（可选）”中填写 `SSH私钥内容`。系统会把私钥写入后端容器可访问的路径，并只在数据库中保存私钥文件路径，不保存私钥明文。

## 新增 OpenVPN 服务器的生产默认操作

OIM 后端生产容器默认把项目目录下的 `./data/oim` 挂载为容器内 `/data/oim`。新增服务器时建议使用“服务器编码 + 私钥文件”的固定规则：

```text
宿主机路径：./data/oim/ssh/<服务器编码>.key
容器内路径：/data/oim/ssh/<服务器编码>.key
```

在 OIM 生产宿主机的项目目录执行：

```bash
sh docs/openvpn/prepare-oim-openvpn-storage.sh <服务器编码> /path/to/private-key
```

例如：

```bash
sh docs/openvpn/prepare-oim-openvpn-storage.sh PH-191 ~/.ssh/PH-191.key
```

如果不想在宿主机手动复制私钥，也可以在系统页面新增或编辑 OpenVPN 服务器时填写 `SSH私钥内容`，后端会自动写入：

```text
/data/oim/ssh/<服务器编码>.key
```

保存服务器后，可以在生产宿主机验证容器内路径：

```bash
docker compose exec backend ls -l /data/oim/ssh/<服务器编码>.key
docker compose exec backend ssh -i /data/oim/ssh/<服务器编码>.key -p 22 <SSH用户>@<OpenVPN服务器IP> 'echo ok'
```

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

   如果服务器管理里已经保存了开发机路径，例如 `/Users/kavin/.ssh/PH-191.key`，需要在页面里清空该字段或改为容器内路径：

   ```text
   /data/oim/ssh/<服务器编码>.key
   ```

   也可以直接执行 SQL 修正已有记录：

   ```sql
   UPDATE openvpn_servers
   SET ssh_key_path = CONCAT('/data/oim/ssh/', code, '.key')
   WHERE certificate_backend = 'ssh_easyrsa'
     AND ssh_key_path LIKE '/Users/%';
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
