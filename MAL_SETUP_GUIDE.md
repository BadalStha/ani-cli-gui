# MAL API Integration Setup Guide

## 🎯 Overview
Your ani-cli GUI now includes official MyAnimeList API integration using your credentials:
- **Client ID**: `01b7258226dd6250f4ef9b083eb8e39f`
- **Client Secret**: `24f5b8f783b104c65b71eb330f65516014b830222febd7e1b6585ab36e3813f9`

## ✨ New Features

### 🔐 MAL Authentication
- **OAuth2 Flow**: Secure authentication with your MAL account
- **Browser Integration**: Opens MAL login page automatically
- **Token Management**: Handles access and refresh tokens

### 🔍 Enhanced Search
- **Dual API Support**: Uses official MAL API when authenticated, falls back to Jikan
- **Better Data**: More detailed anime information from official sources
- **Faster Results**: Direct access to MAL database

### 📊 Progress Tracking
- **Manual Sync**: "Sync to MAL" button for immediate updates
- **Auto-Update**: Optional automatic progress tracking
- **Episode Management**: Accurate episode count updates

## 🚀 How to Use

### 1. Launch the Application
```powershell
cd "c:\Users\DrAnimo\Documents\anime"
C:/Users/DrAnimo/Documents/anime/.venv/Scripts/python.exe ani_cli_gui.py
```

### 2. Authenticate with MAL
1. Click **"Authenticate with MAL"** button
2. Your browser will open to MyAnimeList login page
3. Log in with your MAL account
4. Authorize the application
5. Return to the GUI - you'll see "✅ Authenticated"

### 3. Enable Official API
- Check **"Use Official MAL API"** checkbox
- This uses your authenticated account for better search results

### 4. Search and Watch
- Search for anime normally
- Select anime from results  
- Choose episode and options
- Click **"Play Selected"** to watch

### 5. Sync Progress
- **Automatic**: Enable "Auto-update MAL progress" for hands-off tracking
- **Manual**: Click "Sync to MAL" button to update progress immediately

## ⚙️ Technical Details

### Authentication Flow
1. **PKCE OAuth2**: Secure authentication without exposing secrets
2. **Local Callback**: Uses `localhost:8080` for OAuth redirect
3. **Token Storage**: Keeps access token for session duration

### API Endpoints Used
- **Search**: `https://api.myanimelist.net/v2/anime`
- **Update**: `https://api.myanimelist.net/v2/anime/{id}/my_list_status`
- **User List**: `https://api.myanimelist.net/v2/users/@me/animelist`

### Error Handling
- **Network Issues**: Graceful fallback to Jikan API
- **Authentication Errors**: Clear error messages and retry options
- **API Limits**: Respects MAL rate limiting

## 🔧 Troubleshooting

### "Authentication Failed"
- Check your internet connection
- Ensure port 8080 is available
- Try re-authenticating

### "MAL API Search Failed"
- App falls back to Jikan API automatically
- Check authentication status
- Verify your MAL API application is active

### "Sync Failed"
- Ensure you're authenticated
- Check that the anime has a valid MAL ID
- Verify episode number is valid

## 📝 Configuration

### Files Modified
- `ani_cli_gui.py`: Main application with MAL integration
- API credentials are embedded (already configured)

### Dependencies
- All required packages already installed in your virtual environment
- No additional setup needed

## 🎊 Ready to Use!

Your ani-cli GUI now has full MyAnimeList integration. The app will:
- ✅ Search anime using official MAL API
- ✅ Display enhanced anime information  
- ✅ Track your watching progress
- ✅ Update your MAL list automatically
- ✅ Fall back to Jikan if MAL API is unavailable

Enjoy your enhanced anime watching experience with automatic MAL synchronization!
