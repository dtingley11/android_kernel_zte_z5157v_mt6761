import com.android.build.api.dsl.ApplicationDefaultConfig
import com.android.build.api.dsl.CommonExtension
import com.android.build.gradle.api.AndroidBasePlugin
import java.io.ByteArrayOutputStream

plugins {
    alias(libs.plugins.agp.app) apply false
    alias(libs.plugins.agp.lib) apply false
    alias(libs.plugins.kotlin) apply false
    alias(libs.plugins.compose.compiler) apply false
    alias(libs.plugins.lsplugin.cmaker)
}

// Opt in explicitly; the kernel-side ARM32 port is still incomplete.
val arm32Experimental = providers.gradleProperty("ksuArm32Experimental")
    .map(String::toBoolean).getOrElse(false)
val managerAbis = if (arm32Experimental) listOf("armeabi-v7a")
    else listOf("arm64-v8a", "x86_64", "riscv64")

cmaker {
    default {
        arguments.addAll(
            arrayOf(
                "-DANDROID_STL=none",
            )
        )
        abiFilters(*managerAbis.toTypedArray())
    }
    buildTypes {
        if (it.name == "release") {
            arguments += "-DDEBUG_SYMBOLS_PATH=${layout.buildDirectory.asFile.get().absolutePath}/symbols"
        }
    }
}

val androidMinSdkVersion = 26
val androidTargetSdkVersion = 36
val androidCompileSdkVersion = 36
val androidBuildToolsVersion = "36.1.0"
val androidCompileNdkVersion by extra(libs.versions.ndk.get())
val androidSourceCompatibility = JavaVersion.VERSION_21
val androidTargetCompatibility = JavaVersion.VERSION_21
val managerVersionCode by extra(if (arm32Experimental) 33355 else getVersionCode())
val managerVersionName by extra(if (arm32Experimental) "v3.4.2-arm32-experimental" else getVersionName())

fun getGitCommitCount(): Int {
    val process = Runtime.getRuntime().exec(arrayOf("git", "rev-list", "--count", "HEAD"))
    return process.inputStream.bufferedReader().use { it.readText().trim().toInt() }
}

fun getGitDescribe(): String {
    val process = Runtime.getRuntime().exec(arrayOf("git", "describe", "--tags", "--always"))
    return process.inputStream.bufferedReader().use { it.readText().trim() }
}

fun getVersionCode(): Int {
    val commitCount = getGitCommitCount()
    val major = 1
    return major * 30000 + commitCount
}

fun getVersionName(): String {
    return getGitDescribe()
}

subprojects {
    plugins.withType(AndroidBasePlugin::class.java) {
        extensions.configure(CommonExtension::class.java) {
            compileSdk = androidCompileSdkVersion
            ndkVersion = androidCompileNdkVersion

            defaultConfig {
                minSdk = androidMinSdkVersion
                if (this is ApplicationDefaultConfig) {
                    targetSdk = androidTargetSdkVersion
                    versionCode = managerVersionCode
                    versionName = managerVersionName
                }
                ndk {
                    abiFilters += managerAbis
                }
            }

            lint {
                abortOnError = true
                checkReleaseBuilds = false
            }

            compileOptions {
                sourceCompatibility = androidSourceCompatibility
                targetCompatibility = androidTargetCompatibility
            }
        }
    }
}
