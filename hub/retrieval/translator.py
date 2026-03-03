"""
Server-side translation using Facebook NLLB-200-distilled-600M.
Loaded from local hub_models/nllb/ directory — fully offline.
"""

import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_tokenizer = None
_model = None

# NLLB BCP-47 language code mapping (ISO 639-1 -> NLLB)
LANG_CODES = {
    "en":  "eng_Latn",
    "es":  "spa_Latn",
    "tl":  "tgl_Latn",  # Filipino/Tagalog
    "fr":  "fra_Latn",
    "zh":  "zho_Hans",  # Simplified Chinese
    "ar":  "arb_Arab",
    "vi":  "vie_Latn",
    "hi":  "hin_Deva",
    "ko":  "kor_Hang",
    "ja":  "jpn_Jpan",
    "pt":  "por_Latn",
    "id":  "ind_Latn",
    "ms":  "zsm_Latn",  # Malay
    "th":  "tha_Thai",
    "de":  "deu_Latn",
    "ru":  "rus_Cyrl",
}

def get_nllb_model_path() -> str:
    path = os.environ.get("RESKIOSK_NLLB_PATH")
    if not path:
        path = os.path.join("packaging", "hub_models", "nllb")
    return path


def _load_model() -> Tuple[Optional["AutoModelForSeq2SeqLM"], Optional["NllbTokenizer"]]:
    """
    Lazy-load NLLB model and tokenizer once.

    We avoid the generic transformers.pipeline(\"translation\") here because
    NLLB-200 expects a task name like \"translation_XX_to_YY\". Instead we load
    the model/tokenizer directly and control src/tgt via language codes.
    """
    global _model, _tokenizer
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer

    from transformers import AutoModelForSeq2SeqLM, NllbTokenizer

    model_path = get_nllb_model_path()
    if not os.path.exists(model_path):
        logger.warning(f"NLLB model not found at {model_path}. Translation unavailable.")
        return None, None

    logger.info(f"Loading NLLB-200 from {model_path}...")
    try:
        # Some transformers versions have incomplete AutoTokenizer mappings for
        # m2m_100 / NLLB, which can surface as a NoneType.replace error. Use the
        # concrete NllbTokenizer class directly to avoid that path.
        _tokenizer = NllbTokenizer.from_pretrained(model_path, local_files_only=True)
        _model = AutoModelForSeq2SeqLM.from_pretrained(model_path, local_files_only=True)
        _model.eval()
        logger.info("NLLB-200 loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load NLLB model: {e}")
        _model = None
        _tokenizer = None

    return _model, _tokenizer


def translate(text: str, src_lang: str, tgt_lang: str, max_length: int = 512) -> str:
    """
    Translate text from src_lang to tgt_lang.
    Language codes are ISO 639-1 (e.g. 'en', 'es', 'tl').
    Returns original text if translation fails or languages match.
    """
    if not text or src_lang == tgt_lang:
        return text

    src_nllb = LANG_CODES.get(src_lang)
    tgt_nllb = LANG_CODES.get(tgt_lang)

    if not src_nllb or not tgt_nllb:
        logger.warning(f"Unsupported language pair: {src_lang} -> {tgt_lang}. Returning original.")
        return text

    model, tokenizer = _load_model()
    if model is None or tokenizer is None:
        return text

    try:
        # Configure source and target languages explicitly for NLLB-200
        tokenizer.src_lang = src_nllb
        inputs = tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt_nllb)
        generated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=forced_bos_token_id,
            max_new_tokens=max_length,
        )
        translated = tokenizer.batch_decode(
            generated_tokens, skip_special_tokens=True
        )[0].strip()
        if not translated:
            return text
        logger.info(
            f"Translated ({src_lang}->{tgt_lang}): '{text[:50]}...' -> '{translated[:50]}...'"
        )
        return translated
    except Exception as e:
        logger.error(f"Translation error ({src_lang}->{tgt_lang}): {e}")
        return text


def is_supported_language(lang_code: str) -> bool:
    return lang_code in LANG_CODES
