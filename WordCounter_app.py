import streamlit as st
import pandas as pd
import re
import pymorphy3

# Инициализируем морфологический анализатор
morph = pymorphy3.MorphAnalyzer()

# Функция для приведения слова к начальной форме (лемме)
def get_lemma(word):
    p = morph.parse(word)[0]
    return p.normal_form

st.set_page_config(page_title="Анализатор ключевых слов", layout="wide")

st.title("📊 Анализатор вхождений ключевых слов")
st.markdown("Вставьте текст и список ключей. Слова будут считаться с учетом всех словоформ (склонений).")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Исходный текст")
    text_input = st.text_area("Вставьте сюда ваш текст:", height=300)

with col2:
    st.subheader("2. Список ключевых слов")
    keywords_input = st.text_area("Вставьте ключи (каждый с новой строки):", height=300)

if st.button("🚀 Анализировать", type="primary"):
    if not text_input or not keywords_input:
        st.warning("Пожалуйста, заполните оба поля.")
    else:
        # 1. Обработка списка ключей
        keywords = [line.strip() for line in keywords_input.split('\n') if line.strip()]
        
        # 2. Подготовка текста
        words_in_text = re.findall(r'\b\w+\b', text_input.lower())
        
        # 3. Создаем словарь лемм из текста
        lemma_counts = {}
        for word in words_in_text:
            lemma = get_lemma(word)
            lemma_counts[lemma] = lemma_counts.get(lemma, 0) + 1

        results = []
        
        # 4. Подсчет вхождений
        for kw in keywords:
            kw_lower = kw.lower()
            kw_words = re.findall(r'\b\w+\b', kw_lower)
            kw_lemmas = [get_lemma(w) for w in kw_words]
            
            count = 0
            if len(kw_lemmas) == 1:
                count = lemma_counts.get(kw_lemmas[0], 0)
            else:
                # Простой поиск фраз
                count = text_input.lower().count(kw_lower)

            results.append({"Ключ": kw, "Вхождения": count})

        # Создаем DataFrame и сортируем по убыванию
        df = pd.DataFrame(results)
        df = df.sort_values(by="Вхождения", ascending=False).reset_index(drop=True)
        
        # --- ДОБАВЛЯЕМ НУМЕРАЦИЮ СТРОК ---
        # Создаем колонку "№" и заполняем её порядковыми номерами (начиная с 1)
        df.insert(0, "№", range(1, len(df) + 1))

        # Рассчитываем процентную долю
        total_hits = df["Вхождения"].sum()
        if total_hits > 0:
            df["Процент"] = (df["Вхождения"] / total_hits * 100).round(0).astype(int).astype(str) + "%"
        else:
            df["Процент"] = "0%"

        st.divider()
        st.subheader("Результаты анализа")
        
        # --- НАСТРОЙКА ГРАФИКА ---
        # Фильтруем нулевые значения, чтобы не засорять график
        chart_data = df[df["Вхождения"] > 0]
        
        if not chart_data.empty:
            # Чтобы Streamlit не сортировал столбцы по алфавиту, а строго следовал нашему порядку убывания,
            # мы делаем колонку "Ключ" категориальной и задаем ей порядок.
            # Так как df уже отсортирован по убыванию, мы просто берем список ключей в том порядке, в котором они идут.
            ordered_categories = chart_data["Ключ"].tolist()
            
            # Создаем копию для графика, чтобы не менять основной df
            chart_df = chart_data.copy()
            chart_df["Ключ"] = pd.Categorical(chart_df["Ключ"], categories=ordered_categories, ordered=True)
            
            # Строим график
            st.bar_chart(data=chart_df.set_index("Ключ")["Вхождения"])
        else:
            st.info("Совпадений не найдено.")

        # --- ВЫВОД ТАБЛИЦЫ ---
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True, # Скрываем стандартный индекс Pandas (0, 1, 2...), так как у нас есть своя колонка "№"
            column_config={
                "№": st.column_config.NumberColumn("№", width="small"), # Настраиваем ширину колонки с номером
                "Ключ": st.column_config.TextColumn("Ключевое слово"),
                "Вхождения": st.column_config.NumberColumn("Кол-во", format="%d"),
                "Процент": st.column_config.TextColumn("Доля")
            }
        )
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать таблицу (CSV)",
            data=csv,
            file_name='keywords_stats.csv',
            mime='text/csv',
        )