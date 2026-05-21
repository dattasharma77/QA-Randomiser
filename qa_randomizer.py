"""
QA Alert Randomizer - Streamlit App
=====================================
Weekly QA sampling tool. Bracketing data uploaded separately each month.
User ID column maps to alerts, Zendesk ID column maps to Zendesk tickets.
Picks are frozen weekly and accumulate into a monthly view.
"""

import streamlit as st
import pandas as pd
import json
import hashlib
from datetime import datetime, date
from pathlib import Path

# --- Constants ---

FROZEN_FILE = "qa_frozen_picks.json"
ARCHIVE_FILE = "qa_frozen_archive.json"

# On Streamlit Cloud, use /tmp for writable storage
import os, tempfile
if not os.access(".", os.W_OK):
    FROZEN_FILE = os.path.join(tempfile.gettempdir(), "qa_frozen_picks.json")
    ARCHIVE_FILE = os.path.join(tempfile.gettempdir(), "qa_frozen_archive.json")
NAVY = "#1a2744"

BRACKET_TARGETS = {
    1: {"Zendesk": 4, "Alerts": 2, "BV": 2, "Redeems": 2},
    2: {"Zendesk": 6, "Alerts": 5, "BV": 5, "Redeems": 4},
    3: {"Zendesk": 10, "Alerts": 7, "BV": 7, "Redeems": 6},
}

# Weeks with extra samples (week 2 and 4 get +1 per category)
HEAVY_WEEKS = {2, 4}

# German team identifier — Zendesk excluded, de_idnow_fraud excluded from alerts
GERMAN_TEAM = "GERMAN"

# Zendesk: only keep tickets from these groups (Risk emails / Risk documents)
ZENDESK_ALLOWED_GROUPS = {
    "risk", "risk email", "risk emails", "risk document", "risk documents",
    "risk - email", "risk - document", "risk - documents", "risk - emails",
}

# Zendesk: exclude these channels (outbound = agent-raised tasks)
ZENDESK_EXCLUDED_CHANNELS = {"outbound e-mail", "outbound email"}

# Alert type excluded for German agents
GERMAN_EXCLUDED_ALERT_TYPES = {"de_idnow_fraud"}

# Required cols in data CSVs (NO QA Bracket or Category needed - derived by app)
ALERTS_REQUIRED  = ["ALERT_ID", "UPDATE_DATE", "SRC_RESOLVED_BY_AGENT_ID", "ALERT_TYPE_DESC"]
ZENDESK_REQUIRED = ["TICKET_ID", "UPDATE_DATE", "AGENT_NAME"]

# Bracketing file required columns (case-insensitive)
BRACKET_COLS = ["NAME", "USER ID", "ZENDESK ID", "QA BRACKET"]
BRACKET_COLS_WITH_TL = ["NAME", "USER ID", "ZENDESK ID", "TL", "QA BRACKET"]

# ---------------------------------------------------------------------------
# Proactive alert type mapping (hardcoded from Proactive reference table)
# Category: Alerts | BV | Redeems | Document
# Type: PROACTIVE (only these are sampled) or blank (excluded)
# BV override: bv_deposit_review, bv_redeem_review, suspicious_doc_upload -> "BV"
# Document category -> remapped to "Alerts" (per Power Query logic)
# manual_docupload -> always excluded
# ---------------------------------------------------------------------------

PROACTIVE_MAP = {
    # ── Alerts category (Proactive) ──────────────────────────────────────────
    "active_dup_acnt"                    : ("Alerts", True),
    "bv_deposit_review"                  : ("BV",     True),   # BV override
    "bv_rdm_review"                      : ("BV",     True),   # BV override
    "ccbin_mismatch"                     : ("Alerts", True),
    "cpr_failed"                         : ("Alerts", True),
    "ecopayz_instr_mismatch"             : ("Alerts", True),
    "followup_rmc"                       : ("Alerts", True),
    "instr_mismatch"                     : ("Alerts", True),
    "luxonpay_instr_mismatch"            : ("Alerts", True),
    "maxaccountspercc"                   : ("Alerts", True),
    "mchbtr_ins_msmtch"                  : ("Alerts", True),
    "pwmb_instr_mismatch"               : ("Alerts", True),
    "paypal_adrsdiff"                    : ("Alerts", True),
    "restricted"                         : ("Alerts", True),
    "skrill_name_mismatch"               : ("Alerts", True),
    "susp_duplicate"                     : ("Alerts", True),
    "name_on_card_mismatch"              : ("Alerts", True),
    "psc_instr_mismatch"                 : ("Alerts", True),
    "dnaid_dup_activedup"                : ("Alerts", True),
    "dnaid_dup_fraud"                    : ("Alerts", True),
    "dnaid_dup_moneyowed"                : ("Alerts", True),
    "dias_name_mismatch"                 : ("Alerts", True),
    "maxaccountsperba"                   : ("Alerts", True),
    "lugas_monthly_increase"             : ("Alerts", True),
    "deu_duplicate_alert"                : ("Alerts", True),
    "ontario_name_change"                : ("Alerts", True),
    "maxaccountperpar"                   : ("Alerts", True),
    "truelayer_instr_mismatch"           : ("Alerts", True),
    "truelayer_bank_prev_used"           : ("Alerts", True),
    "truelayer_blk_ac"                   : ("Alerts", True),
    "es_suspicious_match"                : ("Alerts", True),
    # ── Alerts category (Passive) ────────────────────────────────────────────
    "block"                              : ("Alerts", False),
    "fraud_dup"                          : ("Alerts", False),
    "fraudcard"                          : ("Alerts", False),
    "highdep_lesstime"                   : ("Alerts", False),
    "ipcountrymismatch"                  : ("Alerts", False),
    "mb_id"                              : ("Alerts", False),
    "purchaselimits"                     : ("Alerts", False),
    "trustly_dtls_mismatch"              : ("Alerts", False),
    "winnings_vrfn"                      : ("Alerts", False),
    "instr_mismatch/skrill_name_mismatch": ("Alerts", False),
    "maxaccntperpaysafecard"             : ("Alerts", False),
    "rmc_invtgt"                         : ("Alerts", False),
    "dna_id_merge_split_cs"              : ("Alerts", False),
    "swe_bankid_verifi_mismatch"         : ("Alerts", False),
    "bv_deposit_reject"                  : ("Alerts", False),
    "maxaccountsperskrill"               : ("Alerts", False),
    "payoptblock"                        : ("Alerts", False),
    "maxaccountperap"                    : ("Alerts", False),
    "fraud"                              : ("Alerts", False),
    "bv_rdm_reject"                      : ("Alerts", False),
    "maxaccountpernetellerdeposit"       : ("Alerts", False),
    "maxpscaccntperuser"                 : ("Alerts", False),
    "de_tink_pii_mismatch"               : ("Alerts", False),
    "pcs_instr_mismatch"                 : ("Alerts", False),
    "redeemvrfn_sb"                      : ("Alerts", False),
    "casino_big_win"                     : ("Alerts", False),
    "maxaccountperfnbewalletcashout"     : ("Alerts", False),
    "maxaccntperdep"                     : ("Alerts", False),
    "grc_duplicate_acc"                  : ("Alerts", False),
    "rmc_docupload_bra_rekyc"            : ("Alerts", False),
    "rmc_docupload_bra_facematch"        : ("Alerts", False),
    "follow up alerts"                   : ("Alerts", False),
    # ── Document category → remapped to Alerts ───────────────────────────────
    "doc_expiry_upload"                  : ("Alerts", False),
    "suspicious_doc_upload"              : ("BV",     False),  # BV override
    "rmc_docupload"                      : ("Alerts", False),
    "rmc_docupload_rekyc"                : ("Alerts", False),
    "rmc_docupload_bra_id"               : ("Alerts", False),
    "rmc_docupload_bra_cpf_mismatch"     : ("Alerts", False),
    "rmcdocupload_grcupdate"             : ("Alerts", False),
    "rmc_spain_rekyc_doc_upload"         : ("Alerts", False),
    "rmc_es_bankstatment_verification"   : ("Alerts", False),
    "rmc_docupload_expired_id_es"        : ("Alerts", False),
    "rmc_es_payinstru_verification"      : ("Alerts", False),
    "de_payinstru_verification"          : ("Alerts", False),
    "rmc_docupload_bra_manual_cpf_dup"   : ("Alerts", False),
    "rmc_docupload_aml_rekyc_es"         : ("Alerts", False),
    "de_idnow_fraud"                     : ("Alerts", False),
    # ── Redeems ──────────────────────────────────────────────────────────────
    "redeemvrfn"                         : ("Redeems", False),
    # ── Always excluded ──────────────────────────────────────────────────────
    "manual_docupload"                   : ("EXCLUDE", False),
}

def assign_category(alert_type: str) -> tuple:
    """
    Returns (category, is_proactive) for a given alert type.
    BV override: bv_deposit_review, bv_rdm_review, suspicious_doc_upload -> BV
    Document types -> Alerts
    redeemvrfn -> Redeems
    manual_docupload -> EXCLUDE
    Everything else -> Alerts
    """
    BV_OVERRIDE = {"bv_deposit_review", "bv_rdm_review", "suspicious_doc_upload"}
    key = str(alert_type).strip().lower()

    if key == "manual_docupload":
        return ("EXCLUDE", False)
    if key in BV_OVERRIDE:
        entry = PROACTIVE_MAP.get(key, ("BV", False))
        return ("BV", entry[1])
    if key == "redeemvrfn":
        return ("Redeems", False)

    entry = PROACTIVE_MAP.get(key)
    if entry is None:
        for k, v in PROACTIVE_MAP.items():
            if k.lower() == key:
                entry = v
                break
    if entry is None:
        return ("Alerts", False)

    cat, is_proactive = entry
    if cat == "Document":
        cat = "Alerts"
    return (cat, is_proactive)


def transform_alerts(df: pd.DataFrame, bracket_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Apply transformations to raw alerts CSV:
    1. Exclude manual_docupload
    2. Exclude de_idnow_fraud for German agents
    3. Assign Category (BV override, Document->Alerts, Redeems)
    4. Keep all rows (both Proactive and Passive)
    Returns cleaned DataFrame with CATEGORY column added.
    """
    df = df.copy()

    if "ALERT_TYPE_DESC" in df.columns:
        df = df[df["ALERT_TYPE_DESC"].str.strip().str.lower() != "manual_docupload"]

    # Exclude de_idnow_fraud for German agents (TL = Williams Nikita Grace Gary)
    if bracket_df is not None and "SRC_RESOLVED_BY_AGENT_ID" in df.columns:
        # Build user_id -> TL lookup
        uid_to_tl = dict(zip(bracket_df["USER_ID"].str.strip().str.lower(),
                             bracket_df["TL"].str.strip().str.lower()))
        german_uids = set(
            uid for uid, tl in uid_to_tl.items()
            if tl == "williams nikita grace gary"
        )
        german_mask = df["SRC_RESOLVED_BY_AGENT_ID"].str.strip().str.lower().isin(german_uids)
        de_fraud_mask = df["ALERT_TYPE_DESC"].str.strip().str.lower() == "de_idnow_fraud"
        df = df[~(german_mask & de_fraud_mask)]

    results = df["ALERT_TYPE_DESC"].apply(lambda x: assign_category(x))
    df["CATEGORY"] = results.apply(lambda x: x[0])
    df = df[df["CATEGORY"] != "EXCLUDE"]
    return df.reset_index(drop=True)

# --- Page config ---

st.set_page_config(page_title="QA Sampling", page_icon="🎲", layout="wide")

st.markdown(f"""
<style>
  /* ── Global ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
  .main .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {{ background: linear-gradient(180deg, {NAVY} 0%, #0f1a35 100%); }}
  [data-testid="stSidebar"] * {{ color: #e8edf5 !important; }}
  [data-testid="stSidebar"] .stButton > button {{
    background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
    color: #fff !important; border-radius: 8px; width: 100%;
    transition: all 0.2s;
  }}
  [data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.22); border-color: rgba(255,255,255,0.4);
  }}
  [data-testid="stSidebar"] .stFileUploader {{ background: rgba(255,255,255,0.06); border-radius: 8px; padding: 8px; }}
  [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.15); }}

  /* ── Header banner ── */
  .qa-header {{
    background: linear-gradient(135deg, {NAVY} 0%, #2a4080 100%);
    border-radius: 14px; padding: 28px 36px; margin-bottom: 24px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 20px rgba(26,39,68,0.25);
  }}
  .qa-header h1 {{ color: #fff; font-size: 1.9rem; font-weight: 800; margin: 0; letter-spacing: -0.02em; }}
  .qa-header p {{ color: rgba(255,255,255,0.65); font-size: 0.85rem; margin: 4px 0 0; }}
  .qa-badge {{
    background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25);
    color: #fff; border-radius: 20px; padding: 6px 16px; font-size: 0.8rem; font-weight: 600;
  }}

  /* ── Filter bar ── */
  .filter-bar {{
    background: #fff; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06); border: 1px solid #eef0f5;
    display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap;
  }}

  /* ── Metric cards ── */
  .metric-row {{ display: flex; gap: 14px; margin-bottom: 20px; flex-wrap: wrap; }}
  .metric-card {{
    background: #fff; border-radius: 12px; padding: 18px 22px; flex: 1; min-width: 130px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06); border: 1px solid #eef0f5;
    border-left: 4px solid {NAVY};
  }}
  .metric-card.green {{ border-left-color: #1e7e4a; }}
  .metric-card.blue  {{ border-left-color: #2563eb; }}
  .metric-card.amber {{ border-left-color: #d97706; }}
  .metric-card .val {{ font-size: 2rem; font-weight: 800; color: {NAVY}; line-height: 1; }}
  .metric-card .lbl {{ font-size: 0.72rem; color: #888; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600; margin-top: 4px; }}

  /* ── Section headers ── */
  .section-header {{
    display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
    padding-bottom: 10px; border-bottom: 2px solid #eef0f5;
  }}
  .section-header .icon {{
    width: 32px; height: 32px; border-radius: 8px; display: flex;
    align-items: center; justify-content: center; font-size: 1rem;
  }}
  .section-header .icon.alert {{ background: #eff6ff; }}
  .section-header .icon.zendesk {{ background: #f0fdf4; }}
  .section-header h3 {{ margin: 0; font-size: 1rem; font-weight: 700; color: {NAVY}; }}
  .section-header span {{ font-size: 0.78rem; color: #888; margin-left: auto; }}

  /* ── Tables ── */
  .stDataFrame {{ border-radius: 10px; overflow: hidden; border: 1px solid #eef0f5; }}
  .stDataFrame thead th {{
    background: {NAVY} !important; color: #fff !important;
    font-weight: 600 !important; font-size: 0.8rem !important;
  }}
  .stDataFrame tbody tr:hover td {{ background: #f0f4ff !important; }}

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {{
    background: #f8f9fc; border-radius: 10px; padding: 4px; gap: 4px;
  }}
  .stTabs [data-baseweb="tab"] {{
    border-radius: 8px; font-weight: 600; font-size: 0.88rem; padding: 8px 20px;
    color: #666;
  }}
  .stTabs [data-baseweb="tab"][aria-selected="true"] {{
    background: {NAVY}; color: #fff;
  }}

  /* ── Buttons ── */
  .stButton > button {{
    border-radius: 8px; font-weight: 600; font-size: 0.88rem;
    transition: all 0.18s; border: none;
  }}
  .stButton > button[kind="primary"] {{
    background: {NAVY}; color: #fff;
  }}
  .stButton > button[kind="primary"]:hover {{ background: #253660; }}

  /* ── Download button ── */
  .stDownloadButton > button {{
    background: #f0f4ff; color: {NAVY}; border: 1px solid #c5d0f0;
    border-radius: 8px; font-weight: 600; font-size: 0.82rem;
  }}
  .stDownloadButton > button:hover {{ background: #e0e8ff; }}

  /* ── Info/success boxes ── */
  .stAlert {{ border-radius: 10px; }}

  /* ── Divider ── */
  hr {{ border-color: #eef0f5; margin: 20px 0; }}
</style>
""", unsafe_allow_html=True)

# --- Persistence ---

def load_frozen() -> dict:
    if not Path(FROZEN_FILE).exists():
        return {"alerts": [], "zendesk": []}
    try:
        with open(FROZEN_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("alerts", [])
        d.setdefault("zendesk", [])
        return d
    except Exception as e:
        st.warning(f"Could not read frozen picks file (corrupt?). Starting fresh. {e}")
        return {"alerts": [], "zendesk": []}

def save_frozen(data: dict):
    with open(FROZEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    # Auto-archive: persist a copy to the archive file (append-only, never cleared)
    save_to_archive(data)


def load_archive() -> dict:
    """Load the persistent archive of all frozen picks across all months."""
    if not Path(ARCHIVE_FILE).exists():
        return {"alerts": [], "zendesk": []}
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("alerts", [])
        d.setdefault("zendesk", [])
        return d
    except Exception:
        return {"alerts": [], "zendesk": []}


def save_to_archive(current_data: dict):
    """Merge current frozen picks into the archive (deduplicates by ID + Month + Week)."""
    archive = load_archive()

    # Build sets of existing keys for fast dedup
    existing_alerts = set()
    for r in archive["alerts"]:
        key = (str(r.get("ALERT_ID", "")), r.get("Month", ""), r.get("Week", ""))
        existing_alerts.add(key)

    existing_zendesk = set()
    for r in archive["zendesk"]:
        key = (str(r.get("TICKET_ID", "")), r.get("Month", ""), r.get("Week", ""))
        existing_zendesk.add(key)

    # Append only new records
    for r in current_data.get("alerts", []):
        key = (str(r.get("ALERT_ID", "")), r.get("Month", ""), r.get("Week", ""))
        if key not in existing_alerts:
            archive["alerts"].append(r)
            existing_alerts.add(key)

    for r in current_data.get("zendesk", []):
        key = (str(r.get("TICKET_ID", "")), r.get("Month", ""), r.get("Week", ""))
        if key not in existing_zendesk:
            archive["zendesk"].append(r)
            existing_zendesk.add(key)

    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2, default=str)

# --- Date helpers ---

def parse_date(val):
    if pd.isna(val): return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try: return datetime.strptime(s, fmt).date()
        except ValueError: pass
    try: return pd.to_datetime(s).date()
    except: return None

def day_to_week(day: int) -> int:
    if day <= 7: return 1
    if day <= 14: return 2
    if day <= 21: return 3
    return 4

def detect_majority_week(df: pd.DataFrame, date_col: str) -> int:
    weeks = [day_to_week(parse_date(v).day) for v in df[date_col] if parse_date(v)]
    return max(set(weeks), key=weeks.count) if weeks else day_to_week(date.today().day)

# --- Column helpers ---

def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def find_col(cols, name: str):
    name_u = name.upper().strip()
    for c in cols:
        if c.upper().strip() == name_u:
            return c
    return None

def missing_cols(df: pd.DataFrame, required: list) -> list:
    return [r for r in required if r not in df.columns]

# --- Stable hash ---

def stable_hash(id_val, year: int, month: int, week: int) -> int:
    try:
        id_int = int(str(id_val).strip())
    except:
        id_int = int(hashlib.md5(str(id_val).encode()).hexdigest(), 16) % 100000
    return (id_int * 7919 + year * 100 + month * 10 + week) % 1000000

# --- Bracketing file loader ---

def load_bracketing(source) -> pd.DataFrame | None:
    """
    Load bracketing Excel/CSV from a file path (str) or uploaded file object.
    Returns normalized DataFrame with columns: NAME, USER_ID, ZENDESK_ID, QA_BRACKET, TL
    """
    try:
        # Determine if source is a path string or file object
        if isinstance(source, str):
            fname = source.lower()
            if fname.endswith((".xlsx", ".xls")):
                df = pd.read_excel(source)
            else:
                try:
                    df = pd.read_csv(source, encoding="utf-8")
                except UnicodeDecodeError:
                    df = pd.read_csv(source, encoding="cp1252")
        else:
            fname = source.name.lower()
            if fname.endswith(".csv"):
                try:
                    df = pd.read_csv(source, encoding="utf-8")
                except UnicodeDecodeError:
                    source.seek(0)
                    df = pd.read_csv(source, encoding="cp1252")
            else:
                df = pd.read_excel(source)
    except Exception as e:
        st.error(f"Could not read bracketing file: {e}")
        return None

    df = norm_cols(df)

    # Find required columns flexibly
    col_map = {}
    aliases = {
        "NAME":       ["NAME", "AGENT NAME", "FULL NAME"],
        "USER ID":    ["USER ID", "USERID", "USER_ID", "ALERT ID", "ALERT_ID"],
        "ZENDESK ID": ["ZENDESK ID", "ZENDESK_ID", "ZD ID", "ZD_ID"],
        "QA BRACKET": ["QA BRACKET", "BRACKET", "QA_BRACKET"],
        "TL":         ["TL", "TEAM LEAD", "TEAM_LEAD", "TEAMLEAD", "LEAD"],
    }
    for key, options in aliases.items():
        for opt in options:
            if opt in df.columns:
                col_map[key] = opt
                break

    required = ["NAME", "USER ID", "ZENDESK ID", "QA BRACKET"]
    missing = [r for r in required if r not in col_map]
    if missing:
        st.error(f"Bracketing file missing columns: {missing}. Found: {list(df.columns)}")
        return None

    result = pd.DataFrame()
    result["NAME"]       = df[col_map["NAME"]].astype(str).str.strip()
    result["USER_ID"]    = df[col_map["USER ID"]].astype(str).str.strip()
    result["ZENDESK_ID"] = df[col_map["ZENDESK ID"]].astype(str).str.strip()
    result["QA_BRACKET"] = pd.to_numeric(df[col_map["QA BRACKET"]], errors="coerce")
    result["TL"] = df[col_map["TL"]].fillna("Unknown").astype(str).str.strip() if "TL" in col_map else "Unknown"

    result = result.dropna(subset=["QA_BRACKET"])
    result["QA_BRACKET"] = result["QA_BRACKET"].astype(int)
    result = result[result["QA_BRACKET"].isin([1, 2, 3])]

    return result

# --- Core sampling ---

import math

def weekly_quota(monthly_target: int, week_num: int) -> int:
    """
    Spread monthly target evenly across 4 weeks with slight front-load.
    Base = monthly // 4. Remainder goes to W1 first, then W2.

    Examples:
      monthly=2  -> W1=1, W2=1, W3=0, W4=0  (total=2)
      monthly=4  -> W1=1, W2=1, W3=1, W4=1  (total=4)
      monthly=5  -> W1=2, W2=1, W3=1, W4=1  (total=5)
      monthly=6  -> W1=2, W2=2, W3=1, W4=1  (total=6)
      monthly=7  -> W1=2, W2=2, W3=2, W4=1  (total=7)
      monthly=10 -> W1=3, W2=3, W3=2, W4=2  (total=10)
    """
    if monthly_target == 0:
        return 0
    base = monthly_target // 4
    remainder = monthly_target % 4
    # Remainder: W1 gets +1 first, then W2, W3, W4
    bonus = 1 if week_num <= remainder else 0
    return base + bonus


def get_zendesk_frozen_count(agent_key: str, month_str: str, frozen_data: dict) -> int:
    """Return how many Zendesk picks are already frozen for this agent this month."""
    zd = pd.DataFrame(frozen_data.get("zendesk", []))
    if zd.empty or "Month" not in zd.columns or "AGENT_NAME" not in zd.columns:
        return 0
    mask = (zd["Month"] == month_str) & (zd["AGENT_NAME"].astype(str).str.lower() == agent_key)
    return int(mask.sum())


def sample_tab(df: pd.DataFrame, tab: str, month_str: str, week_num: int,
               frozen_data: dict, bracket_df: pd.DataFrame) -> pd.DataFrame:
    """
    Sample new picks for this week.

    Weekly quota = ceil(monthly_target / 4) per week, remainder in week 4.
    Cumulative target up to week N = sum of weekly quotas for weeks 1..N.
    Need = max(0, cumulative_target - already_frozen_this_month).

    Cross-tab compensation (Alerts tab only):
      If agent has fewer Zendesk picks than their Zendesk monthly target,
      the shortfall is added to the Alerts quota for this upload.
      This handles agents who don't work Zendesk at all.
    """
    year  = int(month_str[:4])
    month = int(month_str[5:7])

    id_col     = "ALERT_ID"                if tab == "alerts" else "TICKET_ID"
    agent_col  = "SRC_RESOLVED_BY_AGENT_ID" if tab == "alerts" else "AGENT_NAME"
    lookup_col = "USER_ID"                 if tab == "alerts" else "ZENDESK_ID"

    # ── Build exact lookups from bracketing file ──────────────────────────────
    bracket_lookup = dict(zip(bracket_df[lookup_col].str.lower(), bracket_df["QA_BRACKET"]))
    tl_lookup      = dict(zip(bracket_df[lookup_col].str.lower(), bracket_df["TL"]))
    name_lookup    = dict(zip(bracket_df[lookup_col].str.lower(), bracket_df["NAME"]))

    # ── For Zendesk tab: build fuzzy lookup to handle reversed names ──────────
    # e.g. bracketing has "Pedishetty Lavanya" but Snowflake has "Lavanya Pedishetty"
    if tab == "zendesk":
        # Get all unique agent names from the data
        data_agents = set(df[agent_col].astype(str).str.strip().str.lower().unique())
        # For each bracketing ZENDESK_ID that doesn't exactly match, try fuzzy
        fuzzy_map = {}  # data_agent_key -> bracket_key
        unmatched_data = data_agents - set(bracket_lookup.keys())
        unmatched_bracket = {
            k for k in bracket_lookup.keys()
            if k not in data_agents and k and str(k).lower() != 'nan'
        }

        for data_name in unmatched_data:
            data_tokens = set(str(data_name).split())
            best_key = None
            best_score = 0
            for bk in unmatched_bracket:
                try:
                    bk_tokens = set(str(bk).split())
                except Exception:
                    continue
                if not data_tokens or not bk_tokens:
                    continue
                score = len(data_tokens & bk_tokens) / len(data_tokens | bk_tokens)
                if len(data_tokens) == 2 and data_tokens == bk_tokens:
                    score = 1.0
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_key = bk
            if best_key:
                fuzzy_map[data_name] = best_key

        # Extend lookups with fuzzy matches
        for data_key, bracket_key in fuzzy_map.items():
            if data_key not in bracket_lookup:
                bracket_lookup[data_key] = bracket_lookup[bracket_key]
                tl_lookup[data_key]      = tl_lookup.get(bracket_key, "Unknown")
                name_lookup[data_key]    = name_lookup.get(bracket_key, data_key)

    # Also build a user_id -> zendesk_id map for cross-tab lookup
    uid_to_zid = dict(zip(bracket_df["USER_ID"].str.lower(), bracket_df["ZENDESK_ID"].str.lower()))

    existing = pd.DataFrame(frozen_data.get(tab, []))
    existing_month = pd.DataFrame()
    if not existing.empty and "Month" in existing.columns:
        existing_month = existing[existing["Month"] == month_str]

    frozen_ids = set()
    if not existing_month.empty and id_col in existing_month.columns:
        frozen_ids = set(existing_month[id_col].astype(str))

    all_picks = []

    for agent, agent_df in df.groupby(agent_col):
        agent_key = str(agent).strip().lower()
        bracket = bracket_lookup.get(agent_key)
        if bracket is None or bracket not in BRACKET_TARGETS:
            continue

        tl      = str(tl_lookup.get(agent_key, "") or "Unknown").strip()
        name    = str(name_lookup.get(agent_key, agent) or agent).strip()
        targets = BRACKET_TARGETS[bracket]

        def already_frozen_count(cat, cat_col):
            """Count frozen picks this month for this agent+category."""
            if existing_month.empty or agent_col not in existing_month.columns:
                return 0
            mask = existing_month[agent_col].astype(str).str.lower() == agent_key
            if cat_col and cat_col in existing_month.columns:
                mask = mask & (existing_month[cat_col].str.strip().str.upper() == cat.upper())
            return int(mask.sum())

        def pick_rows(pool_df, n, sample_cat):
            """Pick n rows from pool, excluding already-frozen IDs, stable sorted."""
            if n <= 0 or pool_df.empty:
                return pd.DataFrame()
            pool = pool_df[~pool_df[id_col].astype(str).isin(frozen_ids)].copy()
            if pool.empty:
                return pd.DataFrame()
            pool["RandomNo"] = pool[id_col].apply(
                lambda x: stable_hash(x, year, month, week_num)
            )
            pool = pool.sort_values("RandomNo")
            picks = pool.head(n).copy()
            picks["Month"]          = month_str
            picks["Week"]           = f"Week {week_num}"
            picks["QA_BRACKET"]     = bracket
            picks["TL"]             = tl
            picks["AgentName"]      = name
            picks["FrozenAt"]       = ""
            picks["SampleCategory"] = sample_cat
            return picks

        if tab == "alerts":
            cat_col = "CATEGORY"

            # ── Pools per category ────────────────────────────────────────────
            alert_pool  = agent_df[agent_df[cat_col].str.strip().str.upper() == "ALERTS"].copy() if cat_col in agent_df.columns else agent_df.copy()
            bv_pool     = agent_df[agent_df[cat_col].str.strip().str.upper() == "BV"].copy()      if cat_col in agent_df.columns else pd.DataFrame()
            redeem_pool = agent_df[agent_df[cat_col].str.strip().str.upper() == "REDEEMS"].copy() if cat_col in agent_df.columns else pd.DataFrame()

            def cum_need(cat):
                monthly = targets[cat]
                cum = sum(weekly_quota(monthly, w) for w in range(1, week_num + 1))
                already = already_frozen_count(cat, cat_col)
                return max(0, cum - already)

            # ── Pick each category up to cumulative quota ─────────────────────
            picked_alerts  = pick_rows(alert_pool,  cum_need("Alerts"),  "Alerts")
            picked_bv      = pick_rows(bv_pool,      cum_need("BV"),      "BV")
            picked_redeems = pick_rows(redeem_pool,  cum_need("Redeems"), "Redeems")

            # ── Compensate BV/Redeems shortfall with extra Alerts ─────────────
            bv_shortfall     = cum_need("BV")      - len(picked_bv)
            redeem_shortfall = cum_need("Redeems") - len(picked_redeems)
            total_shortfall  = bv_shortfall + redeem_shortfall

            if total_shortfall > 0:
                already_picked = set(picked_alerts[id_col].astype(str)) if not picked_alerts.empty else set()
                extra_pool = alert_pool[~alert_pool[id_col].astype(str).isin(already_picked | frozen_ids)].copy()
                extra = pick_rows(extra_pool, total_shortfall, "Alerts")
                if not extra.empty:
                    picked_alerts = pd.concat([picked_alerts, extra], ignore_index=True)

            # ── Week 4: compensate Zendesk shortfall with Alerts ──────────────
            if week_num == 4:
                zid_key = uid_to_zid.get(agent_key, agent_key)
                zd_frozen = get_zendesk_frozen_count(zid_key, month_str, frozen_data)
                zd_shortfall = max(0, targets["Zendesk"] - zd_frozen)
                if zd_shortfall > 0:
                    already_picked = set(picked_alerts[id_col].astype(str)) if not picked_alerts.empty else set()
                    extra_pool = alert_pool[~alert_pool[id_col].astype(str).isin(already_picked | frozen_ids)].copy()
                    extra = pick_rows(extra_pool, zd_shortfall, "Alerts")
                    if not extra.empty:
                        picked_alerts = pd.concat([picked_alerts, extra], ignore_index=True)

            # ── Combine and dedup ─────────────────────────────────────────────
            agent_picks = pd.concat([picked_alerts, picked_bv, picked_redeems], ignore_index=True)
            agent_picks = agent_picks.drop_duplicates(subset=[id_col])

            # ── Cap total picks at monthly bracket total ──────────────────────
            # Count already frozen for this agent this month (all categories)
            already_total = 0
            if not existing_month.empty and agent_col in existing_month.columns:
                already_total = int((existing_month[agent_col].astype(str).str.lower() == agent_key).sum())
            monthly_total = targets["Alerts"] + targets["BV"] + targets["Redeems"]
            # Note: Zendesk compensation can push above alerts+bv+redeems but not above grand total
            grand_total = monthly_total + targets["Zendesk"]
            zid_key = uid_to_zid.get(agent_key, agent_key)
            zd_frozen_count = get_zendesk_frozen_count(zid_key, month_str, frozen_data)
            max_alerts_allowed = grand_total - zd_frozen_count - already_total
            if len(agent_picks) > max_alerts_allowed and max_alerts_allowed >= 0:
                agent_picks = agent_picks.head(max_alerts_allowed)

            if not agent_picks.empty:
                all_picks.append(agent_picks)
            continue

        else:
            # Zendesk — weekly quota, no cross-tab compensation
            # Skip entirely for German agents (TL = Williams Nikita Grace Gary)
            agent_tl = str(tl_lookup.get(agent_key, "") or "").strip().lower()
            is_german = agent_tl == "williams nikita grace gary"

            if is_german:
                continue  # skip Zendesk for German agents

            # SQL already filters to Risk groups — no extra group filter needed
            # Only exclude outbound emails
            zd_pool = agent_df.copy()
            if "CHANNEL" in zd_pool.columns:
                zd_pool = zd_pool[
                    ~zd_pool["CHANNEL"].astype(str).str.strip().str.lower()
                    .isin(ZENDESK_EXCLUDED_CHANNELS)
                ]

            monthly_target = targets["Zendesk"]
            cumulative_target = sum(
                weekly_quota(monthly_target, w) for w in range(1, week_num + 1)
            )
            already = already_frozen_count("Zendesk", None)
            need = max(0, cumulative_target - already)
            agent_picks = pick_rows(zd_pool, need, "Zendesk")
            if not agent_picks.empty:
                agent_picks = agent_picks.drop_duplicates(subset=[id_col])
                all_picks.append(agent_picks)

    return pd.concat(all_picks, ignore_index=True) if all_picks else pd.DataFrame()

# --- Frozen section (dashboard view) ---

def render_dashboard(frozen_data: dict, bracket_df: pd.DataFrame | None, month_str: str):
    """Dashboard with improved UI: header, filter bar, metric cards, side-by-side tables."""

    # ── Combine frozen + archive for month slicer ─────────────────────────────
    archive = load_archive()
    alerts_raw  = pd.DataFrame(frozen_data.get("alerts",  []))
    zendesk_raw = pd.DataFrame(frozen_data.get("zendesk", []))

    # Merge archive data so we can see past months too
    arch_alerts  = pd.DataFrame(archive.get("alerts", []))
    arch_zendesk = pd.DataFrame(archive.get("zendesk", []))
    if not arch_alerts.empty:
        alerts_raw = pd.concat([alerts_raw, arch_alerts], ignore_index=True)
        if "ALERT_ID" in alerts_raw.columns and "Month" in alerts_raw.columns and "Week" in alerts_raw.columns:
            alerts_raw = alerts_raw.drop_duplicates(subset=["ALERT_ID", "Month", "Week"])
    if not arch_zendesk.empty:
        zendesk_raw = pd.concat([zendesk_raw, arch_zendesk], ignore_index=True)
        if "TICKET_ID" in zendesk_raw.columns and "Month" in zendesk_raw.columns and "Week" in zendesk_raw.columns:
            zendesk_raw = zendesk_raw.drop_duplicates(subset=["TICKET_ID", "Month", "Week"])

    # ── Month slicer ──────────────────────────────────────────────────────────
    available_months = sorted(set(
        list(alerts_raw["Month"].dropna().unique() if not alerts_raw.empty and "Month" in alerts_raw.columns else []) +
        list(zendesk_raw["Month"].dropna().unique() if not zendesk_raw.empty and "Month" in zendesk_raw.columns else [])
    ), reverse=True)

    # Default to the sidebar month if it exists in data, otherwise first available
    default_idx = 0
    if month_str in available_months:
        default_idx = available_months.index(month_str)

    if available_months:
        selected_dash_month = st.selectbox(
            "📅 Month", available_months, index=default_idx, key="dash_month_slicer"
        )
    else:
        selected_dash_month = month_str

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="qa-header">
      <div>
        <h1>🎲 QA Sampling</h1>
        <p>Fraud Operations &mdash; Monthly QA Review Dashboard</p>
      </div>
      <div class="qa-badge">📅 {selected_dash_month}</div>
    </div>
    """, unsafe_allow_html=True)

    alerts_df  = alerts_raw[alerts_raw["Month"]   == selected_dash_month].copy() if not alerts_raw.empty  and "Month" in alerts_raw.columns  else pd.DataFrame()
    zendesk_df = zendesk_raw[zendesk_raw["Month"] == selected_dash_month].copy() if not zendesk_raw.empty and "Month" in zendesk_raw.columns else pd.DataFrame()

    if alerts_df.empty and zendesk_df.empty:
        st.markdown(f"""
        <div style="background:#f8f9fc;border-radius:12px;padding:40px;text-align:center;border:2px dashed #dde1ec;">
          <div style="font-size:2.5rem;margin-bottom:12px;">📭</div>
          <h3 style="color:{NAVY};margin:0 0 8px;">No picks frozen yet for {selected_dash_month}</h3>
          <p style="color:#888;margin:0;">Use the sidebar to connect to Snowflake and refresh data.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    agent_col_a = "SRC_RESOLVED_BY_AGENT_ID"
    agent_col_z = "AGENT_NAME"

    # ── Name lookups ──────────────────────────────────────────────────────────
    if bracket_df is not None:
        uid_to_name = dict(zip(bracket_df["USER_ID"].str.strip().str.lower(), bracket_df["NAME"].str.strip()))
        zid_to_name = dict(zip(bracket_df["ZENDESK_ID"].str.strip().str.lower(), bracket_df["NAME"].str.strip()))
    else:
        uid_to_name = zid_to_name = {}

    if not alerts_df.empty:
        alerts_df["_DisplayName"] = (alerts_df["AgentName"].astype(str).str.strip()
                                     if "AgentName" in alerts_df.columns
                                     else alerts_df.get(agent_col_a, pd.Series()).astype(str).str.lower().map(uid_to_name).fillna(""))
    if not zendesk_df.empty:
        zendesk_df["_DisplayName"] = (zendesk_df["AgentName"].astype(str).str.strip()
                                      if "AgentName" in zendesk_df.columns
                                      else zendesk_df.get(agent_col_z, pd.Series()).astype(str).str.lower().map(zid_to_name).fillna(""))

    # ── Filter options ────────────────────────────────────────────────────────
    all_tls = sorted(set(
        list(alerts_df["TL"].dropna().unique()  if "TL" in alerts_df.columns  else []) +
        list(zendesk_df["TL"].dropna().unique() if "TL" in zendesk_df.columns else [])
    ))
    all_brackets = sorted(set(
        list(alerts_df["QA_BRACKET"].dropna().astype(int).unique()  if "QA_BRACKET" in alerts_df.columns  else []) +
        list(zendesk_df["QA_BRACKET"].dropna().astype(int).unique() if "QA_BRACKET" in zendesk_df.columns else [])
    ))
    all_weeks = sorted(set(
        list(alerts_df["Week"].dropna().unique()  if "Week" in alerts_df.columns  else []) +
        list(zendesk_df["Week"].dropna().unique() if "Week" in zendesk_df.columns else [])
    ), key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 0)

    # ── Filter row ────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 1.5, 1.5])
    sel_tl      = fc2.selectbox("Team Lead",  ["All"] + all_tls,                        key="dash_tl")
    sel_bracket = fc3.selectbox("QA Bracket", ["All"] + [str(b) for b in all_brackets], key="dash_bracket")
    sel_week    = fc4.selectbox("Week",       ["All"] + all_weeks,                      key="dash_week")

    def cascaded_names():
        a = alerts_df.copy() if not alerts_df.empty else pd.DataFrame()
        z = zendesk_df.copy() if not zendesk_df.empty else pd.DataFrame()
        for df_, col in [(a, "QA_BRACKET"), (z, "QA_BRACKET")]:
            if sel_bracket != "All" and col in df_.columns:
                df_.drop(df_[df_[col].astype(str).str.strip() != str(sel_bracket)].index, inplace=True)
        for df_, col in [(a, "TL"), (z, "TL")]:
            if sel_tl != "All" and col in df_.columns:
                df_.drop(df_[df_[col] != sel_tl].index, inplace=True)
        return sorted(set(
            list(a["_DisplayName"].dropna().unique() if not a.empty and "_DisplayName" in a.columns else []) +
            list(z["_DisplayName"].dropna().unique() if not z.empty and "_DisplayName" in z.columns else [])
        ))

    sel_name = fc1.selectbox("Agent", ["All"] + cascaded_names(), key="dash_agent")

    def apply_filters(df):
        if df.empty: return df
        if sel_name    != "All" and "_DisplayName" in df.columns:
            df = df[df["_DisplayName"] == sel_name]
        if sel_tl      != "All" and "TL"          in df.columns:
            df = df[df["TL"] == sel_tl]
        if sel_bracket != "All" and "QA_BRACKET"  in df.columns:
            df = df[df["QA_BRACKET"].astype(str).str.strip() == str(sel_bracket)]
        if sel_week    != "All" and "Week"         in df.columns:
            df = df[df["Week"] == sel_week]
        return df

    alerts_f  = apply_filters(alerts_df.copy())
    zendesk_f = apply_filters(zendesk_df.copy())

    # ── Metric cards ──────────────────────────────────────────────────────────
    total = len(alerts_f) + len(zendesk_f)
    agents_shown = len(set(
        list(alerts_f["_DisplayName"].dropna().unique()  if "_DisplayName" in alerts_f.columns  else []) +
        list(zendesk_f["_DisplayName"].dropna().unique() if "_DisplayName" in zendesk_f.columns else [])
    ))

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="val">{len(alerts_f):,}</div>
        <div class="lbl">Alert Picks</div>
      </div>
      <div class="metric-card green">
        <div class="val">{len(zendesk_f):,}</div>
        <div class="lbl">Zendesk Picks</div>
      </div>
      <div class="metric-card blue">
        <div class="val">{total:,}</div>
        <div class="lbl">Total Picks</div>
      </div>
      <div class="metric-card amber">
        <div class="val">{agents_shown}</div>
        <div class="lbl">Agents</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Side-by-side tables ───────────────────────────────────────────────────
    col_a, col_z = st.columns(2)

    with col_a:
        st.markdown(f"""
        <div class="section-header">
          <div class="icon alert">🔔</div>
          <h3>Alerts</h3>
          <span>{len(alerts_f)} rows</span>
        </div>
        """, unsafe_allow_html=True)
        if alerts_f.empty:
            st.markdown("""
            <div style="background:#f8f9fc;border-radius:10px;padding:24px;text-align:center;color:#888;">
              No alert picks match the selected filters.
            </div>
            """, unsafe_allow_html=True)
        else:
            show_a = [c for c in [
                "ALERT_ID", "LOGIN_NAME_TXT", "SRC_RESOLVED_BY_AGENT_ID",
                "TL", "UPDATE_DATE", "ALERT_TYPE_DESC", "SampleCategory",
                "ACC_CATEGORY", "SRC_ALERT_RESOLUTION_CD", "Week"
            ] if c in alerts_f.columns]
            rename_a = {"SampleCategory": "Category", "SRC_RESOLVED_BY_AGENT_ID": "Agent ID",
                        "LOGIN_NAME_TXT": "Player", "ALERT_TYPE_DESC": "Alert Type",
                        "ACC_CATEGORY": "Acc Category", "SRC_ALERT_RESOLUTION_CD": "Resolution",
                        "UPDATE_DATE": "Date"}
            st.dataframe(alerts_f[show_a].rename(columns=rename_a),
                         use_container_width=True, hide_index=True, height=460)
            st.download_button("⬇ Download Alerts CSV",
                               alerts_f.to_csv(index=False).encode("utf-8"),
                               f"alerts_{month_str}.csv", "text/csv", key="dl_a")

    with col_z:
        st.markdown(f"""
        <div class="section-header">
          <div class="icon zendesk">🎫</div>
          <h3>Zendesk</h3>
          <span>{len(zendesk_f)} rows</span>
        </div>
        """, unsafe_allow_html=True)
        if zendesk_f.empty:
            st.markdown("""
            <div style="background:#f8f9fc;border-radius:10px;padding:24px;text-align:center;color:#888;">
              No Zendesk picks match the selected filters.
            </div>
            """, unsafe_allow_html=True)
        else:
            show_z = [c for c in [
                "AGENT_NAME", "AgentName", "TICKET_ID", "UPDATE_DATE",
                "TL", "QA_BRACKET", "CHANNEL", "CATEGORY_FULL_PATH", "Week"
            ] if c in zendesk_f.columns]
            rename_z = {"QA_BRACKET": "Bracket", "AgentName": "Agent Name",
                        "AGENT_NAME": "Agent ID", "TICKET_ID": "Ticket ID",
                        "UPDATE_DATE": "Date", "CATEGORY_FULL_PATH": "Category",
                        "CHANNEL": "Channel"}
            st.dataframe(zendesk_f[show_z].rename(columns=rename_z),
                         use_container_width=True, hide_index=True, height=460)
            st.download_button("⬇ Download Zendesk CSV",
                               zendesk_f.to_csv(index=False).encode("utf-8"),
                               f"zendesk_{month_str}.csv", "text/csv", key="dl_z")

    # ── Combined download ─────────────────────────────────────────────────────
    if not alerts_f.empty or not zendesk_f.empty:
        st.markdown("---")
        combined_parts = []
        if not alerts_f.empty:
            a_exp = alerts_f.copy()
            a_exp["Source"] = "Alerts"
            a_exp = a_exp.rename(columns={
                "SRC_RESOLVED_BY_AGENT_ID": "Agent_ID", "AgentName": "Agent_Name",
                "SampleCategory": "Category", "ALERT_ID": "ID", "ALERT_TYPE_DESC": "Type_Desc"
            })
            cols = [c for c in ["Agent_ID","Agent_Name","TL","QA_BRACKET","Week","Month","ID","UPDATE_DATE","Type_Desc","Category","Source"] if c in a_exp.columns]
            combined_parts.append(a_exp[cols])
        if not zendesk_f.empty:
            z_exp = zendesk_f.copy()
            z_exp["Source"] = "Zendesk"
            z_exp = z_exp.rename(columns={
                "AGENT_NAME": "Agent_ID", "AgentName": "Agent_Name",
                "TICKET_ID": "ID", "CATEGORY_FULL_PATH": "Type_Desc", "CHANNEL": "Category"
            })
            cols = [c for c in ["Agent_ID","Agent_Name","TL","QA_BRACKET","Week","Month","ID","UPDATE_DATE","Type_Desc","Category","Source"] if c in z_exp.columns]
            combined_parts.append(z_exp[cols])
        if combined_parts:
            combined = pd.concat(combined_parts, ignore_index=True)
            st.download_button(
                "⬇ Download Combined CSV (Alerts + Zendesk)",
                combined.to_csv(index=False).encode("utf-8"),
                f"qa_combined_{month_str}.csv", "text/csv", key="dl_combined"
            )


# --- Tab renderer ---

def render_tab(tab: str, required_cols: list, id_col: str, agent_col: str,
               bracket_df: pd.DataFrame | None):
    label = "Alerts" if tab == "alerts" else "Zendesk"
    st.header(f"{label} - Weekly Upload")

    if bracket_df is None:
        st.warning("Please upload the Bracketing file in the sidebar first.")
        return

    st.markdown("**Load your CSV** — paste the full file path below (avoids corporate upload restrictions):")
    file_path = st.text_input(
        "Full path to CSV file (e.g. C:\\Users\\you\\Downloads\\alerts.csv)",
        key=f"{tab}_path",
        placeholder=r"C:\Users\S.Mallampalli\Downloads\alerts_week1.csv"
    )

    # Also keep file uploader as fallback
    with st.expander("Or upload directly (may be blocked by Purview)"):
        uploaded = st.file_uploader(f"Upload {label} CSV", type=["csv"], key=f"{tab}_up")

    raw_df = None

    # Try path first
    if file_path and file_path.strip():
        fp = file_path.strip().strip('"').strip("'")
        if not Path(fp).exists():
            st.error(f"File not found: {fp}")
            return
        try:
            ext = Path(fp).suffix.lower()
            if ext in (".xlsx", ".xls"):
                raw_df = pd.read_excel(fp)
            else:
                try:
                    raw_df = pd.read_csv(fp, encoding="utf-8")
                except UnicodeDecodeError:
                    raw_df = pd.read_csv(fp, encoding="cp1252")
            st.success(f"Loaded {len(raw_df):,} rows from {Path(fp).name}")
        except PermissionError:
            st.error("Permission denied — the file may be open in Excel. Close it and try again, or save a copy to C:\\Temp\\")
            return
        except Exception as e:
            st.error(f"Could not read file: {e}")
            return
    elif uploaded is not None:
        try:
            try:
                raw_df = pd.read_csv(uploaded, encoding="utf-8")
            except UnicodeDecodeError:
                uploaded.seek(0)
                raw_df = pd.read_csv(uploaded, encoding="cp1252")
        except Exception as e:
            st.error(f"Could not parse CSV: {e}")
            return

    if raw_df is None:
        st.info("Paste a file path above to load your data.")
        return

    if raw_df.empty:
        st.info("Uploaded file is empty.")
        return

    df = norm_cols(raw_df)
    miss = missing_cols(df, required_cols)
    if miss:
        st.error(f"Missing columns in uploaded CSV: {miss}. Found: {list(df.columns)}")
        return

    # Apply transformations for alerts tab
    if tab == "alerts":
        raw_count = len(df)
        df = transform_alerts(df, bracket_df)
        filtered_count = len(df)
        excluded = raw_count - filtered_count
        if df.empty:
            st.error("No PROACTIVE alerts found after filtering. Check your ALERT_TYPE_DESC values.")
            return
        # Show transformation summary
        cat_counts = df["CATEGORY"].value_counts().to_dict()
        st.info(
            f"Transformed: {raw_count} raw rows → {filtered_count} PROACTIVE rows "
            f"({excluded} excluded) | "
            + " | ".join(f"{k}: {v}" for k, v in sorted(cat_counts.items()))
        )

    # Detect week
    week_num = detect_majority_week(df, "UPDATE_DATE")
    all_weeks = set(day_to_week(parse_date(v).day) for v in df["UPDATE_DATE"] if parse_date(v))
    if len(all_weeks) > 1:
        st.warning(f"Data spans weeks {sorted(all_weeks)}. Using majority: Week {week_num}.")

    # Match agents to bracket
    lookup_col = "USER_ID" if tab == "alerts" else "ZENDESK_ID"
    bracket_lookup = dict(zip(bracket_df[lookup_col].str.lower(), bracket_df["QA_BRACKET"]))
    agents_in_data = df[agent_col].astype(str).str.lower().unique()
    matched   = [a for a in agents_in_data if a in bracket_lookup]
    unmatched = [a for a in agents_in_data if a not in bracket_lookup]

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows uploaded", len(df))
    col2.metric("Agents matched to bracket", len(matched))
    col3.metric("Week detected", f"Week {week_num}")

    if unmatched:
        with st.expander(f"{len(unmatched)} agents not found in bracketing file (will be skipped)"):
            st.write(unmatched)

    # Check if already frozen
    existing = pd.DataFrame(st.session_state.frozen_data.get(tab, []))
    already_frozen_week = False
    if not existing.empty and "Month" in existing.columns and "Week" in existing.columns:
        already_frozen_week = bool(
            ((existing["Month"] == selected_month) & (existing["Week"] == f"Week {week_num}")).any()
        )
    if already_frozen_week:
        st.warning(f"Week {week_num} picks for {selected_month} are already frozen.")

    # Preview button
    if st.button("Preview Sample", key=f"{tab}_prev_btn"):
        with st.spinner("Sampling..."):
            preview = sample_tab(df, tab, selected_month, week_num,
                                 st.session_state.frozen_data, bracket_df)
        st.session_state[f"{tab}_preview"] = preview
        st.session_state[f"{tab}_week_num"] = week_num

    # Show preview
    if f"{tab}_preview" in st.session_state and st.session_state[f"{tab}_preview"] is not None:
        preview = st.session_state[f"{tab}_preview"]

        if preview.empty:
            st.success("Monthly quota already met for all agents - no new picks needed.")
        else:
            st.subheader(f"Preview - {len(preview)} proposed picks for Week {week_num}")

            # Per-agent summary table
            existing_month = existing[existing["Month"] == selected_month] if not existing.empty and "Month" in existing.columns else pd.DataFrame()
            summary = []
            for agent, grp in preview.groupby(agent_col):
                bracket = grp["QA_BRACKET"].iloc[0]
                tl      = grp["TL"].iloc[0] if "TL" in grp.columns else ""
                already = int((existing_month[agent_col] == agent).sum()) if not existing_month.empty and agent_col in existing_month.columns else 0
                new_p   = len(grp)
                summary.append({
                    "Agent (ID)": agent,
                    "Agent Name": grp["AgentName"].iloc[0] if "AgentName" in grp.columns else "",
                    "TL": tl,
                    "Bracket": bracket,
                    "Already Frozen": already,
                    "New Picks": new_p,
                    "Total After": already + new_p,
                })
            st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

            with st.expander("View full pick details"):
                st.dataframe(preview, use_container_width=True, hide_index=True)

            if not already_frozen_week:
                if st.button(f"Freeze These {len(preview)} Picks", key=f"{tab}_freeze", type="primary"):
                    now = datetime.now().isoformat(timespec="seconds")
                    preview_copy = preview.copy()
                    preview_copy["FrozenAt"] = now
                    st.session_state.frozen_data[tab].extend(preview_copy.to_dict(orient="records"))
                    save_frozen(st.session_state.frozen_data)
                    st.success(f"Frozen {len(preview_copy)} picks for {selected_month} Week {week_num}! Go to the Dashboard tab to view.")
                    st.session_state[f"{tab}_preview"] = None
                    st.rerun()
            else:
                st.info("This week is already frozen. Clear month data to re-freeze.")


# --- Sidebar ---

with st.sidebar:
    st.title("QA Randomizer")
    st.caption("Fraud Ops - Weekly QA Sampling")
    st.divider()

    # Month selector
    today = date.today()
    selected_month = st.text_input("Month (YYYY-MM)", value=today.strftime("%Y-%m"))
    try:
        datetime.strptime(selected_month, "%Y-%m")
        month_valid = True
    except ValueError:
        st.error("Use format YYYY-MM")
        month_valid = False

    st.divider()

    # Bracketing file upload
    st.subheader("Bracketing File")
    st.caption("Paste file path OR upload Excel/CSV with: Name, User ID, Zendesk ID, TL, QA Bracket")

    bracket_path = st.text_input(
        "Bracketing file path",
        key="bracket_path",
        placeholder=r"C:\Users\S.Mallampalli\Downloads\bracketing.xlsx"
    )
    with st.expander("Or upload bracketing file"):
        bracket_file = st.file_uploader("Upload Bracketing File", type=["xlsx", "xls", "csv"], key="bracket_up")

    # Load from path or upload
    bracket_source = None
    if bracket_path and bracket_path.strip():
        bp = bracket_path.strip().strip('"').strip("'")
        if Path(bp).exists():
            bracket_source = bp  # pass path string
        else:
            st.error(f"File not found: {bp}")
    elif bracket_file is not None:
        bracket_source = bracket_file  # pass file object

    if bracket_source is not None:
        bracket_df_loaded = load_bracketing(bracket_source)
        if bracket_df_loaded is not None:
            st.session_state["bracket_df"] = bracket_df_loaded
            st.success(f"{len(bracket_df_loaded)} agents loaded")
            tl_count = bracket_df_loaded["TL"].nunique()
            st.caption(f"Brackets: {dict(bracket_df_loaded['QA_BRACKET'].value_counts().sort_index())} | TLs: {tl_count}")
    elif "bracket_df" not in st.session_state:
        st.info("No bracketing file loaded yet.")

    bracket_df = st.session_state.get("bracket_df", None)

    st.divider()

    # Frozen counts
    if "frozen_data" not in st.session_state:
        st.session_state.frozen_data = load_frozen()

    if month_valid:
        fd = st.session_state.frozen_data
        a_df = pd.DataFrame(fd.get("alerts", []))
        z_df = pd.DataFrame(fd.get("zendesk", []))
        a_cnt = len(a_df[a_df["Month"] == selected_month]) if not a_df.empty and "Month" in a_df.columns else 0
        z_cnt = len(z_df[z_df["Month"] == selected_month]) if not z_df.empty and "Month" in z_df.columns else 0
        st.metric("Frozen Alert Picks", a_cnt)
        st.metric("Frozen Zendesk Picks", z_cnt)

    st.divider()

    # ── Snowflake Auto-Refresh ────────────────────────────────────────────────
    st.subheader("Snowflake Auto-Refresh")

    # Allow overriding the pull month (default = selected_month from sidebar)
    pull_month = st.text_input(
        "Pull data for month (YYYY-MM)",
        value=selected_month,
        key="sf_pull_month",
        help="Change this to pull a different month e.g. 2026-03 for March"
    )
    # For past months, pull the full month (all 4 weeks)
    try:
        pull_dt = datetime.strptime(pull_month, "%Y-%m")
        pull_month_valid = True
    except ValueError:
        st.error("Invalid month format")
        pull_month_valid = False

    if pull_month_valid:
        pull_is_current = (pull_month == date.today().strftime("%Y-%m"))
        if pull_is_current:
            pull_week = (1 if date.today().day <= 7 else 2 if date.today().day <= 14
                         else 3 if date.today().day <= 21 else 4)
            st.caption(f"Current month — will pull weeks 1-{pull_week}")
        else:
            pull_week = 4  # past month — pull all 4 weeks
            st.caption(f"Past month — will pull all 4 weeks")

    if st.button("Connect & Refresh from Snowflake", key="sf_refresh"):
        if bracket_df is None:
            st.error("Load the bracketing file first before connecting to Snowflake.")
        elif not pull_month_valid:
            st.error("Fix the month format above.")
        else:
            try:
                import snowflake.connector
                from snowflake_queries import get_alerts_query, get_zendesk_query

                pull_dt = datetime.strptime(pull_month, "%Y-%m")
                month_start = pull_dt.replace(day=1).strftime("%Y-%m-%d")
                month_str   = pull_month
                current_week = pull_week

                with st.spinner(f"Connecting to Snowflake... (browser login may open)"):
                    # Support both SSO (local) and password (Streamlit Cloud)
                    sf_secrets = st.secrets["snowflake"]
                    conn_params = {
                        "account":   sf_secrets["account"],
                        "user":      sf_secrets["user"],
                        "warehouse": sf_secrets["warehouse"],
                        "role":      sf_secrets.get("role", ""),
                        "database":  "EDLDIGITALVIEWS",
                        "schema":    "EDLDIGITALVIEWSBI",
                    }
                    # Use password auth if provided, otherwise SSO
                    if "password" in sf_secrets and sf_secrets["password"]:
                        conn_params["password"] = sf_secrets["password"]
                    else:
                        conn_params["authenticator"] = sf_secrets.get("authenticator", "externalbrowser")

                    conn = snowflake.connector.connect(**conn_params)

                # For past months use last day of that month; for current use CURRENT_DATE-2
                import calendar
                if pull_is_current:
                    month_end_param = None  # uses CURRENT_DATE - 2
                else:
                    last_day = calendar.monthrange(pull_dt.year, pull_dt.month)[1]
                    month_end_param = f"{pull_dt.year}-{pull_dt.month:02d}-{last_day}"

                # ── Pull Alerts (with account category) ──────────────────────
                user_ids = bracket_df["USER_ID"].dropna().str.strip().tolist()
                alerts_sql = get_alerts_query(month_start, user_ids, month_end_param)

                with st.spinner(f"Pulling alerts data (weeks 1-{current_week})..."):
                    alerts_raw = pd.read_sql(alerts_sql, conn)
                    alerts_raw.columns = [c.upper() for c in alerts_raw.columns]

                # ── Pull Pending/Resolved/Denied Redeems ─────────────────────
                from snowflake_queries import get_pending_redeems_query
                redeems_sql = get_pending_redeems_query(month_start, user_ids, month_end_param)

                with st.spinner("Pulling pending/resolved redeems..."):
                    redeems_raw = pd.read_sql(redeems_sql, conn)
                    redeems_raw.columns = [c.upper() for c in redeems_raw.columns]
                    # Tag these as Redeems category and merge into alerts pool
                    if not redeems_raw.empty:
                        redeems_raw["ALERT_TYPE_DESC"] = redeems_raw.get("ALERT_TYPE_DESC", "redeemvrfn")
                        # Align columns with alerts_raw
                        for col in alerts_raw.columns:
                            if col not in redeems_raw.columns:
                                redeems_raw[col] = None
                        redeems_raw = redeems_raw[[c for c in alerts_raw.columns if c in redeems_raw.columns]]
                        alerts_raw = pd.concat([alerts_raw, redeems_raw], ignore_index=True)
                        alerts_raw = alerts_raw.drop_duplicates(subset=["ALERT_ID"])
                        st.info(f"Added {len(redeems_raw)} pending/resolved redeem rows to alerts pool")

                # Apply transformations
                alerts_transformed = transform_alerts(alerts_raw, bracket_df)

                # ── Pull Zendesk ──────────────────────────────────────────────
                zd_ids   = bracket_df["ZENDESK_ID"].dropna().str.strip().tolist()
                zd_names = bracket_df["NAME"].dropna().str.strip().tolist()
                zendesk_sql = get_zendesk_query(month_start, zd_ids, month_end_param, zd_names)

                with st.spinner("Pulling Zendesk data..."):
                    zendesk_raw = pd.read_sql(zendesk_sql, conn)
                    zendesk_raw.columns = [c.upper() for c in zendesk_raw.columns]

                conn.close()

                st.success(f"Pulled {len(alerts_transformed):,} alert rows and {len(zendesk_raw):,} Zendesk rows")

                # ── Sample and freeze each week up to current_week ────────────
                frozen = st.session_state.frozen_data
                alerts_frozen_new = 0
                zendesk_frozen_new = 0
                debug_msgs = []

                for wk in range(1, current_week + 1):
                    # Check if already frozen
                    ex_a = pd.DataFrame(frozen.get("alerts", []))
                    already_a = (not ex_a.empty and "Month" in ex_a.columns and "Week" in ex_a.columns
                                 and ((ex_a["Month"] == month_str) & (ex_a["Week"] == f"Week {wk}")).any())

                    if not already_a:
                        wk_start = 1 + (wk-1)*7
                        wk_end   = wk*7 if wk < 4 else 31

                        wk_df = alerts_transformed.copy()
                        # Robust date parsing — handle Snowflake timestamps
                        try:
                            wk_df["_day"] = pd.to_datetime(wk_df["UPDATE_DATE"], errors="coerce").dt.day
                        except Exception:
                            wk_df["_day"] = wk_df["UPDATE_DATE"].apply(
                                lambda v: parse_date(v).day if parse_date(v) else None
                            )
                        wk_df = wk_df[
                            (wk_df["_day"] >= wk_start) & (wk_df["_day"] <= wk_end)
                        ].drop(columns=["_day"])

                        debug_msgs.append(f"Week {wk} alerts: {len(wk_df)} rows in date range (days {wk_start}-{wk_end})")

                        if not wk_df.empty:
                            picks = sample_tab(wk_df, "alerts", month_str, wk, frozen, bracket_df)
                            debug_msgs.append(f"  → sampled {len(picks)} picks")
                            if not picks.empty:
                                picks["FrozenAt"] = datetime.now().isoformat(timespec="seconds")
                                frozen["alerts"].extend(picks.to_dict(orient="records"))
                                alerts_frozen_new += len(picks)
                                # Show per-agent week breakdown
                                for ag, grp in picks.groupby("SRC_RESOLVED_BY_AGENT_ID") if "SRC_RESOLVED_BY_AGENT_ID" in picks.columns else []:
                                    debug_msgs.append(f"    {ag}: {len(grp)} picks")
                        else:
                            debug_msgs.append(f"  → no rows in week range, skipped")
                    else:
                        debug_msgs.append(f"Week {wk} alerts: already frozen, skipped")

                    ex_z = pd.DataFrame(frozen.get("zendesk", []))
                    already_z = (not ex_z.empty and "Month" in ex_z.columns and "Week" in ex_z.columns
                                 and ((ex_z["Month"] == month_str) & (ex_z["Week"] == f"Week {wk}")).any())

                    if not already_z:
                        wk_start = 1 + (wk-1)*7
                        wk_end   = wk*7 if wk < 4 else 31
                        wk_zdf = zendesk_raw.copy()
                        try:
                            wk_zdf["_day"] = pd.to_datetime(wk_zdf["UPDATE_DATE"], errors="coerce").dt.day
                        except Exception:
                            wk_zdf["_day"] = wk_zdf["UPDATE_DATE"].apply(
                                lambda v: parse_date(v).day if parse_date(v) else None
                            )
                        wk_zdf = wk_zdf[
                            (wk_zdf["_day"] >= wk_start) & (wk_zdf["_day"] <= wk_end)
                        ].drop(columns=["_day"])

                        if not wk_zdf.empty:
                            picks_z = sample_tab(wk_zdf, "zendesk", month_str, wk, frozen, bracket_df)
                            if not picks_z.empty:
                                picks_z["FrozenAt"] = datetime.now().isoformat(timespec="seconds")
                                frozen["zendesk"].extend(picks_z.to_dict(orient="records"))
                                zendesk_frozen_new += len(picks_z)
                    else:
                        debug_msgs.append(f"Week {wk} zendesk: already frozen, skipped")

                save_frozen(frozen)
                st.session_state.frozen_data = frozen
                st.success(f"Done! Frozen {alerts_frozen_new} alert picks + {zendesk_frozen_new} Zendesk picks for weeks 1-{current_week} of {month_str}")
                with st.expander("Debug log"):
                    for m in debug_msgs:
                        st.text(m)
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
                import traceback
                st.code(traceback.format_exc())

    st.divider()

    # Clear month
    st.subheader("Clear Month Data")
    if st.button("Clear Month", key="clear_btn"):
        st.session_state["confirm_clear"] = True

    if st.session_state.get("confirm_clear"):
        st.warning(f"Delete ALL frozen picks for {selected_month}?")
        c1, c2 = st.columns(2)
        if c1.button("Yes", key="yes_clear"):
            fd = st.session_state.frozen_data
            fd["alerts"]  = [r for r in fd["alerts"]  if r.get("Month") != selected_month]
            fd["zendesk"] = [r for r in fd["zendesk"] if r.get("Month") != selected_month]
            save_frozen(fd)
            st.session_state.frozen_data = fd
            st.session_state["confirm_clear"] = False
            st.rerun()
        if c2.button("No", key="no_clear"):
            st.session_state["confirm_clear"] = False
            st.rerun()

# --- Main tabs ---

st.title("QA Alert Randomizer")
st.caption(f"Month: **{selected_month}** | Bracketing: {'Loaded' if bracket_df is not None else 'Not loaded'}")

tab_dash, tab_history = st.tabs(["Dashboard", "📜 History (All Months)"])

with tab_dash:
    if month_valid:
        render_dashboard(st.session_state.frozen_data, bracket_df, selected_month)
    else:
        st.error("Fix month format in sidebar.")

with tab_history:
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1a2744 0%, #2a4080 100%);
                border-radius:14px;padding:24px 32px;margin-bottom:20px;">
      <h2 style="color:#fff;margin:0;">📜 Frozen Picks Archive</h2>
      <p style="color:rgba(255,255,255,0.65);margin:4px 0 0;font-size:0.85rem;">
        All frozen alerts across all months — persists even after clearing monthly data.
      </p>
    </div>
    """, unsafe_allow_html=True)

    archive = load_archive()
    arch_alerts  = pd.DataFrame(archive.get("alerts", []))
    arch_zendesk = pd.DataFrame(archive.get("zendesk", []))

    if arch_alerts.empty and arch_zendesk.empty:
        st.info("No archived picks yet. Picks are archived automatically when you freeze them.")
    else:
        # Month selector for history
        all_months = sorted(set(
            list(arch_alerts["Month"].dropna().unique() if not arch_alerts.empty and "Month" in arch_alerts.columns else []) +
            list(arch_zendesk["Month"].dropna().unique() if not arch_zendesk.empty and "Month" in arch_zendesk.columns else [])
        ), reverse=True)

        hist_month = st.selectbox("Select Month", ["All Months"] + all_months, key="hist_month")

        # Filter by selected month
        if hist_month != "All Months":
            if not arch_alerts.empty and "Month" in arch_alerts.columns:
                arch_alerts = arch_alerts[arch_alerts["Month"] == hist_month]
            else:
                arch_alerts = pd.DataFrame()
            if not arch_zendesk.empty and "Month" in arch_zendesk.columns:
                arch_zendesk = arch_zendesk[arch_zendesk["Month"] == hist_month]
            else:
                arch_zendesk = pd.DataFrame()

        # Metrics
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Alert Picks", len(arch_alerts))
        mc2.metric("Zendesk Picks", len(arch_zendesk))
        mc3.metric("Total", len(arch_alerts) + len(arch_zendesk))
        mc4.metric("Months", len(all_months))

        # Tables
        col_a, col_z = st.columns(2)
        with col_a:
            st.subheader("Alerts")
            if not arch_alerts.empty:
                display_cols_a = [c for c in ["Month", "Week", "AgentName", "TL", "QA_BRACKET",
                                              "ALERT_ID", "ALERT_TYPE_DESC", "SampleCategory",
                                              "UPDATE_DATE", "FrozenAt"] if c in arch_alerts.columns]
                st.dataframe(arch_alerts[display_cols_a] if display_cols_a else arch_alerts,
                             use_container_width=True, height=400)
            else:
                st.caption("No alert picks for this selection.")

        with col_z:
            st.subheader("Zendesk")
            if not arch_zendesk.empty:
                display_cols_z = [c for c in ["Month", "Week", "AgentName", "TL", "QA_BRACKET",
                                              "TICKET_ID", "UPDATE_DATE", "FrozenAt"] if c in arch_zendesk.columns]
                st.dataframe(arch_zendesk[display_cols_z] if display_cols_z else arch_zendesk,
                             use_container_width=True, height=400)
            else:
                st.caption("No Zendesk picks for this selection.")

        # Download archive
        st.divider()
        dl1, dl2 = st.columns(2)
        with dl1:
            if not arch_alerts.empty:
                st.download_button(
                    "⬇️ Download Alerts Archive (CSV)",
                    arch_alerts.to_csv(index=False).encode("utf-8"),
                    f"qa_alerts_archive_{hist_month}.csv",
                    "text/csv",
                    key="dl_arch_alerts"
                )
        with dl2:
            if not arch_zendesk.empty:
                st.download_button(
                    "⬇️ Download Zendesk Archive (CSV)",
                    arch_zendesk.to_csv(index=False).encode("utf-8"),
                    f"qa_zendesk_archive_{hist_month}.csv",
                    "text/csv",
                    key="dl_arch_zendesk"
                )