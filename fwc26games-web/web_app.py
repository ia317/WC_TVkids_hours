import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import streamlit as st
import streamlit.components.v1 as components
import pytz
from datetime import timedelta
from shared.utils import (
    convert_to_tz, get_future_games, get_national_teams,
    get_games_for_team, get_games_in_time_range,
)
from shared.fetch import fetch_schedule

GA4_ID = "G-GH3E1R44Y8"


def _ga4_html(event_name=None, params=None):
    event_js = ""
    if event_name:
        params_js = json.dumps(params or {})
        event_js = f"""
        if (typeof window.parent.gtag === 'function') {{
            window.parent.gtag('event', '{event_name}', {params_js});
        }}
        """
    # Inject gtag.js into the real parent page (not the iframe),
    # so GA4 sees the actual app URL and runs in the top-level context.
    return f"""<script>
(function() {{
    var p = window.parent;
    if (!p._ga4_ready) {{
        p._ga4_ready = true;
        p.dataLayer = p.dataLayer || [];
        p.gtag = function() {{ p.dataLayer.push(arguments); }};
        p.gtag('js', new Date());
        p.gtag('config', '{GA4_ID}');
        var s = p.document.createElement('script');
        s.async = true;
        s.src = 'https://www.googletagmanager.com/gtag/js?id={GA4_ID}';
        p.document.head.appendChild(s);
    }}
    {event_js}
}})();
</script>"""


def inject_ga4():
    components.html(_ga4_html(), height=0)


def track_event(event_name, params=None):
    components.html(_ga4_html(event_name, params), height=0)

# ── Timezones ────────────────────────────────────────────────────────────────
TIMEZONES = {
    # Americas — West to East
    "Hawaii (HST)":                 pytz.timezone("Pacific/Honolulu"),
    "Alaska (AKST)":                pytz.timezone("America/Anchorage"),
    "Los Angeles / Vancouver (PT)": pytz.timezone("America/Los_Angeles"),
    "Denver / Phoenix (MT)":        pytz.timezone("America/Denver"),
    "Chicago / Mexico City (CT)":   pytz.timezone("America/Chicago"),
    "New York / Toronto (ET)":      pytz.timezone("America/New_York"),
    "Halifax / Atlantic (AT)":      pytz.timezone("America/Halifax"),
    "Colombia / Peru (COT)":        pytz.timezone("America/Bogota"),
    "Venezuela (VET)":              pytz.timezone("America/Caracas"),
    "Brazil — Brasilia (BRT)":      pytz.timezone("America/Sao_Paulo"),
    "Argentina / Uruguay (ART)":    pytz.timezone("America/Argentina/Buenos_Aires"),
    "Chile (CLT)":                  pytz.timezone("America/Santiago"),
    # Europe
    "London / Lisbon (GMT/BST)":    pytz.timezone("Europe/London"),
    "Paris / Berlin / Rome (CET)":  pytz.timezone("Europe/Paris"),
    "Athens / Helsinki (EET)":      pytz.timezone("Europe/Athens"),
    "Moscow (MSK)":                 pytz.timezone("Europe/Moscow"),
    # Africa
    "Lagos / Dakar (WAT)":          pytz.timezone("Africa/Lagos"),
    "Cairo / Johannesburg (CAT)":   pytz.timezone("Africa/Johannesburg"),
    "Nairobi / Addis Ababa (EAT)":  pytz.timezone("Africa/Nairobi"),
    # Middle East
    "Israel (IST)":                 pytz.timezone("Asia/Jerusalem"),
    "Turkey / Arabia (TRT)":        pytz.timezone("Europe/Istanbul"),
    "Gulf — Dubai / Muscat (GST)":  pytz.timezone("Asia/Dubai"),
    # Asia
    "Pakistan (PKT)":               pytz.timezone("Asia/Karachi"),
    "India / Sri Lanka (IST)":      pytz.timezone("Asia/Kolkata"),
    "Bangladesh (BST)":             pytz.timezone("Asia/Dhaka"),
    "Bangkok / Jakarta (ICT)":      pytz.timezone("Asia/Bangkok"),
    "Beijing / Singapore (CST)":    pytz.timezone("Asia/Shanghai"),
    "Tokyo / Seoul (JST)":          pytz.timezone("Asia/Tokyo"),
    # Pacific
    "Sydney / Melbourne (AEST)":    pytz.timezone("Australia/Sydney"),
    "New Zealand (NZST)":           pytz.timezone("Pacific/Auckland"),
}
DEFAULT_TZ_NAME = "New York / Toronto (ET)"

# ── Flag images ───────────────────────────────────────────────────────────────
COUNTRY_CODES = {
    "Algeria": "dz", "Argentina": "ar", "Australia": "au", "Austria": "at",
    "Belgium": "be", "Bolivia": "bo", "Brazil": "br", "Cameroon": "cm",
    "Canada": "ca", "Chile": "cl", "China": "cn", "Colombia": "co",
    "Costa Rica": "cr", "Croatia": "hr", "Czech Republic": "cz", "Czechia": "cz",
    "Denmark": "dk", "DR Congo": "cd", "Ecuador": "ec", "Egypt": "eg",
    "England": "gb-eng", "France": "fr", "Germany": "de", "Ghana": "gh",
    "Greece": "gr", "Honduras": "hn", "Hungary": "hu", "Indonesia": "id",
    "Iran": "ir", "Iraq": "iq", "Ireland": "ie", "Israel": "il",
    "Italy": "it", "Ivory Coast": "ci", "Japan": "jp", "Jordan": "jo",
    "Kenya": "ke", "Mali": "ml", "Mexico": "mx", "Morocco": "ma",
    "Netherlands": "nl", "New Zealand": "nz", "Nigeria": "ng",
    "Northern Ireland": "gb-nir", "Oman": "om", "Panama": "pa", "Paraguay": "py",
    "Peru": "pe", "Poland": "pl", "Portugal": "pt", "Qatar": "qa",
    "Romania": "ro", "Saudi Arabia": "sa", "Scotland": "gb-sct", "Senegal": "sn",
    "Serbia": "rs", "Slovakia": "sk", "Slovenia": "si", "South Africa": "za",
    "South Korea": "kr", "Spain": "es", "Switzerland": "ch", "Tunisia": "tn",
    "Turkey": "tr", "Turkiye": "tr", "UAE": "ae", "Ukraine": "ua",
    "United States": "us", "USA": "us", "Uruguay": "uy", "Uzbekistan": "uz",
    "Venezuela": "ve", "Wales": "gb-wls",
}

GROUP_LABELS = {
    "R32": "Round of 32", "R16": "Round of 16", "QF": "Quarter-Final",
    "SF": "Semi-Final", "3RD": "3rd Place", "FINAL": "Final",
}
KNOCKOUT_STAGES = {"R32", "R16", "QF", "SF", "3RD", "FINAL"}


def get_flag_img(team_name, height=24):
    code = COUNTRY_CODES.get(team_name)
    if code:
        return (
            f'<img src="https://flagcdn.com/w40/{code}.png" '
            f'height="{height}" style="vertical-align:middle; border-radius:2px; margin:0 4px;">'
        )
    return ""


def format_group(group):
    if group in GROUP_LABELS:
        return GROUP_LABELS[group]
    if group and len(group) == 1:
        return f"Group {group}"
    return group or ""


# ── Page config & CSS ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FIFA World Cup 2026", page_icon="⚽",
    layout="wide", initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; }
    section[data-testid="stSidebar"] { display: none; }
    button[data-testid="collapsedControl"] { display: none; }
    .game-card {
        background: #ffffff; border-radius: 14px; padding: 18px 24px;
        margin: 10px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        border-left: 5px solid #2e7d32;
    }
    .game-card.knockout { border-left-color: #1565c0; }
    .game-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .team-block { flex: 1; display: flex; align-items: center; gap: 10px;
                  font-size: 17px; font-weight: 600; color: #1a1a2e; }
    .team-block.right { justify-content: flex-end; }
    .center-block { text-align: center; min-width: 120px; }
    .game-time { font-size: 28px; font-weight: 800; color: #1565c0; line-height: 1.1; }
    .game-date { font-size: 13px; color: #666; margin-top: 2px; }
    .tz-label  { font-size: 11px; color: #999; }
    .game-meta { margin-top: 12px; display: flex; align-items: center;
                 gap: 14px; font-size: 13px; color: #777; }
    .badge { background: #e8f5e9; color: #2e7d32; padding: 3px 10px;
             border-radius: 20px; font-size: 12px; font-weight: 600; }
    .badge.knockout-badge { background: #e3f2fd; color: #1565c0; }
    .export-bar { background: #fff; border-radius: 12px; padding: 18px 20px;
                  margin-top: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)


# ── Game card ─────────────────────────────────────────────────────────────────
def render_game_card(game, dt, tz_name):
    home_flag  = get_flag_img(game["home_team"])
    away_flag  = get_flag_img(game["away_team"])
    group      = game.get("group", "")
    group_label = format_group(group)
    is_knockout = group in KNOCKOUT_STAGES
    card_class  = "game-card knockout" if is_knockout else "game-card"
    badge_class = "badge knockout-badge" if is_knockout else "badge"

    st.markdown(f"""
    <div class="{card_class}">
        <div class="game-row">
            <div class="team-block">
                {home_flag}<span>{game["home_team"]}</span>
            </div>
            <div class="center-block">
                <div class="game-time">{dt.strftime("%H:%M")}</div>
                <div class="game-date">{dt.strftime("%a, %b %d")}</div>
                <div class="tz-label">{tz_name}</div>
            </div>
            <div class="team-block right">
                <span>{game["away_team"]}</span>{away_flag}
            </div>
        </div>
        <div class="game-meta">
            <span>📍 {game.get("venue", "")}</span>
            <span class="{badge_class}">{group_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Export helpers ────────────────────────────────────────────────────────────
def _format_stage(group):
    if group in GROUP_LABELS:
        return GROUP_LABELS[group]
    return f"Group {group}" if group and len(group) == 1 else (group or "")


def generate_ics(games_with_dt):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//FWC26Games//EN", "CALSCALE:GREGORIAN"]
    for g, dt in games_with_dt:
        dt_utc = dt.astimezone(pytz.utc)
        dt_end = dt_utc + timedelta(hours=2)
        uid = (f"{g['date']}-{g['home_team'].replace(' ','-')}"
               f"-{g['away_team'].replace(' ','-')}@fwc26")
        stage = _format_stage(g.get("group", ""))
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART:{dt_utc.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:⚽ {g['home_team']} vs {g['away_team']}",
            f"LOCATION:{g.get('venue', '')}",
            f"DESCRIPTION:FIFA World Cup 2026 – {stage}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def _print_html(games_with_dt, tz_name):
    rows = ""
    for g, dt in games_with_dt:
        stage = _format_stage(g.get("group", ""))
        rows += (
            f"<tr><td>{dt.strftime('%a, %b %d')}</td>"
            f"<td><strong>{dt.strftime('%H:%M')}</strong></td>"
            f"<td>{g['home_team']}</td><td style='color:#aaa'>vs</td>"
            f"<td>{g['away_team']}</td>"
            f"<td style='color:#777'>{g.get('venue','')}</td>"
            f"<td><span style='background:#e8f5e9;padding:2px 8px;border-radius:12px;"
            f"font-size:12px;color:#2e7d32'>{stage}</span></td></tr>"
        )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>FIFA WC 2026 Schedule</title>
<style>
  body{{font-family:Arial,sans-serif;padding:32px;color:#222;max-width:960px;margin:auto}}
  h2{{color:#1565c0;margin-bottom:4px}}p{{color:#666;font-size:13px;margin-top:0}}
  table{{border-collapse:collapse;width:100%;margin-top:20px}}
  th{{background:#1565c0;color:#fff;padding:9px 12px;text-align:left;font-size:13px}}
  td{{padding:8px 12px;border-bottom:1px solid #eee;font-size:14px}}
  tr:nth-child(even) td{{background:#f5f7fa}}
  @media print{{body{{padding:16px}}}}
</style></head><body>
<h2>&#9917; FIFA World Cup 2026 &mdash; Match Schedule</h2>
<p>Times in: {tz_name} &nbsp;&bull;&nbsp; {len(games_with_dt)} matches</p>
<table><tr><th>Date</th><th>Time</th><th>Home</th><th></th><th>Away</th>
<th>Venue</th><th>Stage</th></tr>{rows}</table>
<p style="margin-top:24px;color:#bbb;font-size:12px">Generated by FWC26Games</p>
</body></html>"""


# ── Translations ─────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "🇬🇧 English": {
        "tz_label": "🌍 Your Time Zone",
        "tab_all": "📅 All Games", "tab_teams": "👥 By Teams", "tab_time": "🕐 By Time",
        "loading": "Loading schedule...",
        "load_error": "Could not load the schedule. Please check your internet connection and refresh.",
        "match_s": "match", "match_p": "matches",
        "upcoming": "📊 {} upcoming {}",
        "export_title": "📤 Export this list",
        "btn_print": "🖨️ Download for Print",
        "btn_cal": "📅 Download Calendar ({} events)",
        "help_print": "Downloads a clean HTML file — open in browser and press Ctrl+P to print.",
        "help_cal": "Downloads a .ics file — works with Apple Calendar, Google Calendar, and Outlook.",
        "cal_expander": "📖 How to add to your calendar app",
        "teams_label": "Pick one or more teams to see their matches:",
        "teams_ph": "Start typing a country name...",
        "teams_hint": "Select at least one team above to see their schedule.",
        "game_s": "game", "game_p": "games",
        "time_preset_label": "Choose a time window:",
        "time_presets": [
            ("🌅  Morning        06:00 – 12:00", (6, 12)),
            ("☀️  Afternoon      12:00 – 17:00", (12, 17)),
            ("🌆  Early Evening  17:00 – 20:00", (17, 20)),
            ("📺  Prime Time     20:00 – 23:00", (20, 23)),
            ("🌙  Late Night     23:00 – 24:00", (23, 24)),
            ("🔧  Custom Range",                 None),
        ],
        "time_custom": "Drag the handles to set your kick-off window:",
        "time_filter_info": "⏱️ Filters by <strong>match kick-off time</strong> in: <strong>{}</strong>",
        "time_showing": "Showing matches between <strong style='color:#1565c0'>{s}:00</strong> &nbsp;→&nbsp; <strong style='color:#1565c0'>{e}:00</strong>",
        "time_err": "Start time must be earlier than end time.",
        "time_none": "No matches kick off in this time window. Try a different range.",
        "found": "{} {} found",
        "remove_help": "Remove from list",
        "hidden": "{} {} hidden from this list",
        "restore": "↺ Restore all",
        "about_title": "About this app",
        "about_text": "Browse the full FIFA World Cup 2026 schedule with kick-off times in your timezone. Filter by team or time of day — then export to your calendar or print.",
        "match_schedule": "Match Schedule",
        "hosts": "USA · Canada · Mexico · June–July 2026",
    },
    "🇪🇸 Español": {
        "tz_label": "🌍 Tu zona horaria",
        "tab_all": "📅 Todos los partidos", "tab_teams": "👥 Por equipo", "tab_time": "🕐 Por horario",
        "loading": "Cargando calendario...",
        "load_error": "No se pudo cargar el calendario. Verifica tu conexión y recarga.",
        "match_s": "partido", "match_p": "partidos",
        "upcoming": "📊 {} {} próximos",
        "export_title": "📤 Exportar esta lista",
        "btn_print": "🖨️ Descargar para imprimir",
        "btn_cal": "📅 Descargar calendario ({} eventos)",
        "help_print": "Descarga un archivo HTML — ábrelo en tu navegador y presiona Ctrl+P.",
        "help_cal": "Descarga un archivo .ics — compatible con Apple Calendar, Google Calendar y Outlook.",
        "cal_expander": "📖 Cómo agregar a tu app de calendario",
        "teams_label": "Elige uno o más equipos para ver sus partidos:",
        "teams_ph": "Escribe el nombre de un país...",
        "teams_hint": "Selecciona al menos un equipo para ver su calendario.",
        "game_s": "partido", "game_p": "partidos",
        "time_preset_label": "Elige una franja horaria:",
        "time_presets": [
            ("🌅  Mañana          06:00 – 12:00", (6, 12)),
            ("☀️  Tarde           12:00 – 17:00", (12, 17)),
            ("🌆  Primera tarde   17:00 – 20:00", (17, 20)),
            ("📺  Prime Time      20:00 – 23:00", (20, 23)),
            ("🌙  Noche           23:00 – 24:00", (23, 24)),
            ("🔧  Rango personal", None),
        ],
        "time_custom": "Arrastra los controles para definir el rango horario:",
        "time_filter_info": "⏱️ Filtra por <strong>hora de inicio del partido</strong> en: <strong>{}</strong>",
        "time_showing": "Partidos entre <strong style='color:#1565c0'>{s}:00</strong> &nbsp;→&nbsp; <strong style='color:#1565c0'>{e}:00</strong>",
        "time_err": "La hora de inicio debe ser anterior a la hora de fin.",
        "time_none": "No hay partidos en esta franja horaria. Prueba otro rango.",
        "found": "{} {} encontrados",
        "remove_help": "Quitar de la lista",
        "hidden": "{} {} ocultos de esta lista",
        "restore": "↺ Restaurar todo",
        "about_title": "Acerca de esta app",
        "about_text": "Consulta el calendario completo del Mundial FIFA 2026 con horarios en tu zona. Filtra por equipo o franja horaria — luego exporta a tu calendario o imprime.",
        "match_schedule": "Calendario de Partidos",
        "hosts": "EE.UU. · Canadá · México · Junio–Julio 2026",
    },
    "🇫🇷 Français": {
        "tz_label": "🌍 Votre fuseau horaire",
        "tab_all": "📅 Tous les matchs", "tab_teams": "👥 Par équipe", "tab_time": "🕐 Par horaire",
        "loading": "Chargement du calendrier...",
        "load_error": "Impossible de charger le calendrier. Vérifiez votre connexion et réactualisez.",
        "match_s": "match", "match_p": "matchs",
        "upcoming": "📊 {} {} à venir",
        "export_title": "📤 Exporter cette liste",
        "btn_print": "🖨️ Télécharger pour imprimer",
        "btn_cal": "📅 Télécharger le calendrier ({} événements)",
        "help_print": "Télécharge un fichier HTML — ouvrez-le et appuyez sur Ctrl+P.",
        "help_cal": "Télécharge un fichier .ics — compatible avec Apple Calendar, Google Calendar et Outlook.",
        "cal_expander": "📖 Comment ajouter à votre app de calendrier",
        "teams_label": "Choisissez une ou plusieurs équipes pour voir leurs matchs :",
        "teams_ph": "Tapez le nom d'un pays...",
        "teams_hint": "Sélectionnez au moins une équipe pour voir son calendrier.",
        "game_s": "match", "game_p": "matchs",
        "time_preset_label": "Choisissez une plage horaire :",
        "time_presets": [
            ("🌅  Matin           06:00 – 12:00", (6, 12)),
            ("☀️  Après-midi      12:00 – 17:00", (12, 17)),
            ("🌆  Début de soirée 17:00 – 20:00", (17, 20)),
            ("📺  Prime Time      20:00 – 23:00", (20, 23)),
            ("🌙  Nuit            23:00 – 24:00", (23, 24)),
            ("🔧  Plage perso.",   None),
        ],
        "time_custom": "Faites glisser les curseurs pour définir la plage :",
        "time_filter_info": "⏱️ Filtre par <strong>heure de début du match</strong> en : <strong>{}</strong>",
        "time_showing": "Matchs entre <strong style='color:#1565c0'>{s}:00</strong> &nbsp;→&nbsp; <strong style='color:#1565c0'>{e}:00</strong>",
        "time_err": "L'heure de début doit être antérieure à l'heure de fin.",
        "time_none": "Aucun match dans cette plage. Essayez une autre plage.",
        "found": "{} {} trouvés",
        "remove_help": "Retirer de la liste",
        "hidden": "{} {} masqués de cette liste",
        "restore": "↺ Tout restaurer",
        "about_title": "À propos de cette app",
        "about_text": "Consultez le calendrier complet de la Coupe du Monde FIFA 2026 avec les horaires dans votre fuseau. Filtrez par équipe ou plage horaire — puis exportez ou imprimez.",
        "match_schedule": "Calendrier des Matchs",
        "hosts": "USA · Canada · Mexique · Juin–Juillet 2026",
    },
    "🇧🇷 Português": {
        "tz_label": "🌍 Seu fuso horário",
        "tab_all": "📅 Todos os jogos", "tab_teams": "👥 Por seleção", "tab_time": "🕐 Por horário",
        "loading": "Carregando calendário...",
        "load_error": "Não foi possível carregar o calendário. Verifique sua conexão e atualize.",
        "match_s": "jogo", "match_p": "jogos",
        "upcoming": "📊 {} {} próximos",
        "export_title": "📤 Exportar esta lista",
        "btn_print": "🖨️ Baixar para imprimir",
        "btn_cal": "📅 Baixar calendário ({} eventos)",
        "help_print": "Baixa um arquivo HTML — abra no navegador e pressione Ctrl+P para imprimir.",
        "help_cal": "Baixa um arquivo .ics — compatível com Apple Calendar, Google Calendar e Outlook.",
        "cal_expander": "📖 Como adicionar ao seu app de calendário",
        "teams_label": "Escolha uma ou mais seleções para ver seus jogos:",
        "teams_ph": "Digite o nome do país...",
        "teams_hint": "Selecione pelo menos uma seleção para ver o calendário.",
        "game_s": "jogo", "game_p": "jogos",
        "time_preset_label": "Escolha um intervalo de horário:",
        "time_presets": [
            ("🌅  Manhã           06:00 – 12:00", (6, 12)),
            ("☀️  Tarde           12:00 – 17:00", (12, 17)),
            ("🌆  Final da tarde  17:00 – 20:00", (17, 20)),
            ("📺  Prime Time      20:00 – 23:00", (20, 23)),
            ("🌙  Madrugada       23:00 – 24:00", (23, 24)),
            ("🔧  Intervalo custom", None),
        ],
        "time_custom": "Arraste os controles para definir o intervalo:",
        "time_filter_info": "⏱️ Filtra por <strong>horário de início da partida</strong> em: <strong>{}</strong>",
        "time_showing": "Jogos entre <strong style='color:#1565c0'>{s}:00</strong> &nbsp;→&nbsp; <strong style='color:#1565c0'>{e}:00</strong>",
        "time_err": "O horário de início deve ser anterior ao de fim.",
        "time_none": "Nenhum jogo neste intervalo. Tente outro intervalo.",
        "found": "{} {} encontrados",
        "remove_help": "Remover da lista",
        "hidden": "{} {} ocultos desta lista",
        "restore": "↺ Restaurar tudo",
        "about_title": "Sobre este app",
        "about_text": "Consulte o calendário completo da Copa do Mundo FIFA 2026 com horários no seu fuso. Filtre por seleção ou horário — depois exporte para seu calendário ou imprima.",
        "match_schedule": "Calendário de Jogos",
        "hosts": "EUA · Canadá · México · Junho–Julho 2026",
    },
    "🇸🇦 العربية": {
        "tz_label": "🌍 منطقتك الزمنية",
        "tab_all": "📅 جميع المباريات", "tab_teams": "👥 حسب المنتخب", "tab_time": "🕐 حسب الوقت",
        "loading": "جارٍ تحميل الجدول...",
        "load_error": "تعذّر تحميل الجدول. تحقق من اتصالك بالإنترنت وأعد التحميل.",
        "match_s": "مباراة", "match_p": "مباريات",
        "upcoming": "📊 {} {} قادمة",
        "export_title": "📤 تصدير هذه القائمة",
        "btn_print": "🖨️ تنزيل للطباعة",
        "btn_cal": "📅 تنزيل التقويم ({} أحداث)",
        "help_print": "تنزيل ملف HTML — افتحه في متصفحك واضغط Ctrl+P للطباعة.",
        "help_cal": "تنزيل ملف .ics — متوافق مع Apple Calendar وGoogle Calendar وOutlook.",
        "cal_expander": "📖 كيفية الإضافة إلى تطبيق التقويم",
        "teams_label": "اختر منتخباً أو أكثر لعرض مبارياته:",
        "teams_ph": "اكتب اسم الدولة...",
        "teams_hint": "اختر منتخباً واحداً على الأقل لعرض جدوله.",
        "game_s": "مباراة", "game_p": "مباريات",
        "time_preset_label": "اختر نطاقاً زمنياً:",
        "time_presets": [
            ("🌅  الصباح          06:00 – 12:00", (6, 12)),
            ("☀️  الظهيرة         12:00 – 17:00", (12, 17)),
            ("🌆  المساء المبكر   17:00 – 20:00", (17, 20)),
            ("📺  البث المباشر    20:00 – 23:00", (20, 23)),
            ("🌙  منتصف الليل     23:00 – 24:00", (23, 24)),
            ("🔧  نطاق مخصص",      None),
        ],
        "time_custom": "اسحب المقابض لتحديد النطاق الزمني:",
        "time_filter_info": "⏱️ تصفية حسب <strong>وقت انطلاق المباراة</strong> في: <strong>{}</strong>",
        "time_showing": "المباريات بين <strong style='color:#1565c0'>{s}:00</strong> &nbsp;→&nbsp; <strong style='color:#1565c0'>{e}:00</strong>",
        "time_err": "يجب أن يكون وقت البداية قبل وقت النهاية.",
        "time_none": "لا توجد مباريات في هذا النطاق الزمني. جرّب نطاقاً آخر.",
        "found": "{} {} تم العثور عليها",
        "remove_help": "إزالة من القائمة",
        "hidden": "{} {} مخفية من هذه القائمة",
        "restore": "↺ استعادة الكل",
        "about_title": "حول هذا التطبيق",
        "about_text": "استعرض جدول كأس العالم FIFA 2026 كاملاً مع مواعيد المباريات بتوقيتك المحلي. صفّح حسب المنتخب أو الوقت — ثم صدّر إلى تقويمك أو اطبع.",
        "match_schedule": "جدول المباريات",
        "hosts": "الولايات المتحدة · كندا · المكسيك · يونيو–يوليو 2026",
    },
    "🇮🇱 עברית": {
        "tz_label": "🌍 אזור הזמן שלך",
        "tab_all": "📅 כל המשחקים", "tab_teams": "👥 לפי קבוצה", "tab_time": "🕐 לפי שעה",
        "loading": "טוען לוח משחקים...",
        "load_error": "לא ניתן לטעון את הלוח. בדוק את החיבור לאינטרנט ורענן.",
        "match_s": "משחק", "match_p": "משחקים",
        "upcoming": "📊 {} {} קרובים",
        "export_title": "📤 ייצא רשימה זו",
        "btn_print": "🖨️ הורד להדפסה",
        "btn_cal": "📅 הורד יומן ({} אירועים)",
        "help_print": "מוריד קובץ HTML — פתח בדפדפן ולחץ Ctrl+P להדפסה.",
        "help_cal": "מוריד קובץ .ics — תואם ל-Apple Calendar, Google Calendar ו-Outlook.",
        "cal_expander": "📖 איך להוסיף לאפליקציית היומן",
        "teams_label": "בחר קבוצה אחת או יותר לצפייה במשחקיה:",
        "teams_ph": "הקלד שם מדינה...",
        "teams_hint": "בחר לפחות קבוצה אחת לצפייה בלוח המשחקים שלה.",
        "game_s": "משחק", "game_p": "משחקים",
        "time_preset_label": "בחר טווח שעות:",
        "time_presets": [
            ("🌅  בוקר            06:00 – 12:00", (6, 12)),
            ("☀️  צהריים          12:00 – 17:00", (12, 17)),
            ("🌆  בין ערביים      17:00 – 20:00", (17, 20)),
            ("📺  פריים טיים      20:00 – 23:00", (20, 23)),
            ("🌙  לילה            23:00 – 24:00", (23, 24)),
            ("🔧  טווח מותאם אישית", None),
        ],
        "time_custom": "גרור את הידיות להגדרת טווח הזמן:",
        "time_filter_info": "⏱️ מסנן לפי <strong>שעת תחילת המשחק</strong> ב: <strong>{}</strong>",
        "time_showing": "משחקים בין <strong style='color:#1565c0'>{s}:00</strong> &nbsp;→&nbsp; <strong style='color:#1565c0'>{e}:00</strong>",
        "time_err": "שעת ההתחלה חייבת להיות לפני שעת הסיום.",
        "time_none": "אין משחקים בטווח זה. נסה טווח אחר.",
        "found": "{} {} נמצאו",
        "remove_help": "הסר מהרשימה",
        "hidden": "{} {} מוסתרים מרשימה זו",
        "restore": "↺ שחזר הכל",
        "about_title": "אודות האפליקציה",
        "about_text": "עיין בלוח המשחקים המלא של מונדיאל FIFA 2026 עם שעות הקיקאוף באזור הזמן שלך. סנן לפי קבוצה או שעה — ולאחר מכן ייצא ליומן או הדפס.",
        "match_schedule": "לוח משחקים",
        "hosts": "ארה\"ב · קנדה · מקסיקו · יוני–יולי 2026",
    },
    "🇨🇳 中文": {
        "tz_label": "🌍 您的时区",
        "tab_all": "📅 全部比赛", "tab_teams": "👥 按球队", "tab_time": "🕐 按时间",
        "loading": "正在加载赛程...",
        "load_error": "无法加载赛程，请检查网络连接后刷新。",
        "match_s": "场比赛", "match_p": "场比赛",
        "upcoming": "📊 即将进行 {} {}",
        "export_title": "📤 导出此列表",
        "btn_print": "🖨️ 下载打印版",
        "btn_cal": "📅 下载日历（{} 个赛事）",
        "help_print": "下载 HTML 文件，在浏览器中打开后按 Ctrl+P 打印。",
        "help_cal": "下载 .ics 文件，适用于 Apple 日历、Google 日历和 Outlook。",
        "cal_expander": "📖 如何添加到日历应用",
        "teams_label": "选择一个或多个球队查看比赛：",
        "teams_ph": "输入国家名称...",
        "teams_hint": "请至少选择一支球队以查看其赛程。",
        "game_s": "场比赛", "game_p": "场比赛",
        "time_preset_label": "选择时间段：",
        "time_presets": [
            ("🌅  早上             06:00 – 12:00", (6, 12)),
            ("☀️  下午             12:00 – 17:00", (12, 17)),
            ("🌆  傍晚             17:00 – 20:00", (17, 20)),
            ("📺  黄金时段         20:00 – 23:00", (20, 23)),
            ("🌙  深夜             23:00 – 24:00", (23, 24)),
            ("🔧  自定义范围",      None),
        ],
        "time_custom": "拖动滑块设置时间范围：",
        "time_filter_info": "⏱️ 按 <strong>比赛开球时间</strong> 筛选（时区：<strong>{}</strong>）",
        "time_showing": "显示开球时间在 <strong style='color:#1565c0'>{s}:00</strong> &nbsp;→&nbsp; <strong style='color:#1565c0'>{e}:00</strong> 之间的比赛",
        "time_err": "开始时间必须早于结束时间。",
        "time_none": "此时间段内没有比赛，请尝试其他时间段。",
        "found": "找到 {} {}",
        "remove_help": "从列表中移除",
        "hidden": "已隐藏 {} {}",
        "restore": "↺ 恢复全部",
        "about_title": "关于此应用",
        "about_text": "查看 2026 年 FIFA 世界杯完整赛程，比赛时间已转换为您所在时区。按球队或时间段筛选，然后导出到日历或打印。",
        "match_schedule": "赛程表",
        "hosts": "美国 · 加拿大 · 墨西哥 · 2026年6月–7月",
    },
}


def render_export_options(games_with_dt, tz_name, key, T):
    if not games_with_dt:
        return
    n = len(games_with_dt)
    m = T["match_s"] if n == 1 else T["match_p"]
    st.markdown(
        f"<div class='export-bar'><strong>{T['export_title']}</strong>"
        f"&nbsp;&nbsp;<span style='color:#888;font-size:13px;'>{n} {m}</span></div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)

    with col1:
        if st.download_button(
            label=T["btn_print"],
            data=_print_html(games_with_dt, tz_name),
            file_name="wc2026_schedule.html",
            mime="text/html",
            use_container_width=True,
            help=T["help_print"],
            key=f"print_{key}",
        ):
            track_event("print_download", {"tab": key, "matches": n})

    with col2:
        if st.download_button(
            label=T["btn_cal"].format(n),
            data=generate_ics(games_with_dt),
            file_name="wc2026_schedule.ics",
            mime="text/calendar",
            use_container_width=True,
            help=T["help_cal"],
            key=f"cal_{key}",
        ):
            track_event("calendar_download", {"tab": key, "matches": n})

    with st.expander(T["cal_expander"]):
        st.markdown("""
| Platform | Steps |
|---|---|
| **iPhone / iPad → Apple Calendar** | Tap the button → tap the downloaded file → tap **"Add All"** in Apple Calendar |
| **iPhone / iPad → Google Calendar** | Tap the button → save the file → open **Safari** → go to [calendar.google.com](https://calendar.google.com) → **Settings ⚙️ → Import** → choose the saved file |
| **Android → Google Calendar** | Tap the button → the file opens in **Google Calendar** automatically |
| **Mac** | Click the button → double-click the downloaded file → Apple Calendar opens and asks to import |
| **Windows – Outlook** | Click the button → double-click the downloaded `.ics` file → Outlook will import all events |
| **Google Calendar (browser)** | Click the button → go to [calendar.google.com](https://calendar.google.com) → **Settings ⚙️ → Import** → choose the file → click Import |
| **Other apps** | Any calendar app that supports `.ics` import (Thunderbird, Fantastical, etc.) will work the same way |

> Each match is added as a **separate event**, 2 hours long, with the venue in the location field.
        """)



# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    return fetch_schedule()


def game_key(g):
    return f"{g['date']}|{g['home_team']}|{g['away_team']}"


def render_games_list(games_with_dt, tz_name, export_key, T):
    removed = st.session_state.removed_games
    visible = [(g, dt) for g, dt in games_with_dt if game_key(g) not in removed]
    hidden  = len(games_with_dt) - len(visible)

    n = len(visible)
    m = T["match_s"] if n == 1 else T["match_p"]
    st.info(T["upcoming"].format(n, m))

    render_export_options(visible, tz_name, key=export_key, T=T)

    if hidden > 0:
        col_msg, col_btn = st.columns([3, 1])
        with col_msg:
            gw = T["game_s"] if hidden == 1 else T["game_p"]
            st.caption(T["hidden"].format(hidden, gw))
        with col_btn:
            if st.button(T["restore"], key=f"restore_{export_key}"):
                st.session_state.removed_games.clear()
                st.rerun()

    for g, dt in visible:
        col_card, col_rm = st.columns([11, 1])
        with col_card:
            render_game_card(g, dt, tz_name)
        with col_rm:
            st.markdown("<div style='padding-top:18px'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"rm_{export_key}_{game_key(g)}",
                         help=T["remove_help"], use_container_width=True):
                st.session_state.removed_games.add(game_key(g))
                track_event("game_removed", {"tab": export_key})
                st.rerun()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    inject_ga4()

    if "removed_games" not in st.session_state:
        st.session_state.removed_games = set()

    # Language selector
    prev_lang = st.session_state.get("lang")
    lang = st.selectbox(
        "🌐 Language", list(TRANSLATIONS.keys()), key="lang", label_visibility="collapsed"
    )
    T = TRANSLATIONS[lang]

    # Track language changes
    if prev_lang and prev_lang != lang:
        track_event("language_changed", {"language": lang})

    # Timezone picker
    tz_names = list(TIMEZONES.keys())
    tz_name  = st.selectbox(
        T["tz_label"], tz_names, index=tz_names.index(DEFAULT_TZ_NAME),
    )
    tz = TIMEZONES[tz_name]

    st.markdown(f"""
    <div style="background:#ffffff;border-radius:18px;padding:28px 20px 22px;
    text-align:center;margin-bottom:24px;
    box-shadow:0 2px 18px rgba(0,0,0,0.08);
    border-top:5px solid #1565c0;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/2026_FIFA_World_Cup_emblem.svg/250px-2026_FIFA_World_Cup_emblem.svg.png"
             alt="FIFA World Cup 2026"
             style="height:130px;filter:drop-shadow(0 2px 8px rgba(0,0,0,0.12));">
        <div style="margin-top:16px;display:flex;align-items:center;
        justify-content:center;gap:10px;">
            <div style="height:1px;width:36px;background:#ddd;"></div>
            <div style="font-size:12px;font-weight:800;color:#1565c0;
            letter-spacing:3px;text-transform:uppercase;">{T["match_schedule"]}</div>
            <div style="height:1px;width:36px;background:#ddd;"></div>
        </div>
        <div style="font-size:12px;color:#aaa;margin-top:6px;letter-spacing:1px;">
            {T["hosts"]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load schedule before tabs so we can show the count above them
    with st.spinner(T["loading"]):
        schedule = load_data()

    if not schedule:
        st.error(T["load_error"])
        return

    future_games = get_future_games(schedule)
    teams = get_national_teams(future_games)

    st.markdown("---")

    # Tabs — always visible on mobile
    tab_all, tab_teams, tab_time = st.tabs(
        [T["tab_all"], T["tab_teams"], T["tab_time"]]
    )

    # ── All Games ──────────────────────────────────────────────────────────────
    with tab_all:
        games_with_dt = [
            (g, convert_to_tz(g["date"], g["time"], g["utc_offset"], tz))
            for g in future_games
        ]
        render_games_list(games_with_dt, tz_name, export_key="all", T=T)

    # ── By Teams ───────────────────────────────────────────────────────────────
    with tab_teams:
        selected_teams = st.multiselect(
            T["teams_label"], options=teams, placeholder=T["teams_ph"],
        )

        if not selected_teams:
            st.info(T["teams_hint"])
        else:
            seen, team_games = set(), []
            for team in selected_teams:
                for g in get_games_for_team(future_games, team):
                    tkey = (g["date"], g["time"], g["home_team"], g["away_team"])
                    if tkey not in seen:
                        seen.add(tkey)
                        team_games.append(g)
            team_games.sort(key=lambda g: (g["date"], g["time"]))

            flags_html = " ".join(get_flag_img(t, height=22) for t in selected_teams)
            count = len(team_games)
            cw = T["match_s"] if count == 1 else T["match_p"]
            st.markdown(
                f"<div style='background:#f0f4f8;padding:12px 18px;border-radius:8px;"
                f"font-size:15px;color:#333;margin:10px 0 16px;'>"
                f"{flags_html}&nbsp; <strong>{', '.join(selected_teams)}</strong>"
                f"&nbsp;—&nbsp; {count} {cw}</div>",
                unsafe_allow_html=True,
            )

            games_with_dt = [
                (g, convert_to_tz(g["date"], g["time"], g["utc_offset"], tz))
                for g in team_games
            ]
            render_games_list(games_with_dt, tz_name, export_key="teams", T=T)

    # ── By Time ────────────────────────────────────────────────────────────────
    with tab_time:
        st.markdown(
            f"<div style='background:#e8f4fd;border-left:4px solid #1565c0;padding:10px 16px;"
            f"border-radius:6px;margin-bottom:18px;font-size:14px;color:#1a3a5c;'>"
            f"{T['time_filter_info'].format(tz_name)}</div>",
            unsafe_allow_html=True,
        )

        time_presets = T["time_presets"]
        preset_labels = [label for label, _ in time_presets]
        preset_hours  = {label: hours for label, hours in time_presets}

        preset_choice = st.selectbox(T["time_preset_label"], preset_labels, index=3)

        if preset_hours[preset_choice] is None:
            hour_labels    = [f"{h:02d}:00" for h in range(25)]
            selected_range = st.select_slider(
                T["time_custom"], options=hour_labels, value=("18:00", "23:00"),
            )
            start_hour = int(selected_range[0].split(":")[0])
            end_hour   = int(selected_range[1].split(":")[0])
        else:
            start_hour, end_hour = preset_hours[preset_choice]

        st.markdown(
            f"<div style='background:#f0f4f8;padding:12px 18px;border-radius:8px;"
            f"font-size:15px;color:#333;margin:10px 0 4px;'>"
            f"{T['time_showing'].format(s=start_hour, e=end_hour)}"
            f"&nbsp;&nbsp;<span style='color:#888;font-size:13px;'>({tz_name})</span></div>",
            unsafe_allow_html=True,
        )

        if start_hour >= end_hour:
            st.error(T["time_err"])
        else:
            filtered = get_games_in_time_range(future_games, start_hour, end_hour, tz)
            if not filtered:
                st.info(T["time_none"])
            else:
                fw = T["match_s"] if len(filtered) == 1 else T["match_p"]
                st.markdown(f"**{T['found'].format(len(filtered), fw)}**")
                render_games_list(filtered, tz_name, export_key="time", T=T)

    st.markdown("---")
    st.markdown(f"""
    <div style="background:#ffffff;border-radius:16px;padding:24px 28px;
    max-width:560px;margin:0 auto 8px;
    box-shadow:0 2px 16px rgba(0,0,0,0.09);
    border-top: 4px solid #f5a623;">
        <div style="font-size:13px;font-weight:700;color:#f5a623;letter-spacing:2px;
        text-transform:uppercase;margin-bottom:6px;">{T["about_title"]}</div>
        <div style="font-size:14px;color:#444;line-height:1.75;margin-bottom:16px;">
            {T["about_text"]}
        </div>
        <div style="border-top:1px solid #f0f0f0;padding-top:14px;
        display:flex;flex-wrap:wrap;gap:20px;align-items:center;">
            <span style="color:#222;font-size:14px;font-weight:600;">👤 Idan Atiya</span>
            <a href="http://www.linkedin.com/in/idanatiya317" target="_blank"
               style="color:#0a66c2;text-decoration:none;font-size:14px;font-weight:500;">
               🔗 LinkedIn</a>
            <a href="https://github.com/ia317/WC_TVkids_hours" target="_blank"
               style="color:#333;text-decoration:none;font-size:14px;font-weight:500;">
               💻 GitHub</a>
        </div>
    </div>
    <div style="text-align:center;color:#ccc;font-size:11px;margin-top:10px;margin-bottom:4px;">
        Data from OpenFootball
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
