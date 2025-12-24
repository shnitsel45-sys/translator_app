import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random
import sys
import os
import json
from threading import Thread
import queue
import re
from typing import Dict, List, Tuple, Optional


sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class TranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Transformational Russian-English Translator")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        # Очередь для межпоточного общения
        self.translation_queue = queue.Queue()

        # Загружаем примеры из JSON или используем встроенные
        self.load_examples()

        self.setup_ui()
        self.setup_translator()

    def load_examples(self):
        """Загружаем примеры для перевода из JSON файла или используем встроенные"""
        self.examples = [
            "Студент читает книгу в библиотеке",
            "Что ты делаешь?",
            "Она пишет письмо",
            "Мы изучаем язык",
            "Мама дала дочери книгу",
            "В библиотеке студент читает книгу",
            "Мама пьет кофе",
            "Кофе пьет мама"
        ]

        try:
            with open('translation_examples.json', 'r', encoding='utf-8') as f:
                examples_data = json.load(f)
                if 'examples' in examples_data:
                    self.examples = examples_data['examples']
                    print("Примеры загружены из файла translation_examples.json")
        except Exception as e:
            print(f"Не удалось загрузить примеры из файла: {e}")

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Создаем notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Вкладка перевода
        self.translate_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.translate_frame, text="Трансформационный перевод")

        # Вкладка анализа
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="Синтаксический анализ")

        # Вкладка правил
        self.rules_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.rules_frame, text="Правила перевода")

        self.setup_translation_tab()
        self.setup_analysis_tab()
        self.setup_rules_tab()

        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief='sunken',
            anchor='w'
        )
        status_bar.pack(side='bottom', fill='x')

    def setup_translation_tab(self):
        """Настройка вкладки перевода"""
        # Заголовок
        title_label = tk.Label(
            self.translate_frame,
            text="Трансформационный переводчик русского в английский",
            font=('Arial', 16, 'bold'),
            bg='#f0f0f0',
            fg='#333'
        )
        title_label.pack(pady=10)

        # Фрейм для ввода текста
        input_frame = ttk.Frame(self.translate_frame)
        input_frame.pack(pady=10, padx=20, fill='x')

        ttk.Label(input_frame, text="Введите русское предложение:", font=('Arial', 11)).pack(anchor='w')
        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            height=4,
            width=70,
            font=('Arial', 11),
            wrap=tk.WORD
        )
        self.input_text.pack(pady=5, fill='x')
        self.input_text.focus()

        # Фрейм для кнопок
        button_frame = ttk.Frame(self.translate_frame)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame,
            text="Перевести",
            command=self.translate_text,
            style='Accent.TButton'
        ).pack(side='left', padx=5)

        ttk.Button(
            button_frame,
            text="Очистить",
            command=self.clear_text
        ).pack(side='left', padx=5)

        ttk.Button(
            button_frame,
            text="Случайный пример",
            command=self.generate_example
        ).pack(side='left', padx=5)

        # Фрейм для результата перевода
        result_frame = ttk.Frame(self.translate_frame)
        result_frame.pack(pady=10, padx=20, fill='both', expand=True)

        ttk.Label(result_frame, text="Английский перевод:", font=('Arial', 11)).pack(anchor='w')
        self.output_text = scrolledtext.ScrolledText(
            result_frame,
            height=6,
            width=70,
            font=('Arial', 11, 'bold'),
            wrap=tk.WORD,
            state='disabled',
            bg='#e8f4f8',
            fg='#003366'
        )
        self.output_text.pack(pady=5, fill='both', expand=True)

        # Фрейм для информации о переводе
        info_frame = ttk.Frame(self.translate_frame)
        info_frame.pack(pady=5, padx=20, fill='x')

        ttk.Label(info_frame, text="Детали перевода:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(5, 0))

        self.translation_details = scrolledtext.ScrolledText(
            info_frame,
            height=8,
            width=70,
            font=('Consolas', 9),
            wrap=tk.WORD,
            state='disabled'
        )
        self.translation_details.pack(pady=5, fill='x')

        # Прогресс бар
        self.progress = ttk.Progressbar(
            self.translate_frame,
            mode='indeterminate',
            length=200
        )
        self.progress.pack(side='bottom', fill='x', padx=20, pady=5)
        self.progress.pack_forget()

        # Настройка стилей
        self.setup_styles()

        # Бинд Enter для быстрого перевода
        self.root.bind('<Return>', lambda e: self.translate_text())

    def setup_analysis_tab(self):
        """Настройка вкладки синтаксического анализа"""
        # Фрейм для деревьев зависимостей (горизонтальное размещение)
        tree_frame = ttk.Frame(self.analysis_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Заголовок
        ttk.Label(tree_frame, text="Структура предложения:", font=('Arial', 11, 'bold')).pack(anchor='w')

        # Фрейм для двух деревьев
        trees_container = ttk.Frame(tree_frame)
        trees_container.pack(fill='both', expand=True)

        # Левое дерево — русское
        left_frame = ttk.Frame(trees_container)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))

        ttk.Label(left_frame, text="Русский анализ:", font=('Arial', 10, 'bold', 'underline')).pack(anchor='w')
        self.tree_text_ru = scrolledtext.ScrolledText(
            left_frame,
            height=15,
            font=('Consolas', 9),
            wrap=tk.WORD,
            state='disabled',
            bg='#f9f9f9'
        )
        self.tree_text_ru.pack(pady=5, fill='both', expand=True)

        # Правое дерево — детали структуры
        right_frame = ttk.Frame(trees_container)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))

        ttk.Label(right_frame, text="Структурные элементы:", font=('Arial', 10, 'bold', 'underline')).pack(anchor='w')
        self.structure_text = scrolledtext.ScrolledText(
            right_frame,
            height=15,
            font=('Consolas', 9),
            wrap=tk.WORD,
            state='disabled',
            bg='#f9f9f9'
        )
        self.structure_text.pack(pady=5, fill='both', expand=True)

        # Фрейм для трансформаций
        transforms_frame = ttk.Frame(self.analysis_frame)
        transforms_frame.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Label(transforms_frame, text="Грамматические трансформации:", font=('Arial', 11, 'bold')).pack(anchor='w')
        self.transforms_text = scrolledtext.ScrolledText(
            transforms_frame,
            height=8,
            font=('Arial', 10),
            wrap=tk.WORD,
            state='disabled',
            bg='#f0f8ff'
        )
        self.transforms_text.pack(pady=5, fill='both', expand=True)

    def setup_rules_tab(self):
        """Настройка вкладки правил перевода"""
        rules_frame = ttk.Frame(self.rules_frame)
        rules_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Заголовок
        ttk.Label(rules_frame, text="Правила трансформационной грамматики:",
                  font=('Arial', 12, 'bold')).pack(anchor='w', pady=5)

        # Область для отображения правил
        self.rules_text = scrolledtext.ScrolledText(
            rules_frame,
            height=25,
            width=90,
            font=('Consolas', 9),
            wrap=tk.WORD,
            state='disabled'
        )
        self.rules_text.pack(pady=5, fill='both', expand=True)

        # Кнопка для обновления правил
        ttk.Button(
            rules_frame,
            text="Обновить правила",
            command=self.update_rules_display
        ).pack(pady=5)

    def setup_styles(self):
        """Настройка стилей для виджетов"""
        style = ttk.Style()
        style.configure('Accent.TButton', background='#0078d4', foreground='white', font=('Arial', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#005fa3')])

        style.configure('TNotebook', background='#f0f0f0')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')

    def setup_translator(self):
        """Инициализация переводчика"""
        try:
            from main import AdvancedTransformationalTranslator
            self.translator = AdvancedTransformationalTranslator()
            self.status_var.set("Трансформационный переводчик готов")
            self.update_rules_display()
        except ImportError as e:
            self.status_var.set(f"Ошибка загрузки переводчика: {e}")
            messagebox.showerror("Ошибка",
                                 "Не удалось загрузить переводчика. Убедитесь, что main.py находится в той же папке.")
        except Exception as e:
            self.status_var.set(f"Ошибка инициализации: {e}")
            import traceback
            traceback.print_exc()

    def update_rules_display(self):
        """Обновление отображения правил перевода"""
        self.rules_text.config(state='normal')
        self.rules_text.delete('1.0', tk.END)

        try:
            if hasattr(self, 'translator') and self.translator.json_loaded:
                rules = self.translator.grammar_rules

                # Отображаем информацию о версии
                if "metadata" in rules["english_grammar_system"]:
                    metadata = rules["english_grammar_system"]["metadata"]
                    self.rules_text.insert(tk.END, f"Система правил: {metadata.get('description', 'Неизвестно')}\n")
                    self.rules_text.insert(tk.END, f"Версия: {metadata.get('version', 'Неизвестно')}\n")
                    self.rules_text.insert(tk.END, f"Обновлено: {metadata.get('last_updated', 'Неизвестно')}\n\n")

                # Отображаем основные шаблоны
                self.rules_text.insert(tk.END, "ОСНОВНЫЕ СИНТАКСИЧЕСКИЕ ШАБЛОНЫ:\n")
                self.rules_text.insert(tk.END, "=" * 50 + "\n\n")

                patterns = rules["english_grammar_system"]["sentence_patterns"]["basic_clause_patterns"]
                for pattern_name, pattern_info in patterns.items():
                    self.rules_text.insert(tk.END, f"{pattern_name}: {pattern_info['description']}\n")
                    self.rules_text.insert(tk.END, f"   Пример: {pattern_info['example']}\n\n")

                # Отображаем специальные конструкции
                self.rules_text.insert(tk.END, "\nСПЕЦИАЛЬНЫЕ КОНСТРУКЦИИ:\n")
                self.rules_text.insert(tk.END, "=" * 50 + "\n\n")

                special_constructions = rules["english_grammar_system"]["special_constructions"]
                for construction, details in special_constructions.items():
                    self.rules_text.insert(tk.END, f"{construction.replace('_', ' ').title()}\n")
                    if isinstance(details, dict) and "examples" in details:
                        for example in details["examples"]:
                            self.rules_text.insert(tk.END, f"   • {example}\n")
                    self.rules_text.insert(tk.END, "\n")

                self.rules_text.insert(tk.END, "\nПравила загружены из файла transformational_grammar_rules.json")
                self.status_var.set("Правила перевода обновлены")
            else:
                self.rules_text.insert(tk.END, "Правила перевода не загружены.\n\n")
                self.rules_text.insert(tk.END, "Возможные причины:\n")
                self.rules_text.insert(tk.END, "1. Файл transformational_grammar_rules.json не найден\n")
                self.rules_text.insert(tk.END, "2. Файл содержит ошибки форматирования\n")
                self.rules_text.insert(tk.END, "3. Структура файла не соответствует ожидаемой\n\n")
                self.rules_text.insert(tk.END, "Будут использоваться встроенные базовые правила перевода.")
                self.status_var.set("Используются встроенные правила перевода")
        except Exception as e:
            self.rules_text.insert(tk.END, f"Ошибка при загрузке правил:\n{str(e)}")
            self.status_var.set(f"Ошибка отображения правил: {e}")

        self.rules_text.config(state='disabled')

    def translate_text(self):
        """Перевод текста в отдельном потоке"""
        text = self.input_text.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("Внимание", "Введите текст для перевода")
            return

        # Проверяем длину текста
        if len(text) > 200:
            if not messagebox.askyesno("Подтверждение",
                                       "Текст слишком длинный для анализа. Перевести только первые 200 символов?"):
                return
            text = text[:200]

        # Показываем прогресс
        self.progress.pack(side='bottom', fill='x', padx=20, pady=5)
        self.progress.start(10)
        self.status_var.set("Перевожу и анализирую...")

        # Очищаем поля
        for widget in [self.output_text, self.translation_details, self.tree_text_ru,
                       self.structure_text, self.transforms_text]:
            widget.config(state='normal')
            widget.delete('1.0', tk.END)
            widget.config(state='disabled')

        self.output_text.config(state='normal')
        self.output_text.insert('1.0', "Идет перевод...")
        self.output_text.config(state='disabled')

        # Запускаем в отдельном потоке
        thread = Thread(target=self._translate_thread, args=(text,))
        thread.daemon = True
        thread.start()

        # Проверяем результат каждые 100мс
        self.root.after(100, self._check_translation_result)

    def _translate_thread(self, text):
        """Поток для перевода и синтаксического анализа"""
        try:
            if hasattr(self, 'translator'):
                # Получаем полный результат перевода
                result = self.translator.translate_with_analysis(text)

                # Строим детальный анализ для отображения
                detailed_analysis = self._build_sentence_analysis(result)
                structure_analysis = self._build_structure_analysis(result)
                transform_analysis = self._build_transform_analysis(result)

                result_display = {
                    'translation': result['translation'],
                    'details': self._format_translation_details(result),
                    'analysis': detailed_analysis,
                    'structure': structure_analysis,
                    'transforms': transform_analysis,
                    'error': None
                }
            else:
                result_display = {
                    'translation': "Ошибка: Переводчик не загружен",
                    'details': "",
                    'analysis': "",
                    'structure': "",
                    'transforms': "",
                    'error': "Translator not loaded"
                }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            result_display = {
                'translation': f"Ошибка перевода: {str(e)}",
                'details': f"Текст ошибки:\n{error_trace}",
                'analysis': "",
                'structure': "",
                'transforms': "",
                'error': str(e)
            }

        self.translation_queue.put(result_display)

    def _check_translation_result(self):
        """Проверка результата перевода"""
        try:
            result = self.translation_queue.get_nowait()
            self._show_translation_result(result)
        except queue.Empty:
            self.root.after(100, self._check_translation_result)

    def _show_translation_result(self, result):
        """Показать результат перевода и анализов"""
        self.progress.stop()
        self.progress.pack_forget()

        # Показываем перевод
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert('1.0', result['translation'])
        self.output_text.config(state='disabled')

        # Показываем детали перевода
        self.translation_details.config(state='normal')
        self.translation_details.delete('1.0', tk.END)
        self.translation_details.insert('1.0', result['details'])
        self.translation_details.config(state='disabled')

        # Показываем синтаксический анализ
        self.tree_text_ru.config(state='normal')
        self.tree_text_ru.delete('1.0', tk.END)
        self.tree_text_ru.insert('1.0', result['analysis'])
        self.tree_text_ru.config(state='disabled')

        # Показываем структурный анализ
        self.structure_text.config(state='normal')
        self.structure_text.delete('1.0', tk.END)
        self.structure_text.insert('1.0', result['structure'])
        self.structure_text.config(state='disabled')

        # Показываем трансформации
        self.transforms_text.config(state='normal')
        self.transforms_text.delete('1.0', tk.END)
        self.transforms_text.insert('1.0', result['transforms'])
        self.transforms_text.config(state='disabled')

        if result['error']:
            self.status_var.set(f"Ошибка перевода: {result['error']}")
        else:
            self.status_var.set(f"Перевод завершен | Шаблон: {result.get('pattern', 'Неизвестен')}")

    def _format_translation_details(self, result):
        """Форматирование деталей перевода"""
        details = []
        details.append("=" * 60)
        details.append("ДЕТАЛИ ПЕРЕВОДА")
        details.append("=" * 60)
        details.append(f"Исходное предложение: {result['original']}")
        details.append(f"Перевод: {result['translation']}")
        details.append(f"Источник правил: {result['rules_source']}")
        details.append("")

        if "sentence_structure" in result:
            structure = result["sentence_structure"]
            details.append("Структура предложения:")
            details.append(f"   Подлежащее (Subject): {structure.get('subject', 'Не найдено')}")
            details.append(f"   Сказуемое (Verb): {structure.get('verb', 'Не найдено')}")
            details.append(f"   Прямое дополнение (Object): {structure.get('object', 'Не найдено')}")
            if structure.get('indirect_object'):
                details.append(f"   Косвенное дополнение: {structure['indirect_object']}")
            if structure.get('question_word'):
                details.append(f"   Вопросительное слово: {structure['question_word']}")

        details.append("\nСловарный перевод слов:")
        for word_ru, word_en in result["word_translations"].items():
            details.append(f"   {word_ru} → {word_en}")

        return "\n".join(details)

    def _build_sentence_analysis(self, result):
        """Построение детального синтаксического анализа"""
        analysis_lines = []
        analysis_lines.append("=" * 60)
        analysis_lines.append("СИНТАКСИЧЕСКИЙ АНАЛИЗ ПРЕДЛОЖЕНИЯ")
        analysis_lines.append("=" * 60)

        if "stanza_analysis" in result:
            analysis = result["stanza_analysis"]

            for sent_idx, sentence in enumerate(analysis.get("sentences", []), 1):
                analysis_lines.append(f"\nПРЕДЛОЖЕНИЕ #{sent_idx}: {sentence['text']}")
                analysis_lines.append("-" * 40)

                # Строим таблицу слов
                analysis_lines.append("{:<5} {:<15} {:<10} {:<10} {:<10} {:<15}".format(
                    "ID", "СЛОВО", "ЛЕММА", "ЧР", "HEAD", "ЗАВИСИМОСТЬ"
                ))
                analysis_lines.append("-" * 75)

                for word in sentence.get("words", []):
                    analysis_lines.append("{:<5} {:<15} {:<10} {:<10} {:<10} {:<15}".format(
                        word.get("id", ""),
                        word.get("text", ""),
                        word.get("lemma", ""),
                        word.get("upos", ""),
                        word.get("head", ""),
                        word.get("deprel", "")
                    ))
        else:
            analysis_lines.append("\nДетальный синтаксический анализ недоступен.")
            analysis_lines.append("Возможно, Stanza анализатор не был инициализирован.")

        return "\n".join(analysis_lines)

    def _build_structure_analysis(self, result):
        """Построение анализа структуры предложения"""
        structure_lines = []
        structure_lines.append("=" * 60)
        structure_lines.append("СТРУКТУРА ПРЕДЛОЖЕНИЯ")
        structure_lines.append("=" * 60)

        if "sentence_structure" in result:
            structure = result["sentence_structure"]

            structure_lines.append(f"\nТип предложения: {result.get('sentence_type', 'Не определен').capitalize()}")
            structure_lines.append(f"Использованный шаблон: {result.get('sentence_pattern', 'Не определен')}")

            # Подлежащее
            subject = structure.get("subject")
            if subject:
                structure_lines.append(f"\nПодлежащее (Subject): '{subject}'")
                if subject.lower() in ["он", "она", "оно"]:
                    structure_lines.append("   └── Третье лицо единственного числа")

            # Глагол
            verb = structure.get("verb")
            if verb:
                structure_lines.append(f"\nГлагол (Verb): '{verb}'")
                tense = result.get("verb_tense", "Не определено")
                structure_lines.append(f"   └── Время: {tense}")

            # Прямое дополнение
            obj = structure.get("object")
            if obj:
                structure_lines.append(f"\nПрямое дополнение (Object): '{obj}'")
                article = result.get("article")
                if article:
                    structure_lines.append(f"   └── Артикль: '{article}'")

            # Косвенное дополнение
            indirect_obj = structure.get("indirect_object")
            if indirect_obj:
                structure_lines.append(f"\nКосвенное дополнение (Indirect Object): '{indirect_obj}'")

            # Вопросительное слово
            question_word = structure.get("question_word")
            if question_word:
                structure_lines.append(f"\nВопросительное слово: '{question_word}'")
        else:
            structure_lines.append("\nСтруктурный анализ недоступен.")

        return "\n".join(structure_lines)

    def _build_transform_analysis(self, result):
        """Построение анализа грамматических трансформаций"""
        transform_lines = []
        transform_lines.append("ТРАНСФОРМАЦИОННЫЙ АНАЛИЗ")
        transform_lines.append("=" * 40)

        if "syntax_transformations" in result and result["syntax_transformations"]:
            transform_lines.append("\nВыполненные грамматические трансформации:")
            for i, transform in enumerate(result["syntax_transformations"], 1):
                transform_lines.append(f"{i}. {transform}")
        else:
            transform_lines.append("\nСпецифические трансформации не применялись.")

        transform_lines.append("\n" + "-" * 40)

        # Добавляем информацию об использованных шаблонах
        if result.get('sentence_pattern') == "SVOO":
            transform_lines.append("Шаблон SVOO (Subject + Verb + Indirect Object + Direct Object):")
            transform_lines.append("   Применяется для глаголов передачи (дать, сказать, показать и т.д.)")
            transform_lines.append("   Порядок: Подлежащее + Глагол + Косвенное дополнение + Прямое дополнение")

        elif result.get('sentence_pattern') == "SVOA":
            transform_lines.append("Шаблон SVOA (Subject + Verb + Object + Adverbial):")
            transform_lines.append("   Применяется для предложений с обстоятельствами места/времени")
            transform_lines.append("   Обстоятельства всегда располагаются в конце предложения")

        return "\n".join(transform_lines)

    def generate_example(self):
        """Генерация случайного примера"""
        example = random.choice(self.examples)
        self.input_text.delete('1.0', tk.END)
        self.input_text.insert('1.0', example)
        self.translate_text()
        self.status_var.set(f"Сгенерирован пример: '{example}'")

    def clear_text(self):
        """Очистка полей ввода и вывода"""
        self.input_text.delete('1.0', tk.END)
        for widget in [self.output_text, self.translation_details, self.tree_text_ru,
                       self.structure_text, self.transforms_text]:
            widget.config(state='normal')
            widget.delete('1.0', tk.END)
            widget.config(state='disabled')
        self.status_var.set("Поля очищены")


def main():
    """Запуск приложения"""
    try:
        root = tk.Tk()
        app = TranslationApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Ошибка запуска приложения: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":

    main()

