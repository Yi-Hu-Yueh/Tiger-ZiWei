plugins {
    id("com.android.library")
}

android {
    namespace = "com.tiger.ziwei.core"
    compileSdk {
        version = release(36) { minorApiLevel = 1 }
    }
    defaultConfig { minSdk = 29 }
    sourceSets.getByName("test").resources.srcDir("../golden")
}

dependencies {
    api(files("../libs/lunar-1.7.7.jar"))
    api(files("../libs/gson-2.11.0.jar"))
    testImplementation("junit:junit:4.13.2")
}
