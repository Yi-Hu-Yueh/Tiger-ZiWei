plugins {
    id("com.android.application")
}

android {
    namespace = "com.tiger.ziwei"
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }

    defaultConfig {
        applicationId = "com.tiger.ziwei"
        minSdk = 29
        targetSdk = 36
        versionCode = 2
        versionName = "9.1"
    }

    buildTypes {
        debug {
            manifestPlaceholders["usesCleartextTraffic"] = "false"
        }
        release {
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            isMinifyEnabled = false
        }
    }
    sourceSets.getByName("main").apply {
        assets.srcDir("../../app/static")
    }
}

dependencies {
    implementation(project(":ziwei-core"))
    testImplementation("junit:junit:4.13.2")
}
