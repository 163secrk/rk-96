import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os


class SQLiteManager:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite 数据库管理器")
        self.root.geometry("1200x800")
        
        self.conn = None
        self.current_db = None
        
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
        self.sql_text = tk.Text(parent, height=8, font=("Consolas", 10))
        sql_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.sql_text.yview)
        self.sql_text.configure(yscrollcommand=sql_scroll.set)
        
        self.sql_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sql_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="执行 (F5)", command=self.execute_sql).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="清空", command=self.clear_sql).pack(side=tk.LEFT, padx=2)
        
        self.root.bind("<F5>", lambda e: self.execute_sql())
        
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
            self.conn = sqlite3.connect(filename)
            self.conn.row_factory = sqlite3.Row
            self.current_db = filename
            self.root.title(f"SQLite 数据库管理器 - {os.path.basename(filename)}")
            self.populate_tree()
            self.status_label.config(text=f"已连接: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"打开数据库失败: {str(e)}")
            
    def close_database(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.current_db = None
            self.tree.delete(*self.tree.get_children())
            self.clear_data_table()
            self.root.title("SQLite 数据库管理器")
            self.status_label.config(text="已断开连接")
            
    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        
        if not self.conn:
            return
            
        db_node = self.tree.insert("", tk.END, text=os.path.basename(self.current_db), 
                                   values=("database",), open=True)
        
        tables_node = self.tree.insert(db_node, tk.END, text="表", values=("tables",), open=True)
        views_node = self.tree.insert(db_node, tk.END, text="视图", values=("views",), open=True)
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            for row in cursor.fetchall():
                table_name = row['name']
                table_node = self.tree.insert(tables_node, tk.END, text=table_name, 
                                              values=("table", table_name))
                self.tree.insert(table_node, tk.END, text="列", values=("columns", table_name))
                self.tree.insert(table_node, tk.END, text="索引", values=("indexes", table_name))
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
            for row in cursor.fetchall():
                view_name = row['name']
                view_node = self.tree.insert(views_node, tk.END, text=view_name, 
                                             values=("view", view_name))
                self.tree.insert(view_node, tk.END, text="列", values=("columns", view_name))
                
        except Exception as e:
            messagebox.showerror("错误", f"加载数据库结构失败: {str(e)}")
            
    def refresh_tree(self):
        if self.conn:
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
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.quote_identifier(table_name)})")
            rows = cursor.fetchall()
            
            columns = ["cid", "name", "type", "notnull", "dflt_value", "pk"]
            self.display_data(columns, rows)
            self.status_label.config(text=f"表结构: {table_name} ({len(rows)} 列)")
            
        except Exception as e:
            messagebox.showerror("错误", f"获取表结构失败: {str(e)}")
            
    def show_table_indexes(self, table_name):
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA index_list({self.quote_identifier(table_name)})")
            rows = cursor.fetchall()
            
            if rows:
                columns = [desc[0] for desc in cursor.description]
                self.display_data(columns, rows)
                self.status_label.config(text=f"索引: {table_name} ({len(rows)} 个)")
            else:
                self.clear_data_table()
                self.status_label.config(text=f"索引: {table_name} (无索引)")
            
        except Exception as e:
            messagebox.showerror("错误", f"获取索引失败: {str(e)}")
            
    def show_table_data(self, table_name):
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {self.quote_identifier(table_name)}")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            self.display_data(columns, rows)
            self.status_label.config(text=f"表数据: {table_name} ({len(rows)} 行)")
            
        except Exception as e:
            messagebox.showerror("错误", f"获取表数据失败: {str(e)}")
            
    def display_data(self, columns, rows):
        self.clear_data_table()
        
        self.data_tree["columns"] = columns
        for col in columns:
            self.data_tree.heading(col, text=col)
            max_width = max(len(str(col)), 100)
            for row in rows:
                max_width = max(max_width, len(str(row[col])) if col in row.keys() else 10)
            self.data_tree.column(col, width=min(max_width * 8, 300), stretch=True)
            
        for i, row in enumerate(rows):
            values = [str(row[col]) if row[col] is not None else "" for col in columns]
            tag = "even" if i % 2 == 0 else "odd"
            self.data_tree.insert("", tk.END, values=values, tags=(tag,))
            
        self.data_tree.tag_configure("even", background="#f0f0f0")
        self.data_tree.tag_configure("odd", background="#ffffff")
        
    def clear_data_table(self):
        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree["columns"] = ()
        
    def execute_sql(self):
        if not self.conn:
            messagebox.showwarning("警告", "请先打开数据库")
            return
            
        sql = self.sql_text.get("1.0", tk.END).strip()
        if not sql:
            messagebox.showwarning("警告", "请输入SQL语句")
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            
            if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA"):
                rows = cursor.fetchall()
                if rows:
                    columns = [desc[0] for desc in cursor.description]
                    self.display_data(columns, rows)
                    self.status_label.config(text=f"查询成功: {len(rows)} 行")
                else:
                    self.clear_data_table()
                    self.status_label.config(text="查询成功: 无结果")
            else:
                self.conn.commit()
                self.status_label.config(text=f"执行成功: 影响 {cursor.rowcount} 行")
                self.refresh_tree()
                
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("错误", f"SQL执行失败: {str(e)}")
            
    def clear_sql(self):
        self.sql_text.delete("1.0", tk.END)
        
    def quote_identifier(self, identifier):
        return f'"{identifier}"'
        
    def show_er_diagram(self):
        if not self.conn:
            messagebox.showwarning("警告", "请先打开数据库")
            return
        ERDiagramWindow(self.root, self.conn)

    def show_about(self):
        messagebox.showinfo("关于", "SQLite 数据库管理器\n\n使用 Python Tkinter 开发\n功能: 数据库管理、表结构浏览、数据查询、SQL执行")
        
    def on_closing(self):
        self.close_database()
        self.root.destroy()


class ERDiagramWindow:
    TABLE_WIDTH = 220
    ROW_HEIGHT = 22
    HEADER_HEIGHT = 32
    H_GAP = 120
    V_GAP = 80
    SCALE_FACTOR = 1.1

    def __init__(self, parent, conn):
        self.conn = conn
        self.tables = {}
        self.relations = []
        self.table_boxes = {}
        self.scale = 1.0
        self._drag_data = None

        self.top = tk.Toplevel(parent)
        self.top.title("ER 关系图")
        self.top.geometry("1200x800")

        self._create_toolbar()
        self._create_canvas()

        self.analyze_schema()
        if not self.tables:
            messagebox.showinfo("提示", "数据库中没有表")
            self.top.destroy()
            return

        self.auto_layout()
        self.draw_er_diagram()

    def _create_toolbar(self):
        toolbar = ttk.Frame(self.top, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="放大", command=lambda: self._set_scale(self.SCALE_FACTOR)).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="缩小", command=lambda: self._set_scale(1 / self.SCALE_FACTOR)).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="重置大小", command=lambda: self._set_scale(0, reset=True)).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="重新布局", command=self._relayout).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._refresh).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.legend = tk.Label(toolbar, text="  ◆ 主键  ● 外键  ── 1:N  ──◆ 1:1  ──◇ M:N  ",
                               font=("Arial", 9), fg="#333")
        self.legend.pack(side=tk.LEFT, padx=10)

    def _create_canvas(self):
        container = ttk.Frame(self.top)
        container.pack(fill=tk.BOTH, expand=True)

        xbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL)
        ybar = ttk.Scrollbar(container, orient=tk.VERTICAL)

        self.canvas = tk.Canvas(container, bg="#fafafa",
                                xscrollcommand=xbar.set, yscrollcommand=ybar.set,
                                highlightthickness=0)
        xbar.config(command=self.canvas.xview)
        ybar.config(command=self.canvas.yview)

        xbar.pack(side=tk.BOTTOM, fill=tk.X)
        ybar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self._set_scale(self.SCALE_FACTOR))
        self.canvas.bind("<Button-5>", lambda e: self._set_scale(1 / self.SCALE_FACTOR))

    def analyze_schema(self):
        self.tables = {}
        self.relations = []
        cursor = self.conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        table_names = [row[0] for row in cursor.fetchall()]

        for tbl in table_names:
            cursor.execute(f'PRAGMA table_info("{tbl}")')
            cols = []
            pk_cols = []
            for col in cursor.fetchall():
                cid, name, ctype, notnull, dflt, pk = col
                cols.append({
                    "cid": cid, "name": name, "type": ctype or "TEXT",
                    "notnull": notnull, "pk": pk
                })
                if pk:
                    pk_cols.append(name)

            cursor.execute(f'PRAGMA foreign_key_list("{tbl}")')
            fks = []
            for fk in cursor.fetchall():
                fid, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
                fks.append({
                    "ref_table": ref_table, "from": from_col, "to": to_col
                })

            unique_cols = set()
            cursor.execute(f'PRAGMA index_list("{tbl}")')
            for idx in cursor.fetchall():
                seq, idx_name, is_unique, origin, partial = idx[0], idx[1], idx[2], idx[3], idx[4] if len(idx) > 4 else 0
                if is_unique:
                    try:
                        cursor.execute(f'PRAGMA index_info("{idx_name}")')
                        idx_cols = [r[2] for r in cursor.fetchall()]
                        if len(idx_cols) == 1:
                            unique_cols.add(idx_cols[0])
                    except Exception:
                        pass

            self.tables[tbl] = {
                "columns": cols, "pk": pk_cols, "foreign_keys": fks,
                "unique_cols": unique_cols,
                "x": 50, "y": 50
            }

        self._build_relations()

    def _build_relations(self):
        join_tables = set()
        for tbl_name, tbl in self.tables.items():
            fk_count = len(tbl["foreign_keys"])
            pk_set = set(tbl["pk"])
            if fk_count >= 2:
                fk_cols = {fk["from"] for fk in tbl["foreign_keys"]}
                if fk_cols.issubset(pk_set) or fk_cols == pk_set:
                    join_tables.add(tbl_name)

        for tbl_name, tbl in self.tables.items():
            for fk in tbl["foreign_keys"]:
                ref_table = fk["ref_table"]
                if ref_table not in self.tables:
                    continue

                from_pk = set(tbl["pk"])
                unique_set = tbl.get("unique_cols", set())
                fk_col_in_pk = fk["from"] in from_pk
                fk_col_unique = fk["from"] in unique_set
                ref_pk = set(self.tables[ref_table]["pk"])
                fk_target_in_pk = fk["to"] in ref_pk

                is_self_ref = (tbl_name == ref_table)

                if (not is_self_ref) and tbl_name in join_tables:
                    rtype = "M:N"
                elif (not is_self_ref) and (fk_col_in_pk or fk_col_unique) and fk_target_in_pk:
                    rtype = "1:1"
                else:
                    rtype = "1:N"

                self.relations.append({
                    "from_table": ref_table, "from_col": fk["to"],
                    "to_table": tbl_name, "to_col": fk["from"],
                    "type": rtype
                })

    def auto_layout(self):
        if not self.tables:
            return

        visited = set()
        levels = {}
        queue = []

        table_list = list(self.tables.keys())
        indegree = {t: 0 for t in table_list}
        for t in table_list:
            for fk in self.tables[t]["foreign_keys"]:
                if fk["ref_table"] in indegree and fk["ref_table"] != t:
                    indegree[t] += 1

        for t in table_list:
            if indegree[t] == 0:
                queue.append(t)
                levels[t] = 0
                visited.add(t)

        while queue:
            current = queue.pop(0)
            current_level = levels.get(current, 0)
            for t in table_list:
                if t in visited:
                    continue
                for fk in self.tables[t]["foreign_keys"]:
                    if fk["ref_table"] == current:
                        indegree[t] -= 1
                        if indegree[t] <= 0:
                            visited.add(t)
                            levels[t] = current_level + 1
                            queue.append(t)
                            break

        for t in table_list:
            if t not in levels:
                levels[t] = len([lv for lv in levels.values() if lv > 0])

        level_groups = {}
        for t, lv in levels.items():
            level_groups.setdefault(lv, []).append(t)

        sorted_levels = sorted(level_groups.keys())
        x = 60
        for lv in sorted_levels:
            tables_at_level = sorted(level_groups[lv])
            y = 60
            for t in tables_at_level:
                col_count = len(self.tables[t]["columns"])
                tbl_h = self.HEADER_HEIGHT + col_count * self.ROW_HEIGHT + 8
                self.tables[t]["x"] = x
                self.tables[t]["y"] = y
                y += tbl_h + self.V_GAP
            x += self.TABLE_WIDTH + self.H_GAP

        self._resolve_overlaps()

    def _resolve_overlaps(self):
        changed = True
        iterations = 0
        while changed and iterations < 50:
            changed = False
            iterations += 1
            items = list(self.tables.keys())
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    a, b = items[i], items[j]
                    ax, ay = self.tables[a]["x"], self.tables[a]["y"]
                    bx, by = self.tables[b]["x"], self.tables[b]["y"]
                    ah = self.HEADER_HEIGHT + len(self.tables[a]["columns"]) * self.ROW_HEIGHT + 8
                    bh = self.HEADER_HEIGHT + len(self.tables[b]["columns"]) * self.ROW_HEIGHT + 8

                    overlap_x = ax < bx + self.TABLE_WIDTH and ax + self.TABLE_WIDTH > bx
                    overlap_y = ay < by + bh and ay + ah > by

                    if overlap_x and overlap_y:
                        if abs(ax - bx) < abs(ay - by):
                            if ay < by:
                                self.tables[b]["y"] = ay + ah + self.V_GAP
                            else:
                                self.tables[a]["y"] = by + bh + self.V_GAP
                        else:
                            if ax < bx:
                                self.tables[b]["x"] = ax + self.TABLE_WIDTH + self.H_GAP
                            else:
                                self.tables[a]["x"] = bx + self.TABLE_WIDTH + self.H_GAP
                        changed = True

    def _table_height(self, tbl_name):
        return self.HEADER_HEIGHT + len(self.tables[tbl_name]["columns"]) * self.ROW_HEIGHT + 8

    def draw_er_diagram(self):
        self.canvas.delete("all")
        self.table_boxes = {}

        for tbl_name, tbl in self.tables.items():
            self._draw_table(tbl_name, tbl["x"], tbl["y"])

        for rel in self.relations:
            self._draw_relation(rel)

        self._update_scroll_region()

    def _draw_table(self, tbl_name, x, y):
        w = self.TABLE_WIDTH
        h = self._table_height(tbl_name)
        cols = self.tables[tbl_name]["columns"]
        pk_set = set(self.tables[tbl_name]["pk"])
        fk_set = set(fk["from"] for fk in self.tables[tbl_name]["foreign_keys"])

        base_items = []

        shadow = self.canvas.create_rectangle(x + 3, y + 3, x + w + 3, y + h + 3,
                                              fill="#cccccc", outline="", tags=("table", tbl_name))
        base_items.append(shadow)

        box = self.canvas.create_rectangle(x, y, x + w, y + h,
                                           fill="#ffffff", outline="#2c5f8a", width=2,
                                           tags=("table", tbl_name))
        base_items.append(box)

        header_bg = self.canvas.create_rectangle(x + 1, y + 1, x + w - 1, y + self.HEADER_HEIGHT,
                                                 fill="#3a7bbf", outline="", tags=("table", tbl_name))
        base_items.append(header_bg)

        title = self.canvas.create_text(x + w / 2, y + self.HEADER_HEIGHT / 2,
                                        text=tbl_name, fill="white",
                                        font=("Arial", 11, "bold"),
                                        tags=("table", tbl_name))
        base_items.append(title)

        line_y = y + self.HEADER_HEIGHT
        sep = self.canvas.create_line(x + 1, line_y, x + w - 1, line_y,
                                      fill="#2c5f8a", width=1, tags=("table", tbl_name))
        base_items.append(sep)

        col_y = line_y + self.ROW_HEIGHT / 2 + 2
        for i, col in enumerate(cols):
            is_pk = col["name"] in pk_set
            is_fk = col["name"] in fk_set

            if i < len(cols) - 1:
                sep_line = self.canvas.create_line(x + 6, col_y + self.ROW_HEIGHT / 2,
                                                   x + w - 6, col_y + self.ROW_HEIGHT / 2,
                                                   fill="#e0e0e0", dash=(3, 2),
                                                   tags=("table", tbl_name))
                base_items.append(sep_line)

            marker = ""
            color = "#222"
            f = ("Arial", 10)
            if is_pk and is_fk:
                marker = "◆●"
                color = "#8b008b"
                f = ("Arial", 10, "bold")
            elif is_pk:
                marker = "◆"
                color = "#c0392b"
                f = ("Arial", 10, "bold")
            elif is_fk:
                marker = "●"
                color = "#1e6bb8"
                f = ("Arial", 10, "italic")

            left_x = x + 14
            if marker:
                mk = self.canvas.create_text(left_x - 8, col_y, text=marker, fill=color,
                                             font=("Arial", 9, "bold"),
                                             tags=("table", tbl_name))
                base_items.append(mk)
                left_x += 6

            nm = self.canvas.create_text(left_x, col_y, text=col["name"], fill=color,
                                         anchor="w", font=f,
                                         tags=("table", tbl_name))
            base_items.append(nm)

            tp = self.canvas.create_text(x + w - 10, col_y, text=col["type"],
                                         fill="#666", anchor="e", font=("Arial", 9),
                                         tags=("table", tbl_name))
            base_items.append(tp)

            col_y += self.ROW_HEIGHT

        for item in base_items:
            self.canvas.tag_bind(item, "<ButtonPress-1>",
                                 lambda e, tn=tbl_name: self._start_drag(e, tn))
            self.canvas.tag_bind(item, "<B1-Motion>",
                                 lambda e, tn=tbl_name: self._on_drag(e, tn))
            self.canvas.tag_bind(item, "<ButtonRelease-1>",
                                 lambda e, tn=tbl_name: self._end_drag(e, tn))

        self.table_boxes[tbl_name] = {"x": x, "y": y, "w": w, "h": h, "items": base_items}

    def _draw_relation(self, rel):
        ft = rel["from_table"]
        tt = rel["to_table"]

        if ft not in self.table_boxes or tt not in self.table_boxes:
            return

        fb = self.table_boxes[ft]
        tb = self.table_boxes[tt]

        from_idx = self._col_index(ft, rel["from_col"])
        to_idx = self._col_index(tt, rel["to_col"])
        if from_idx < 0:
            from_idx = 0
        if to_idx < 0:
            to_idx = 0

        from_point_y = fb["y"] + self.HEADER_HEIGHT + from_idx * self.ROW_HEIGHT + self.ROW_HEIGHT / 2 + 2
        to_point_y = tb["y"] + self.HEADER_HEIGHT + to_idx * self.ROW_HEIGHT + self.ROW_HEIGHT / 2 + 2

        fx, fy, tx, ty = self._connect_points(fb, tb, from_point_y, to_point_y)

        rtype = rel["type"]
        color = "#555"
        dash = None
        if rtype == "1:1":
            color = "#27ae60"
        elif rtype == "1:N":
            color = "#2980b9"
        elif rtype == "M:N":
            color = "#8e44ad"
            dash = (6, 3)

        mid_x = (fx + tx) / 2
        mid_y = (fy + ty) / 2

        bend = abs(tx - fx) > 60 or abs(ty - fy) > 60
        if bend:
            path = self._bend_path(fx, fy, tx, ty, fb, tb)
        else:
            path = [fx, fy, tx, ty]

        line_id = self.canvas.create_line(*path, fill=color, width=2,
                                          dash=dash if dash else (),
                                          arrow=tk.LAST, arrowshape=(14, 14, 5))

        self.canvas.tag_lower(line_id, "table")

        rtype_label = f"  {rtype}  "
        bg = self.canvas.create_rectangle(mid_x - 22, mid_y - 10, mid_x + 22, mid_y + 10,
                                          fill="#fff9e6", outline=color, width=1)
        lbl = self.canvas.create_text(mid_x, mid_y, text=rtype_label.strip(),
                                      fill=color, font=("Arial", 9, "bold"))

        self.canvas.tag_lower(bg, "table")
        self.canvas.tag_raise(lbl, "table")
        self.canvas.tag_raise(bg, "table")

    def _bend_path(self, fx, fy, tx, ty, fb, tb):
        dx = tx - fx
        dy = ty - fy
        path = []
        if abs(dx) > abs(dy):
            mid_x = (fx + tx) // 2
            path = [fx, fy, mid_x, fy, mid_x, ty, tx, ty]
        else:
            mid_y = (fy + ty) // 2
            path = [fx, fy, fx, mid_y, tx, mid_y, tx, ty]
        return path

    def _connect_points(self, fb, tb, from_y, to_y):
        fx_center = fb["x"] + fb["w"] / 2
        tx_center = tb["x"] + tb["w"] / 2

        dx = tx_center - fx_center
        dy = to_y - from_y

        if abs(dx) >= abs(dy):
            if dx >= 0:
                fx = fb["x"] + fb["w"]
                tx = tb["x"]
            else:
                fx = fb["x"]
                tx = tb["x"] + tb["w"]
            fy = from_y
            ty = to_y
        else:
            if dy >= 0:
                fy = fb["y"] + fb["h"]
                ty = tb["y"]
            else:
                fy = fb["y"]
                ty = tb["y"] + tb["h"]
            fx = fx_center
            tx = tx_center

        return fx, fy, tx, ty

    def _col_index(self, tbl_name, col_name):
        for i, c in enumerate(self.tables[tbl_name]["columns"]):
            if c["name"] == col_name:
                return i
        return -1

    def _start_drag(self, event, tbl_name):
        if tbl_name not in self.table_boxes:
            return
        b = self.table_boxes[tbl_name]
        self._drag_data = {
            "table": tbl_name,
            "start_x": event.x,
            "start_y": event.y,
            "orig_x": b["x"],
            "orig_y": b["y"]
        }
        self.canvas.config(cursor="fleur")

    def _on_drag(self, event, tbl_name):
        if not self._drag_data or self._drag_data["table"] != tbl_name:
            return
        d = self._drag_data
        dx = (event.x - d["start_x"]) / self.scale
        dy = (event.y - d["start_y"]) / self.scale
        new_x = d["orig_x"] + dx
        new_y = d["orig_y"] + dy

        self.tables[tbl_name]["x"] = new_x
        self.tables[tbl_name]["y"] = new_y
        self.draw_er_diagram()

    def _end_drag(self, event, tbl_name):
        self._drag_data = None
        self.canvas.config(cursor="")

    def _set_scale(self, factor, reset=False):
        if reset:
            self.scale = 1.0
        else:
            self.scale *= factor
            if self.scale < 0.3:
                self.scale = 0.3
            if self.scale > 4.0:
                self.scale = 4.0
        self.canvas.scale("all", 0, 0, self.scale, self.scale)
        self._update_scroll_region()

    def _on_mousewheel(self, event):
        if event.state & 0x0004:
            if event.delta > 0:
                self._set_scale(self.SCALE_FACTOR)
            else:
                self._set_scale(1 / self.SCALE_FACTOR)
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _update_scroll_region(self):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 100
            self.canvas.configure(scrollregion=(
                bbox[0] - padding, bbox[1] - padding,
                bbox[2] + padding, bbox[3] + padding
            ))

    def _relayout(self):
        self.auto_layout()
        self.draw_er_diagram()

    def _refresh(self):
        self.analyze_schema()
        if not self.tables:
            messagebox.showinfo("提示", "数据库中没有表")
            return
        self.auto_layout()
        self.draw_er_diagram()


def main():
    root = tk.Tk()
    app = SQLiteManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
