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

# Функция для подсветки строк
def highlight_rows(row):
    # Проверяем значение в колонке "Вхождения"
    val = row['Вхождения']
    if val == 0:
        # Красный фон для нулевых вхождений
        return ['background-color: #ffcccc'] * len(row)
    elif val > 1:
        # Желтый фон для тех, что встречаются больше одного раза
        return ['background-color: #fff4cc'] * len(row)
    else:
        # Обычный фон для остальных (1 вхождение)
        return [''] * len(row)

st.set_page_config(page_title="Анализатор ключевых слов", layout="wide")

st.title("📊 Анализатор вхождений ключевых слов")
st.markdown("Вставьте текст и список ключей. Слова считаются с учетом всех словоформ.")

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
        
        # 3. Создаем словарь лемм из текста
        lemma_counts = {}
        for word in words_in_text:
            lemma = get_lemma(word)
            lemma_counts[lemma] = lemma_counts.get(lemma, 0) + 1

        results = []
        
        # 4. Подсчет вхождений
        for kw in keywords:
            kw_words = re.findall(r'\b\w+\b', kw)
            if not kw_words:
                continue
                
            kw_lemmas = [get_lemma(w) for w in kw_words]
            
            count = 0
            if len(kw_lemmas) == 1:
                count = lemma_counts.get(kw_lemmas[0], 0)
            else:
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

        st.divider()
        st.subheader("Результаты анализа")
        
        # График
        chart_data = df[df["Вхождения"] > 0]
        if not chart_data.empty:
            ordered_categories = chart_data["Ключ"].tolist()
            chart_df = chart_data.copy()
            chart_df["Ключ"] = pd.Categorical(chart_df["Ключ"], categories=ordered_categories, ordered=True)
            st.bar_chart(data=chart_df.set_index("Ключ")["Вхождения"])
        
        # --- ВЫВОД ТАБЛИЦЫ С ПОДСВЕТКОЙ ---
        # Применяем стили к DataFrame
        styled_df = df.style.apply(highlight_rows, axis=1)
        
        # Выводим таблицу
        st.dataframe(
            styled_df, 
            use_container_width=False, 
            hide_index=True,
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
