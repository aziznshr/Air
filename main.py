import streamlit as st
import pandas as pd
import altair as alt

# --- KONFIGURASI DAN STANDAR DASAR ---
# Berdasarkan data dari laporan dan berbagai standar (SNI, dll.)
STANDARDS = {
    "pengunjung_sanitasi": 10,  # L/pengunjung/hari (untuk toilet, cuci tangan, dll.)
    "staf_umum": 50,            # L/staf/hari
    "staf_dapur": 100,          # L/staf/hari
    "restoran_konsumsi": 15,    # L/pengunjung makan/hari
    "restoran_dapur": 3,        # L/pengunjung makan/hari
    "akomodasi_glamping": 150,  # L/tempat tidur/hari
    "hewan_domba": 5,           # L/ekor/hari
    "hewan_unggas": 0.6,        # L/ekor/hari
    "lanskap_irigasi": 1.5,     # L/m2/hari (estimasi)
    "kolam_renang_topup": 0.05, # Persentase top-up harian dari total volume (estimasi gabungan penguapan, cipratan, backwash)
    "club_beverage_service": 5, # L/pengunjung club/malam (cuci gelas, es, dll. - estimasi)
    "club_sanitasi": 10         # L/pengunjung club/malam (sama dengan sanitasi umum)
}

BIAYA_AIR_PER_M3 = {
    "Rendah (Perkotaan, PDAM Lancar)": 7500,
    "Menengah (Perbukitan, Akses Terbatas)": 15000,
    "Tinggi (Rawan Kekeringan, Andalkan Tangki)": 45000
}

# --- FUNGSI-FUNGSI PERHITUNGAN MODULAR ---

def calculate_base_needs(jml_pengunjung, jml_staf):
    """Menghitung kebutuhan dasar dari pengunjung dan staf."""
    kebutuhan_pengunjung = jml_pengunjung * STANDARDS["pengunjung_sanitasi"]
    kebutuhan_staf = jml_staf * STANDARDS["staf_umum"]
    
    detail = {
        "Sanitasi Pengunjung Umum": kebutuhan_pengunjung,
        "Kebutuhan Staf Operasional": kebutuhan_staf
    }
    return sum(detail.values()), detail

def calculate_restaurant_needs(jml_pengunjung, persentase_makan, jml_staf_dapur):
    """Menghitung kebutuhan air untuk fasilitas restoran."""
    pengunjung_makan = jml_pengunjung * (persentase_makan / 100)
    
    konsumsi_tamu = pengunjung_makan * STANDARDS["restoran_konsumsi"]
    operasional_dapur = pengunjung_makan * STANDARDS["restoran_dapur"]
    kebutuhan_staf_dapur = jml_staf_dapur * STANDARDS["staf_dapur"]
    
    detail = {
        "Konsumsi Pengunjung di Restoran": konsumsi_tamu,
        "Operasional Dapur (Memasak & Cuci)": operasional_dapur,
        "Kebutuhan Staf Dapur": kebutuhan_staf_dapur
    }
    return sum(detail.values()), detail

def calculate_club_needs(kapasitas, tingkat_kunjungan):
    """Menghitung kebutuhan air untuk fasilitas club/bar/lounge."""
    pengunjung_club = kapasitas * (tingkat_kunjungan / 100)
    kebutuhan_minuman = pengunjung_club * STANDARDS["club_beverage_service"]
    kebutuhan_sanitasi = pengunjung_club * STANDARDS["club_sanitasi"]
    detail = {
        "Layanan Minuman Club/Bar": kebutuhan_minuman,
        "Sanitasi Pengunjung Club/Bar": kebutuhan_sanitasi
    }
    return sum(detail.values()), detail

def calculate_accommodation_needs(jml_tempat_tidur):
    """Menghitung kebutuhan air untuk fasilitas akomodasi."""
    kebutuhan = jml_tempat_tidur * STANDARDS["akomodasi_glamping"]
    detail = {"Akomodasi (Glamping/Hotel)": kebutuhan}
    return kebutuhan, detail

def calculate_zoo_needs(jml_domba, jml_unggas, kebutuhan_pembersihan):
    """Menghitung kebutuhan air untuk fasilitas mini zoo."""
    kebutuhan_domba = jml_domba * STANDARDS["hewan_domba"]
    kebutuhan_unggas = jml_unggas * STANDARDS["hewan_unggas"]
    
    detail = {
        "Minum Ternak (Domba)": kebutuhan_domba,
        "Minum Ternak (Unggas)": kebutuhan_unggas,
        "Pembersihan Kandang & Area": kebutuhan_pembersihan
    }
    return sum(detail.values()), detail

def calculate_pool_needs(luas_permukaan, kedalaman):
    """Menghitung kebutuhan top-up harian untuk kolam renang."""
    volume_m3 = luas_permukaan * kedalaman
    kebutuhan_harian_liter = (volume_m3 * 1000) * STANDARDS["kolam_renang_topup"]
    detail = {"Top-up Kolam Renang (Penguapan, dll.)": kebutuhan_harian_liter}
    return kebutuhan_harian_liter, detail

def calculate_landscape_needs(luas_lanskap):
    """Menghitung kebutuhan air untuk irigasi lanskap."""
    kebutuhan = luas_lanskap * STANDARDS["lanskap_irigasi"]
    detail = {"Irigasi Lanskap/Taman": kebutuhan}
    return kebutuhan, detail

# --- ANTARMUKA STREAMLIT ---

st.set_page_config(layout="wide", page_title="Kalkulator Kebutuhan Air Destinasi Wisata")

# --- JUDUL DAN PENDAHULUAN ---
st.title("💧 Kalkulator Kebutuhan Air Destinasi Wisata")
st.markdown("""
Aplikasi ini dirancang untuk memberikan estimasi kebutuhan air yang lebih akurat untuk **destinasi wisata modern**, 
seperti Obelix Hills, Village, atau Sea View. Model perhitungannya beralih dari asumsi 'jumlah kamar' ke **'jumlah pengunjung'** dan **fasilitas spesifik** yang ada di lokasi.
""")
st.markdown("---")

# --- SIDEBAR UNTUK INPUT ---
with st.sidebar:
    st.header("1. Parameter Dasar")
    with st.container(border=True):
        scenario = st.radio(
            "Pilih Skenario Operasional",
            ("Hari Biasa (Weekday)", "Hari Puncak (Weekend/Libur)"),
            help="Skenario 'Hari Puncak' akan mengalikan jumlah pengunjung dengan faktor pengali di bawah."
        )
        pengunjung_harian = st.number_input(
            "Estimasi Pengunjung/Hari (saat hari biasa)", 
            min_value=0, value=750, step=50,
            help="Masukkan jumlah rata-rata pengunjung pada 'Hari Biasa'."
        )
        faktor_puncak = st.slider(
            "Faktor Pengali Hari Puncak", 1.0, 5.0, 2.0, 0.1,
            help="Pengali untuk jumlah pengunjung saat skenario 'Hari Puncak' dipilih. Contoh: 2.0 berarti 2x lipat dari hari biasa."
        )
        staf_operasional = st.number_input(
            "Jumlah Staf Operasional (Non-Dapur)", 
            min_value=0, value=60, step=5,
            help="Jumlah staf di luar dapur (tiket, kebersihan, keamanan, dll.)."
        )

    if scenario == "Hari Puncak (Weekend/Libur)":
        pengunjung_efektif = int(pengunjung_harian * faktor_puncak)
        st.info(f"Jumlah pengunjung efektif untuk skenario puncak: **{pengunjung_efektif} orang**")
    else:
        pengunjung_efektif = pengunjung_harian

    st.header("2. Fasilitas yang Tersedia")
    with st.container(border=True):
        has_restaurant = st.checkbox("🍽️ Restoran / Food Court", value=True)
        has_club = st.checkbox("🎉 Club / Bar / Lounge")
        has_accommodation = st.checkbox("🏨 Akomodasi (Hotel/Glamping)")
        has_pool = st.checkbox("🏊 Kolam Renang")
        has_zoo = st.checkbox("🐑 Mini Zoo / Peternakan")
        has_landscape = st.checkbox("🌳 Lanskap / Taman (Irigasi)")

    st.header("3. Faktor Penyesuaian & Biaya")
    with st.container(border=True):
        faktor_kehilangan_air = st.slider(
            "Faktor Kehilangan Air (%)", 0, 30, 20, 
            help="Persentase tambahan untuk mengantisipasi kehilangan air akibat kebocoran pipa, penguapan tak terduga, dll. Standar umum 10-20%."
        )
        risiko_air_lokasi = st.selectbox(
            "Risiko & Biaya Air Lokasi",
            options=list(BIAYA_AIR_PER_M3.keys()),
            index=1,
            help="Pilih kondisi sumber daya air di lokasi Anda. Ini akan memengaruhi estimasi biaya."
        )
        biaya_per_m3 = BIAYA_AIR_PER_M3[risiko_air_lokasi]

# --- CONTAINER UNTUK DETAIL INPUT FASILITAS ---
st.sidebar.header("4. Detail Input Fasilitas")
detail_inputs = {}

with st.sidebar.expander("🍽️ Detail Restoran / Food Court", expanded=has_restaurant):
    if has_restaurant:
        detail_inputs['restoran_persentase_makan'] = st.slider(
            "% Pengunjung yang Makan", 0, 100, 80,
            help="Estimasi persentase pengunjung harian yang menggunakan fasilitas F&B."
        )
        detail_inputs['restoran_staf_dapur'] = st.number_input(
            "Jumlah Staf Dapur", min_value=0, value=40, step=2,
            help="Jumlah staf yang bekerja di area dapur dan F&B."
        )

with st.sidebar.expander("🎉 Detail Club / Bar / Lounge", expanded=has_club):
    if has_club:
        detail_inputs['club_kapasitas'] = st.number_input(
            "Kapasitas Maksimum Club (orang)", min_value=0, value=150, step=10
        )
        detail_inputs['club_kunjungan_malam'] = st.slider(
            "Tingkat Kunjungan Malam (%)", 0, 100, 75
        )

with st.sidebar.expander("🏨 Detail Akomodasi", expanded=has_accommodation):
    if has_accommodation:
        detail_inputs['akomodasi_tempat_tidur'] = st.number_input(
            "Jumlah Total Tempat Tidur", min_value=0, value=10, step=2
        )

with st.sidebar.expander("🏊 Detail Kolam Renang", expanded=has_pool):
    if has_pool:
        detail_inputs['kolam_luas'] = st.number_input("Luas Permukaan Kolam (m²)", min_value=0.0, value=200.0, step=10.0)
        detail_inputs['kolam_kedalaman'] = st.number_input("Rata-rata Kedalaman (m)", min_value=0.0, value=1.5, step=0.1)

with st.sidebar.expander("🐑 Detail Mini Zoo", expanded=has_zoo):
    if has_zoo:
        detail_inputs['zoo_domba'] = st.number_input("Jumlah Domba/Kambing", min_value=0, value=20)
        detail_inputs['zoo_unggas'] = st.number_input("Jumlah Unggas", min_value=0, value=50)
        detail_inputs['zoo_pembersihan'] = st.number_input(
            "Kebutuhan Pembersihan Harian (Liter)", min_value=0, value=5000, step=100
        )

with st.sidebar.expander("🌳 Detail Lanskap / Taman", expanded=has_landscape):
    if has_landscape:
        detail_inputs['lanskap_luas'] = st.number_input("Luas Area Irigasi (m²)", min_value=0, value=2000, step=100)

# --- PERHITUNGAN UTAMA ---
total_kebutuhan_sub = 0
rincian_kebutuhan = {}

# Kebutuhan Dasar
kebutuhan, detail = calculate_base_needs(pengunjung_efektif, staf_operasional)
total_kebutuhan_sub += kebutuhan
rincian_kebutuhan.update(detail)

# Kebutuhan Modular
if has_restaurant:
    kebutuhan, detail = calculate_restaurant_needs(
        pengunjung_efektif, 
        detail_inputs.get('restoran_persentase_makan', 80),
        detail_inputs.get('restoran_staf_dapur', 40)
    )
    total_kebutuhan_sub += kebutuhan
    rincian_kebutuhan.update(detail)

if has_club:
    kebutuhan, detail = calculate_club_needs(
        detail_inputs.get('club_kapasitas', 150),
        detail_inputs.get('club_kunjungan_malam', 75)
    )
    total_kebutuhan_sub += kebutuhan
    rincian_kebutuhan.update(detail)

if has_accommodation:
    kebutuhan, detail = calculate_accommodation_needs(detail_inputs.get('akomodasi_tempat_tidur', 10))
    total_kebutuhan_sub += kebutuhan
    rincian_kebutuhan.update(detail)

if has_pool:
    kebutuhan, detail = calculate_pool_needs(detail_inputs.get('kolam_luas', 200.0), detail_inputs.get('kolam_kedalaman', 1.5))
    total_kebutuhan_sub += kebutuhan
    rincian_kebutuhan.update(detail)

if has_zoo:
    kebutuhan, detail = calculate_zoo_needs(
        detail_inputs.get('zoo_domba', 20), 
        detail_inputs.get('zoo_unggas', 50),
        detail_inputs.get('zoo_pembersihan', 5000)
    )
    total_kebutuhan_sub += kebutuhan
    rincian_kebutuhan.update(detail)

if has_landscape:
    kebutuhan, detail = calculate_landscape_needs(detail_inputs.get('lanskap_luas', 2000))
    total_kebutuhan_sub += kebutuhan
    rincian_kebutuhan.update(detail)

# Finalisasi dengan faktor kehilangan air
kehilangan_air = total_kebutuhan_sub * (faktor_kehilangan_air / 100)
total_kebutuhan_final = total_kebutuhan_sub + kehilangan_air
if kehilangan_air > 0:
    rincian_kebutuhan["Cadangan Kehilangan Air"] = kehilangan_air

# --- TAMPILAN HASIL DI HALAMAN UTAMA ---
st.header(f"📊 Dashboard Estimasi: Skenario {scenario}")

# --- Container Hasil Utama ---
with st.container(border=True):
    col1, col2 = st.columns([1,1])
    with col1:
        st.subheader("Total Kebutuhan Air")
        subcol1, subcol2 = st.columns(2)
        subcol1.metric(label="Liter / Hari", value=f"{total_kebutuhan_final:,.0f}")
        subcol2.metric(label="Meter Kubik / Hari", value=f"{total_kebutuhan_final / 1000:,.2f}")
        subcol1.metric(label="Liter / Bulan", value=f"{total_kebutuhan_final * 30:,.0f}")
        subcol2.metric(label="Meter Kubik / Bulan", value=f"{(total_kebutuhan_final * 30) / 1000:,.2f}")

    with col2:
        st.subheader("Estimasi Biaya Air")
        biaya_harian = (total_kebutuhan_final / 1000) * biaya_per_m3
        biaya_bulanan = biaya_harian * 30
        
        subcol1, subcol2 = st.columns(2)
        subcol1.metric("Biaya Harian", f"Rp {biaya_harian:,.0f}")
        subcol2.metric("Biaya Bulanan", f"Rp {biaya_bulanan:,.0f}")
        st.info(f"Biaya per m³ (1.000 L) untuk lokasi '{risiko_air_lokasi}': **Rp {biaya_per_m3:,.0f}**")

st.markdown("---")

# --- RINCIAN PERHITUNGAN ---
st.header("🔬 Rincian Komponen Kebutuhan Air")
with st.container(border=True):
    if not rincian_kebutuhan:
        st.warning("Tidak ada fasilitas yang dipilih. Aktifkan modul di sidebar untuk melihat rincian.")
    else:
        df_rincian = pd.DataFrame(list(rincian_kebutuhan.items()), columns=['Komponen', 'Kebutuhan (Liter/Hari)'])
        df_rincian = df_rincian.sort_values(by='Kebutuhan (Liter/Hari)', ascending=False)

        # Membuat chart
        chart = alt.Chart(df_rincian).mark_bar().encode(
            x=alt.X('Kebutuhan (Liter/Hari):Q', title='Kebutuhan Air (Liter/Hari)'),
            y=alt.Y('Komponen:N', sort='-x', title='Komponen Fasilitas'),
            tooltip=['Komponen', 'Kebutuhan (Liter/Hari)']
        ).properties(
            title='Distribusi Kebutuhan Air per Komponen'
        )
        st.altair_chart(chart, use_container_width=True)

        with st.expander("Lihat Data Tabel Rincian"):
            df_rincian['Persentase'] = (df_rincian['Kebutuhan (Liter/Hari)'] / total_kebutuhan_final) * 100
            
            # Format tampilan
            df_rincian['Kebutuhan (Liter/Hari)'] = df_rincian['Kebutuhan (Liter/Hari)'].map('{:,.0f} L'.format)
            df_rincian['Persentase'] = df_rincian['Persentase'].map('{:.1f}%'.format)
            
            st.dataframe(df_rincian, use_container_width=True, hide_index=True)
            
            st.markdown(f"""
            - **Subtotal Kebutuhan:** `{total_kebutuhan_sub:,.0f}` Liter
            - **Cadangan Kehilangan Air ({faktor_kehilangan_air}%):** `{kehilangan_air:,.0f}` Liter
            - **Total Kebutuhan Final:** `{total_kebutuhan_final:,.0f}` Liter
            """)

st.markdown("---")
st.caption("Dibuat dengan Streamlit | Didasarkan pada analisis data dan standar teknis.")
st.caption("Setiap titik konsumsi ditetapkan berdasarkan standar teknis yang relevan, terutama yang bersumber dari Standar Nasional Indonesia (SNI) seperti SNI 03-7065-2005 dan SNI 03-6481-2000, serta data dari berbagai publikasi teknis dan studi kasus sejenis")
