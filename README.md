# FastGithubPy

用 **Python + PyQt6** 复刻 [FastGithub](https://github.com/yuan71058/FastGithub) 的桌面界面，并集成 [github.akams.cn](https://github.akams.cn/) 的公开 ghproxy 节点功能。暗色卡片式界面、系统托盘、本地正向代理 + GitHub IP 测速优选。

> 这是界面与功能复刻的学习项目，不包含原项目的 WinDivert 内核驱动与 CA 中间人机制。加速采用「本地 HTTP 正向代理 → 域名优选最快 IP → 转发」的方式实现。

## 功能

- **加速总览**：一键启动/停止本地代理、实时流量图（上传/下载）、域名 IP 候选列表（TCP+TLS 双探测排序）
- **加速节点**：内置 github.akams.cn 的 40+ 个 ghproxy 节点，批量测速排序，粘贴 GitHub 链接一键生成任意节点的加速下载地址
- **Releases**：输入 `owner/repo`（如 `tidain/YunX-Desktop`）查询发布列表，右键资源直接用各节点生成加速下载链接
- **直链转换**：把 `github.com/.../blob/...` 文件页链接转成可直接下载/访问的 raw 直链，支持多行批量、实时转换、可选加速代理（功能参考 nav.sdyun.eu.org/tools/github-direct-link.html）；`tree` 目录页转成 codeload 打包下载
- **日志**：实时运行日志、自动滚动、级别标识
- **设置**：代理模式（PAC 自动 / 全局 / 不修改）、开机自启、最小化到托盘、代理端口、自动刷新间隔、hosts 源、目录入口
- **系统托盘**：显示主界面、启停加速、更新 IP、退出

## 工作原理

```
浏览器 / git  ──(系统代理/PAC)──>  本地正向代理 127.0.0.1:38457
                                   │
                              域名 → 最快 IP
                    (GitHub官方meta + hosts源 + 内置池 + DNS)
                          TCP连接 + TLS握手 双探测
                                   │
                            github.com 等上游
```

- **官方 meta API**：默认拉取 `https://api.github.com/meta`，取 `web`/`api`/`git` 等分组的官方 CIDR 网段（`/32` 优先、大网段限量展开），作为权威候选 IP 来源； hosts 源/DNS 的 IP 会被官方网段白名单校验，过滤掉被污染的解析结果。可在 `config/settings.json` 里设 `use_meta_api: false` 关闭。
- **IP 选路**：对每个加速域名并发探测候选 IP 的 TCP 连接 + TLS 握手，以握手成功为可用性门槛，按延迟升序选最快；请求阶段失败的 IP 熔断 90 秒。
- **降级保护**：某域名全部候选探测失败时保留上次结果，不会把可用 IP 清空。
- **节点加速**：ghproxy 节点通过 `节点地址 + / + 原始 GitHub 链接` 拼接生成加速地址，适合 Raw / Releases / Archive / Gist / Clone 等场景。

## 安装与运行

环境：Python 3.10+（已在 3.13 验证）

```bash
pip install -r requirements.txt
python main.py
```

开机自启场景可带参数后台启动：

```bash
python main.py --minimized
```

## 使用提示

1. 首次启动进入「加速总览」，点「更新 IP」做一轮测速（约 10~30 秒）。
2. 点「启动加速」会开启本地代理，并按「设置」里选择的模式应用系统代理；停止时自动还原。
3. **代理模式**（设置页可切换，推荐 PAC）：
   - **PAC 自动代理（默认/推荐）**：只有 GitHub 系域名走本地代理，其它网站全部直连。程序即使异常退出或电脑重启，其它网站也不受影响，**不会全网断网**。
   - **全局代理**：所有网站都走本地代理。注意：若程序未运行而代理残留，会导致全网断网（程序启动时会自检清理残留）。
   - **不修改系统设置**：程序只启动本地代理，需手动把浏览器/git 代理设为 `http://127.0.0.1:38457`。
4. 「加速节点」页的批量测速依赖网络访问 GitHub，节点可用性随时间波动，属于正常现象。
5. Releases 查询走 GitHub API，网络受限时可先启动本地加速再查询。
6. 若已断网（代理残留），可到「设置」把系统代理关闭，或手动删除注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` 下的 `ProxyEnable`(设为 0)、`AutoConfigURL`、`ProxyServer`。

## 目录结构

```
FastGithubPy/
├── main.py                 入口
├── core/
│   ├── config.py           配置与内置 IP 池
│   ├── loghub.py           日志中心
│   ├── ipprobe.py          IP 解析与 TCP/TLS 双探测
│   ├── proxy.py            本地 HTTP 正向代理
│   ├── systemproxy.py      系统代理与开机自启（Windows 注册表）
│   ├── nodes.py            ghproxy 节点与加速链接生成
│   ├── githubapi.py        Releases 获取
│   └── service.py          应用服务层 / 异步线程
├── ui/
│   ├── theme.py            暗色 QSS 主题
│   ├── widgets.py          通用控件
│   ├── main_window.py      主窗口与托盘
│   └── pages/              五个功能页
├── config/                 运行时配置与 IP 缓存
└── logs/                   运行日志
```

## 自动打包

仓库已配置 GitHub Actions（`.github/workflows/build.yml`），**每次 push 代码都会自动打包 Windows exe**：

- 普通 push：打包后生成构建产物 `FastGithubPy-windows.zip`，在 Actions 运行页面的 **Artifacts** 中下载（保留 90 天）。
- 推送 `v*` 标签（如 `v1.0`）：除构建产物外，还会自动创建 **Release** 并附带 zip，可直接下载。
- 也可在 Actions 页面手动点 **Run workflow** 触发。

本地如需手动打包：

```bash
pip install pyinstaller
pyinstaller FastGithubPy.spec --noconfirm
# 产物在 dist/FastGithubPy/ 目录
```

## 说明

- 仅用于学习与个人使用，请遵守相关法律法规及 GitHub 服务条款。
- 节点列表来自公开项目 github.akams.cn，其可用性由节点提供方决定。
- 非 Windows 平台不会自动设置系统代理，需手动配置代理地址。
