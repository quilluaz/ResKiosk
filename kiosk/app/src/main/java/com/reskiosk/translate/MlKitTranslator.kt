package com.reskiosk.translate

import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import com.google.mlkit.nl.translate.TranslateRemoteModel
import kotlinx.coroutines.tasks.await

class MlKitTranslator {

    // Cache translators
    private val translatorCache = mutableMapOf<String, Translator>()

    suspend fun translate(text: String, sourceLang: String, targetLang: String): String {
        if (sourceLang == targetLang) return text

        val source = mapLangCode(sourceLang)
        val target = mapLangCode(targetLang)

        if (source == null || target == null) return text // Fail safe: return original

        val key = "$source-$target"
        var translator = translatorCache[key]

        if (translator == null) {
            val options = TranslatorOptions.Builder()
                .setSourceLanguage(source)
                .setTargetLanguage(target)
                .build()
            translator = Translation.getClient(options)
            translatorCache[key] = translator
        }

        val t = translator!! // known non-null

        return try {
            t.translate(text).await()
        } catch (e: Exception) {
            throw e
        }
    }

    suspend fun downloadModel(langCode: String): Boolean {
        val code = mapLangCode(langCode) ?: return false
        val modelManager = com.google.mlkit.common.model.RemoteModelManager.getInstance()
        val model = TranslateRemoteModel.Builder(code).build()

        val conditions = DownloadConditions.Builder()
            .requireWifi()
            .build()

        return try {
            modelManager.download(model, conditions).await()
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun mapLangCode(appCode: String): String? {
        return when (appCode.lowercase()) {
            "en", "english" -> TranslateLanguage.ENGLISH
            "es", "spanish" -> TranslateLanguage.SPANISH
            "zh", "chinese" -> TranslateLanguage.CHINESE
            else -> null // Unsupported
        }
    }

    fun close() {
        translatorCache.values.forEach { it.close() }
        translatorCache.clear()
    }
}
