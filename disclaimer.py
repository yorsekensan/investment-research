import streamlit as st

DISCLAIMER_TEXT = (
    "This page shows the output of a personal, rules-based technical/quantitative model "
    "(moving averages, RSI, Bollinger %B, MACD, and related indicators). It is **not financial "
    "advice, not a research recommendation, and not a solicitation** to buy, sell, or hold any "
    "asset. It reflects one individual's personal, non-commercial research process only, and is "
    "not issued by a licensed investment advisor or research analyst. Markets involve real risk "
    "of loss; indicator signals and historical patterns do not guarantee future results. Do your "
    "own research and consult a licensed financial advisor before making any investment decision."
)


def render_disclaimer():
    st.info(f"⚠️ **Disclaimer:** {DISCLAIMER_TEXT}")
