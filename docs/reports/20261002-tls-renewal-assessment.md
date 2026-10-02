# TLS 续期评估（遗留 #5）：结论 ① —— 续期已自动化且 80/443 有保障，降为「运维常识项」

> 分支 `docs/tls-renewal-20261002`（基于 main `7fe8b80`）；**已于 2026-10-02 经 T19 `--no-ff` 合并进 main（merge `6db27a6`）**。
> 本轮**只取证与评估**：不改 `.env`/`settings.yml`/闸门参数、不重启任何容器、不动现网。

## 0. 结论摘要（选 ①）

| 项 | 结论 | 依据类型 |
| --- | --- | --- |
| ACME 方式 | **Let's Encrypt ACME（证书域名 `43.106.104.49.sslip.io`），无 DNS-01**；续期与首签走同一条路（HTTP-01 / TLS-ALPN-01，需要公网回连 80 或 443） | **实测**（Caddyfile `tls { issuer acme; issuer internal }` + 证书签发者） |
| 续期自动化 | **Caddy 已按 ARI 排定续期窗口：2026-11-23 19:03 → 2026-11-25 14:14 UTC**（约到期前 30 天），并持续刷新续期信息 | **实测**（Caddy 日志 `got renewal info` / `updated and stored ACME renewal information`） |
| 证书现状 | Let's Encrypt 真证书，`notBefore 2026-09-25 → notAfter 2026-12-24`，**剩余 83 天**；SAN 与站点一致 | **实测**（对 `127.0.0.1:443` 握手取证书 + `cryptography` 解析） |
| 80/443 保障 | 宿主侧：`ufw inactive`、`iptables INPUT ACCEPT`、`0.0.0.0:80/443` 监听；云侧：安全组 22/80/443 已放行（2026-09-25），且**当天的 LE 签发成功本身**证明公网回连可用 | 宿主 = **实测**；安全组 = **文档 + 签发成功这一实测旁证** |
| 早期告警 | `ops_check.py` 的「证书剩余 <30 天」分支**实测可告警**：`--cert-min-days 100` 跑出 `[ALERT] … 证书剩余 83.2 天（< 100 天，到期 2026-12-24T16:19:34+00:00）`，**exit=1** 并写入 `data/ops-check.log` | **实测** |

⇒ **按 ① 结案**：把遗留 #5 从「待触发」降为**运维常识项**（安全组 22/80/443 长期放行 + 到期前 30 天
`ops_check` 证书告警会兜底），不再作为「无法提前发现」的风险项；仅在 2026-11-24 前后留一次**只读核对**。

## 1. 取证细节

### 1.1 配置与版本（实测）

* `Caddyfile`：站点块 `{$UTF8SEARCH_DOMAIN}`（默认 `43.106.104.49.sslip.io`），
  `tls { issuer acme; issuer internal }` —— **acme 优先、internal 兜底**；**没有** DNS-01 相关配置
  ⇒ 续期依赖公网回连 **80（HTTP-01）或 443（TLS-ALPN-01）**；
* `docker exec utf8-search-caddy caddy version` → **v2.11.4**；
* 证书存储：`/data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/43.106.104.49.sslip.io/`
  下 `.crt`/`.key`（Sep 25 17:18 写入）与 **`.json`（Oct 2 08:15 刷新，即 ARI 续期信息）**。

### 1.2 证书实况（实测）

```
subject  : CN=43.106.104.49.sslip.io
issuer   : CN=YE1, O=Let's Encrypt, C=US
notBefore: 2026-09-25T16:19:35+00:00
notAfter : 2026-12-24T16:19:34+00:00   （评估时剩余 83 天）
SAN      : ['43.106.104.49.sslip.io']
```

### 1.3 续期是否已经/将会发生（实测）

`docker logs utf8-search-caddy` 里可见 **2026-09-25 的首次签发**（`tls.obtain`：安全组放行前先落到
`issuer=local` 自签兜底，放行后 `obtaining certificate` → `certificate obtained successfully`，
`issuer=acme-v02.api.letsencrypt.org-directory`，UTC 17:18）；**全量日志 grep `certificate renewed` = 0 次**
—— 即 **续期尚未实际发生过**（该证书 9-25 才签发，首次续期未到期），但有**周期性**的续期排程证据：

```
http.acme_client  "got renewal info"  names=["43.106.104.49.sslip.io"]
  window_start=2026-11-23 19:03 UTC  window_end=2026-11-25 14:14 UTC
tls.cache.maintenance "updated and stored ACME renewal information"  （持续刷新）
pki "renewed intermediate" ca=local  ← 这是 internal CA 的中间证书，与 LE 证书无关
```

⇒ 与 `docs/05` §5.4 的说法一致（「到期前 30 天开始续」），而且现在有 **ARI 窗口**这一精确排程。

### 1.4 80/443 放行状态

| 面 | 状态 | 类型 |
| --- | --- | --- |
| 宿主防火墙 | `ufw: inactive`；`iptables -P INPUT ACCEPT` | 实测 |
| 监听 | `0.0.0.0:80`、`0.0.0.0:443`（docker-proxy，caddy 容器） | 实测 |
| 阿里云安全组 | **22/80/443 已放行**（2026-09-25 放行后复核通过；报告明确要求「长期放行」） | 文档 + 旁证 |
| 公网回连可用的旁证 | 该证书本身就是 **Let's Encrypt 于 2026-09-25 签发成功**的产物 —— 说明当时 80/443 对 LE 可达 | 实测（证书签发者/时间） |

### 1.5 早期告警分支实测（本轮唯一“动手”项，且不碰现网）

```bash
.venv/bin/python scripts/ops_check.py --cert-min-days 100     # 阈值调到 > 剩余 83 天，触发告警分支
[ALERT] health=200 error=0.0 rejected=0 … 通知=log-only
  ⚠️ 证书剩余 83.2 天（< 100 天，到期 2026-12-24T16:19:34+00:00）：43.106.104.49.sslip.io:443
exit=1
```

`data/ops-check.log` 已留档（`"level": "ALERT"`，含 `cert_days`/`cert_not_after`）；本轮二次执行复核
同样 **`EXIT=1`**（用 `--cert-min-days 100` 调大阈值，属「临时调阈值」而非伪造证书，未触碰现网证书）。
⇒ 若将来 80/443 被关导致续期失败，**从到期前 30 天起**（即 2026-11-24 之后）巡检会每天报 ALERT，
补上了此前「Caddy 不主动告警」的盲面。

## 2. 哪些是实测、哪些是文档/推断

| 内容 | 性质 |
| --- | --- |
| Caddy 版本、Caddyfile 的 issuer 配置、证书 subject/issuer/有效期/SAN、ARI 续期窗口、宿主防火墙与监听、`ops_check` 告警 exit=1 | **实测**（本轮命令输出） |
| 「安全组 22/80/443 长期放行」 | **文档**（`m4-4.2-deploy-20260925.md`；`docs/05` §5.4），旁证是 LE 签发成功 |
| 「LE 会在 ARI 窗口内自动完成续期」 | **推断**（Caddy 官方行为 + 已实测到排程与刷新；**首次续期尚未实际发生**，最近核对点 2026-11-24） |
| 「续期默认提前 30 天」 | **实测**（本轮 ARI 窗口正是 11-23 → 11-25，距 12-24 到期约 30 天） |

## 3. 遗留 #5 的处置与观察点

* 总表 §2 第 5 条：**由「运维约束（待触发风险）」改为「✅ 已结案（2026-10-02 评估）→ 降为运维常识项」**，
  依据即本文 §0/§1；`docs/04` §8 的遗留清单同步（证书一项移出“待触发”，转为基础运维要求）。
* **唯一观察点（只读）**：2026-11-24 前后核对一次续期是否发生（`docker exec utf8-search-caddy ls -l …` 看
  `.crt` mtime 是否更新，或读 `docker logs` 的 `certificate renewed`）；若此时 `ops_check` 已经连续报
  「证书剩余 <30 天」ALERT，则按 `docs/05` §5.4 的手工流程处理（删缓存自签证书 → 重启 caddy；
  本轮不动手，等用户确认窗口）。
* 不变项：安全组 **22/80/443 不得长期关闭**；`.env`/`settings.yml`/闸门参数本轮未改。

## 4. 产物

* 本文（含实测命令输出与性质标注）；
* 实测告警日志：`data/ops-check.log`（本地运行时数据，不入库；结论已抄录在 §1.5）；
* 分支 `docs/tls-renewal-20261002`（**未合并 main，等确认**）；离线套件不受影响（文档轮）。
