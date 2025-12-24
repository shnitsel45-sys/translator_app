import json
from typing import Dict, List, Tuple, Optional
import re
from deep_translator import GoogleTranslator
import os


class AdvancedTransformationalTranslator:
    def __init__(self):
        self.MORPH_AVAILABLE = False
        self.STANZA_AVAILABLE = False

        try:
            import pymorphy2
            import stanza
            self.MORPH_AVAILABLE = True
            self.STANZA_AVAILABLE = True
            print("✅ Все лингвистические анализаторы доступны")
        except ImportError as e:
            print(f"⚠️ Не все анализаторы установлены: {e}")
            self.MORPH_AVAILABLE = False
            self.STANZA_AVAILABLE = False

        self.translator = GoogleTranslator(source='ru', target='en')
        self.translation_cache = {}

        # Минимальный словарь для критически важных слов
        self.correction_dict = {
            'я': 'i',
            'ты': 'you',
            'он': 'he',
            'она': 'she',
            'оно': 'it',
            'мы': 'we',
            'вы': 'you',
            'они': 'they',
            'что': 'what',
            'кто': 'who',
            'где': 'where',
            'когда': 'when',
            'почему': 'why',
            'как': 'how',
            'сколько': 'how much'
        }

        self.grammar_rules = self.load_grammar_rules()
        self.morph = None
        self.stanza_nlp = None

        if self.MORPH_AVAILABLE:
            try:
                import pymorphy2
                self.morph = pymorphy2.MorphAnalyzer()
                print("✅ Морфологический анализатор инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации pymorphy2: {e}")
                self.MORPH_AVAILABLE = False

        if self.STANZA_AVAILABLE:
            try:
                import stanza
                try:
                    self.stanza_nlp = stanza.Pipeline('ru', processors='tokenize,pos,lemma,depparse')
                    print("✅ Stanza синтаксический анализатор инициализирован")
                except:
                    print("📥 Скачиваем модель Stanza для русского языка...")
                    stanza.download('ru')
                    self.stanza_nlp = stanza.Pipeline('ru', processors='tokenize,pos,lemma,depparse')
                    print("✅ Stanza синтаксический анализатор инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации Stanza: {e}")
                self.STANZA_AVAILABLE = False

        if self.is_json_loaded_properly():
            print("✅ Файл JSON успешно загружен! Используются правила из файла.")
            self.json_loaded = True
            self.patterns = self.grammar_rules["english_grammar_system"]["sentence_patterns"]["basic_clause_patterns"]
            self.extended_patterns = self.grammar_rules["english_grammar_system"]["sentence_patterns"][
                "extended_patterns"]
            self.lexical_corrections = self.grammar_rules["english_grammar_system"].get("lexical_corrections", {})
            self.preposition_rules = self.grammar_rules["english_grammar_system"].get("preposition_rules", {})
        else:
            print("⚠️ Файл JSON не загружен. Используются встроенные правила.")
            self.json_loaded = False
            self.patterns = {}
            self.extended_patterns = {}
            self.lexical_corrections = {}
            self.preposition_rules = {}

    def is_json_loaded_properly(self) -> bool:
        if not self.grammar_rules or "error" in self.grammar_rules:
            return False
        return "english_grammar_system" in self.grammar_rules

    def load_grammar_rules(self) -> Dict:
        json_files = ['transformational_grammar_rules.json']
        for json_file in json_files:
            try:
                if os.path.exists(json_file):
                    print(f"🔍 Найден файл: {json_file}")
                    with open(json_file, 'r', encoding='utf-8') as f:
                        rules = json.load(f)
                        print(f"✅ Файл {json_file} успешно загружен")
                        return rules
            except Exception as e:
                print(f"❌ Ошибка при загрузке {json_file}: {e}")
        return {"error": "No JSON file found"}

    def stanza_syntax_analysis(self, sentence: str) -> Dict:
        if not self.STANZA_AVAILABLE or not self.stanza_nlp:
            return {"error": "Stanza analyzer not available"}
        try:
            doc = self.stanza_nlp(sentence)
            analysis = {"sentences": [], "tokens": [], "dependencies": []}
            for sent in doc.sentences:
                sentence_info = {"text": sent.text, "words": [], "dependencies": []}
                for word in sent.words:
                    word_info = {
                        "id": word.id,
                        "text": word.text,
                        "lemma": word.lemma,
                        "upos": word.upos,
                        "xpos": word.xpos,
                        "feats": word.feats,
                        "head": word.head,
                        "deprel": word.deprel
                    }
                    sentence_info["words"].append(word_info)
                    analysis["tokens"].append(word_info)
                for word in sent.words:
                    if word.head > 0:
                        dependency = {
                            "governor": word.head,
                            "dependent": word.id,
                            "relation": word.deprel
                        }
                        sentence_info["dependencies"].append(dependency)
                        analysis["dependencies"].append(dependency)
                analysis["sentences"].append(sentence_info)
            return analysis
        except Exception as e:
            return {"error": str(e)}

    def find_subject_with_stanza(self, analysis: Dict) -> Tuple[str, str]:
        if "error" in analysis or not analysis.get("sentences"):
            return None, None
        subject = None
        predicate = None
        for sentence in analysis["sentences"]:
            for word in sentence["words"]:
                if word["deprel"] == "nsubj":
                    subject = word["text"]
                elif word["deprel"] == "root" and word["upos"] == "VERB":
                    predicate = word["text"]
                elif word["deprel"] in ["nsubj:pass", "csubj"]:
                    subject = word["text"]
            if not subject or not predicate:
                for word in sentence["words"]:
                    if word["upos"] == "NOUN" and word["deprel"] != "obj":
                        subject = word["text"]
                    elif word["upos"] == "VERB" and not predicate:
                        predicate = word["text"]
        return subject, predicate

    def find_objects_with_stanza(self, analysis: Dict) -> Tuple[str, str]:
        if "error" in analysis or not analysis.get("sentences"):
            return None, None
        direct_object = None
        indirect_object = None
        for sentence in analysis["sentences"]:
            for word in sentence["words"]:
                if word["deprel"] == "obj":
                    direct_object = word["text"]
                elif word["deprel"] == "iobj":
                    indirect_object = word["text"]
                elif word["deprel"] in ["obl", "nmod"]:
                    if not direct_object:
                        direct_object = word["text"]
        return direct_object, indirect_object

    def advanced_syntax_analysis_with_stanza(self, structure: Dict, sentence: str):
        stanza_analysis = self.stanza_syntax_analysis(sentence)
        if "error" not in stanza_analysis:
            structure["stanza_analysis"] = stanza_analysis
            subject, predicate = self.find_subject_with_stanza(stanza_analysis)
            direct_obj, indirect_obj = self.find_objects_with_stanza(stanza_analysis)
            if subject:
                structure["subject"] = subject
            if predicate:
                structure["verb"] = predicate
            if direct_obj:
                structure["object"] = direct_obj
            if indirect_obj:
                structure["indirect_object"] = indirect_obj
            return
        self.fallback_syntax_analysis(structure, sentence)

    def fallback_syntax_analysis(self, structure: Dict, sentence: str):
        clean_sentence = re.sub(r'[^\w\s]', ' ', sentence)
        words = [word for word in clean_sentence.strip().split() if word]
        question_words = ['что', 'кто', 'где', 'когда', 'почему', 'как', 'сколько']
        for word in words:
            if word.lower() in question_words:
                structure["question_word"] = word
                break
        for word in words:
            if self.is_verb_simple(word):
                structure["verb"] = word
                break
        for word in words:
            if word.lower() in ['я', 'ты', 'он', 'она', 'оно', 'мы', 'вы', 'они']:
                structure["subject"] = word
                break
        if structure.get("verb"):
            verb_index = words.index(structure["verb"])
            for i in range(verb_index + 1, len(words)):
                word = words[i]
                if word != structure.get("subject") and not self.is_verb_simple(word):
                    structure["object"] = word
                    break

    def is_verb_simple(self, word: str) -> bool:
        if self.MORPH_AVAILABLE and self.morph:
            parses = self.morph.parse(word)
            for p in parses:
                if p.tag.POS in {'VERB', 'INFN'}:
                    return True
        word_lower = word.lower()
        verb_endings = [
            'ть', 'ет', 'ёт', 'ит', 'ат', 'ят',
            'ешь', 'ёшь', 'ишь', 'ашь', 'яшь',
            'ем', 'ём', 'им', 'ам', 'ям',
            'ете', 'ёте', 'ите', 'ате', 'яте',
            'ут', 'ют'
        ]
        special_verbs = ['есть', 'быть', 'являться', 'стать', 'казаться']
        return any(word_lower.endswith(ending) for ending in verb_endings) or word_lower in special_verbs

    def _safe_translate_word(self, word: str) -> str:
        if word in self.translation_cache:
            return self.translation_cache[word]
        try:
            # Проверяем лексические исправления из JSON
            if self.json_loaded and self.lexical_corrections:
                for category in self.lexical_corrections.values():
                    if word.lower() in category:
                        result = category[word.lower()]
                        self.translation_cache[word] = result
                        return result

            # Используем correction_dict
            word_lower = word.lower()
            if word_lower in self.correction_dict:
                result = self.correction_dict[word_lower]
                self.translation_cache[word] = result
                return result

            # Обычный перевод
            raw = self.translator.translate(word).lower().strip()
            if ' ' in raw:
                stop_words = {'i', 'you', 'he', 'she', 'it', 'we', 'they',
                              'am', 'is', 'are', 'was', 'were',
                              'do', 'does', 'did',
                              'have', 'has', 'had',
                              'be', 'been', 'being'}
                candidates = [w for w in raw.split() if w not in stop_words]
                result = candidates[0] if candidates else word
            else:
                result = raw
            self.translation_cache[word] = result
            return result
        except:
            self.translation_cache[word] = word
            return word

    def get_verb_info(self, russian_verb: str) -> dict:
        if self.MORPH_AVAILABLE and self.morph:
            parses = self.morph.parse(russian_verb)
            for p in parses:
                if p.tag.POS in {'VERB', 'INFN'}:
                    normal_form = p.normal_form
                    tense = getattr(p.tag, 'tense', None)
                    return {"infinitive": normal_form, "tense": tense}
        return {"infinitive": russian_verb, "tense": None}

    def get_word_translation_improved(self, word: str) -> str:
        if self.MORPH_AVAILABLE and self.morph:
            parses = self.morph.parse(word)
            if parses:
                p = parses[0]
                normal_form = p.normal_form
                return self._safe_translate_word(normal_form)
        return self._safe_translate_word(word)

    def detect_special_pattern(self, sentence: str, structure: Dict) -> str:
        """Определяет специальную конструкцию по шаблонам из JSON"""
        sentence_lower = sentence.lower()

        # 1. POSSESSION: "У меня есть..."
        if self.extended_patterns and "POSSESSION" in self.extended_patterns:
            possession_pattern = self.extended_patterns["POSSESSION"].get("trigger_regex")
            if possession_pattern and re.search(possession_pattern, sentence_lower):
                return "POSSESSION"

        # 2. PRICE_QUESTION: "Сколько стоит..."
        if self.extended_patterns and "PRICE_QUESTION" in self.extended_patterns:
            price_pattern = self.extended_patterns["PRICE_QUESTION"].get("trigger_regex")
            if price_pattern and re.search(price_pattern, sentence_lower):
                return "PRICE_QUESTION"

        # 3. PHRASAL_VERB: "ждать", "смотреть", "идти"
        if self.extended_patterns and "PHRASAL_VERB" in self.extended_patterns:
            trigger_verbs = self.extended_patterns["PHRASAL_VERB"].get("trigger_verbs", [])
            if any(verb in sentence_lower for verb in trigger_verbs):
                return "PHRASAL_VERB"

        # Стандартные шаблоны
        has_subject = structure.get("subject") is not None
        has_verb = structure.get("verb") is not None
        has_object = structure.get("object") is not None
        has_indirect = structure.get("indirect_object") is not None

        adverbial_found = False
        prepositions = {'в', 'во', 'на', 'у', 'с', 'к', 'из', 'без', 'о', 'об', 'за', 'по'}
        for word in structure["words_ru"]:
            if word.lower() in prepositions:
                adverbial_found = True
                break

        if not has_subject or not has_verb:
            return "SV"

        verb = structure.get("verb", "").lower()
        dative_verbs = {"дал", "дала", "дало", "дали", "дать", "подарил", "подарила", "отдал", "отдала", "передал",
                        "передала"}
        if has_indirect and has_object and verb in dative_verbs:
            return "SVOO"

        if has_object and adverbial_found:
            return "SVOA"
        elif has_object:
            return "SVO"
        elif adverbial_found:
            return "SVA"
        else:
            return "SV"

    def determine_article(self, structure: Dict, word_ru: str) -> str:
        """Определяет артикль для слова"""
        word_lower = word_ru.lower()

        # Неисчисляемые существительные — без артикля
        uncountable = {"чай", "кофе", "молоко", "вода", "дома", "работы"}
        if word_lower in uncountable:
            return ""

        # После предлогов — всегда "the" для конкретных мест
        if self.preposition_rules:
            specific_places = self.preposition_rules.get("article_after_preposition", {}).get("specific_places", [])
            if any(place in word_lower for place in ["парк", "офис", "сад", "деревн", "стол", "библиотек"]):
                return "the"

        # Исчисляемые существительные — "a"
        if word_lower in ["дом", "книга", "газета", "собака", "яблоко", "папа", "мама"]:
            return "a"

        return "a"

    def determine_sentence_pattern(self, structure: Dict, sentence: str) -> str:
        return self.detect_special_pattern(sentence, structure)

    def parse_russian_sentence_improved(self, sentence: str) -> Dict:
        original = sentence.strip()
        words = []

        if self.STANZA_AVAILABLE:
            stanza_analysis = self.stanza_syntax_analysis(original)
            if "error" not in stanza_analysis:
                for sent in stanza_analysis.get("sentences", []):
                    for word in sent.get("words", []):
                        words.append(word["text"])
            else:
                clean = re.sub(r'[^\w\s]', ' ', original)
                words = [w for w in clean.strip().split() if w]
        else:
            clean = re.sub(r'[^\w\s]', ' ', original)
            words = [w for w in clean.strip().split() if w]

        punctuation_marks = {'?', '!', '.', ',', ';', ':', '"', "'", '»', '«', '(', ')'}
        words = [w for w in words if w not in punctuation_marks]

        word_translations = {}
        for word in words:
            word_translations[word] = self.get_word_translation_improved(word)

        structure = {
            "original": original,
            "words_ru": words,
            "words_en": [word_translations[word] for word in words],
            "word_translations": word_translations,
            "type": self.detect_sentence_type(original),
            "subject": None,
            "verb": None,
            "object": None,
            "indirect_object": None,
            "verb_tense": None,
            "adverbs": [],
            "question_word": None,
            "punctuation": self.extract_punctuation(original),
            "stanza_used": self.STANZA_AVAILABLE,
            "morph_used": self.MORPH_AVAILABLE
        }

        self.advanced_syntax_analysis_with_stanza(structure, original)

        # Постобработка вопросительных слов
        if structure["type"] == "interrogative" and not structure.get("question_word"):
            question_words = {'что', 'кто', 'где', 'когда', 'почему', 'как', 'сколько'}
            for word in structure["words_ru"]:
                if word.lower() in question_words:
                    structure["question_word"] = word
                    break
        if structure["type"] == "interrogative" and "сколько" in sentence.lower():
            # Разбираем структуру "Сколько стоит/стоят X?"
            words_lower = [w.lower() for w in structure["words_ru"]]

            if "сколько" in words_lower:
                сколько_index = words_lower.index("сколько")

                # Ищем глагол "стоит" или "стоят"
                for i in range(сколько_index + 1, len(structure["words_ru"])):
                    word_lower = structure["words_ru"][i].lower()
                    if word_lower in ["стоит", "стоят"]:
                        # Следующее слово после глагола - это объект
                        if i + 1 < len(structure["words_ru"]):
                            next_word = structure["words_ru"][i + 1]
                            # Проверяем, что это не знак препинания
                            if next_word not in ['?', '!', '.', ',']:
                                structure["object"] = next_word
                        break

        # Обработка косвенного дополнения
        if structure["verb"]:
            verb_clean = structure["verb"].lower()
            dative_verbs = {"дал", "дала", "дало", "дали", "дать", "подарил", "подарила", "отдал", "отдала", "передал",
                            "передала"}
            if verb_clean in dative_verbs:
                verb_index = None
                for i, word in enumerate(structure["words_ru"]):
                    if word == structure["verb"]:
                        verb_index = i
                        break
                candidates = []
                if verb_index is not None:
                    for i in range(verb_index + 1, len(structure["words_ru"])):
                        word = structure["words_ru"][i]
                        if word == structure.get("object"):
                            continue
                        candidates.append(word)
                if structure.get("object") and len(candidates) >= 1:
                    structure["indirect_object"] = candidates[0]

        if structure["verb"]:
            verb_info = self.get_verb_info(structure["verb"])
            structure["verb_tense"] = verb_info["tense"]
            verb_inf_en = self._safe_translate_word(verb_info["infinitive"])
            structure["word_translations"][structure["verb"]] = verb_inf_en
            structure["words_en"] = [structure["word_translations"].get(w, w) for w in structure["words_ru"]]

        structure["pattern"] = self.determine_sentence_pattern(structure, original)
        return structure

    def detect_sentence_type(self, sentence: str) -> str:
        if '?' in sentence:
            return "interrogative"
        elif '!' in sentence:
            return "exclamative"
        else:
            return "declarative"

    def extract_punctuation(self, sentence: str) -> str:
        if sentence.endswith('?'):
            return '?'
        elif sentence.endswith('!'):
            return '!'
        else:
            return '.'

    def transform_sentence_structure(self, ru_structure: Dict) -> Dict:
        en_structure = ru_structure.copy()
        en_structure["rules_source"] = "JSON файл" if self.json_loaded else "Встроенные правила"
        transformations = []

        if en_structure["type"] == "interrogative":
            en_structure["word_order"] = "question_word + auxiliary + subject + verb"
            transformations.append("Инверсия вопроса")
        else:
            transformations.append(f"Применён шаблон: {en_structure['pattern']}")

        en_structure["transformations"] = transformations
        return en_structure

    def build_improved_question(self, en_structure: Dict) -> str:
        """Построение вопросительного предложения"""
        words = []
        question_word = en_structure.get("question_word", "").lower()

        # Специальная обработка для "сколько"
        if question_word == "сколько":
            pattern = self.detect_special_pattern(en_structure["original"], en_structure)

            if pattern == "PRICE_QUESTION":
                # Получаем объект разными способами
                obj_ru = en_structure.get("object")

                # Способ 1: Из структуры
                if not obj_ru:
                    # Способ 2: Из анализа слов
                    words_ru = en_structure.get("words_ru", [])
                    for i, word in enumerate(words_ru):
                        if word.lower() == "сколько" and i + 2 < len(words_ru):
                            # Пропускаем "стоит/стоят"
                            obj_ru = words_ru[i + 2]
                            break

                # Способ 3: Находим первое существительное после глагола
                if not obj_ru:
                    verb_found = False
                    words_ru = en_structure.get("words_ru", [])
                    for word in words_ru:
                        if word.lower() in ["стоит", "стоят"]:
                            verb_found = True
                            continue
                        if verb_found and word not in ["сколько", "?"]:
                            obj_ru = word
                            break

                # Если объект не найден
                if not obj_ru:
                    return "How much does it cost?"

                obj_ru_lower = obj_ru.lower()

                # Определяем тип объекта
                uncountable_nouns = {"кофе", "чай", "молоко", "вода", "сахар", "соль", "хлеб"}
                countable_nouns = {"яблоки", "яблоко", "книги", "книга", "газеты", "газета", "собаки", "собака"}

                # Получаем перевод
                obj_en = en_structure["word_translations"].get(obj_ru, obj_ru)

                # Используем JSON правила если доступны
                if self.json_loaded and "PRICE_QUESTION" in self.extended_patterns:
                    price_config = self.extended_patterns["PRICE_QUESTION"]
                    question_mapping = price_config.get("question_mapping", {})

                    is_uncountable = any(unc in obj_ru_lower for unc in uncountable_nouns)
                    is_countable = any(cnt in obj_ru_lower for cnt in countable_nouns)

                    if is_uncountable:
                        mapping = question_mapping.get("uncountable", {})
                    elif is_countable:
                        mapping = question_mapping.get("countable", {})
                    else:
                        # По умолчанию для неизвестных слов
                        mapping = question_mapping.get("uncountable", {})

                    # Извлекаем компоненты
                    q_word = mapping.get("question_word", "How much")
                    auxiliary = mapping.get("auxiliary", "does")
                    verb_word = mapping.get("verb", "cost")

                    # Подставляем объект в subject если нужно
                    subject_text = mapping.get("subject", "{object}")
                    if "{object}" in subject_text:
                        subject_text = subject_text.replace("{object}", obj_en)

                    # Собираем вопрос
                    return f"{q_word} {auxiliary} {subject_text} {verb_word}?"

                # Fallback
                if any(unc in obj_ru_lower for unc in uncountable_nouns):
                    return f"How much does {obj_en} cost?"
                else:
                    return f"How much do {obj_en} cost?"

        # Стандартная обработка для других вопросов
        if en_structure.get("question_word"):
            q_ru = en_structure["question_word"].lower()
            q_en = self.correction_dict.get(q_ru, q_ru)
            words.append(q_en.capitalize())

        subject_ru = en_structure.get("subject", "")
        subj_lower = subject_ru.lower() if subject_ru else ""

        # Вспомогательный глагол
        if subj_lower in ["он", "она", "оно", "папа", "мама"]:
            auxiliary = "does"
        else:
            auxiliary = "do"

        words.append(auxiliary)

        if subject_ru:
            subj_en = self.correction_dict.get(
                subj_lower,
                en_structure["word_translations"].get(subject_ru, subject_ru)
            )
            words.append(subj_en)

        if en_structure.get("verb"):
            verb_base = en_structure["word_translations"].get(
                en_structure["verb"],
                en_structure["verb"]
            )
            words.append(verb_base)

        # Добавляем остальные слова
        to_skip = set()
        if en_structure.get("question_word"):
            to_skip.add(en_structure["question_word"].lower())
        if en_structure.get("subject"):
            to_skip.add(en_structure["subject"].lower())
        if en_structure.get("verb"):
            to_skip.add(en_structure["verb"].lower())

        for word_ru in en_structure.get("words_ru", []):
            if word_ru.lower() in to_skip:
                continue

            if word_ru == en_structure.get("object"):
                article = self.determine_article(en_structure, word_ru)
                if article:
                    words.append(article)
                word_en = en_structure["word_translations"].get(word_ru, word_ru)
                words.append(word_en)
            else:
                word_en = en_structure["word_translations"].get(word_ru, word_ru)
                words.append(word_en)

        return " ".join(words) + "?"

    def build_improved_statement(self, en_structure: Dict) -> str:
        pattern = en_structure.get("pattern", "SVO")

        # Проверяем специальные шаблоны из JSON
        if self.json_loaded and self.extended_patterns and pattern in self.extended_patterns:
            return self.generate_from_json_template(en_structure, pattern)

        # Стандартные шаблоны
        return self.generate_from_basic_pattern(en_structure, pattern)

    def generate_from_json_template(self, en_structure: Dict, pattern: str) -> str:
        """Генерация предложения строго по шаблону из JSON"""
        template_config = self.extended_patterns[pattern]
        template = template_config.get("template", "{subject} {verb}")

        # Базовые компоненты
        components = {}

        # Подлежащее и глагол
        if pattern == "POSSESSION":
            subject_ru = en_structure.get("subject", "").lower()
            subject_data = template_config["subject_mapping"].get(subject_ru, {"subject": subject_ru, "verb": "have"})
            components["subject"] = subject_data["subject"]
            components["verb"] = subject_data["verb"]

            # Объект
            obj_ru = en_structure.get("object", "")
            obj_en = en_structure["word_translations"].get(obj_ru, obj_ru)
            article = self.determine_article(en_structure, obj_ru)
            components["object"] = (article + " " + obj_en).strip() if article else obj_en

            # Место
            location = ""
            for word_ru in en_structure["words_ru"]:
                if word_ru.lower() in ["в", "во", "на", "у"] and word_ru != obj_ru:
                    idx = en_structure["words_ru"].index(word_ru)
                    if idx + 1 < len(en_structure["words_ru"]):
                        place_ru = en_structure["words_ru"][idx + 1]
                        place_en = en_structure["word_translations"].get(place_ru, place_ru)
                        location = f" in the {place_en}"
            components["location"] = location

            try:
                result = template.format(**components)
                return result + en_structure["punctuation"]
            except KeyError as e:
                pass

        elif pattern == "PHRASAL_VERB":
            subject_ru = en_structure.get("subject", "").lower()
            subject_en = self.correction_dict.get(subject_ru,
                                                  en_structure["word_translations"].get(en_structure.get("subject", ""),
                                                                                        subject_ru))
            components["subject"] = subject_en.capitalize()

            verb_ru = en_structure.get("verb", "").lower()
            verb_mapping = template_config.get("verb_mapping", {})
            verb_data = verb_mapping.get(verb_ru, {"verb_phrase": verb_ru})
            components["verb_phrase"] = verb_data["verb_phrase"]

            obj_ru = en_structure.get("object", "")
            components["object"] = en_structure["word_translations"].get(obj_ru, obj_ru)

            # Место
            location = ""
            for word_ru in en_structure["words_ru"]:
                if word_ru.lower() in ["в", "во", "на", "у"] and word_ru != obj_ru:
                    idx = en_structure["words_ru"].index(word_ru)
                    if idx + 1 < len(en_structure["words_ru"]):
                        place_ru = en_structure["words_ru"][idx + 1]
                        place_en = en_structure["word_translations"].get(place_ru, place_ru)
                        location = f" in the {place_en}"
            components["location"] = location

            try:
                result = template.format(**components)
                return result + en_structure["punctuation"]
            except KeyError as e:
                pass

        # Если что-то пошло не так, fallback
        return self.generate_from_basic_pattern(en_structure, pattern)

    def generate_from_basic_pattern(self, en_structure: Dict, pattern: str) -> str:
        words = []
        if en_structure.get("subject"):
            subj_ru = en_structure["subject"].lower()
            subj_en = self.correction_dict.get(subj_ru, en_structure["word_translations"].get(en_structure["subject"],
                                                                                              en_structure["subject"]))
            words.append(subj_en.capitalize())
        if en_structure.get("verb"):
            verb_base = en_structure["word_translations"][en_structure["verb"]]
            # Согласование для 3-го лица
            subject_ru = en_structure.get("subject", "").lower()
            if subject_ru in ["он", "она", "оно", "папа", "мама", "учитель"]:
                if verb_base == "have":
                    verb_conj = "has"
                elif verb_base == "do":
                    verb_conj = "does"
                else:
                    verb_conj = verb_base + "s"
                words.append(verb_conj)
            else:
                words.append(verb_base)
        if pattern == "SVOO":
            if en_structure.get("indirect_object"):
                words.append(en_structure["word_translations"][en_structure["indirect_object"]])
            if en_structure.get("object"):
                article = self.determine_article(en_structure, en_structure["object"])
                if article:
                    words.append(article)
                words.append(en_structure["word_translations"][en_structure["object"]])
        elif pattern in ["SVOA", "SVO"]:
            if en_structure.get("object"):
                article = self.determine_article(en_structure, en_structure["object"])
                if article:
                    words.append(article)
                words.append(en_structure["word_translations"][en_structure["object"]])
            if pattern == "SVOA":
                # Добавляем обстоятельства в конец
                for word_ru in en_structure["words_ru"]:
                    if word_ru in [en_structure.get("subject"), en_structure.get("verb"), en_structure.get("object")]:
                        continue
                    word_en = en_structure["word_translations"][word_ru]
                    if word_ru.lower() not in ["в", "во", "на", "у"]:  # Пропускаем предлоги
                        words.append(word_en)
        return " ".join(words) + en_structure["punctuation"]

    def generate_english_sentence(self, en_structure: Dict) -> str:
        if en_structure["type"] == "interrogative":
            return self.build_improved_question(en_structure)
        else:
            return self.build_improved_statement(en_structure)

    def translate_with_analysis(self, russian_sentence: str) -> Dict:
        ru_structure = self.parse_russian_sentence_improved(russian_sentence)
        en_structure = self.transform_sentence_structure(ru_structure)
        translation = self.generate_english_sentence(en_structure)
        return {
            "original": russian_sentence,
            "translation": translation,
            "word_translations": ru_structure["word_translations"],
            "syntax_transformations": en_structure["transformations"],
            "sentence_type": ru_structure["type"],
            "sentence_pattern": ru_structure["pattern"],
            "rules_source": en_structure.get("rules_source", "Неизвестно"),
            "sentence_structure": {
                "subject": ru_structure["subject"],
                "verb": ru_structure["verb"],
                "object": ru_structure["object"],
                "indirect_object": ru_structure["indirect_object"],
                "question_word": ru_structure["question_word"]
            },
            "stanza_used": ru_structure["stanza_used"],
            "morph_used": ru_structure["morph_used"]
        }


def demonstrate_stanza_translator():
    translator = AdvancedTransformationalTranslator()
    test_sentences = [
        "В парке я вижу собаку.",
        "Она пьёт чай с молоком.",
        "Когда я пришел домой, мама готовила ужин.",
        "У меня есть дом в деревне.",
        "Я кладу книгу на стол.",
        "Кто работает в офисе?",
        "Что делает папа в саду?",
        "Сколько стоит кофе?",
        "Сколько стоят яблоки?",
        "Они читают газету и пьют воду.",
        "Я иду в парк.",
        "Он видит большой дом.",
        "Я жду тебя здесь.",
        "Мы начали читать книгу вчера."
    ]
    print("\n" + "=" * 70)
    print("ДЕМОНСТРАЦИЯ: ОБНОВЛЕННЫЙ ПЕРЕВОДЧИК")
    print("=" * 70)
    for i, sentence in enumerate(test_sentences, 1):
        print(f"\n{i}. 📝 РУССКИЙ: {sentence}")
        result = translator.translate_with_analysis(sentence)
        print(f"   🌐 АНГЛИЙСКИЙ: {result['translation']}")
        print(f"   🔤 Переводы слов: {result['word_translations']}")
        print(f"   🏗️  Шаблон: {result['sentence_pattern']}")
        print("-" * 70)


if __name__ == "__main__":
    demonstrate_stanza_translator()