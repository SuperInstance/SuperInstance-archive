"""
Multi-Language Translation Service
"""

import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..database import LanguageTranslation, LanguageCode


class TranslationService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.supported_languages = {
            "en_us": "English (US)",
            "es_es": "Spanish (Spain)", 
            "fr_fr": "French (France)",
            "de_de": "German (Germany)",
            "it_it": "Italian (Italy)",
            "pt_br": "Portuguese (Brazil)",
            "zh_cn": "Chinese (Simplified)",
            "ja_jp": "Japanese",
            "ko_kr": "Korean",
            "ru_ru": "Russian"
        }
        
        # Common phrases and responses by language
        self.common_phrases = {
            "greeting": {
                "en_us": "Hello! How can I help you today?",
                "es_es": "¡Hola! ¿Cómo puedo ayudarte hoy?",
                "fr_fr": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
                "de_de": "Hallo! Wie kann ich Ihnen heute helfen?",
                "it_it": "Ciao! Come posso aiutarti oggi?",
                "pt_br": "Olá! Como posso ajudá-lo hoje?",
                "zh_cn": "您好！今天我能为您做些什么？",
                "ja_jp": "こんにちは！今日はどのようにお手伝いできますか？",
                "ko_kr": "안녕하세요! 오늘 어떻게 도와드릴까요?",
                "ru_ru": "Привет! Чем могу помочь вам сегодня?"
            },
            "goodbye": {
                "en_us": "Thank you for contacting us. Have a great day!",
                "es_es": "Gracias por contactarnos. ¡Que tengas un gran día!",
                "fr_fr": "Merci de nous avoir contactés. Passez une excellente journée !",
                "de_de": "Vielen Dank, dass Sie uns kontaktiert haben. Haben Sie einen schönen Tag!",
                "it_it": "Grazie per averci contattato. Buona giornata!",
                "pt_br": "Obrigado por entrar em contato conosco. Tenha um ótimo dia!",
                "zh_cn": "感谢您联系我们。祝您有美好的一天！",
                "ja_jp": "お問い合わせいただきありがとうございます。良い一日をお過ごしください！",
                "ko_kr": "저희에게 연락해 주셔서 감사합니다. 좋은 하루 되세요!",
                "ru_ru": "Спасибо, что связались с нами. Хорошего дня!"
            },
            "escalation": {
                "en_us": "I'm connecting you with a human agent who can better assist you.",
                "es_es": "Te estoy conectando con un agente humano que puede ayudarte mejor.",
                "fr_fr": "Je vous mets en relation avec un agent humain qui pourra mieux vous aider.",
                "de_de": "Ich verbinde Sie mit einem menschlichen Agenten, der Ihnen besser helfen kann.",
                "it_it": "Ti sto collegando con un agente umano che può aiutarti meglio.",
                "pt_br": "Estou conectando você com um agente humano que pode ajudá-lo melhor.",
                "zh_cn": "我正在为您连接能够更好地帮助您的人工客服。",
                "ja_jp": "より良いサポートを提供できる人間のエージェントにおつなぎします。",
                "ko_kr": "더 나은 도움을 드릴 수 있는 상담원과 연결해드리겠습니다.",
                "ru_ru": "Я соединяю вас с оператором, который сможет лучше помочь вам."
            }
        }
    
    async def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context_category: str = "general"
    ) -> Dict[str, Any]:
        """Translate text from source to target language"""
        
        if source_language == target_language:
            return {
                "translated_text": text,
                "confidence": 1.0,
                "cached": False
            }
        
        if source_language not in self.supported_languages:
            raise ValueError(f"Unsupported source language: {source_language}")
        
        if target_language not in self.supported_languages:
            raise ValueError(f"Unsupported target language: {target_language}")
        
        # Check cache first
        cached_translation = await self._get_cached_translation(
            text, source_language, target_language
        )
        
        if cached_translation:
            # Update usage count
            await self._update_translation_usage(cached_translation.id)
            return {
                "translated_text": cached_translation.translated_text,
                "confidence": cached_translation.confidence_score,
                "cached": True
            }
        
        # Perform translation (mock implementation)
        translated_text = await self._perform_translation(
            text, source_language, target_language
        )
        
        confidence = await self._calculate_translation_confidence(
            text, translated_text, source_language, target_language
        )
        
        # Cache translation
        await self._cache_translation(
            text, translated_text, source_language, target_language,
            confidence, context_category
        )
        
        return {
            "translated_text": translated_text,
            "confidence": confidence,
            "cached": False
        }
    
    async def get_phrase_translation(
        self,
        phrase_key: str,
        target_language: str
    ) -> str:
        """Get pre-translated common phrase"""
        
        if phrase_key in self.common_phrases:
            phrases = self.common_phrases[phrase_key]
            if target_language in phrases:
                return phrases[target_language]
            # Fallback to English if target language not available
            return phrases.get("en_us", "")
        
        return ""
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language of input text"""
        
        # Mock language detection (in production, use Azure Translator, Google Translate, etc.)
        await asyncio.sleep(0.01)  # Simulate API call
        
        # Simple heuristic detection based on character patterns
        detected_languages = []
        
        # Check for common patterns
        if any(char in text for char in "¿¡ñáéíóú"):
            detected_languages.append({"language": "es_es", "confidence": 0.85})
        elif any(char in text for char in "àâäéèêëîïôöùûüÿç"):
            detected_languages.append({"language": "fr_fr", "confidence": 0.80})
        elif any(char in text for char in "äöüß"):
            detected_languages.append({"language": "de_de", "confidence": 0.85})
        elif any('\u4e00' <= char <= '\u9fff' for char in text):
            detected_languages.append({"language": "zh_cn", "confidence": 0.90})
        elif any('\u3040' <= char <= '\u309f' for char in text) or any('\u30a0' <= char <= '\u30ff' for char in text):
            detected_languages.append({"language": "ja_jp", "confidence": 0.95})
        elif any('\uac00' <= char <= '\ud7af' for char in text):
            detected_languages.append({"language": "ko_kr", "confidence": 0.90})
        elif any(char in text for char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
            detected_languages.append({"language": "ru_ru", "confidence": 0.85})
        else:
            detected_languages.append({"language": "en_us", "confidence": 0.95})
        
        # Default to English if no specific patterns detected
        if not detected_languages:
            detected_languages.append({"language": "en_us", "confidence": 0.5})
        
        return {
            "detected_languages": detected_languages,
            "primary_language": detected_languages[0]["language"],
            "confidence": detected_languages[0]["confidence"]
        }
    
    async def get_localized_responses(
        self,
        response_templates: Dict[str, str],
        target_language: str
    ) -> Dict[str, str]:
        """Get localized versions of response templates"""
        
        localized = {}
        
        for key, template in response_templates.items():
            if target_language == "en_us":
                localized[key] = template
            else:
                translation_result = await self.translate_text(
                    template, "en_us", target_language, "response_template"
                )
                localized[key] = translation_result["translated_text"]
        
        return localized
    
    async def validate_translation_quality(
        self,
        original_text: str,
        translated_text: str,
        source_language: str,
        target_language: str
    ) -> Dict[str, Any]:
        """Validate quality of translation"""
        
        # Mock quality validation
        quality_score = 0.85  # Would use actual quality metrics
        
        issues = []
        if len(translated_text) < len(original_text) * 0.3:
            issues.append("Translation appears too short")
            quality_score -= 0.2
        
        if len(translated_text) > len(original_text) * 3:
            issues.append("Translation appears too long")
            quality_score -= 0.1
        
        return {
            "quality_score": max(0, quality_score),
            "issues": issues,
            "is_acceptable": quality_score >= 0.7,
            "recommendations": self._get_quality_recommendations(issues)
        }
    
    # Private methods
    async def _get_cached_translation(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> Optional[LanguageTranslation]:
        """Get cached translation if available"""
        
        stmt = select(LanguageTranslation).where(
            LanguageTranslation.source_text == text,
            LanguageTranslation.source_language == source_language,
            LanguageTranslation.target_language == target_language,
            LanguageTranslation.is_validated == True
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _update_translation_usage(self, translation_id):
        """Update usage count for cached translation"""
        
        stmt = update(LanguageTranslation).where(
            LanguageTranslation.id == translation_id
        ).values(
            usage_count=LanguageTranslation.usage_count + 1
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _perform_translation(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        """Perform actual translation (mock implementation)"""
        
        # Mock translation - in production, use real translation service
        await asyncio.sleep(0.1)  # Simulate API call
        
        # For demo purposes, return the original text with a language indicator
        language_names = {
            "en_us": "English",
            "es_es": "Spanish",
            "fr_fr": "French",
            "de_de": "German",
            "it_it": "Italian",
            "pt_br": "Portuguese",
            "zh_cn": "Chinese",
            "ja_jp": "Japanese",
            "ko_kr": "Korean",
            "ru_ru": "Russian"
        }
        
        target_name = language_names.get(target_language, "Unknown")
        return f"[{target_name} translation of: {text}]"
    
    async def _calculate_translation_confidence(
        self,
        original_text: str,
        translated_text: str,
        source_language: str,
        target_language: str
    ) -> float:
        """Calculate confidence in translation quality"""
        
        # Mock confidence calculation
        base_confidence = 0.85
        
        # Adjust based on language pair complexity
        complex_pairs = [("en_us", "zh_cn"), ("en_us", "ja_jp"), ("en_us", "ko_kr")]
        if (source_language, target_language) in complex_pairs or \
           (target_language, source_language) in complex_pairs:
            base_confidence -= 0.1
        
        # Adjust based on text length
        if len(original_text) > 100:
            base_confidence -= 0.05
        
        return max(0.5, base_confidence)
    
    async def _cache_translation(
        self,
        source_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        confidence: float,
        context_category: str
    ):
        """Cache translation for future use"""
        
        translation = LanguageTranslation(
            source_language=source_language,
            target_language=target_language,
            source_text=source_text,
            translated_text=translated_text,
            confidence_score=confidence,
            context_category=context_category,
            is_validated=confidence >= 0.8,  # Auto-validate high confidence translations
            usage_count=1
        )
        
        self.db.add(translation)
        await self.db.commit()
    
    def _get_quality_recommendations(self, issues: List[str]) -> List[str]:
        """Get recommendations for improving translation quality"""
        
        recommendations = []
        
        for issue in issues:
            if "too short" in issue:
                recommendations.append("Consider manual review for completeness")
            elif "too long" in issue:
                recommendations.append("Review for unnecessary elaboration")
        
        if not recommendations:
            recommendations.append("Translation appears to be of good quality")
        
        return recommendations