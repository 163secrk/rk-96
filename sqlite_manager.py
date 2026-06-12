import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
import re
import csv
import json
from db_connection import DBConnection
from er_diagram_window import ERDiagramWindow

SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "CREATE", "TABLE", "DROP", "ALTER", "ADD", "COLUMN", "INDEX",
    "VIEW", "TRIGGER", "JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "CROSS",
    "ON", "AND", "OR", "NOT", "IN", "IS", "NULL", "LIKE", "BETWEEN",
    "EXISTS", "DISTINCT", "ALL", "AS", "ORDER", "BY", "GROUP", "HAVING",
    "LIMIT", "OFFSET", "UNION", "ALL", "ASC", "DESC", "PRIMARY", "KEY",
    "FOREIGN", "REFERENCES", "UNIQUE", "CHECK", "DEFAULT", "CONSTRAINT",
    "IF", "ELSE", "BEGIN", "END", "CASE", "WHEN", "THEN", "REPLACE",
    "INTEGER", "TEXT", "REAL", "BLOB", "NUMERIC", "BOOLEAN", "VARCHAR",
    "CHAR", "DATETIME", "DATE", "TIME", "TIMESTAMP", "AUTOINCREMENT",
    "CONFLICT", "ABORT", "FAIL", "IGNORE", "REPLACE", "ROLLBACK",
    "ATTACH", "DETACH", "DATABASE", "VACUUM", "REINDEX", "EXPLAIN",
    "QUERY", "PLAN", "ANALYZE", "PRAGMA", "TRANSACTION", "COMMIT",
    "SAVEPOINT", "RELEASE", "GLOB", "MATCH", "REGEXP", "OVER",
    "PARTITION", "WINDOW", "ROW", "ROWS", "RANGE", "UNBOUNDED",
    "PRECEDING", "FOLLOWING", "CURRENT", "FILTER", "WITH", "RECURSIVE",
    "EXCEPT", "INTERSECT", "NATURAL", "USING", "FULL", "CAST",
    "COLLATE", "ESCAPE", "RAISE", "QUOTE", "TOTAL", "COUNT", "SUM",
    "AVG", "MAX", "MIN", "GROUP_CONCAT", "ABS", "ROUND", "UPPER",
    "LOWER", "LENGTH", "SUBSTR", "TRIM", "LTRIM", "RTRIM", "REPLACE",
    "COALESCE", "IFNULL", "IIF", "TYPEOF", "LAST_INSERT_ROWID",
    "CHANGES", "TOTAL_CHANGES", "RANDOM", "ZEROBLOB", "HEX", "UNHEX",
    "NULLIF", "LIKELY", "UNLIKELY", "LIKELIHOOD",
}


class SQLiteManager:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite 数据库管理器")
        self.root.geometry("1200x800")

        self.db = DBConnection()
        self.current_table = None
        self._completion_window = None
        self._completion_listbox = None
        self._completion_candidates = []
        self._completion_start = None
        self._highlight_job = None

        self.page_size = 100
        self.current_page = 1
        self.total_rows = 0
        self._paged_data = False

        self.create_menu()
        self.create_toolbar()
        self.create_main_layout()

    def create_menu(self):
        menubar = tk.Menu(self.root)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="创建数据库", command=self.create_database)
        filemenu.add_command(label="打开数据库", command=self.open_database)
        filemenu.add_separator()
        filemenu.add_command(label="关闭数据库", command=self.close_database)
        filemenu.add_separator()
        filemenu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=helpmenu)

        self.root.config(menu=menubar)

    def create_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="创建数据库", command=self.create_database).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="打开数据库", command=self.open_database).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="关闭数据库", command=self.close_database).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="执行SQL", command=self.execute_sql).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self.refresh_tree).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="ER图", command=self.show_er_diagram).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Label(toolbar, text="格式:").pack(side=tk.LEFT, padx=(5, 2))
        self.format_var = tk.StringVar(value="CSV")
        format_combo = ttk.Combobox(toolbar, textvariable=self.format_var,
                                    values=["CSV", "JSON", "SQL INSERT"],
                                    state="readonly", width=12)
        format_combo.pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar, text="导入", command=self.import_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="导出", command=self.export_data).pack(side=tk.LEFT, padx=2)

    def create_main_layout(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_paned, width=300)
        right_frame = ttk.Frame(main_paned)

        main_paned.add(left_frame, weight=1)
        main_paned.add(right_frame, weight=3)

        self.create_tree_view(left_frame)
        self.create_right_panel(right_frame)

    def create_tree_view(self, parent):
        tree_frame = ttk.LabelFrame(parent, text="数据库结构", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, show="tree")
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

    def create_right_panel(self, parent):
        right_paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)

        sql_frame = ttk.LabelFrame(right_paned, text="SQL 编辑器", padding=5)
        data_frame = ttk.LabelFrame(right_paned, text="数据显示", padding=5)

        right_paned.add(sql_frame, weight=1)
        right_paned.add(data_frame, weight=2)

        self.create_sql_editor(sql_frame)
        self.create_data_table(data_frame)

    def create_sql_editor(self, parent):
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.sql_text = tk.Text(text_frame, height=8, font=("Consolas", 10),
                                undo=True, wrap=tk.NONE)
        sql_scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.sql_text.yview)
        sql_scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.sql_text.xview)
        self.sql_text.configure(yscrollcommand=sql_scroll_y.set, xscrollcommand=sql_scroll_x.set)

        self.sql_text.grid(row=0, column=0, sticky="nsew")
        sql_scroll_y.grid(row=0, column=1, sticky="ns")
        sql_scroll_x.grid(row=1, column=0, sticky="ew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.sql_text.tag_configure("keyword", foreground="#0000FF", font=("Consolas", 10, "bold"))
        self.sql_text.tag_configure("string", foreground="#A31515")
        self.sql_text.tag_configure("number", foreground="#098658")
        self.sql_text.tag_configure("comment", foreground="#008000", font=("Consolas", 10, "italic"))
        self.sql_text.tag_configure("table_ref", foreground="#6F42C1")

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="执行 (F5)", command=self.execute_sql).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="清空", command=self.clear_sql).pack(side=tk.LEFT, padx=2)

        self.root.bind("<F5>", lambda e: self.execute_sql())

        self.sql_text.bind("<KeyRelease>", self._on_sql_key_release)
        self.sql_text.bind("<Tab>", self._on_completion_tab)
        self.sql_text.bind("<Return>", self._on_completion_return)
        self.sql_text.bind("<Up>", self._on_completion_up)
        self.sql_text.bind("<Down>", self._on_completion_down)
        self.sql_text.bind("<Escape>", self._on_completion_escape)
        self.sql_text.bind("<FocusOut>", self._on_sql_focus_out)

    def _apply_syntax_highlight(self):
        if self._highlight_job:
            self.root.after_cancel(self._highlight_job)

        self._highlight_job = self.root.after(50, self._do_apply_highlight)

    def _do_apply_highlight(self):
        self._highlight_job = None
        self.sql_text.tag_remove("keyword", "1.0", tk.END)
        self.sql_text.tag_remove("string", "1.0", tk.END)
        self.sql_text.tag_remove("number", "1.0", tk.END)
        self.sql_text.tag_remove("comment", "1.0", tk.END)
        self.sql_text.tag_remove("table_ref", "1.0", tk.END)

        content = self.sql_text.get("1.0", tk.END)
        lines = content.split("\n")
        in_block_comment = False

        for line_idx, line in enumerate(lines):
            line_start = f"{line_idx + 1}.0"

            if in_block_comment:
                end_pos = line.find("*/")
                if end_pos != -1:
                    in_block_comment = False
                    self.sql_text.tag_add("comment", line_start, f"{line_idx + 1}.{end_pos + 2}")
                    rest = line[end_pos + 2:]
                    self._highlight_line(line_idx + 1, end_pos + 2, rest)
                else:
                    self.sql_text.tag_add("comment", line_start, f"{line_idx + 1}.end")
                continue

            block_start = line.find("/*")
            if block_start != -1:
                block_end = line.find("*/", block_start + 2)
                if block_end != -1:
                    before = line[:block_start]
                    comment_part = line[block_start:block_end + 2]
                    after = line[block_end + 2:]
                    self._highlight_line(line_idx + 1, 0, before)
                    self.sql_text.tag_add("comment", f"{line_idx + 1}.{block_start}", f"{line_idx + 1}.{block_end + 2}")
                    self._highlight_line(line_idx + 1, block_end + 2, after)
                    continue
                else:
                    before = line[:block_start]
                    self._highlight_line(line_idx + 1, 0, before)
                    self.sql_text.tag_add("comment", f"{line_idx + 1}.{block_start}", f"{line_idx + 1}.end")
                    in_block_comment = True
                    continue

            stripped = line.lstrip()
            if stripped.startswith("--"):
                self.sql_text.tag_add("comment", line_start, f"{line_idx + 1}.end")
                continue

            dash_pos = line.find("--")
            if dash_pos != -1:
                before_dash = line[:dash_pos]
                self._highlight_line(line_idx + 1, 0, before_dash)
                self.sql_text.tag_add("comment", f"{line_idx + 1}.{dash_pos}", f"{line_idx + 1}.end")
            else:
                self._highlight_line(line_idx + 1, 0, line)

    def _highlight_line(self, line_num, col_offset, line):
        patterns = [
            (r"'(?:[^'\\]|\\.)*'", "string"),
            (r'"(?:[^"\\]|\\.)*"', "string"),
            (r"\b\d+\.?\d*\b", "number"),
            (r"\b[A-Za-z_][A-Za-z0-9_]*\b", "keyword"),
        ]

        matched_ranges = []

        for pattern, tag_name in patterns:
            for m in re.finditer(pattern, line):
                overlap = False
                for start, end in matched_ranges:
                    if not (m.end() <= start or m.start() >= end):
                        overlap = True
                        break
                if overlap:
                    continue

                start = f"{line_num}.{col_offset + m.start()}"
                end = f"{line_num}.{col_offset + m.end()}"
                text = m.group()

                if tag_name == "keyword":
                    if text.upper() in SQL_KEYWORDS:
                        self.sql_text.tag_add("keyword", start, end)
                        matched_ranges.append((m.start(), m.end()))
                else:
                    self.sql_text.tag_add(tag_name, start, end)
                    matched_ranges.append((m.start(), m.end()))

        if self.db.is_connected():
            try:
                tables = self.db.get_tables()
                for tbl in tables:
                    escaped = re.escape(tbl)
                    for m in re.finditer(r'\b' + escaped + r'\b', line, re.IGNORECASE):
                        overlap = False
                        for start, end in matched_ranges:
                            if not (m.end() <= start or m.start() >= end):
                                overlap = True
                                break
                        if overlap:
                            continue
                        start = f"{line_num}.{col_offset + m.start()}"
                        end = f"{line_num}.{col_offset + m.end()}"
                        self.sql_text.tag_add("table_ref", start, end)
            except Exception:
                pass

    def _on_sql_key_release(self, event):
        if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R",
                            "Alt_L", "Alt_R", "Caps_Lock", "Tab", "Escape"):
            return

        self._apply_syntax_highlight()

        if event.keysym == "period":
            self.root.after(10, lambda: self._show_completion(event))
        else:
            self._show_completion(event)

    def _on_sql_focus_out(self, event):
        self.root.after(200, self._hide_completion)

    def _get_completion_context(self):
        cursor_pos = self.sql_text.index(tk.INSERT)
        line_num, col_num = map(int, cursor_pos.split("."))
        line = self.sql_text.get(f"{line_num}.0", f"{line_num}.end")
        text_before = line[:col_num]

        m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)$', text_before)
        current_word = None
        start_col = col_num

        if m:
            current_word = m.group(1)
            start_col = m.start()

        dot_prefix = None
        before_word = text_before[:start_col].rstrip()
        if before_word.endswith("."):
            dm = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\.$', before_word)
            if dm:
                dot_prefix = dm.group(1)
                if current_word is None:
                    current_word = ""
                    start_col = col_num

        return current_word, start_col, dot_prefix

    def _get_completion_items(self, prefix, dot_prefix):
        items = []

        if dot_prefix:
            if self.db.is_connected():
                try:
                    tables = self.db.get_tables()
                    matched_table = None
                    for tbl in tables:
                        if tbl.lower() == dot_prefix.lower():
                            matched_table = tbl
                            break
                    if matched_table:
                        cols, _ = self.db.get_table_columns(matched_table)
                        for col in cols:
                            items.append(("column", col["name"], matched_table))
                except Exception:
                    pass
        else:
            if self.db.is_connected():
                try:
                    tables = self.db.get_tables()
                    for tbl in tables:
                        items.append(("table", tbl, None))
                    views = self.db.get_views()
                    for vw in views:
                        items.append(("view", vw, None))
                except Exception:
                    pass

            for kw in SQL_KEYWORDS:
                items.append(("keyword", kw, None))

        prefix_lower = prefix.lower()
        filtered = [(t, n, s) for t, n, s in items if n.lower().startswith(prefix_lower)]
        filtered.sort(key=lambda x: (0 if x[0] in ("table", "view") else 1, x[1].lower()))
        return filtered

    def _show_completion(self, event):
        if event.keysym in ("Up", "Down", "Escape"):
            return

        current_word, start_col, dot_prefix = self._get_completion_context()
        if current_word is None:
            self._hide_completion()
            return

        candidates = self._get_completion_items(current_word, dot_prefix)
        if not candidates:
            self._hide_completion()
            return

        self._completion_candidates = candidates
        self._completion_start = start_col

        if self._completion_window is None:
            self._create_completion_window()

        self._completion_listbox.delete(0, tk.END)
        for item_type, name, source in candidates:
            if item_type == "table":
                display = f"\U0001F4CB {name}"
            elif item_type == "view":
                display = f"\U0001F441 {name}"
            elif item_type == "column":
                display = f"\U0001F4CC {name} ({source})"
            else:
                display = f"\U0001F527 {name}"
            self._completion_listbox.insert(tk.END, display)

        self._completion_listbox.selection_set(0)
        self._completion_listbox.activate(0)

        cursor_pos = self.sql_text.index(tk.INSERT)
        bbox = self.sql_text.bbox(cursor_pos)
        if bbox:
            x = self.sql_text.winfo_rootx() + bbox[0]
            y = self.sql_text.winfo_rooty() + bbox[1] + bbox[3] + 2

            max_visible = min(len(candidates), 8)
            height = max_visible * 20 + 4
            width = 280

            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            if x + width > screen_w:
                x = screen_w - width
            if y + height > screen_h:
                y = self.sql_text.winfo_rooty() + bbox[1] - height

            self._completion_window.geometry(f"{width}x{height}+{x}+{y}")
            self._completion_window.deiconify()
            self._completion_window.lift()

    def _create_completion_window(self):
        self._completion_window = tk.Toplevel(self.root)
        self._completion_window.wm_overrideredirect(True)
        self._completion_window.attributes("-topmost", True)
        self._completion_window.withdraw()

        frame = ttk.Frame(self._completion_window, borderwidth=1, relief="solid")
        frame.pack(fill=tk.BOTH, expand=True)

        self._completion_listbox = tk.Listbox(
            frame, font=("Consolas", 9), selectmode=tk.SINGLE,
            activestyle="none", height=8, width=35,
            bg="#FFFFFF", fg="#000000", selectbackground="#0078D7",
            selectforeground="#FFFFFF", relief="flat", highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._completion_listbox.yview)
        self._completion_listbox.configure(yscrollcommand=scrollbar.set)
        self._completion_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._completion_listbox.bind("<ButtonRelease-1>", self._on_completion_click)
        self._completion_listbox.bind("<Double-Button-1>", self._on_completion_double_click)

    def _hide_completion(self):
        if self._completion_window:
            self._completion_window.withdraw()

    def _insert_completion(self, index):
        if not self._completion_candidates or index < 0 or index >= len(self._completion_candidates):
            return

        item_type, name, source = self._completion_candidates[index]
        cursor_pos = self.sql_text.index(tk.INSERT)
        line_num = int(cursor_pos.split(".")[0])
        start_pos = f"{line_num}.{self._completion_start}"
        end_pos = cursor_pos

        self.sql_text.delete(start_pos, end_pos)
        self.sql_text.insert(start_pos, name)

        if item_type == "keyword" and name.upper() in ("SELECT", "FROM", "WHERE", "INSERT", "INTO", 
                                                       "UPDATE", "SET", "DELETE", "CREATE", "TABLE",
                                                       "DROP", "ALTER", "ADD", "JOIN", "INNER", 
                                                       "LEFT", "RIGHT", "OUTER", "ON", "AND", "OR",
                                                       "NOT", "IN", "IS", "LIKE", "BETWEEN", "EXISTS",
                                                       "DISTINCT", "AS", "ORDER", "BY", "GROUP", 
                                                       "HAVING", "LIMIT", "OFFSET", "UNION", "VALUES"):
            self.sql_text.insert(self.sql_text.index(tk.INSERT), " ")

        self._hide_completion()
        self._apply_syntax_highlight()

    def _on_completion_click(self, event):
        selection = self._completion_listbox.curselection()
        if selection:
            self._insert_completion(selection[0])

    def _on_completion_double_click(self, event):
        selection = self._completion_listbox.curselection()
        if selection:
            self._insert_completion(selection[0])

    def _on_completion_tab(self, event):
        if self._completion_window and self._completion_window.winfo_viewable():
            selection = self._completion_listbox.curselection()
            if selection:
                self._insert_completion(selection[0])
            return "break"
        return None

    def _on_completion_return(self, event):
        if self._completion_window and self._completion_window.winfo_viewable():
            selection = self._completion_listbox.curselection()
            if selection:
                self._insert_completion(selection[0])
                return "break"
        return None

    def _on_completion_up(self, event):
        if self._completion_window and self._completion_window.winfo_viewable():
            selection = self._completion_listbox.curselection()
            if selection:
                idx = selection[0] - 1
                if idx >= 0:
                    self._completion_listbox.selection_clear(0, tk.END)
                    self._completion_listbox.selection_set(idx)
                    self._completion_listbox.activate(idx)
                    self._completion_listbox.see(idx)
            return "break"
        return None

    def _on_completion_down(self, event):
        if self._completion_window and self._completion_window.winfo_viewable():
            selection = self._completion_listbox.curselection()
            if selection:
                idx = selection[0] + 1
                if idx < self._completion_listbox.size():
                    self._completion_listbox.selection_clear(0, tk.END)
                    self._completion_listbox.selection_set(idx)
                    self._completion_listbox.activate(idx)
                    self._completion_listbox.see(idx)
            return "break"
        return None

    def _on_completion_escape(self, event):
        if self._completion_window and self._completion_window.winfo_viewable():
            self._hide_completion()
            return "break"
        return None

    def create_data_table(self, parent):
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.data_tree = ttk.Treeview(table_frame, show="headings")
        data_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        data_scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=data_scroll_y.set, xscrollcommand=data_scroll_x.set)

        self.data_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        data_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        data_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        pager_frame = ttk.Frame(parent)
        pager_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(pager_frame, text="每页:").pack(side=tk.LEFT)
        self.page_size_var = tk.StringVar(value="100")
        page_size_combo = ttk.Combobox(pager_frame, textvariable=self.page_size_var,
                                       values=["50", "100", "200", "500", "1000"],
                                       state="readonly", width=6)
        page_size_combo.pack(side=tk.LEFT, padx=(2, 10))
        page_size_combo.bind("<<ComboboxSelected>>", self._on_page_size_change)

        self.btn_first = ttk.Button(pager_frame, text="首页", command=self._goto_first_page, state="disabled")
        self.btn_first.pack(side=tk.LEFT, padx=1)
        self.btn_prev = ttk.Button(pager_frame, text="上一页", command=self._goto_prev_page, state="disabled")
        self.btn_prev.pack(side=tk.LEFT, padx=1)

        self.page_label = ttk.Label(pager_frame, text="第 0 / 0 页")
        self.page_label.pack(side=tk.LEFT, padx=10)

        self.btn_next = ttk.Button(pager_frame, text="下一页", command=self._goto_next_page, state="disabled")
        self.btn_next.pack(side=tk.LEFT, padx=1)
        self.btn_last = ttk.Button(pager_frame, text="末页", command=self._goto_last_page, state="disabled")
        self.btn_last.pack(side=tk.LEFT, padx=1)

        ttk.Label(pager_frame, text="  跳转到:").pack(side=tk.LEFT)
        self.goto_page_var = tk.StringVar()
        self.goto_entry = ttk.Entry(pager_frame, textvariable=self.goto_page_var, width=5)
        self.goto_entry.pack(side=tk.LEFT, padx=2)
        self.goto_entry.bind("<Return>", self._on_goto_page)
        self.btn_goto = ttk.Button(pager_frame, text="跳转", command=self._on_goto_page, state="disabled")
        self.btn_goto.pack(side=tk.LEFT, padx=1)

        self.total_label = ttk.Label(pager_frame, text="共 0 行")
        self.total_label.pack(side=tk.RIGHT)

        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, pady=5)
        self.status_label = ttk.Label(info_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

    def create_database(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite 数据库", "*.db"), ("所有文件", "*.*")],
            title="创建数据库"
        )
        if filename:
            try:
                conn = sqlite3.connect(filename)
                conn.close()
                self.open_database_file(filename)
                messagebox.showinfo("成功", f"数据库创建成功: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"创建数据库失败: {str(e)}")

    def open_database(self):
        filename = filedialog.askopenfilename(
            filetypes=[("SQLite 数据库", "*.db *.sqlite *.sqlite3"), ("所有文件", "*.*")],
            title="打开数据库"
        )
        if filename:
            self.open_database_file(filename)

    def open_database_file(self, filename):
        self.close_database()
        try:
            self.db.connect(filename)
            self.root.title(f"SQLite 数据库管理器 - {os.path.basename(filename)}")
            self.populate_tree()
            self.status_label.config(text=f"已连接: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"打开数据库失败: {str(e)}")

    def close_database(self):
        if self.db.is_connected():
            self.db.close()
            self.tree.delete(*self.tree.get_children())
            self.clear_data_table()
            self.root.title("SQLite 数据库管理器")
            self.status_label.config(text="已断开连接")

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())

        if not self.db.is_connected():
            return

        db_node = self.tree.insert("", tk.END, text=os.path.basename(self.db.current_db),
                                   values=("database",), open=True)

        tables_node = self.tree.insert(db_node, tk.END, text="表", values=("tables",), open=True)
        views_node = self.tree.insert(db_node, tk.END, text="视图", values=("views",), open=True)

        try:
            tables = self.db.get_tables()
            for table_name in tables:
                table_node = self.tree.insert(tables_node, tk.END, text=table_name,
                                              values=("table", table_name))
                self.tree.insert(table_node, tk.END, text="列", values=("columns", table_name))
                self.tree.insert(table_node, tk.END, text="索引", values=("indexes", table_name))

            views = self.db.get_views()
            for view_name in views:
                view_node = self.tree.insert(views_node, tk.END, text=view_name,
                                             values=("view", view_name))
                self.tree.insert(view_node, tk.END, text="列", values=("columns", view_name))

        except Exception as e:
            messagebox.showerror("错误", f"加载数据库结构失败: {str(e)}")

    def refresh_tree(self):
        if self.db.is_connected():
            self.populate_tree()

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        item_type, item_name = self.tree.item(item, "values")

        if item_type == "columns":
            self.show_table_columns(item_name)
        elif item_type == "indexes":
            self.show_table_indexes(item_name)

    def on_tree_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        item_type, item_name = self.tree.item(item, "values")

        if item_type == "table" or item_type == "view":
            self.show_table_data(item_name)

    def show_table_columns(self, table_name):
        if not self.db.is_connected():
            return

        try:
            rows = self.db.get_table_info(table_name)
            columns = ["cid", "name", "type", "notnull", "dflt_value", "pk"]
            self.display_data(columns, rows)
            self.status_label.config(text=f"表结构: {table_name} ({len(rows)} 列)")

        except Exception as e:
            messagebox.showerror("错误", f"获取表结构失败: {str(e)}")

    def show_table_indexes(self, table_name):
        if not self.db.is_connected():
            return

        try:
            rows = self.db.get_indexes(table_name)

            if rows:
                columns = [desc[0] for desc in self.db.conn.cursor().description]
                self.display_data(columns, rows)
                self.status_label.config(text=f"索引: {table_name} ({len(rows)} 个)")
            else:
                self.clear_data_table()
                self.status_label.config(text=f"索引: {table_name} (无索引)")

        except Exception as e:
            messagebox.showerror("错误", f"获取索引失败: {str(e)}")

    def show_table_data(self, table_name):
        if not self.db.is_connected():
            return

        try:
            self.current_table = table_name
            self.current_page = 1
            self._paged_data = True
            self._load_paged_data()

        except Exception as e:
            messagebox.showerror("错误", f"获取表数据失败: {str(e)}")

    def _load_paged_data(self):
        if not self.current_table or not self.db.is_connected():
            return

        self.page_size = int(self.page_size_var.get())
        offset = (self.current_page - 1) * self.page_size

        columns, rows, total = self.db.get_table_data_paged(
            self.current_table, limit=self.page_size, offset=offset
        )
        self.total_rows = total
        self.display_data(columns, rows)
        self._update_pager()
        self.status_label.config(
            text=f"表数据: {self.current_table} ({total} 行, 第 {self.current_page} 页)"
        )

    def _update_pager(self):
        if not self._paged_data:
            self.page_label.config(text=f"共 {self.total_rows} 行")
            self.total_label.config(text="")
            self.btn_first.config(state="disabled")
            self.btn_prev.config(state="disabled")
            self.btn_next.config(state="disabled")
            self.btn_last.config(state="disabled")
            self.btn_goto.config(state="disabled")
            return

        total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)

        self.page_label.config(text=f"第 {self.current_page} / {total_pages} 页")
        self.total_label.config(text=f"共 {self.total_rows} 行")

        has_prev = self.current_page > 1
        has_next = self.current_page < total_pages

        self.btn_first.config(state="normal" if has_prev else "disabled")
        self.btn_prev.config(state="normal" if has_prev else "disabled")
        self.btn_next.config(state="normal" if has_next else "disabled")
        self.btn_last.config(state="normal" if has_next else "disabled")
        self.btn_goto.config(state="normal" if total_pages > 1 else "disabled")

    def _goto_first_page(self):
        if self.current_page > 1:
            self.current_page = 1
            self._load_paged_data()

    def _goto_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._load_paged_data()

    def _goto_next_page(self):
        total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self._load_paged_data()

    def _goto_last_page(self):
        total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page = total_pages
            self._load_paged_data()

    def _on_page_size_change(self, event=None):
        self.page_size = int(self.page_size_var.get())
        self.current_page = 1
        if self._paged_data and self.current_table:
            self._load_paged_data()

    def _on_goto_page(self, event=None):
        try:
            page = int(self.goto_page_var.get())
            total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
            if 1 <= page <= total_pages:
                self.current_page = page
                self._load_paged_data()
            else:
                messagebox.showwarning("警告", f"页码必须在 1 到 {total_pages} 之间")
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的页码")
        self.goto_page_var.set("")

    def display_data(self, columns, rows):
        self.clear_data_table()

        self.data_tree["columns"] = columns
        sample_rows = rows[:50]
        for col in columns:
            self.data_tree.heading(col, text=col)
            max_width = max(len(str(col)), 100)
            for row in sample_rows:
                try:
                    val = str(row[col]) if row[col] is not None else ""
                    max_width = max(max_width, len(val))
                except (KeyError, IndexError):
                    pass
            self.data_tree.column(col, width=min(max_width * 8, 300), stretch=True)

        self._batch_insert_rows(columns, rows, 0)

        self.data_tree.tag_configure("even", background="#f0f0f0")
        self.data_tree.tag_configure("odd", background="#ffffff")

    def _batch_insert_rows(self, columns, rows, start_idx, batch_size=50):
        end_idx = min(start_idx + batch_size, len(rows))
        for i in range(start_idx, end_idx):
            row = rows[i]
            values = []
            for col in columns:
                try:
                    val = row[col]
                except (KeyError, IndexError):
                    val = None
                values.append(str(val) if val is not None else "")
            tag = "even" if i % 2 == 0 else "odd"
            self.data_tree.insert("", tk.END, values=values, tags=(tag,))

        if end_idx < len(rows):
            self.root.after(10, lambda: self._batch_insert_rows(columns, rows, end_idx, batch_size))

    def clear_data_table(self):
        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree["columns"] = ()
        self._paged_data = False

    def execute_sql(self):
        if not self.db.is_connected():
            messagebox.showwarning("警告", "请先打开数据库")
            return

        sql = self.sql_text.get("1.0", tk.END).strip()
        if not sql:
            messagebox.showwarning("警告", "请输入SQL语句")
            return

        try:
            columns, rows, count = self.db.execute_sql(sql)

            if rows is not None and columns is not None:
                if rows:
                    self._paged_data = False
                    self.total_rows = count
                    self.display_data(columns, rows)
                    self._update_pager()
                    self.status_label.config(text=f"查询成功: {count} 行")
                else:
                    self.clear_data_table()
                    self.status_label.config(text="查询成功: 无结果")
            else:
                self.clear_data_table()
                self.status_label.config(text=f"执行成功: 影响 {count} 行")
                self.refresh_tree()

        except Exception as e:
            self.db.rollback()
            messagebox.showerror("错误", f"SQL执行失败: {str(e)}")

    def clear_sql(self):
        self.sql_text.delete("1.0", tk.END)

    def show_er_diagram(self):
        if not self.db.is_connected():
            messagebox.showwarning("警告", "请先打开数据库")
            return
        ERDiagramWindow(self.root, self.db)

    def export_data(self):
        if not self.db.is_connected():
            messagebox.showwarning("警告", "请先打开数据库")
            return

        if not self.current_table:
            messagebox.showwarning("警告", "请先在左侧选中并双击打开一个表")
            return

        fmt = self.format_var.get()
        if fmt == "CSV":
            self._export_csv()
        elif fmt == "JSON":
            self._export_json()
        elif fmt == "SQL INSERT":
            self._export_sql_insert()

    def _export_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
            title=f"导出 {self.current_table} 为 CSV"
        )
        if not filename:
            return

        try:
            columns, rows = self.db.get_table_data(self.current_table)
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([row[col] for col in columns])
            self.status_label.config(text=f"导出成功: {filename} ({len(rows)} 行)")
            messagebox.showinfo("成功", f"导出成功!\n文件: {filename}\n共 {len(rows)} 行数据")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def _export_json(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title=f"导出 {self.current_table} 为 JSON"
        )
        if not filename:
            return

        try:
            columns, rows = self.db.get_table_data(self.current_table)
            data = []
            for row in rows:
                data.append({col: row[col] for col in columns})
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            self.status_label.config(text=f"导出成功: {filename} ({len(rows)} 行)")
            messagebox.showinfo("成功", f"导出成功!\n文件: {filename}\n共 {len(rows)} 行数据")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def _export_sql_insert(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("SQL 文件", "*.sql"), ("所有文件", "*.*")],
            title=f"导出 {self.current_table} 为 SQL INSERT"
        )
        if not filename:
            return

        try:
            columns, rows = self.db.get_table_data(self.current_table)
            table_name = self.current_table
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"-- 导出表: {table_name}\n")
                f.write(f"-- 记录数: {len(rows)}\n\n")
                for row in rows:
                    cols = ", ".join([f'"{col}"' for col in columns])
                    values = []
                    for col in columns:
                        val = row[col]
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        else:
                            escaped = str(val).replace("'", "''")
                            values.append(f"'{escaped}'")
                    values_str = ", ".join(values)
                    f.write(f'INSERT INTO "{table_name}" ({cols}) VALUES ({values_str});\n')
            self.status_label.config(text=f"导出成功: {filename} ({len(rows)} 行)")
            messagebox.showinfo("成功", f"导出成功!\n文件: {filename}\n共 {len(rows)} 行数据")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def import_data(self):
        if not self.db.is_connected():
            messagebox.showwarning("警告", "请先打开数据库")
            return

        if not self.current_table:
            messagebox.showwarning("警告", "请先在左侧选中并双击打开一个目标表")
            return

        fmt = self.format_var.get()
        if fmt == "CSV":
            self._import_csv()
        elif fmt == "JSON":
            self._import_json()
        elif fmt == "SQL INSERT":
            self._import_sql_insert()

    def _import_csv(self):
        filename = filedialog.askopenfilename(
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
            title=f"导入 CSV 到 {self.current_table}"
        )
        if not filename:
            return

        try:
            table_cols, _ = self.db.get_table_columns(self.current_table)
            col_names = [col["name"] for col in table_cols]

            with open(filename, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                csv_cols = reader.fieldnames

                if not csv_cols:
                    raise Exception("CSV 文件为空或没有表头")

                count = 0
                cursor = self.db.conn.cursor()
                table_name = self.current_table

                for row in reader:
                    cols = []
                    placeholders = []
                    values = []
                    for col in csv_cols:
                        if col in col_names:
                            cols.append(f'"{col}"')
                            placeholders.append("?")
                            val = row[col]
                            if val == "":
                                values.append(None)
                            else:
                                values.append(val)
                    if cols:
                        sql = f'INSERT INTO "{table_name}" ({", ".join(cols)}) VALUES ({", ".join(placeholders)})'
                        cursor.execute(sql, values)
                        count += 1

                self.db.conn.commit()

            self.refresh_tree()
            if self.current_table:
                self.show_table_data(self.current_table)
            self.status_label.config(text=f"导入成功: {filename} ({count} 行)")
            messagebox.showinfo("成功", f"导入成功!\n文件: {filename}\n共导入 {count} 行数据")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def _import_json(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title=f"导入 JSON 到 {self.current_table}"
        )
        if not filename:
            return

        try:
            table_cols, _ = self.db.get_table_columns(self.current_table)
            col_names = [col["name"] for col in table_cols]

            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise Exception("JSON 文件必须是数组格式")

            count = 0
            cursor = self.db.conn.cursor()
            table_name = self.current_table

            for row in data:
                if not isinstance(row, dict):
                    continue
                cols = []
                placeholders = []
                values = []
                for key, val in row.items():
                    if key in col_names:
                        cols.append(f'"{key}"')
                        placeholders.append("?")
                        values.append(val)
                if cols:
                    sql = f'INSERT INTO "{table_name}" ({", ".join(cols)}) VALUES ({", ".join(placeholders)})'
                    cursor.execute(sql, values)
                    count += 1

            self.db.conn.commit()

            self.refresh_tree()
            if self.current_table:
                self.show_table_data(self.current_table)
            self.status_label.config(text=f"导入成功: {filename} ({count} 行)")
            messagebox.showinfo("成功", f"导入成功!\n文件: {filename}\n共导入 {count} 行数据")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def _import_sql_insert(self):
        filename = filedialog.askopenfilename(
            filetypes=[("SQL 文件", "*.sql"), ("所有文件", "*.*")],
            title=f"执行 SQL INSERT 文件到 {self.current_table}"
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                sql_content = f.read()

            cursor = self.db.conn.cursor()
            count = 0
            statements = [s.strip() for s in sql_content.split(";") if s.strip()]

            for sql in statements:
                if sql.upper().startswith("INSERT"):
                    cursor.execute(sql)
                    count += cursor.rowcount

            self.db.conn.commit()

            self.refresh_tree()
            if self.current_table:
                self.show_table_data(self.current_table)
            self.status_label.config(text=f"导入成功: {filename} ({count} 行)")
            messagebox.showinfo("成功", f"导入成功!\n文件: {filename}\n共影响 {count} 行")
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def show_about(self):
        messagebox.showinfo("关于", "SQLite 数据库管理器\n\n使用 Python Tkinter 开发\n功能: 数据库管理、表结构浏览、数据查询、SQL执行、数据导入导出")

    def on_closing(self):
        self.close_database()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SQLiteManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
