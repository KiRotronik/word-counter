import streamlit as st
import pandas as pd
import re
import pymorphy3
import snowballstemmer

# Инициализируем морфологический анализатор и стеммер
morph = pymorphy3.MorphAnalyzer()
stemmer = snowballstemmer.stemmer('russian')

# Функция для получения стема (корня) слова
def get_stem(word):
    # Сначала приводим к начальной форме, чтобы убрать сложные окончания
    p = morph.parse(word)[0]
    normal_form = p.normal_form
    # Затем отсекаем окончание у начальной формы
    return stemmer.stemWord(normal_form)

# Функция для подсветки строк (с черным текстом)
def highlight_rows(row):
    val = row['Вхождения']
    if val == 0:
        return ['background-color: #ffcccc; color: black;'] * len(row)
    elif val > 1:
        return ['background-color: #fff4cc; color: black;'] * len(row)
    else:
        return [''] * len(row)

st.set_page_config(page_title="Анализатор ключевых слов", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ ИСТОРИИ В ПАМЯТИ ---
if 'history' not in st.session_state:
    st.session_state.history = []

st.title("📊 Анализатор вхождений ключевых слов")
st.markdown("Вставьте текст и список ключей. Слова считаются с учетом всех словоформ и однокоренных слов.")

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
        # 1. Обработка списка ключей
        raw_keywords = re.split(r'\W+', keywords_input.lower())
        keywords = [kw for kw in raw_keywords if len(kw) > 1]
        
        # 2. Подготовка текста
        words_in_text = re.findall(r'\b\w+\b', text_input.lower())
        
        # 3. Создаем словарь стемов из текста
        # Теперь мы считаем не леммы, а корни слов
        stem_counts = {}
        for word in words_in_text:
            stem = get_stem(word)
            stem_counts[stem] = stem_counts.get(stem, 0) + 1

        results = []
        
        # 4. Подсчет вхождений
        for kw in keywords:
            kw_words = re.findall(r'\b\w+\b', kw)
            if not kw_words:
                continue
                
            # Берем стем ключевого слова
            kw_stem = get_stem(kw_words[0])
            
            count = 0
            if len(kw_words) == 1:
                # Ищем по корню
                count = stem_counts.get(kw_stem, 0)
            else:
                # Поиск фраз (оставляем простой вариант)
                count = text_input.lower().count(kw)

            results.append({"Ключ": kw, "Вхождения": count})

        # Создаем DataFrame и сортируем по убыванию
        df = pd.DataFrame(results)
        df = df.sort_values(by="Вхождения", ascending=False).reset_index(drop=True)
        
        # Добавляем нумерацию
        df.insert(0, "№", range(1, len(df) + 1))

        # Рассчитываем процент
        total_hits = df["Вхождения"].sum()
        if total_hits > 0:
            df["Процент"] = (df["Вхождения"] / total_hits * 100).round(0).astype(int).astype(str) + "%"
        else:
            df["Процент"] = "0%"

        # --- СОХРАНЕНИЕ В ИСТОРИЮ ---
        text_snippet = text_input.strip().replace('\n', ' ')[:20] + "..."
        found_keywords = df[df["Вхождения"] > 0]["Ключ"].tolist()
        
        new_entry = {
            "Время": pd.Timestamp.now().strftime("%H:%M:%S"),
            "Фрагмент текста": text_snippet,
            "Найдено ключей": ", ".join(found_keywords) if found_keywords else "Нет совпадений"
        }
        
        st.session_state.history.insert(0, new_entry)
        st.session_state.history = st.session_state.history[:100]

        # --- ВЫВОД РЕЗУЛЬТАТОВ ---
        st.divider()
        st.subheader("Результаты анализа")
        
        # График
        chart_data = df[df["Вхождения"] > 0]
        if not chart_data.empty:
            ordered_categories = chart_data["Ключ"].tolist()
            chart_df = chart_data.copy()
            chart_df["Ключ"] = pd.Categorical(chart_df["Ключ"], categories=ordered_categories, ordered=True)
            st.bar_chart(data=chart_df.set_index("Ключ")["Вхождения"])
        
        # Таблица с подсветкой
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
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать таблицу (CSV)",
            data=csv,
            file_name='keywords_stats.csv',
            mime='text/csv',
        )

# --- БЛОК ИСТОРИИ ---
st.divider()
st.subheader("🕒 История последних 100 запросов")
if st.session_state.history:
    history_df = pd.DataFrame(st.session_state.history)
    st.dataframe(history_df, use_container_width=True, hide_index=True)
    
    if st.button("Очистить историю"):
        st.session_state.history = []
        st.rerun()
else:
    st.info("История пока пуста. Сделайте первый анализ.")
