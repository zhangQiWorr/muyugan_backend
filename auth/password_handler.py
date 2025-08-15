"""
密码处理器
"""
from passlib.context import CryptContext
import secrets
import string
from typing import Optional


class PasswordHandler:
    """密码处理器"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_reset_token(self, length: int = 32) -> str:
        """生成密码重置令牌"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_verification_token(self, length: int = 32) -> str:
        """生成邮箱验证令牌"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def validate_password_strength(self, password: str) -> dict:
        """验证密码强度"""
        result = {
            "is_valid": True,
            "errors": [],
            "score": 0
        }
        
        # 长度检查
        if len(password) < 8:
            result["is_valid"] = False
            result["errors"].append("密码长度至少8位")
        else:
            result["score"] += 1
        
        # 包含数字
        if any(c.isdigit() for c in password):
            result["score"] += 1
        else:
            result["errors"].append("密码应包含至少一个数字")
        
        # 包含小写字母
        if any(c.islower() for c in password):
            result["score"] += 1
        else:
            result["errors"].append("密码应包含至少一个小写字母")
        
        # 包含大写字母
        if any(c.isupper() for c in password):
            result["score"] += 1
        else:
            result["errors"].append("密码应包含至少一个大写字母")
        
        # 包含特殊字符
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if any(c in special_chars for c in password):
            result["score"] += 1
        else:
            result["errors"].append("密码应包含至少一个特殊字符")
        
        # 最终验证（至少满足3个条件）
        if result["score"] < 3:
            result["is_valid"] = False
        
        return result
    
    def generate_secure_password(self, length: int = 12) -> str:
        """生成安全密码"""
        # 确保包含各种字符类型
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # 每种类型至少一个字符
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # 剩余长度随机选择
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # 打乱顺序
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password) 