package com.reskiosk.network

import android.content.Context
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Body
import java.util.concurrent.TimeUnit

// Interface Definition
interface HubApi {
    @GET("admin/ping")
    suspend fun ping(): PingResponse

    @GET("kb/version")
    suspend fun getKbVersion(): KbVersionResponse

    @GET("kb/snapshot")
    suspend fun getKbSnapshot(): KbSnapshotResponse

    @GET("network/info")
    suspend fun getNetworkInfo(): NetworkInfoResponse
    
    @POST("query")
    suspend fun postQuery(@Body payload: Map<String, Any?>): QueryResponse
}

// Data Classes
data class PingResponse(val status: String, val hub_version: String)
data class KbVersionResponse(val kb_version: Int, val updated_at: Long?)
data class KbSnapshotResponse(val kb_version: Int, val articles: List<Any>, val structured_config: Any)
data class NetworkInfoResponse(val hub_ip: String, val network_mode: String, val connected_kiosks: Int)
data class QueryResponse(
    val answer_text_en: String,
    val answer_type: String,
    val confidence: Double,
    val clarification_categories: List<String>?,
    val kb_version: Int
)

object HubClient {
    private const val DEFAULT_TIMEOUT_SEC = 10L
    private var retrofit: Retrofit? = null
    
    fun getApi(context: Context, baseUrl: String): HubApi {
        if (retrofit == null || retrofit?.baseUrl().toString() != baseUrl) {
            val kioskId = getKioskId(context)
            
            val client = OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS) // Phase 4: 5s connect
                .readTimeout(10, TimeUnit.SECONDS)   // Phase 4: 10s read
                .addInterceptor { chain ->
                    val request = chain.request().newBuilder()
                        .addHeader("X-Kiosk-ID", kioskId)
                        .build()
                    chain.proceed(request)
                }
                .build()

            // Ensure baseUrl ends with /
            val validUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

            retrofit = Retrofit.Builder()
                .baseUrl(validUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        return retrofit!!.create(HubApi::class.java)
    }

    private fun getKioskId(context: Context): String {
        // Simple persistent ID
        val prefs = context.getSharedPreferences("reskiosk_prefs", Context.MODE_PRIVATE)
        var id = prefs.getString("kiosk_id", null)
        if (id == null) {
            id = java.util.UUID.randomUUID().toString()
            prefs.edit().putString("kiosk_id", id).apply()
        }
        return id
    }
}
