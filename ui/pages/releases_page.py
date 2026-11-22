"""Releases 页：查询仓库发布列表，右键资源直接用浏览器下载。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from core.nodes import NodeManager
from ui.widgets import card
from ui.theme import COLORS


class ReleasesPage(ttk.Frame):
    def __init__(self, service, master=None):
        super().__init__(master)
        self.service = service
        self._releases = []
        self._tree_data = {}  # item id -> ReleaseAsset
        self._build_ui()
        self.service.releases_done_signal.connect(self._on_releases)

    def _build_ui(self):
        # 查询区
        search_wrap, search_body = card(self, "查询仓库")
        search_wrap.pack(fill="x", pady=(0, 14))
        row = ttk.Frame(search_body)
        row.pack(fill="x")
        ttk.Label(row, text="仓库：").pack(side="left")
        self.repo_var = tk.StringVar()
        self.repo_input = ttk.Entry(row, textvariable=self.repo_var, width=48)
        self.repo_input.pack(side="left", padx=(0, 8))
        self.repo_input.bind("<Return>", lambda e: self._search())
        self.search_btn = ttk.Button(row, text="查询 Releases", style="Primary.TButton", command=self._search)
        self.search_btn.pack(side="left")
        ttk.Label(search_body, text="输入 owner/repo，如 tidain/YunX-Desktop",
                  style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

        # 发布列表（Treeview 层级：版本 → 资源）
        tree_wrap, tree_body = card(self, "发布列表（右键资源直接用浏览器下载）")
        tree_wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_body, columns=("size", "downloads"), show="tree headings", height=14)
        self.tree.heading("#0", text="版本 / 资源", anchor="w")
        self.tree.heading("size", text="大小", anchor="w")
        self.tree.heading("downloads", text="下载次数", anchor="w")
        self.tree.column("#0", width=460, stretch=True)
        self.tree.column("size", width=100, stretch=False, anchor="w")
        self.tree.column("downloads", width=100, stretch=False, anchor="w")
        vsb = ttk.Scrollbar(tree_body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.tag_configure("release", foreground=COLORS["purple"], font=("Microsoft YaHei UI", 10, "bold"))
        self.tree.tag_configure("asset", foreground="#1B1B1B")
        # 右键菜单
        self.menu = tk.Menu(self, tearoff=0)
        self.tree.bind("<Button-3>", self._on_right_click)

    def _search(self):
        text = self.repo_var.get().strip().rstrip("/")
        if text.startswith("https://github.com/"):
            text = text[len("https://github.com/"):]
        elif text.startswith("http://github.com/"):
            text = text[len("http://github.com/"):]
        elif text.startswith("git@github.com:"):
            text = text[len("git@github.com:"):]
        parts = [p for p in text.split("/") if p]
        if len(parts) < 2:
            messagebox.showinfo("提示", "请按 owner/repo 格式输入，如 tidain/YunX-Desktop", parent=self)
            return
        owner, repo = parts[0], parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        self.search_btn.configure(state="disabled", text="查询中…")
        self.service.fetch_releases(owner, repo)

    def _on_releases(self, releases, owner, repo):
        self.search_btn.configure(state="normal", text="查询 Releases")
        self._releases = releases
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._tree_data.clear()
        if not releases:
            messagebox.showwarning("无结果", f"没有获取到 {owner}/{repo} 的 Releases，可能仓库不存在或网络受限", parent=self)
            return
        for rel in releases:
            top = self.tree.insert("", "end", text=f"{rel.tag}  {rel.name}",
                                   values=("", rel.published_at), tags=("release",), open=True)
            for asset in rel.assets:
                child = self.tree.insert(top, "end", text=asset.name,
                                         values=(f"{asset.size / 1048576:.1f} MB", str(asset.downloads)),
                                         tags=("asset",))
                self._tree_data[child] = asset

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item or item not in self._tree_data:
            return
        asset = self._tree_data[item]
        self.tree.selection_set(item)
        # 重建菜单
        self.menu.delete(0, "end")
        nodes = [n for n in self.service.nodemgr.results if n.ok][:8]
        if not nodes:
            nodes = self.service.nodemgr.results[:8]
        for node in nodes:
            self.menu.add_command(label=f"用 {node.name} 下载（浏览器）",
                                  command=lambda n=node, a=asset: self._open_download(n, a))
        self.menu.add_separator()
        sub = tk.Menu(self.menu, tearoff=0)
        for node in nodes:
            sub.add_command(label=node.name, command=lambda n=node, a=asset: self._copy_link(n, a))
        self.menu.add_cascade(label="复制加速链接…", menu=sub)
        self.menu.add_command(label="复制原始 GitHub 直链", command=lambda a=asset: self._copy_raw(a))
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _open_download(self, node, asset):
        url = NodeManager.build_url(node.url, asset.browser_download_url)
        webbrowser.open(url)

    def _copy_link(self, node, asset):
        url = NodeManager.build_url(node.url, asset.browser_download_url)
        self.clipboard_clear()
        self.clipboard_append(url)
        self.update()
        messagebox.showinfo("已复制", f"加速链接已复制：\n{url}", parent=self)

    def _copy_raw(self, asset):
        self.clipboard_clear()
        self.clipboard_append(asset.browser_download_url)
        self.update()
        messagebox.showinfo("已复制", f"原始直链已复制：\n{asset.browser_download_url}", parent=self)
