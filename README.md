# 🤖 Telegram Auto-Responder Bot

An intelligent AI-powered Telegram auto-responder bot that manages your account when you're away. Features multilingual support (English, French, Arabic, Darija), product catalog management, and speech-to-text capabilities.

## ✨ Features

- 🤖 **AI-Powered Responses** - Uses Azure OpenAI GPT-4o for intelligent, context-aware replies
- 🌍 **Multilingual Support** - English, French, Arabic, and Darija (Moroccan/Algerian Arabic)
- 📦 **Product Catalog** - Automatic product promotion and sales assistance
- 🎤 **Speech-to-Text** - Handles voice messages using Azure OpenAI Whisper
- 👥 **Smart Context Detection** - Distinguishes between friends and customers
- 💾 **Conversation History** - Maintains context across conversations
- 🔒 **Secure Configuration** - Environment variables for sensitive data

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Telegram API credentials
- Azure OpenAI resource with GPT-4o and Whisper deployments
- FFmpeg (for voice message processing)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd telegram-auto-responder
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install FFmpeg** (for voice messages)
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Run the bot**
```bash
python telegram_auto_responder.py
```

## ⚙️ Configuration

### Required Environment Variables

```env
# Telegram API (get from https://my.telegram.org)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=your_phone_number

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_GPT_DEPLOYMENT=your_gpt_deployment_name
AZURE_WHISPER_DEPLOYMENT=your_whisper_deployment_name

# Owner Information
OWNER_NAME=your_name
```

### Optional Settings

```env
# Bot Behavior
RESPONSE_DELAY=2                    # Delay before responding (seconds)
MAX_RESPONSE_TOKENS=150            # Maximum response length
AUTO_RESPOND=true                  # Enable/disable auto-responses
RESPOND_TO_GROUPS=false           # Respond in group chats

# File Paths
PRODUCTS_FILE=products.json        # Product catalog file
LOG_LEVEL=INFO                     # Logging level
```

## 📦 Product Management

Edit `products.json` to add your products:

```json
[
  {
    "id": 1,
    "name": "Your Product",
    "price": "100",
    "currency": "USD",
    "description": "Product description",
    "category": "electronics",
    "available": true
  }
]
```

## 🎯 How It Works

1. **Context Detection** - AI analyzes messages to determine if user is a friend/family or potential customer
2. **Dynamic Responses** - Tailors responses based on context, conversation history, and available products
3. **Multilingual Support** - Automatically detects and responds in the user's language
4. **Voice Processing** - Converts voice messages to text for AI processing
5. **Sales Integration** - Promotes relevant products when customers inquire

## 🛠️ Development

### Project Structure

```
telegram-auto-responder/
├── telegram_auto_responder.py     # Main bot file
├── .env                          # Environment variables (not in repo)
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── products.json                 # Product catalog (auto-generated)
├── telegram_bot.db              # SQLite database (auto-generated)
└── README.md                    # This file
```

### Key Components

- **Config**: Environment variable management with validation
- **AIResponder**: Handles AI interactions and prompt engineering
- **ProductCatalog**: Manages product information and sales
- **DatabaseManager**: Conversation history and user sessions
- **AudioConverter**: Voice message processing with FFmpeg

## 📝 Logging

The bot logs all activities to `telegram_bot.log` with timestamps:

```
2025-01-01 12:00:00 | INFO | 🤖 Enhanced Auto-responder started
2025-01-01 12:00:01 | INFO | 📨 [PRIVATE] John (123456): Hello!
2025-01-01 12:00:03 | INFO | ✅ [FRIEND] Responded to John: Hey! I'm away...
```

## 🔒 Security

- **Environment Variables**: All sensitive data in `.env` file
- **Gitignore**: Prevents committing credentials and session files
- **Session Management**: Telegram sessions stored locally
- **Input Validation**: Sanitizes user inputs and file paths

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use. Ensure compliance with Telegram's Terms of Service and your local laws when using automated responses.

## 🆘 Troubleshooting

### Common Issues

**Bot not responding:**
- Check `.env` file configuration
- Verify Azure OpenAI deployments exist
- Ensure phone number is authenticated with Telegram

**Voice messages not working:**
- Install FFmpeg and add to PATH
- Check Whisper deployment name in Azure
- Verify audio file permissions

**Database errors:**
- Delete `telegram_bot.db` to reset database
- Check file permissions in bot directory

### Getting Help

- Check logs in `telegram_bot.log`
- Verify all environment variables are set
- Ensure Azure OpenAI quotas are not exceeded

---

Made with ❤️ for intelligent conversation management