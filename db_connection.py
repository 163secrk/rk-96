import sqlite3
import os


class DBConnection:
    def __init__(self):
        self.conn = None
        self.current_db = None

    def connect(self, filename):
        self.close()
        self.conn = sqlite3.connect(filename)
        self.conn.row_factory = sqlite3.Row
        self.current_db = filename
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.current_db = None

    def is_connected(self):
        return self.conn is not None

    def quote_identifier(self, identifier):
        return f'"{identifier}"'

    def get_tables(self):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def get_views(self):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def get_table_info(self, table_name):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({self.quote_identifier(table_name)})")
        return cursor.fetchall()

    def get_table_columns(self, table_name):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute(f'PRAGMA table_info("{table_name}")')
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
        return cols, pk_cols

    def get_foreign_keys(self, table_name):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute(f'PRAGMA foreign_key_list("{table_name}")')
        fks = []
        for fk in cursor.fetchall():
            fid, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
            fks.append({
                "ref_table": ref_table, "from": from_col, "to": to_col
            })
        return fks

    def get_indexes(self, table_name):
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA index_list({self.quote_identifier(table_name)})")
        return cursor.fetchall()

    def get_unique_columns(self, table_name):
        if not self.conn:
            return set()
        cursor = self.conn.cursor()
        cursor.execute(f'PRAGMA index_list("{table_name}")')
        unique_cols = set()
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
        return unique_cols

    def get_table_data(self, table_name):
        if not self.conn:
            return None, None
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {self.quote_identifier(table_name)}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return columns, rows

    def execute_sql(self, sql):
        if not self.conn:
            raise Exception("未连接到数据库")
        cursor = self.conn.cursor()
        cursor.execute(sql)
        if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA"):
            rows = cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in cursor.description]
                return columns, rows, len(rows)
            return None, None, 0
        else:
            self.conn.commit()
            return None, None, cursor.rowcount

    def rollback(self):
        if self.conn:
            self.conn.rollback()
