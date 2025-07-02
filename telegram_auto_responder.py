#!/usr/bin/env python3
"""
Telegram Auto-Responder Bot
Enhanced version with AI-powered dynamic responses and speech-to-text
"""

import asyncio
import logging
import sqlite3
import json
import time
import os
import tempfile
import subprocess
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# =================== CONFIGURATION ===================
class Config:
    # Telegram API credentials
    API_ID = int(os.getenv("TELEGRAM_API_ID"))
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER")
    
    # Your info
    OWNER_NAME = os.getenv("OWNER_NAME", "User")
    
    # Azure OpenAI Configuration
    AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")
    AZURE_DEPLOYMENT = os.getenv("AZURE_GPT_DEPLOYMENT", "gpt-4o")
    
    # Speech-to-Text Configuration
    AZURE_WHISPER_DEPLOYMENT = os.getenv("AZURE_WHISPER_DEPLOYMENT", "whisper")
    
    # Text-to-Speech Configuration
    AZURE_TTS_MODEL = os.getenv("AZURE_TTS_MODEL", "tts-1-hd")
    AZURE_TTS_VOICE = os.getenv("AZURE_TTS_VOICE", "alloy")
    
    # Bot behavior
    RESPONSE_DELAY = int(os.getenv("RESPONSE_DELAY", "2"))
    MAX_HISTORY_LENGTH = int(os.getenv("MAX_HISTORY_LENGTH", "8"))
    MAX_RESPONSE_TOKENS = int(os.getenv("MAX_RESPONSE_TOKENS", "150"))
    
    # Auto-response settings
    AUTO_RESPOND = os.getenv("AUTO_RESPOND", "true").lower() == "true"
    RESPOND_TO_GROUPS = os.getenv("RESPOND_TO_GROUPS", "false").lower() == "true"
    
    # Files
    PRODUCTS_FILE = os.getenv("PRODUCTS_FILE", "products.json")
    
    @classmethod
    def validate(cls):
        """Validate required environment variables"""
        required_vars = [
            "TELEGRAM_API_ID",
            "TELEGRAM_API_HASH", 
            "TELEGRAM_PHONE_NUMBER",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# =================== AUDIO CONVERTER ===================
class AudioConverter:
    @staticmethod
    def check_ffmpeg():
        """Check if ffmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def convert_to_wav(input_file: str, output_file: str) -> bool:
        """Convert audio file to WAV format using ffmpeg"""
        try:
            cmd = [
                'ffmpeg', '-i', input_file,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',  # Overwrite output file
                output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, check=True)
            return os.path.exists(output_file)
            
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ FFmpeg conversion failed: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Audio conversion error: {e}")
            return False

# =================== PRODUCT CATALOG MANAGER ===================
class ProductCatalog:
    def __init__(self, products_file: str):
        self.products_file = products_file
        self.products = self.load_products()
    
    def load_products(self) -> List[Dict]:
        """Load products from JSON file"""
        if os.path.exists(self.products_file):
            try:
                with open(self.products_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"❌ Error loading products: {e}")
        
        # Create sample products file if it doesn't exist
        sample_products = [
            {
                "id": 1,
                "name": "Gaming Laptop",
                "price": "1500",
                "currency": "USD",
                "description": "High-performance gaming laptop with RTX 4070, 16GB RAM, perfect for gaming and work",
                "category": "electronics",
                "available": True
            },
            {
                "id": 2,
                "name": "Wireless Headphones",
                "price": "200",
                "currency": "USD", 
                "description": "Premium noise-canceling wireless headphones with 30h battery life",
                "category": "electronics",
                "available": True
            },
            {
                "id": 3,
                "name": "Programming Course",
                "price": "99",
                "currency": "USD",
                "description": "Complete Python programming course for beginners to advanced level",
                "category": "courses",
                "available": True
            }
        ]
        
        self.save_products(sample_products)
        return sample_products
    
    def save_products(self, products: List[Dict]):
        """Save products to JSON file"""
        try:
            with open(self.products_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"❌ Error saving products: {e}")
    
    def get_all_products_text(self) -> str:
        """Get all available products as text"""
        if not self.products:
            return "No products currently available."
        
        text = "📦 **Available Products:**\n\n"
        for product in self.products:
            if product.get('available', True):
                text += f"**{product['name']}**\n"
                text += f"💰 Price: {product['price']} {product['currency']}\n"
                text += f"📝 {product['description']}\n\n"
        
        return text

# =================== LOGGING SETUP ===================
def setup_logging():
    log_format = "%(asctime)s | %(levelname)8s | %(message)s"
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(os.getenv("LOG_FILE", "telegram_bot.log"), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.getLogger('telethon').setLevel(logging.WARNING)

# =================== DATABASE MANAGER ===================
class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("DATABASE_PATH", "telegram_bot.db")
        self.init_database()
    
    def init_database(self):
        """Initialize database tables with proper schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_type TEXT DEFAULT 'private'
                )
            """)
            
            # Add user_type column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE conversations ADD COLUMN user_type TEXT DEFAULT 'unknown'")
                logging.info("✅ Added user_type column to conversations table")
            except sqlite3.OperationalError:
                pass
            
            # Create user_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    conversation_history TEXT DEFAULT '[]'
                )
            """)
            
            # Add user_type column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN user_type TEXT DEFAULT 'unknown'")
                logging.info("✅ Added user_type column to user_sessions table")
            except sqlite3.OperationalError:
                pass
            
            conn.commit()
    
    def log_conversation(self, user_id: int, chat_id: int, user_message: str, 
                        bot_response: str, message_type: str = 'private', user_type: str = 'unknown'):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations (user_id, chat_id, user_message, bot_response, message_type, user_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, chat_id, user_message, bot_response, message_type, user_type))
    
    def update_user_session(self, user_id: int, first_name: str, username: str, 
                           conversation_history: List[str], user_type: str = 'unknown'):
        history_json = json.dumps(conversation_history, ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_sessions 
                (user_id, first_name, username, last_seen, message_count, conversation_history, user_type)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 
                       COALESCE((SELECT message_count FROM user_sessions WHERE user_id = ?) + 1, 1), ?, ?)
            """, (user_id, first_name, username, user_id, history_json, user_type))
    
    def get_user_history(self, user_id: int) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT conversation_history FROM user_sessions WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                try:
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    return []
            return []

# =================== AI RESPONDER ===================
class AIResponder:
    def __init__(self, config: Config):
        self.config = config
        self.product_catalog = ProductCatalog(config.PRODUCTS_FILE)
        self.audio_converter = AudioConverter()
        self.tts_converter = TTSConverter(config)
        self.setup_openai()
    
    def setup_openai(self):
        try:
            self.client = AzureOpenAI(
                api_version=self.config.AZURE_API_VERSION,
                azure_endpoint=self.config.AZURE_ENDPOINT,
                api_key=self.config.AZURE_API_KEY,
            )
            
            # Check if ffmpeg is available for audio conversion
            self.ffmpeg_available = self.audio_converter.check_ffmpeg()
            if self.ffmpeg_available:
                logging.info(f"✅ Azure OpenAI client initialized with speech-to-text support")
            else:
                logging.warning(f"⚠️  Azure OpenAI client initialized but ffmpeg not found - voice messages will be limited")
                
        except Exception as e:
            logging.error(f"❌ Failed to initialize Azure OpenAI: {e}")
            raise
    
    async def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio file to text using Azure OpenAI Whisper"""
        if not self.ffmpeg_available:
            return "[Voice message - audio conversion not available (ffmpeg required)]"
        
        temp_wav_file = None
        try:
            # Create temporary WAV file
            temp_wav_file = tempfile.mktemp(suffix='.wav')
            
            # Convert audio to WAV format
            logging.info("🔄 Converting audio format...")
            if not self.audio_converter.convert_to_wav(audio_file_path, temp_wav_file):
                return "[Voice message - audio conversion failed]"
            
            # Transcribe the converted audio
            logging.info("🎤 Transcribing converted audio...")
            with open(temp_wav_file, "rb") as audio_file:
                result = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.config.AZURE_WHISPER_DEPLOYMENT
                )
                return result.text
                
        except Exception as e:
            logging.error(f"❌ Speech-to-text error: {e}")
            return "[Voice message - transcription failed]"
        finally:
            # Clean up temporary file
            if temp_wav_file and os.path.exists(temp_wav_file):
                try:
                    os.remove(temp_wav_file)
                except:
                    pass
    
    def create_smart_system_prompt(self, user_name: str, conversation_history: List[str]) -> str:
        """Create AI-powered dynamic system prompt"""
        
        # Get products info
        products_info = self.product_catalog.get_all_products_text()
        
        return f"""You are a smart, multilingual AI assistant replying on behalf of {self.config.OWNER_NAME}, who is currently unavailable.

✨ **CRITICAL INSTRUCTIONS**:
- Keep replies SHORT and clear (2–3 sentences max)
- Always respond in the user’s language (supports English, French, Arabic, and Darija 🇲🇦🇩🇿)
- Use emojis to keep tone light and friendly (where appropriate)
- Be creative — avoid repetitive responses!
- ❗️ **NEVER reveal or mention the AI model you are using**
    - If asked, always reply: **"I'm powered by {self.config.OWNER_NAME} ✨"**

📌 **CONTEXT ANALYSIS**:
Analyze the incoming message and recent conversation history to decide:
1. Is this a **FRIEND/FAMILY** checking in casually?
   - Let them know {self.config.OWNER_NAME} is away and will reply later
   - Ask if they need help with anything
   - Be relaxed, funny ,love , and warm 😄  

2. Is this a **CUSTOMER/BUSINESS** inquiry?
   - Be professional but friendly
   - If they’re asking about products or services, mention relevant items from the catalog
   - Offer prices if applicable and suggest contacting {self.config.OWNER_NAME} to complete the order 🛍️

3. Are they asking a **general question or seeking help**?
   - Offer simple, helpful answers if possible
   - Let them know {self.config.OWNER_NAME} will get back to them soon

🛒 **PRODUCTS / SERVICES AVAILABLE**:
{products_info}

📣 **RESPONSE RULES**:

➡️ **IF CUSTOMER/BUSINESS**:
- Stay professional and helpful
- Share product/service info clearly (with prices if possible)
- Encourage them to reach out to {self.config.OWNER_NAME} for buying or more help
- Be polite, brief, and sales-positive — but not pushy

➡️ **IF FRIEND/FAMILY**:
- Use a casual and friendly tone
- Say {self.config.OWNER_NAME} is away but will respond soon
- Offer basic help if you can
- Add charm and humor 🤗✨

➡️ **IF GENERAL QUESTION**:
- Be polite and helpful
- Keep it simple
- Let them know {self.config.OWNER_NAME} will reply when available

📍 **Current user**: {user_name}  
📜 **Recent messages**: {conversation_history[-4:] if conversation_history else "First message"}
""


Remember: BE CONCISE, HELPFUL, and MATCH THE USER'S LANGUAGE!"""
    
    async def generate_response(self, user_message: str, user_name: str, 
                              conversation_history: List[str]) -> tuple[str, str]:
        """Generate AI response with dynamic context awareness"""
        try:
            # Create smart system prompt
            system_prompt = self.create_smart_system_prompt(user_name, conversation_history)
            
            # Prepare messages
            context_messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent conversation history
            for i, msg in enumerate(conversation_history[-4:]):
                role = "user" if i % 2 == 0 else "assistant"
                context_messages.append({"role": role, "content": msg})
            
            context_messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = self.client.chat.completions.create(
                messages=context_messages,
                max_tokens=self.config.MAX_RESPONSE_TOKENS,
                temperature=0.8,
                top_p=0.9,
                model=self.config.AZURE_DEPLOYMENT
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # AI determines user type based on response content
            user_type = "customer" if any(word in ai_response.lower() for word in ["product", "price", "buy", "sale"]) else "friend"
            
            return ai_response, user_type
            
        except Exception as e:
            logging.error(f"❌ OpenAI API Error: {e}")
            
            # Simple fallback
            fallback = f"Hi {user_name}! {self.config.OWNER_NAME} is away but I'll let them know you messaged 😊"
            return fallback, 'unknown'

# =================== MAIN BOT CLASS ===================
class TelegramAutoResponder:
    def __init__(self):
        self.config = Config()
        self.client = TelegramClient("auto_responder_session", 
                                   self.config.API_ID, 
                                   self.config.API_HASH)
        self.db = DatabaseManager()
        self.ai = AIResponder(self.config)
        self.my_id = None
    
    async def start(self):
        await self.client.start(phone=self.config.PHONE_NUMBER)
        me = await self.client.get_me()
        self.my_id = me.id
        
        logging.info(f"🤖 Enhanced Auto-responder started for {me.first_name}")
        logging.info(f"📦 Products loaded: {len(self.ai.product_catalog.products)}")
        logging.info("🚀 Bot ready - AI-powered dynamic responses!")
        
        if self.ai.ffmpeg_available:
            logging.info("🎤 Speech-to-text enabled for voice messages")
        else:
            logging.warning("⚠️  Speech-to-text limited - install ffmpeg for full support")
        
        # Check if TTS is properly configured
        if self.config.AZURE_TTS_MODEL and self.config.AZURE_TTS_VOICE:
            logging.info("🔊 Text-to-speech enabled - will respond with voice to voice messages")
        else:
            logging.warning("⚠️  Text-to-speech not fully configured - check AZURE_TTS_MODEL and AZURE_TTS_VOICE")
        
        self.client.add_event_handler(self.handle_new_message, events.NewMessage(incoming=True))
        await self.client.run_until_disconnected()
    
    async def handle_voice_message(self, event) -> str:
        """Handle voice messages by converting to text"""
        try:
            # Download voice message
            logging.info("📥 Downloading voice message...")
            voice_file = await event.message.download_media()
            
            if voice_file:
                # Transcribe audio
                transcribed_text = await self.ai.transcribe_audio(voice_file)
                
                # Clean up the downloaded file
                try:
                    os.remove(voice_file)
                except:
                    pass
                
                logging.info(f"📝 Voice transcribed: {transcribed_text[:100]}...")
                return f"[Voice message]: {transcribed_text}"
            
            return "[Voice message - download failed]"
            
        except Exception as e:
            logging.error(f"❌ Error handling voice message: {e}")
            return "[Voice message - could not process]"
    
    async def send_voice_response(self, event, response_text: str) -> bool:
        """Send a voice response using TTS"""
        try:
            # Generate speech from text
            audio_file_path = await self.ai.tts_converter.text_to_speech(response_text)
            
            if audio_file_path and os.path.exists(audio_file_path):
                # Send the voice message
                await event.respond(file=audio_file_path, voice_note=True)
                
                # Clean up the temporary audio file
                try:
                    os.remove(audio_file_path)
                except:
                    pass
                
                logging.info("🔊 Voice response sent successfully")
                return True
            else:
                logging.error("❌ Failed to generate voice response")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error sending voice response: {e}")
            return False
    
    async def handle_new_message(self, event):
        try:
            if not self.config.AUTO_RESPOND or event.sender_id == self.my_id:
                return
            
            if not event.is_private and not self.config.RESPOND_TO_GROUPS:
                return
            
            sender = await event.get_sender()
            user_name = self.get_display_name(sender)
            
            # Handle different message types
            is_voice_message = False
            if event.message.voice:
                user_message = await self.handle_voice_message(event)
                is_voice_message = True
            elif event.message.message:
                user_message = event.message.message
            else:
                user_message = "[Media/Sticker]"
            
            chat_type = "private" if event.is_private else "group"
            
            logging.info(f"📨 [{chat_type.upper()}] {user_name} ({event.sender_id}): {user_message}")
            
            conversation_history = self.db.get_user_history(event.sender_id)
            
            # Generate AI response
            logging.info("🤖 Generating AI response...")
            ai_response, user_type = await self.ai.generate_response(
                user_message, user_name, conversation_history
            )
            
            await asyncio.sleep(self.config.RESPONSE_DELAY)
            
            # If user sent a voice message, respond with voice
            if is_voice_message:
                # Try to send voice response first
                voice_sent = await self.send_voice_response(event, ai_response)
                if not voice_sent:
                    # Fallback to text if voice fails
                    await event.respond(ai_response)
                    logging.info("⚠️  Voice response failed, sent text instead")
                else:
                    logging.info(f"✅ [{user_type.upper()}] Voice response sent to {user_name}: {ai_response[:80]}...")
            else:
                # Send text response for text messages
                await event.respond(ai_response)
                logging.info(f"✅ [{user_type.upper()}] Text response sent to {user_name}: {ai_response[:80]}...")
            
            # Update history
            updated_history = conversation_history[-self.config.MAX_HISTORY_LENGTH:]
            updated_history.extend([user_message, ai_response])
            
            # Save to database
            self.db.log_conversation(event.sender_id, event.chat_id, 
                                   user_message, ai_response, chat_type, user_type)
            
            username = getattr(sender, 'username', '') or ''
            self.db.update_user_session(event.sender_id, user_name, username, updated_history, user_type)
            
        except Exception as e:
            logging.error(f"❌ Error handling message: {e}", exc_info=True)
    
    def get_display_name(self, user) -> str:
        if hasattr(user, 'first_name') and user.first_name:
            name = user.first_name
            if hasattr(user, 'last_name') and user.last_name:
                name += f" {user.last_name}"
            return name
        elif hasattr(user, 'username') and user.username:
            return f"@{user.username}"
        else:
            return "User"

# =================== MAIN EXECUTION ===================
async def main():
    setup_logging()
    
    try:
        # Validate environment variables
        Config.validate()
        
        logging.info("🚀 Starting Enhanced AI-Powered Telegram Auto-Responder...")
        logging.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        bot = TelegramAutoResponder()
        await bot.start()
        
    except ValueError as e:
        logging.error(f"❌ Configuration error: {e}")
        print(f"\n❌ Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
    except KeyboardInterrupt:
        logging.info("⏹️  Bot stopped by user")
    except Exception as e:
        logging.error(f"💥 Bot crashed: {e}", exc_info=True)
    finally:
        logging.info("👋 Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")