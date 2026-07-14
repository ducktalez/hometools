<#
.SYNOPSIS
    Setup, Build und optionales TV-Deployment für die hometools Android TV App.

.DESCRIPTION
    Prüft Voraussetzungen (JDK 17, Android SDK, local.properties, Gradle Wrapper JAR),
    führt den Build durch und kann die APK optional per ADB auf einen Android TV deployen.

.PARAMETER Action
    Aktion: "check" | "build" | "test" | "install" | "deploy"
    - check:   Nur Voraussetzungen prüfen
    - build:   APK bauen (assembleDebug)
    - test:    JVM-Unit-Tests ausführen (kein Emulator nötig)
    - install: APK auf verbundenes Gerät deployen (installDebug)
    - deploy:  build + per ADB auf TV deployen (TV_IP muss angegeben werden)

.PARAMETER TvIp
    IP-Adresse des Android TV (z.B. 192.168.178.100). Nur für "install"/"deploy" nötig.

.PARAMETER SdkPath
    Android SDK Pfad. Standard: C:\Users\<user>\AppData\Local\Android\Sdk

.EXAMPLE
    .\build.ps1 -Action check
    .\build.ps1 -Action build
    .\build.ps1 -Action test
    .\build.ps1 -Action deploy -TvIp 192.168.178.100
#>

param(
    [ValidateSet("check", "build", "test", "install", "deploy")]
    [string]$Action = "build",

    [string]$TvIp = "",

    [string]$SdkPath = "$env:LOCALAPPDATA\Android\Sdk"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir   # clients/androidtv/

# ── Farb-Ausgabe ─────────────────────────────────────────────────────────────

function Write-Ok   { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green  }
function Write-Warn { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Err  { param($msg) Write-Host "  [ERR] $msg" -ForegroundColor Red    }
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan     }

# ── Voraussetzungs-Checks ─────────────────────────────────────────────────────

function Test-Jdk {
    Write-Step "JDK 17 prüfen"
    $javaCmd = Get-Command java -ErrorAction SilentlyContinue
    if (-not $javaCmd) {
        Write-Err "Java nicht gefunden. Bitte JDK 17 installieren:"
        Write-Host "        winget install Microsoft.OpenJDK.17"
        Write-Host "        -- oder -- https://adoptium.net/de/temurin/releases/?version=17"
        return $false
    }
    $ver = java -version 2>&1 | Select-String "version"
    if ($ver -match '"17') {
        Write-Ok  "JDK 17 gefunden: $ver"
        return $true
    }
    Write-Warn "Java gefunden, aber Version ist nicht 17: $ver"
    Write-Host "        Bitte JAVA_HOME auf JDK 17 setzen."
    return $false
}

function Test-AndroidSdk {
    Write-Step "Android SDK prüfen"
    $sdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME }
               elseif ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT }
               else { $SdkPath }

    if (Test-Path "$sdkRoot\build-tools") {
        Write-Ok  "Android SDK gefunden: $sdkRoot"
        return $sdkRoot
    }
    Write-Err "Android SDK nicht gefunden in: $sdkRoot"
    Write-Host "        Optionen:"
    Write-Host "        A) Android Studio installieren: https://developer.android.com/studio"
    Write-Host "        B) Nur Kommandozeilen-Tools:    https://developer.android.com/studio#command-line-tools-only"
    Write-Host "           Dann: sdkmanager 'platforms;android-34' 'build-tools;34.0.0'"
    return $null
}

function Ensure-LocalProperties {
    param([string]$sdkRoot)
    Write-Step "local.properties prüfen"
    $lp = Join-Path $ProjectRoot "local.properties"
    if (Test-Path $lp) {
        Write-Ok  "local.properties vorhanden"
        return $true
    }
    if ($sdkRoot) {
        $sdkForward = $sdkRoot -replace '\\', '/'
        "sdk.dir=$sdkForward" | Out-File -FilePath $lp -Encoding utf8
        Write-Ok  "local.properties erstellt mit sdk.dir=$sdkForward"
        return $true
    }
    Write-Err "local.properties fehlt und kein SDK-Pfad bekannt."
    Write-Host "        Bitte manuell anlegen: echo sdk.dir=C:/Users/<User>/AppData/Local/Android/Sdk > local.properties"
    return $false
}

function Ensure-GradleWrapperJar {
    Write-Step "Gradle Wrapper JAR prüfen"
    $jar = Join-Path $ProjectRoot "gradle\wrapper\gradle-wrapper.jar"
    if (Test-Path $jar) {
        Write-Ok  "Gradle Wrapper JAR vorhanden"
        return $true
    }
    Write-Warn "Gradle Wrapper JAR fehlt (git-ignoriert). Generiere via 'gradle wrapper'..."
    $gradle = Get-Command gradle -ErrorAction SilentlyContinue
    if (-not $gradle) {
        Write-Err "gradle nicht im PATH. Bitte Gradle installieren:"
        Write-Host "        winget install Gradle.Gradle"
        Write-Host "        -- oder -- https://gradle.org/install/"
        Write-Host "        Dann: cd clients/androidtv && gradle wrapper --gradle-version 8.9"
        return $false
    }
    Push-Location $ProjectRoot
    try {
        gradle wrapper --gradle-version 8.9
        Write-Ok  "Gradle Wrapper JAR generiert"
        return $true
    } finally {
        Pop-Location
    }
}

function Get-Gradlew {
    $bat = Join-Path $ProjectRoot "gradlew.bat"
    if (Test-Path $bat) { return $bat }
    return Join-Path $ProjectRoot "gradlew"
}

# ── Aktionen ──────────────────────────────────────────────────────────────────

function Invoke-Check {
    $jdkOk  = Test-Jdk
    $sdkRoot = Test-AndroidSdk
    $propsOk = Ensure-LocalProperties -sdkRoot $sdkRoot
    $wrapOk  = Ensure-GradleWrapperJar

    Write-Host ""
    if ($jdkOk -and $sdkRoot -and $propsOk -and $wrapOk) {
        Write-Host "Alle Voraussetzungen erfüllt — bereit zum Bauen." -ForegroundColor Green
    } else {
        Write-Host "Einige Voraussetzungen fehlen (siehe oben)." -ForegroundColor Yellow
        exit 1
    }
}

function Invoke-Build {
    Invoke-Check
    Write-Step "APK bauen (assembleDebug)"
    $gradlew = Get-Gradlew
    Push-Location $ProjectRoot
    try {
        & $gradlew assembleDebug
        $apk = Get-ChildItem -Recurse "app\build\outputs\apk\debug\*.apk" | Select-Object -First 1
        if ($apk) {
            Write-Ok  "APK erstellt: $($apk.FullName)"
        }
    } finally {
        Pop-Location
    }
}

function Invoke-Test {
    Invoke-Check
    Write-Step "JVM-Unit-Tests ausführen (kein Emulator nötig)"
    $gradlew = Get-Gradlew
    Push-Location $ProjectRoot
    try {
        & $gradlew test
        Write-Ok  "Tests abgeschlossen. Report: app/build/reports/tests/testDebugUnitTest/index.html"
    } finally {
        Pop-Location
    }
}

function Invoke-Install {
    param([string]$tvIp)

    $sdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME }
               elseif ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT }
               else { $SdkPath }

    $adb = Get-Command adb -ErrorAction SilentlyContinue
    if (-not $adb) {
        $adbPath = "$sdkRoot\platform-tools\adb.exe"
        if (Test-Path $adbPath) {
            $env:PATH += ";$sdkRoot\platform-tools"
            $adb = Get-Command adb -ErrorAction SilentlyContinue
        }
    }
    if (-not $adb) {
        Write-Err "adb nicht gefunden. Sicherstellen dass Android SDK platform-tools im PATH sind."
        Write-Host "        Android SDK platform-tools Pfad: $sdkRoot\platform-tools"
        exit 1
    }

    if ($tvIp) {
        Write-Step "ADB: Verbinde mit TV ($tvIp)"
        adb connect "${tvIp}:5555"
        Start-Sleep 2
        $devices = adb devices | Select-String $tvIp
        if (-not $devices) {
            Write-Err "TV nicht erreichbar auf $tvIp. Prüfe:"
            Write-Host "        1. TV ist im gleichen WLAN"
            Write-Host "        2. ADB Debugging ist aktiviert (Einstellungen > Gerät > Entwickleroptionen)"
            Write-Host "        3. TV-IP-Adresse korrekt (Einstellungen > Netzwerk)"
            exit 1
        }
        Write-Ok  "TV verbunden"
    }

    Write-Step "APK auf Gerät installieren (installDebug)"
    $gradlew = Get-Gradlew
    Push-Location $ProjectRoot
    try {
        & $gradlew installDebug
        Write-Ok  "App installiert — starte 'hometools TV' auf dem Fernseher!"
    } finally {
        Pop-Location
    }
}

function Invoke-Deploy {
    param([string]$tvIp)
    if (-not $tvIp) {
        Write-Err "TvIp ist erforderlich für -Action deploy. Beispiel: .\build.ps1 -Action deploy -TvIp 192.168.178.100"
        exit 1
    }
    Invoke-Build
    Invoke-Install -tvIp $tvIp
}

# ── Main ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "hometools TV — Android Build Script" -ForegroundColor Cyan
Write-Host "Aktion: $Action  |  Projekt: $ProjectRoot"
Write-Host ""

switch ($Action) {
    "check"   { Invoke-Check }
    "build"   { Invoke-Build }
    "test"    { Invoke-Test }
    "install" { Invoke-Install -tvIp $TvIp }
    "deploy"  { Invoke-Deploy  -tvIp $TvIp }
}

