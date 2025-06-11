from os import path,makedirs,remove
import sqlite3
from uuid import uuid4
from shutil import copy2
from PySide6.QtCore import QStandardPaths

class AvatarManager:
    """管理头像文件的存储和加载"""
    def __init__(self):
        self.avatar_dir = path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation),
            'avatars'
        )
        makedirs(self.avatar_dir, exist_ok=True)
    
    def save_avatar(self, source_path):
        """保存头像文件到应用目录"""
        if not path.exists(source_path):
            return source_path
        
        ext = path.splitext(source_path)[1]
        filename = f"{uuid4().hex}{ext}"
        dest_path = path.join(self.avatar_dir, filename)
        
        try:
            copy2(source_path, dest_path)
            return dest_path
        except Exception as e:
            print(f"保存头像失败: {e}")
            return source_path
    
    def get_avatar(self, avatar_path):
        """获取头像路径，如果不存在返回None"""
        if avatar_path and path.exists(avatar_path):
            return avatar_path
        return None
    
    def delete_avatar(self, avatar_path):
        """删除头像文件"""
        if avatar_path and path.exists(avatar_path):
            try:
                remove(avatar_path)
                return True
            except Exception as e:
                print(f"删除头像失败: {e}")
        return False
    
    def get_default_avatar(self):
        """获取默认头像路径"""
        default_path = path.join(self.avatar_dir, "default.png")
        if path.exists(default_path):
            return default_path
        return None

class AccountManager:
    """管理账户数据的存储和检索"""
    def __init__(self):
        self.avatar_manager = AvatarManager()
        self.db_path = path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation),
            'accounts.db'
        )
        makedirs(path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modeltype TEXT NOT NULL UNIQUE,
            modelname TEXT NOT NULL,
            apikey TEXT ,
            tavilykey TEXT,
            remember_apikey BOOLEAN DEFAULT 0,
            auto_login BOOLEAN DEFAULT 0,
            avatar_path TEXT,
            api_base TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        # ,UNIQUE(modeltype, modelname))
        conn.commit()
        conn.close()
    
    def add_account(self, modeltype, modelname, apikey, tavilykey=None, 
                   remember_apikey=False, auto_login=False, avatar_path=None, api_base=None):
        """添加新账户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO accounts 
            (modeltype, modelname, apikey, tavilykey, remember_apikey, auto_login, avatar_path, api_base)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (modeltype, modelname, apikey, tavilykey, 
                 remember_apikey, auto_login, avatar_path, api_base))
            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            return False
        finally:
            conn.close()
    
    def update_account_pro(self, modeltype, **updates):
        """
        更新账户的多个字段
        :param modeltype: 模型类型，用于定位账户
        :param updates: 要更新的字段键值对（包含 modelname 等）
        :return: 是否更新成功
        """
        # 允许更新的字段
        allowed_fields = {'apikey', 'tavilykey', 'remember_apikey', 'auto_login', 'avatar_path', 'modelname','baseurl'}
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not updates:
            return False  # 没有需要更新的字段
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 拼接 sql
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [modeltype]
            
            cursor.execute(f'''
            UPDATE accounts 
            SET {set_clause}
            WHERE modeltype = ?
            ''', values)
            
            conn.commit()
            return cursor.rowcount > 0  # 是否有行被更新
        except Exception as e:
            print(f"更新账户失败: {e}")
            return False
        finally:
            conn.close()

    def update_account(self, account_id, **kwargs):
        """更新账户信息"""
        valid_fields = {'modelname', 'apikey', 'tavilykey', 'remember_apikey', 'avatar_path','auto_login', 'api_base'}
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not updates:
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [account_id]
            
            cursor.execute(f'''
            UPDATE accounts 
            SET {set_clause}
            WHERE id = ?
            ''', values)
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_accounts(self):
        """获取所有账户基本信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id, modeltype, modelname, remember_apikey, auto_login 
            FROM accounts 
            ORDER BY created_at DESC
            ''')
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_account_details(self, account_id):
        """获取账户详细信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT modeltype, modelname, apikey, tavilykey, remember_apikey, auto_login, avatar_path, api_base
            FROM accounts 
            WHERE id = ?
            ''', (account_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def get_account_details_by_modeltype(self, modeltype):
        """根据 modeltype 获取账户详细信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT modeltype, modelname, apikey, tavilykey, remember_apikey, auto_login, avatar_path, api_base
            FROM accounts 
            WHERE modeltype = ?
            ''', (modeltype,))
            return cursor.fetchone()  # 查到返回元组，没查到返回 None
        finally:
            conn.close()

    def get_account_id_by_modeltype(self, modeltype):
        """根据 modeltype 获取 account id"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id
            FROM accounts
            WHERE modeltype = ?
            ''', (modeltype,))
            
            result = cursor.fetchone()
            
            if result:
                return result[0]  # 返回 account id
            else:
                return None  # 没找到
        finally:
            conn.close()

    def update_avatar(self, account_id, new_avatar_path):
        """更新账户头像"""
        # 获取旧头像路径
        details = self.get_account_details(account_id)
        if not details:
            raise ValueError("账户不存在")
        old_avatar_path = details[6]
        
        # 保存新头像
        new_stored_path = self.avatar_manager.save_avatar(new_avatar_path)
        if not new_stored_path:
            raise ValueError("保存选择头像失败")
        
        # 更新数据库
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE accounts SET avatar_path = ? WHERE id = ?
            ''', (new_stored_path, account_id))
            conn.commit()
            
            # 删除旧头像
            if old_avatar_path:
                try:
                    self.avatar_manager.delete_avatar(old_avatar_path)
                except Exception as e:
                    raise ValueError(f"删除旧头像失败: {e}")
                finally:return new_stored_path
        except Exception as e:
            print(f"更新头像失败: {e}")
            self.avatar_manager.delete_avatar(new_stored_path)
            raise ValueError("头像保存地址写入数据库失败")
        finally:
            conn.close()
    
    def delete_account(self, account_id):
        """删除账户及其头像"""
        avatar_path = None
        details = self.get_account_details(account_id)
        if details:
            avatar_path = details[6]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            conn.commit()
            
            if avatar_path:
                try:
                    self.avatar_manager.delete_avatar(avatar_path)
                except Exception as e:
                    print(f"删除旧头像失败: {e}")
                    pass
            return cursor.rowcount > 0
        except Exception as e:
            print(f"删除账户失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_auto_login_account(self):
        """获取设置为自动登录的账户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id FROM accounts 
            WHERE auto_login = 1
            LIMIT 1
            ''')
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()