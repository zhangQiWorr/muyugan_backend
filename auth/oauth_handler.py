"""
OAuth 第三方登录处理器
"""
from typing import Optional, Dict, Any
import httpx
import os
from urllib.parse import urlencode


class OAuthHandler:
    """OAuth 第三方登录处理器"""
    
    def __init__(self):
        # Google OAuth 配置
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
        
        # GitHub OAuth 配置
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID")
        self.github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        self.github_redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback")
    
    def get_google_oauth_url(self, state: str = None) -> str:
        """获取Google OAuth授权URL"""
        if not self.google_client_id:
            raise ValueError("Google Client ID not configured")
        
        params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.google_redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        if state:
            params["state"] = state
        
        base_url = "https://accounts.google.com/o/oauth2/auth"
        return f"{base_url}?{urlencode(params)}"
    
    def get_github_oauth_url(self, state: str = None) -> str:
        """获取GitHub OAuth授权URL"""
        if not self.github_client_id:
            raise ValueError("GitHub Client ID not configured")
        
        params = {
            "client_id": self.github_client_id,
            "redirect_uri": self.github_redirect_uri,
            "scope": "user:email",
            "state": state or ""
        }
        
        base_url = "https://github.com/login/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"
    
    async def exchange_google_code(self, code: str) -> Optional[Dict[str, Any]]:
        """交换Google授权码获取用户信息"""
        if not self.google_client_id or not self.google_client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        # 获取access token
        token_data = {
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.google_redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            # 获取访问令牌
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data
            )
            
            if token_response.status_code != 200:
                return None
            
            token_info = token_response.json()
            access_token = token_info.get("access_token")
            
            if not access_token:
                return None
            
            # 获取用户信息
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                return None
            
            user_info = user_response.json()
            return {
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "verified_email": user_info.get("verified_email", False)
            }
    
    async def exchange_github_code(self, code: str) -> Optional[Dict[str, Any]]:
        """交换GitHub授权码获取用户信息"""
        if not self.github_client_id or not self.github_client_secret:
            raise ValueError("GitHub OAuth credentials not configured")
        
        async with httpx.AsyncClient() as client:
            # 获取访问令牌
            token_data = {
                "client_id": self.github_client_id,
                "client_secret": self.github_client_secret,
                "code": code
            }
            
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data=token_data,
                headers={"Accept": "application/json"}
            )
            
            if token_response.status_code != 200:
                return None
            
            token_info = token_response.json()
            access_token = token_info.get("access_token")
            
            if not access_token:
                return None
            
            # 获取用户信息
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"}
            )
            
            if user_response.status_code != 200:
                return None
            
            user_info = user_response.json()
            
            # 获取用户邮箱（GitHub可能需要单独请求）
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"token {access_token}"}
            )
            
            emails = []
            if email_response.status_code == 200:
                emails = email_response.json()
            
            primary_email = None
            for email in emails:
                if email.get("primary"):
                    primary_email = email.get("email")
                    break
            
            return {
                "id": str(user_info.get("id")),
                "username": user_info.get("login"),
                "email": primary_email or user_info.get("email"),
                "name": user_info.get("name"),
                "avatar_url": user_info.get("avatar_url")
            } 