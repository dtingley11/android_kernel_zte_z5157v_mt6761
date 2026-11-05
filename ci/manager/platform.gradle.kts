plugins {
    alias(libs.plugins.agp.lib)
    alias(libs.plugins.kotlin)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.ksp)
    id("kotlin-parcelize")
}

android {
    namespace = "com.dergoogler.mmrl.platform"
    defaultConfig {
        minSdk = 26
        consumerProguardFiles("consumer-rules.pro")
        externalNativeBuild.cmake.arguments += "-DANDROID_STL=c++_static"
        val aidlDir = file("src/main/aidl")
        aidlPackagedList += aidlDir.walkTopDown()
            .filter { it.isFile && it.extension == "aidl" }
            .map { it.relativeTo(aidlDir).path }.toList()
    }
    externalNativeBuild.cmake {
        path = file("src/main/jni/CMakeLists.txt")
        version = "3.22.1"
    }
    buildFeatures {
        compose = true
        aidl = true
    }
}

dependencies {
    compileOnly(libs.mmrl.hidden.api)
    implementation("com.github.MMRLApp.MMRL:ext:2bb00b3c2b")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("org.lsposed.hiddenapibypass:hiddenapibypass:4.3")
    implementation(platform(libs.androidx.compose.bom))
    implementation("androidx.compose.runtime:runtime")
    implementation("org.apache.commons:commons-compress:1.27.1")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi:1.15.1")
    ksp("com.squareup.moshi:moshi-kotlin-codegen:1.15.1")
}
