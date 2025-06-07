import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from io import StringIO

# --- Konfigurasi Halaman & Kunci API ---
st.set_page_config(
    page_title="Dasbor Intelijen Media Interaktif",
    page_icon="🌸",
    layout="wide",
)

# --- Styling Kustom (Coquette/Pastel Theme) ---
st.markdown("""
<style>
    .stApp {
        background-color: #FFF0F5; /* Lavender Blush */
    }
    .st-emotion-cache-16txtl3 {
        padding: 3rem 1rem;
    }
    .st-emotion-cache-1avcm0n {
        background-color: #FFFFFF;
        border: 1px solid #FADADD; /* Pinkish border */
        border-radius: 15px;
    }
    h1 {
        color: #DB7093; /* PaleVioletRed */
        font-weight: bold;
        text-shadow: 2px 2px 4px #FADADD;
    }
    h2, h3 {
        color: #C71585; /* MediumVioletRed */
    }
    .stButton>button {
        background-color: #FFB6C1; /* LightPink */
        color: white;
        border-radius: 10px;
        border: 1px solid #FFC0CB; /* Pink */
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #FF69B4; /* HotPink */
        transform: scale(1.05);
    }
    .stSelectbox, .stDateInput {
        border-radius: 10px;
    }
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }
    .key-insights {
        background-color: #FFF5EE; /* Seashell */
        padding: 1rem;
        border-radius: 10px;
        border: 1px dashed #FADADD;
    }
</style>
""", unsafe_allow_html=True)


# --- Fungsi Bantuan ---

# Fungsi untuk mem-parsing CSV yang diunggah
def parse_csv(uploaded_file):
    """Membaca file CSV yang diunggah dan mengembalikannya sebagai DataFrame."""
    try:
        # Untuk menangani file yang diunggah, kita perlu membacanya sebagai string
        string_data = StringIO(uploaded_file.getvalue().decode("utf-8"))
        df = pd.read_csv(string_data)
        return df
    except Exception as e:
        st.error(f"Error: Gagal mem-parsing file CSV. Pastikan formatnya benar. Detail: {e}")
        return None

# Fungsi untuk membersihkan data
def clean_data(df):
    """Membersihkan DataFrame dengan mengonversi tipe data dan menangani nilai yang hilang."""
    if 'Date' not in df.columns or 'Engagements' not in df.columns:
        st.error("Error: File CSV harus memiliki kolom 'Date' dan 'Engagements'.")
        return None
    
    # Mengonversi 'Date' ke datetime, error akan diubah menjadi NaT (Not a Time)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Menghapus baris dengan tanggal yang tidak valid
    df.dropna(subset=['Date'], inplace=True)
    
    # Mengisi nilai 'Engagements' yang kosong/NaN dengan 0 dan mengonversi ke integer
    df['Engagements'] = pd.to_numeric(df['Engagements'], errors='coerce').fillna(0).astype(int)
    return df

# --- Integrasi Gemini AI ---
def generate_campaign_summary(data, api_key):
    """Menghasilkan ringkasan strategi kampanye menggunakan Gemini AI."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Siapkan data agregat untuk prompt
        dominant_sentiment = data['Sentiment'].mode()[0] if not data['Sentiment'].empty else 'N/A'
        top_platform = data.groupby('Platform')['Engagements'].sum().idxmax() if not data.empty else 'N/A'
        top_platform_engagements = data.groupby('Platform')['Engagements'].sum().max() if not data.empty else 0
        
        # Tren keseluruhan
        trend = 'stabil'
        if not data.empty and data['Date'].nunique() > 1:
            daily_engagements = data.groupby('Date')['Engagements'].sum().sort_index()
            first_day_engagement = daily_engagements.iloc[0]
            last_day_engagement = daily_engagements.iloc[-1]
            if last_day_engagement > first_day_engagement * 1.1:
                trend = 'meningkat'
            elif last_day_engagement < first_day_engagement * 0.9:
                trend = 'menurun'

        start_date = data['Date'].min().strftime('%Y-%m-%d') if not data.empty else 'N/A'
        end_date = data['Date'].max().strftime('%Y-%m-%d') if not data.empty else 'N/A'
        dominant_media_type = data['Media Type'].mode()[0] if not data['Media Type'].empty else 'N/A'
        top_location = data.groupby('Location')['Engagements'].sum().idxmax() if not data.empty else 'N/A'
        top_location_engagements = data.groupby('Location')['Engagements'].sum().max() if not data.empty else 0
        
        prompt = f"""
        Berdasarkan data intelijen media dan wawasan berikut, berikan ringkasan strategi kampanye yang ringkas dalam format poin-poin (tindakan dan rekomendasi utama).
        - Sentimen Dominan: {dominant_sentiment}.
        - Platform Keterlibatan Teratas: {top_platform} dengan {top_platform_engagements:,.0f} keterlibatan.
        - Tren Keterlibatan Keseluruhan: {trend} dari {start_date} hingga {end_date}.
        - Jenis Media yang Paling Sering Digunakan: {dominant_media_type}.
        - Lokasi Teratas untuk Keterlibatan: {top_location} dengan {top_location_engagements:,.0f} keterlibatan.

        Sarankan 3-5 rekomendasi yang dapat ditindaklanjuti untuk mengoptimalkan kampanye media. Fokus pada langkah-langkah praktis berdasarkan poin data ini. Gunakan format markdown.
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Gagal menghasilkan ringkasan. Error: {e}"


# --- UI Aplikasi Streamlit ---

st.title("Dasbor Intelijen Media Interaktif")

# Gunakan session state untuk menyimpan status unggah file
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'df' not in st.session_state:
    st.session_state.df = None

# Area unggah file
uploaded_file = st.file_uploader(
    "Unggah file CSV Anda",
    type="csv",
    help="Pastikan file CSV memiliki kolom: 'Date', 'Engagements', 'Sentiment', 'Platform', 'Media Type', 'Location'"
)

if uploaded_file is not None:
    df_original = parse_csv(uploaded_file)
    if df_original is not None:
        df_cleaned = clean_data(df_original.copy())
        if df_cleaned is not None:
            st.session_state.df = df_cleaned
            st.session_state.file_uploaded = True

if not st.session_state.file_uploaded:
    st.info("Silakan unggah file CSV untuk memulai analisis.")
    st.stop() # Hentikan eksekusi jika tidak ada file

# --- Sidebar untuk Filter ---
st.sidebar.header("Filter Data")

df_filtered = st.session_state.df

# Filter berdasarkan Platform
if 'Platform' in df_filtered.columns:
    platforms = ['All'] + sorted(df_filtered['Platform'].unique().tolist())
    platform_filter = st.sidebar.selectbox("Platform", platforms)
    if platform_filter != 'All':
        df_filtered = df_filtered[df_filtered['Platform'] == platform_filter]

# Filter berdasarkan Sentimen
if 'Sentiment' in df_filtered.columns:
    sentiments = ['All'] + sorted(df_filtered['Sentiment'].unique().tolist())
    sentiment_filter = st.sidebar.selectbox("Sentiment", sentiments)
    if sentiment_filter != 'All':
        df_filtered = df_filtered[df_filtered['Sentiment'] == sentiment_filter]

# Filter berdasarkan Media Type
if 'Media Type' in df_filtered.columns:
    media_types = ['All'] + sorted(df_filtered['Media Type'].unique().tolist())
    media_type_filter = st.sidebar.selectbox("Media Type", media_types)
    if media_type_filter != 'All':
        df_filtered = df_filtered[df_filtered['Media Type'] == media_type_filter]

# Filter berdasarkan Lokasi
if 'Location' in df_filtered.columns:
    locations = ['All'] + sorted(df_filtered['Location'].unique().tolist())
    location_filter = st.sidebar.selectbox("Location", locations)
    if location_filter != 'All':
        df_filtered = df_filtered[df_filtered['Location'] == location_filter]

# Filter berdasarkan Rentang Tanggal
min_date = df_filtered['Date'].min().date()
max_date = df_filtered['Date'].max().date()
start_date = st.sidebar.date_input("Tanggal Mulai", min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("Tanggal Akhir", max_date, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.sidebar.error("Error: Tanggal akhir harus setelah tanggal mulai.")
else:
    # Mengonversi ke datetime untuk perbandingan
    df_filtered = df_filtered[
        (df_filtered['Date'].dt.date >= start_date) &
        (df_filtered['Date'].dt.date <= end_date)
    ]

# --- Konten Utama Dasbor ---

if df_filtered.empty:
    st.warning("Tidak ada data yang cocok dengan filter yang dipilih. Coba sesuaikan filter Anda.")
else:
    # --- Ringkasan Strategi Kampanye (AI) ---
    st.subheader("✨ Ringkasan Strategi Kampanye (didukung oleh AI)")
    
    # Kunci API telah ditambahkan langsung ke dalam kode.
    # Menghapus input manual untuk API Key.
    api_key = "AIzaSyD5qY5biPQ1ccEq-qVKhWJ7rvdNZlUTN9Y"
    
    if st.button("Buat Ringkasan Strategi"):
        with st.spinner("AI sedang menganalisis data dan menyusun strategi..."):
            summary = generate_campaign_summary(df_filtered, api_key)
            st.markdown(summary)
    
    st.markdown("---")

    # --- Layout Kolom untuk Visualisasi ---
    col1, col2 = st.columns(2)

    with col1:
        # 1. Analisis Sentimen
        st.subheader("😊 Analisis Sentimen")
        sentiment_data = df_filtered['Sentiment'].value_counts().reset_index()
        sentiment_data.columns = ['Sentiment', 'Jumlah']
        fig_sentiment = px.pie(
            sentiment_data,
            names='Sentiment',
            values='Jumlah',
            color_discrete_sequence=px.colors.sequential.Pastel1,
            hole=0.3
        )
        fig_sentiment.update_layout(legend_title_text='Sentimen')
        st.plotly_chart(fig_sentiment, use_container_width=True)
        with st.container(border=True):
            st.markdown("<div class='key-insights'><b>Wawasan Utama:</b> Sentimen dominan memberikan gambaran umum tentang persepsi publik terhadap kampanye.</div>", unsafe_allow_html=True)


    with col2:
        # 2. Kombinasi Jenis Media
        st.subheader("📰 Kombinasi Jenis Media")
        media_type_data = df_filtered['Media Type'].value_counts().reset_index()
        media_type_data.columns = ['Media Type', 'Jumlah']
        fig_media_type = px.pie(
            media_type_data,
            names='Media Type',
            values='Jumlah',
            color_discrete_sequence=px.colors.sequential.Pastel2,
            hole=0.3
        )
        fig_media_type.update_layout(legend_title_text='Jenis Media')
        st.plotly_chart(fig_media_type, use_container_width=True)
        with st.container(border=True):
             st.markdown("<div class='key-insights'><b>Wawasan Utama:</b> Menganalisis jenis media yang paling banyak digunakan dapat menginformasikan strategi konten di masa depan.</div>", unsafe_allow_html=True)


    st.markdown("---")
    
    # 3. Tren Keterlibatan Seiring Waktu
    st.subheader("📈 Tren Keterlibatan Seiring Waktu")
    engagement_trend = df_filtered.groupby(df_filtered['Date'].dt.date)['Engagements'].sum().reset_index()
    fig_trend = px.line(
        engagement_trend,
        x='Date',
        y='Engagements',
        title='Total Keterlibatan per Hari',
        markers=True
    )
    fig_trend.update_traces(line_color='#FF6B6B')
    st.plotly_chart(fig_trend, use_container_width=True)
    with st.container(border=True):
        st.markdown("<div class='key-insights'><b>Wawasan Utama:</b> Puncak keterlibatan sering kali berkorelasi dengan peristiwa atau postingan kampanye tertentu. Analisis tren membantu mengidentifikasi apa yang berhasil.</div>", unsafe_allow_html=True)


    st.markdown("---")
    
    col3, col4 = st.columns(2)

    with col3:
        # 4. Keterlibatan per Platform
        st.subheader("📊 Keterlibatan per Platform")
        platform_engagement = df_filtered.groupby('Platform')['Engagements'].sum().sort_values(ascending=False).reset_index()
        fig_platform = px.bar(
            platform_engagement,
            x='Platform',
            y='Engagements',
            color='Platform',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_platform, use_container_width=True)
        with st.container(border=True):
            st.markdown("<div class='key-insights'><b>Wawasan Utama:</b> Mengidentifikasi platform dengan kinerja terbaik sangat penting untuk alokasi sumber daya dan fokus strategis.</div>", unsafe_allow_html=True)


    with col4:
        # 5. 5 Lokasi Teratas berdasarkan Keterlibatan
        st.subheader("📍 5 Lokasi Teratas")
        location_engagement = df_filtered.groupby('Location')['Engagements'].sum().nlargest(5).sort_values(ascending=True).reset_index()
        fig_location = px.bar(
            location_engagement,
            y='Location',
            x='Engagements',
            orientation='h',
            color='Location',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_location, use_container_width=True)
        with st.container(border=True):
            st.markdown("<div class='key-insights'><b>Wawasan Utama:</b> Menargetkan lokasi dengan keterlibatan tinggi dapat memaksimalkan jangkauan dan dampak kampanye.</div>", unsafe_allow_html=True)
