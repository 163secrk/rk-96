import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
import csv
import json
from db_connection import DBConnection
from er_diagram_window import ERDiagramWindow


class SQLiteManager:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite 数据库管理器")
        self.root.geometry("1200x800")

        self.db = DBConnection()
        self.current_table = None

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
            columns, rows = self.db.get_table_data(table_name)
            self.display_data(columns, rows)
            self.current_table = table_name
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
        if not self.db.is_connected():
            messagebox.showwarning("警告", "请先打开数据库")
            return

        sql = self.sql_text.get("1.0", tk.END).strip()
        if not sql:
            messagebox.showwarning("警告", "请输入SQL语句")
            return

        try:
            columns, rows, count = self.db.execute_sql(sql)

            if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA"):
                if rows:
                    self.display_data(columns, rows)
                    self.status_label.config(text=f"查询成功: {count} 行")
                else:
                    self.clear_data_table()
                    self.status_label.config(text="查询成功: 无结果")
            else:
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
