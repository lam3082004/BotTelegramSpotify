import os
import logging
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Tải biến môi trường từ file .env
load_dotenv()

# Constants và states cho conversation handler
CHOOSING, GENRE, MOOD, ARTIST = range(4)

# Khởi tạo kết nối Spotify API
spotify = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
    )
)

# Hàm bắt đầu bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào mừng đến với Bot Âm Nhạc! 🎵\n\n"
        "Sử dụng các lệnh sau:\n"
        "/music - Đề xuất nhạc theo thể loại, tâm trạng hoặc nghệ sĩ\n"
        "/search - Tìm kiếm thông tin bài hát hoặc nghệ sĩ\n"
        "/help - Hiển thị trợ giúp"
    )

# Hàm hiển thị trợ giúp
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📍 *Hướng dẫn sử dụng Bot Âm Nhạc* 📍\n\n"
        "*Các lệnh có sẵn:*\n"
        "/start - Khởi động bot\n"
        "/music - Đề xuất nhạc theo thể loại, tâm trạng hoặc nghệ sĩ\n"
        "/search - Tìm kiếm thông tin bài hát hoặc nghệ sĩ\n"
        "/cancel - Hủy thao tác hiện tại\n\n"
        "*Tính năng:*\n"
        "- Đề xuất âm nhạc theo thể loại\n"
        "- Đề xuất âm nhạc theo tâm trạng\n"
        "- Đề xuất âm nhạc theo nghệ sĩ yêu thích\n"
        "- Tìm kiếm thông tin chi tiết về bài hát hoặc nghệ sĩ",
        parse_mode='Markdown'
    )

# Hàm bắt đầu quá trình đề xuất nhạc
async def music_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Thể loại", callback_data='genre'),
            InlineKeyboardButton("Tâm trạng", callback_data='mood')
        ],
        [InlineKeyboardButton("Nghệ sĩ", callback_data='artist')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Bạn muốn đề xuất nhạc theo?",
        reply_markup=reply_markup
    )
    return CHOOSING

# Xử lý các lựa chọn từ người dùng
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    if choice == 'genre':
        await query.message.edit_text("Nhập thể loại nhạc bạn muốn (ví dụ: rock, pop, jazz, hip hop):")
        return GENRE
    elif choice == 'mood':
        keyboard = [
            [
                InlineKeyboardButton("Vui vẻ", callback_data='happy'),
                InlineKeyboardButton("Buồn", callback_data='sad')
            ],
            [
                InlineKeyboardButton("Thư giãn", callback_data='chill'),
                InlineKeyboardButton("Năng động", callback_data='energetic')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Chọn tâm trạng của bạn:", reply_markup=reply_markup)
        return MOOD
    elif choice == 'artist':
        await query.message.edit_text("Nhập tên nghệ sĩ bạn yêu thích:")
        return ARTIST
    elif choice in ['happy', 'sad', 'chill', 'energetic']:
        await get_mood_recommendations(query.message, choice)
        return ConversationHandler.END

# Hủy cuộc trò chuyện
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Đã hủy thao tác.")
    return ConversationHandler.END

# Xử lý đề xuất theo thể loại
async def get_genre_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    genre = update.message.text.strip().lower()
    try:
        # Tìm kiếm các playlist liên quan đến thể loại
        results = spotify.search(q=f'genre:{genre}', type='playlist', limit=5)
        
        if not results['playlists']['items']:
            await update.message.reply_text(f"Không tìm thấy playlist nào cho thể loại '{genre}'. Vui lòng thử lại với thể loại khác.")
            return ConversationHandler.END
            
        await update.message.reply_text(f"Đề xuất cho thể loại '{genre}':")
        
        for playlist in results['playlists']['items']:
            # Lấy một số bài hát từ playlist
            tracks = spotify.playlist_tracks(playlist['id'], limit=3)
            
            playlist_text = f"📀 *{playlist['name']}*\n"
            playlist_text += f"👤 Tạo bởi: {playlist['owner']['display_name']}\n"
            playlist_text += f"🔗 Link: {playlist['external_urls']['spotify']}\n\n"
            
            playlist_text += "*Một số bài hát:*\n"
            for i, item in enumerate(tracks['items'], 1):
                track = item['track']
                artists = ", ".join([artist['name'] for artist in track['artists']])
                playlist_text += f"{i}. {track['name']} - {artists}\n"
            
            await update.message.reply_text(playlist_text, parse_mode='Markdown')
            
        return ConversationHandler.END
    
    except Exception as e:
        logging.error(f"Lỗi khi lấy đề xuất thể loại: {e}")
        await update.message.reply_text("Có lỗi xảy ra khi lấy đề xuất. Vui lòng thử lại sau.")
        return ConversationHandler.END

# Xử lý đề xuất theo tâm trạng
async def get_mood_recommendations(message, mood):
    mood_mapping = {
        'happy': 'happy',
        'sad': 'sad',
        'chill': 'chill',
        'energetic': 'energetic'
    }
    
    mood_term = mood_mapping.get(mood, mood)
    
    try:
        # Tìm kiếm playlist phù hợp với tâm trạng
        results = spotify.search(q=mood_term, type='playlist', limit=3)
        
        if not results['playlists']['items']:
            await message.reply_text(f"Không tìm thấy playlist nào cho tâm trạng '{mood_term}'. Vui lòng thử lại.")
            return
            
        await message.reply_text(f"Đề xuất cho tâm trạng '{mood_term}':")
        
        for playlist in results['playlists']['items']:
            # Lấy một số bài hát từ playlist
            tracks = spotify.playlist_tracks(playlist['id'], limit=5)
            
            playlist_text = f"🎵 *{playlist['name']}*\n"
            playlist_text += f"📊 Số lượng: {playlist['tracks']['total']} bài hát\n"
            playlist_text += f"🔗 Link: {playlist['external_urls']['spotify']}\n\n"
            
            playlist_text += "*Một số bài hát nổi bật:*\n"
            for i, item in enumerate(tracks['items'], 1):
                if i > 3:  # Chỉ hiển thị 3 bài
                    break
                track = item['track']
                if track is None:  # Kiểm tra track có tồn tại không
                    continue
                artists = ", ".join([artist['name'] for artist in track['artists']])
                playlist_text += f"{i}. {track['name']} - {artists}\n"
            
            await message.reply_text(playlist_text, parse_mode='Markdown')
            
    except Exception as e:
        logging.error(f"Lỗi khi lấy đề xuất tâm trạng: {e}")
        await message.reply_text("Có lỗi xảy ra khi lấy đề xuất. Vui lòng thử lại sau.")

# Xử lý đề xuất theo nghệ sĩ
async def get_artist_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    artist_name = update.message.text.strip()
    try:
        # Tìm kiếm nghệ sĩ
        results = spotify.search(q=f'artist:{artist_name}', type='artist', limit=1)
        
        if not results['artists']['items']:
            await update.message.reply_text(f"Không tìm thấy nghệ sĩ '{artist_name}'. Vui lòng thử lại.")
            return ConversationHandler.END
            
        artist = results['artists']['items'][0]
        artist_id = artist['id']
        
        # Lấy thông tin nghệ sĩ
        artist_info = f"🎤 *{artist['name']}*\n"
        if artist['genres']:
            artist_info += f"🎵 Thể loại: {', '.join(artist['genres'][:3])}\n"
        artist_info += f"👥 Người theo dõi: {artist['followers']['total']:,}\n"
        artist_info += f"🔗 Link: {artist['external_urls']['spotify']}\n\n"
        
        await update.message.reply_text(artist_info, parse_mode='Markdown')
        
        # Lấy các bài hát nổi bật của nghệ sĩ
        top_tracks = spotify.artist_top_tracks(artist_id)
        
        if top_tracks['tracks']:
            tracks_text = "*Các bài hát nổi bật:*\n"
            for i, track in enumerate(top_tracks['tracks'][:5], 1):
                tracks_text += f"{i}. {track['name']} - {track['album']['name']}\n"
            
            await update.message.reply_text(tracks_text, parse_mode='Markdown')
        
        # Lấy các nghệ sĩ liên quan
        related = spotify.artist_related_artists(artist_id)
        
        if related['artists']:
            related_text = "*Nghệ sĩ tương tự:*\n"
            for i, rel_artist in enumerate(related['artists'][:5], 1):
                related_text += f"{i}. {rel_artist['name']}\n"
            
            await update.message.reply_text(related_text, parse_mode='Markdown')
            
        return ConversationHandler.END
        
    except Exception as e:
        logging.error(f"Lỗi khi lấy thông tin nghệ sĩ: {e}")
        await update.message.reply_text("Có lỗi xảy ra khi lấy thông tin. Vui lòng thử lại sau.")
        return ConversationHandler.END

# Hàm tìm kiếm thông tin
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập từ khóa tìm kiếm. Ví dụ:\n"
            "/search Sơn Tùng MTP\n"
            "/search Shape of You"
        )
        return
    
    query = ' '.join(context.args)
    try:
        # Tìm kiếm bài hát
        track_results = spotify.search(q=query, type='track', limit=3)
        
        if track_results['tracks']['items']:
            await update.message.reply_text("🎵 *Các bài hát liên quan:*", parse_mode='Markdown')
            
            for track in track_results['tracks']['items']:
                artists = ", ".join([artist['name'] for artist in track['artists']])
                album = track['album']['name']
                duration = track['duration_ms'] // 1000
                minutes = duration // 60
                seconds = duration % 60
                
                track_info = f"🎧 *{track['name']}*\n"
                track_info += f"👤 Nghệ sĩ: {artists}\n"
                track_info += f"💿 Album: {album}\n"
                track_info += f"⏱️ Thời lượng: {minutes}:{seconds:02d}\n"
                track_info += f"🔗 Link: {track['external_urls']['spotify']}\n"
                
                await update.message.reply_text(track_info, parse_mode='Markdown')
        
        # Tìm kiếm nghệ sĩ
        artist_results = spotify.search(q=query, type='artist', limit=2)
        
        if artist_results['artists']['items']:
            await update.message.reply_text("👤 *Các nghệ sĩ liên quan:*", parse_mode='Markdown')
            
            for artist in artist_results['artists']['items']:
                genres = ", ".join(artist['genres'][:3]) if artist['genres'] else "Không có thông tin"
                followers = artist['followers']['total']
                
                artist_info = f"🎤 *{artist['name']}*\n"
                artist_info += f"🎵 Thể loại: {genres}\n"
                artist_info += f"👥 Người theo dõi: {followers:,}\n"
                artist_info += f"🔗 Link: {artist['external_urls']['spotify']}\n"
                
                await update.message.reply_text(artist_info, parse_mode='Markdown')
        
        if not track_results['tracks']['items'] and not artist_results['artists']['items']:
            await update.message.reply_text(f"Không tìm thấy kết quả nào cho '{query}'. Vui lòng thử với từ khóa khác.")
            
    except Exception as e:
        logging.error(f"Lỗi khi tìm kiếm: {e}")
        await update.message.reply_text("Có lỗi xảy ra khi tìm kiếm. Vui lòng thử lại sau.")

def main():
    # Tạo và cấu hình ứng dụng
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    # Tạo conversation handler cho đề xuất nhạc
    music_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('music', music_command)],
        states={
            CHOOSING: [CallbackQueryHandler(button_handler)],
            GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_genre_recommendations)],
            MOOD: [CallbackQueryHandler(button_handler)],
            ARTIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_artist_recommendations)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Thêm các handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('search', search_command))
    application.add_handler(music_conv_handler)
    
    # Khởi động bot
    application.run_polling()

if __name__ == '__main__':
    main()