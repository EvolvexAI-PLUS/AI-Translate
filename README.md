# 🎤 AI Real-Time Translator

A production-ready real-time speech translation web application powered by Google Gemini 2.5 Flash and ElevenLabs, deployed on Railway.

## Features

- **Real-time speech translation** between Arabic and English
- **Professional UI** with modern responsive design
- **Gemini 2.5 Flash** for accurate transcription and translation
- **ElevenLabs Flash v2.5** for high-quality TTS
- **WebSocket streaming** for real-time communication
- **Voice activity detection** and audio optimization
- **Cross-device compatibility** (desktop, tablet, mobile)

## 🚀 Railway Deployment

### 1. Prepare Your Repository
```bash
# Make sure all files are ready
ls -la
# Should show: requirements.txt, railway.toml, Procfile, wsgi.py, speech_translator.py, templates/
```

### 2. Push to Git (Required for Railway)
```bash
git init
git add .
git commit -m "Initial deployment of AI Real-Time Translator"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 3. Deploy on Railway
1. Go to [Railway.app](https://railway.app) and sign in
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. Railway will automatically detect Python Flask app

### 4. Environment Variables
In Railway dashboard, go to **"Variables"** and add:
```
GOOGLE_API_KEY=your_google_gemini_api_key_here
ELEVEN_LABS_API_KEY=your_elevenlabs_api_key_here
FLASK_ENV=production
SECRET_KEY=your_secret_key_here (optional)
```

### 5. Deploy
Railway will automatically:
- Install dependencies from `requirements.txt`
- Use `railway.toml` configuration
- Start the app with `python wsgi.py`

## 🔧 Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables in .env file
GOOGLE_API_KEY=your_key_here
ELEVEN_LABS_API_KEY=your_key_here

# Run locally
python speech_translator.py
# Access at http://localhost:5001
```

## 🛠️ Project Structure

```
📁 AI Translate/
├── 📄 speech_translator.py          # Main Flask application
├── 📄 wsgi.py                      # Production entry point
├── 📄 requirements.txt             # Python dependencies
├── 📄 railway.toml                 # Railway configuration
├── 📄 Procfile                     # Railway startup script
├── 📄 .gitignore                   # Git ignore rules
├── 📄 README.md                    # This file
├── 📁 templates/
│   └── 📄 index.html              # Web interface
└── 📄 .env                        # Environment variables (local only)
```

## 🎯 API Endpoints

- `GET /` - Web interface
- `GET /status` - Application status and model info
- `POST /translate` - Audio translation endpoint

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Gemini 2.5 Flash API key | ✅ |
| `ELEVEN_LABS_API_KEY` | ElevenLabs API key | ✅ |
| `FLASK_ENV` | Environment (development/production) | ❌ |
| `SECRET_KEY` | Flask secret key (auto-generated if not set) | ❌ |
| `PORT` | Server port (Railway sets this automatically) | ❌ |

## 📊 Features

- **Recording Mode**: Click microphone → speak for 5s → get translation
- **Streaming Mode**: Click microphone → continuous real-time transcription
- **Audio Playback**: Auto-plays ElevenLabs TTS after translation
- **Language Detection**: Automatically detects Arabic vs English input
- **Performance**: Optimized for low latency with Flash models

## 🐛 Troubleshooting

### Audio Not Audible Issues

If audio works locally but not on Railway deployment:

1. **Check ElevenLabs API Key**: Ensure `ELEVEN_LABS_API_KEY` is set in Railway environment variables
2. **Verify API Key Access**: Check Railway deployment logs for successful initialization
3. **Look for Debug Messages**:
   ```
   🔍 ELEVEN_LABS_API_KEY status: Present ✅
   🔑 ElevenLabs API Key loaded: sk_cb81f...b22 ***
   ✅ ElevenLabs Flash v2.5 TTS initialized successfully
   ```
4. **Check TTS Generation**: Look for audio generation logs:
   ```
   🎤 Generating ElevenLabs TTS for: 'text' in en
   ✅ ElevenLabs TTS generated: XXXX bytes
   🎵 Audio data ready for base64 encoding
   ```

### Other Common Issues

- **HTTP 400 errors**: Fixed in frontend by proper audio data formatting
- **Microphone permission**: Ensure HTTPS/Secure context for production
- **SocketIO issues**: Railway handles WebSocket connections automatically
- **Browser autoplay**: Some browsers block autoplay - look for manual play button

### Getting ElevenLabs API Key

1. Visit [ElevenLabs](https://elevenlabs.io/account/profile)
2. Sign up/login to get your API key
3. Copy the key to Railway environment variables: `ELEVEN_LABS_API_KEY`

## 📝 License

Your project - customize as needed!

---

Made with ❤️ using Gemini 2.5 Flash, ElevenLabs, and Railway