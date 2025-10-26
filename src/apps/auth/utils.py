import smtplib
import secrets
import hashlib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from decouple import config

# Password hashing - using SHA256 pre-hash to handle long passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = config('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(config('ACCESS_TOKEN_EXPIRE_MINUTES', default=30))
EMAIL_TOKEN_EXPIRE_HOURS = int(config('EMAIL_TOKEN_EXPIRE_HOURS', default=24))

# Email settings
SMTP_USER = config('SMTP_USER')
SMTP_PASSWORD = config('SMTP_PASSWORD')
SMTP_FROM_NAME = config('SMTP_FROM_NAME', default='Your App')
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')


def _hash_password_for_bcrypt(password: str) -> str:
    """Pre-hash password with SHA256 to handle bcrypt's 72-byte limit."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    # Pre-hash the password to handle bcrypt limit
    pre_hashed = _hash_password_for_bcrypt(plain_password)
    return pwd_context.verify(pre_hashed, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Pre-hash the password to handle bcrypt limit
    pre_hashed = _hash_password_for_bcrypt(password)
    return pwd_context.hash(pre_hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token with longer expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 7 days for refresh token
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_email_verification_token(email: str) -> str:
    """Create JWT token for email verification."""
    expire = datetime.utcnow() + timedelta(hours=EMAIL_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": email, "exp": expire, "type": "email_verification"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_reset_token() -> str:
    """Create a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """Verify JWT token and return the subject (email)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        # Check token type if specified
        if token_type != "access" and payload.get("type") != token_type:
            return None
            
        if email is None:
            return None
        return email
    except JWTError:
        return None


def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
    """Send email using Gmail SMTP."""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        
        # Gmail SMTP configuration
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enable security
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        # Send email
        text = msg.as_string()
        server.sendmail(SMTP_USER, to_email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_verification_email(email: str, token: str) -> bool:
    """Send email verification email."""
    verification_link = f"{FRONTEND_URL}/verify-email?token={token}"
    
    subject = "Verify Your Email Address"
    body = f"""
    <html>
        <body>
            <h2>Welcome to {SMTP_FROM_NAME}!</h2>
            <p>Please click the link below to verify your email address:</p>
            <p><a href="{verification_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
            <p>Or copy and paste this link in your browser:</p>
            <p>{verification_link}</p>
            <p>This link will expire in {EMAIL_TOKEN_EXPIRE_HOURS} hours.</p>
            <br>
            <p>If you didn't create an account, please ignore this email.</p>
        </body>
    </html>
    """
    
    return send_email(email, subject, body, is_html=True)


def send_password_reset_email(email: str, token: str) -> bool:
    """Send password reset email."""
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    
    subject = "Reset Your Password"
    body = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You have requested to reset your password. Click the link below to reset it:</p>
            <p><a href="{reset_link}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
            <p>Or copy and paste this link in your browser:</p>
            <p>{reset_link}</p>
            <p>This link will expire in 1 hour for security reasons.</p>
            <br>
            <p>If you didn't request a password reset, please ignore this email.</p>
        </body>
    </html>
    """
    
    return send_email(email, subject, body, is_html=True)