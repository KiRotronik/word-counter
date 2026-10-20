import streamlit as st
import pandas as pd
import re
import pymorphy3
import snowballstemmer
import os
import json

morph = pymorphy3.MorphAnalyzer()
stemmer = snowballstemmer.stemmer('russian')

HISTORY_FILE = "history.csv"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE)
            # Преобразуем строки JSON обратно в словари/списки
            df['results'] = df['results'].apply(lambda x: json.loads(x) if pd.notna(x) else [])
            df['keywords'] = df['keywords'].apply(lambda x: x.split(', ') if pd.notna(x) else [])
            return df.to_dict('records')
        except Exception as e:
            st.error(f"Ошибка загрузки истории: {e}")
            return []
    return []

def save_history(history_list):
    if not history_list:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        return
    
    df = pd.DataFrame(history_list)
    # Преобразуем список результатов в JSON-строку для сохранения в CSV
    df['results'] = df['results'].apply(lambda x: json.dumps(x, ensure_ascii=False))
    df['keywords'] = df['keywords'].apply(lambda x: ', '.join(x))
    df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')

def get_stem(word):
    p = morph.parse(word)[0]
    return stemmer.stemWord(p.normal_form)

def highlight_rows(row):
    val = row['Вхождения']
    if val == 0:
        return ['background-color: #ffcccc; color: black;'] * len(row)
    elif val > 1:
        return ['background-color: #fff4cc; color: black;'] * len(row)
    else:
        return [''] * len(row)

# Функция для отрисовки результатов (чтобы использовать и при анализе, и в истории)
def render_results(df, text_input=""):
    if text_input:
        st.info(f"**Фрагмент текста:** {text_input[:200]}...")
        
    chart_data = df[df["Вхождения"] > 0]
    if not chart_data.empty:
        ordered_categories = chart_data["Ключ"].tolist()
        chart_df = chart_data.copy()
        chart_df["Ключ"] = pd.Categorical(chart_df["Ключ"], categories=ordered_categories, ordered=True)
        st.bar_chart(data=chart_df.set_index("Ключ")["Вхождения"])
    
    styled_df = df.style.apply(highlight_rows, axis=1)
    table_height = (len(df) * 35) + 40
    
    st.dataframe(
        styled_df, 
        use_container_width=False, 
        hide_index=True,
        height=table_height,
        column_config={
            "№": st.column_config.NumberColumn("№", width="small"),
            "Ключ": st.column_config.TextColumn("Ключевое слово", width="medium"),
            "Вхождения": st.column_config.NumberColumn("Кол-во", width="small"),
            "Процент": st.column_config.TextColumn("Доля", width="small")
        }
    )

st.set_page_config(page_title="Анализатор ключевых слов", layout="wide")

if 'history' not in st.session_state:
    st.session_state.history = load_history()

# Переменная для хранения выбранного из истории запроса
if 'selected_history' not in st.session_state:
    st.session_state.selected_history = None

st.title("📊 Анализатор вхождений ключевых слов")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Исходный текст")
    text_input = st.text_area("Вставьте сюда ваш текст:", height=300)

with col2:
    st.subheader("2. Список ключевых слов")
    keywords_input = st.text_area("Вставьте ключи (можно через пробел, запятую или с новой строки):", height=300)

if st.button("🚀 Анализировать", type="primary"):
    if not text_input or not keywords_input:
        st.warning("Пожалуйста, заполните оба поля.")
    else:
        raw_keywords = re.split(r'\W+', keywords_input.lower())
        keywords = list(set([kw for kw in raw_keywords if len(kw) > 1])) # Убираем дубликаты
        
        words_in_text = re.findall(r'\b\w+\b', text_input.lower())
        
        stem_counts = {}
        for word in words_in_text:
            p = morph.parse(word)[0]
            stem = stemmer.stemWord(p.normal_form)
            stem_counts[stem] = stem_counts.get(stem, 0) + 1

        results = []
        for kw in keywords:
            kw_words = re.findall(r'\b\w+\b', kw)
            if not kw_words: continue
                
            kw_lemma = morph.parse(kw_words[0])[0].normal_form
            kw_stem = stemmer.stemWord(kw_lemma)
            
            count = 0
            if len(kw_words) == 1:
                if kw_stem in stem_counts:
                    count = stem_counts[kw_stem]
                else:
                    if len(kw_lemma) >= 5:
                        prefix = kw_lemma[:-1] if kw_lemma[-1] in 'аеёиоуыэюя' else kw_lemma
                        for text_word in words_in_text:
                            if text_word.startswith(prefix): count += 1
            else:
                count = text_input.lower().count(kw)

            results.append({"Ключ": kw, "Вхождения": count})

        df = pd.DataFrame(results)
        df = df.sort_values(by="Вхождения", ascending=False).reset_index(drop=True)
        df.insert(0, "№", range(1, len(df) + 1))

        total_hits = df["Вхождения"].sum()
        if total_hits > 0:
            df["Процент"] = (df["Вхождения"] / total_hits * 100).round(0).astype(int).astype(str) + "%"
        else:
            df["Процент"] = "0%"

        # --- СОХРАНЕНИЕ В ИСТОРИЮ ---
        new_entry = {
            "Время": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M:%S"),
            "Краткий текст": text_input.strip().replace('\n', ' ')[:30] + "...",
            "text": text_input, # Сохраняем полный текст
            "keywords": keywords, # Сохраняем список ключей
            "results": df.to_dict('records') # Сохраняем результаты
        }
        
        st.session_state.history.insert(0, new_entry)
        st.session_state.history = st.session_state.history[:100]
        save_history(st.session_state.history)
        
        # Сбрасываем выбранный элемент при новом анализе
        st.session_state.selected_history = None

        st.divider()
        st.subheader("Результаты анализа")
        render_results(df, text_input)

# --- БЛОК ИСТОРИИ (С КНОПКАМИ) ---
st.divider()
st.subheader("🕒 История последних 100 запросов")

if not st.session_state.history:
    st.info("История пока пуста.")
else:
    # Выводим историю в виде кнопок (по 1 в строке или в 2 колонки)
    for i, entry in enumerate(st.session_state.history):
        # Формируем текст кнопки: Время + краткий текст
        btn_label = f"🕒 {entry['Время']} | {entry['Краткий текст']}"
        
        if st.button(btn_label, key=f"hist_btn_{i}"):
            # При клике сохраняем выбранный элемент в session_state
            st.session_state.selected_history = entry

    if st.button("❌ Очистить историю"):
        st.session_state.history = []
        st.session_state.selected_history = None
        save_history([])
        st.rerun()

# --- ОКНО ПРОСМОТРА ВЫБРАННОГО ЗАПРОСА ---
if st.session_state.selected_history is not None:
    entry = st.session_state.selected_history
    st.divider()
    st.subheader(f"📄 Детали запроса от {entry['Время']}")
    
    with st.expander("Показать исходный текст и ключи", expanded=False):
        st.text_area("Исходный текст:", entry['text'], height=150, disabled=True)
        st.write(f"**Ключи:** {', '.join(entry['keywords'])}")
    
    # Восстанавливаем DataFrame из сохраненных словарей
    df_history = pd.DataFrame(entry['results'])
    
    # Добавляем колонку "Процент", если её нет (для старых записей)
    if "Процент" not in df_history.columns:
        total = df_history["Вхождения"].sum()
        df_history["Процент"] = (df_history["Вхождения"] / total * 100).round(0).astype(int).astype(str) + "%" if total > 0 else "0%"
        
    render_results(df_history)
    
    if st.button("Закрыть детали"):
        st.session_state.selected_history = None
        st.rerun()
