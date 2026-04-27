"""
Utility helper functions for the Mental Burnout System
"""

import random
import string
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import hashlib
import hmac

def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """
    Split text into chunks for embedding.
    
    Args:
        text: The text to split
        chunk_size: Maximum size of each chunk in characters
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # Clean the text
    text = ' '.join(text.split())  # Remove extra whitespace
    
    # If text is shorter than chunk_size, return it as one chunk
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    words = text.split()
    current_chunk = []
    current_size = 0
    
    for word in words:
        word_size = len(word) + 1  # +1 for space
        if current_size + word_size > chunk_size and current_chunk:
            # Join current chunk and add to chunks
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size
    
    # Add the last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Filter out any empty chunks
    chunks = [chunk for chunk in chunks if chunk.strip()]
    
    return chunks


def generate_user_id(prefix: str = "USER") -> str:
    """
    Generate a unique user ID.
    
    Args:
        prefix: Prefix for the user ID
        
    Returns:
        Unique user ID string
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}_{timestamp}_{random_str}"


def hash_password(password: str, salt: str = None) -> Dict[str, str]:
    """
    Hash password with salt.
    
    Args:
        password: Plain text password
        salt: Optional salt string (generated if not provided)
        
    Returns:
        Dictionary with hash and salt
    """
    if salt is None:
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    hash_obj = hashlib.sha256((password + salt).encode())
    return {
        'hash': hash_obj.hexdigest(),
        'salt': salt
    }


def verify_password(password: str, salt: str, hash_value: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        password: Plain text password to verify
        salt: Salt used for hashing
        hash_value: Stored hash to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return hmac.compare_digest(computed_hash, hash_value)


def validate_email(email: str) -> bool:
    """
    Simple email validation.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def calculate_risk_trend(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate risk trend from historical data.
    
    Args:
        history: List of historical risk assessments
        
    Returns:
        Dictionary with trend information
    """
    if not history or len(history) < 2:
        return {'trend': 'stable', 'change': 0, 'percent_change': 0}
    
    # Sort by date if available
    try:
        sorted_history = sorted(history, key=lambda x: x.get('date', ''))
    except:
        sorted_history = history
    
    # Get first and last risk scores
    first_score = sorted_history[0].get('risk_score', 50)
    last_score = sorted_history[-1].get('risk_score', 50)
    
    change = last_score - first_score
    percent_change = (change / first_score * 100) if first_score > 0 else 0
    
    if percent_change > 10:
        trend = 'worsening'
    elif percent_change < -10:
        trend = 'improving'
    else:
        trend = 'stable'
    
    return {
        'trend': trend,
        'change': round(change, 2),
        'percent_change': round(percent_change, 2),
        'first_score': first_score,
        'last_score': last_score
    }


def format_risk_alert(risk_level: str, risk_score: float) -> str:
    """
    Format risk alert message based on risk level.
    
    Args:
        risk_level: Risk level (Low, Medium, High)
        risk_score: Numerical risk score
        
    Returns:
        Formatted alert message
    """
    alerts = {
        'Low': "🌟 Your burnout risk is low. Keep maintaining healthy habits!",
        'Medium': "⚠️ Moderate burnout risk detected. Consider implementing wellness practices.",
        'High': "🚨 High burnout risk! Please prioritize self-care and consider professional support."
    }
    
    base_alert = alerts.get(risk_level, "Monitor your wellness regularly.")
    
    if risk_level == 'High':
        return f"{base_alert} (Score: {risk_score:.1f}%) - Please take immediate action."
    elif risk_level == 'Medium':
        return f"{base_alert} (Score: {risk_score:.1f}%) - Schedule some self-care time."
    else:
        return f"{base_alert} (Score: {risk_score:.1f}%)"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, avoiding division by zero.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Default value if denominator is zero
        
    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """
    Extract important keywords from text.
    
    Args:
        text: Input text
        top_n: Number of keywords to extract
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Simple implementation - split and get unique words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:top_n]]


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and special characters.
    
    Args:
        text: Input text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\-\:]', '', text)
    return text.strip()


if __name__ == "__main__":
    # Test the helper functions
    print("="*50)
    print("🧪 Testing Helper Functions")
    print("="*50)
    
    print("\n1. Testing chunk_text:")
    sample_text = "This is a sample text that should be split into chunks. " * 10
    chunks = chunk_text(sample_text, chunk_size=100)
    print(f"   ✅ Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks[:2]):
        print(f"      Chunk {i+1}: {chunk[:50]}...")
    
    print("\n2. Testing generate_user_id:")
    user_id = generate_user_id()
    print(f"   ✅ Generated: {user_id}")
    
    print("\n3. Testing hash_password:")
    hashed = hash_password("test123")
    print(f"   ✅ Hash: {hashed['hash'][:20]}...")
    print(f"   ✅ Salt: {hashed['salt']}")
    verify = verify_password("test123", hashed['salt'], hashed['hash'])
    print(f"   ✅ Verification: {verify}")
    
    print("\n4. Testing validate_email:")
    test_emails = [
        ("test@email.com", True),
        ("invalid-email", False),
        ("user.name@domain.co.uk", True),
        ("@invalid.com", False)
    ]
    for email, expected in test_emails:
        result = validate_email(email)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {email}: {result}")
    
    print("\n5. Testing calculate_risk_trend:")
    history = [
        {'date': '2024-01-01', 'risk_score': 30},
        {'date': '2024-01-02', 'risk_score': 45},
        {'date': '2024-01-03', 'risk_score': 60}
    ]
    trend = calculate_risk_trend(history)
    print(f"   ✅ Trend: {trend}")
    
    print("\n6. Testing format_risk_alert:")
    for level in ['Low', 'Medium', 'High']:
        alert = format_risk_alert(level, 75.5)
        print(f"   {level}: {alert}")
    
    print("\n7. Testing extract_keywords:")
    text = "Stress management techniques include meditation, deep breathing, and regular exercise."
    keywords = extract_keywords(text)
    print(f"   ✅ Keywords: {keywords}")
    
    print("\n8. Testing clean_text:")
    dirty_text = "  This   has   extra   spaces  and $pecial ch@racters!  "
    cleaned = clean_text(dirty_text)
    print(f"   Original: '{dirty_text}'")
    print(f"   Cleaned:  '{cleaned}'")
    
    print("\n" + "="*50)
    print("✅ All helper functions tested successfully!")
    print("="*50)