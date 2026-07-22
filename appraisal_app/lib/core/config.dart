import 'package:flutter/material.dart';

class AppConfig {
  static const String appName = "Staff Appraisal System";
  
  static String get defaultBaseUrl {
    // USB (adb reverse tcp:9092 tcp:9092): use http://127.0.0.1:9092/api
    // Physical device over Wi-Fi: tap ⚙️ on login screen and enter http://<YOUR_PC_IP>:9092/api
    return "https://appraisalsystem.site/api";
  }

  // Exact Website Accent & Brand Palette (Emerald to Teal Gradient)
  static const Color primaryColor = Color(0xFF059669); // Emerald 600
  static const Color secondaryColor = Color(0xFF0D9488); // Teal 600
  static const Color accentColor = Color(0xFF10B981); // Emerald 500
  static const Color warningColor = Color(0xFFF59E0B); // Amber 500
  static const Color dangerColor = Color(0xFFEF4444); // Rose 500
  
  // Website Dark Palette (dark:bg-[#0b0f1a], card:bg-[#0d1117] / bg-slate-900)
  static const Color darkBackgroundColor = Color(0xFF0B0F1A); // Deep Slate 950
  static const Color darkCardColor = Color(0xFF131B2E); // Slate 900
  static const Color darkSurfaceColor = Color(0xFF1E293B); // Slate 800
  static const Color darkTextPrimary = Color(0xFFF8FAFC); // Slate 50
  static const Color darkTextSecondary = Color(0xFF94A3B8); // Slate 400

  // Website Light Palette (bg-slate-50, card:bg-white, text-slate-900)
  static const Color lightBackgroundColor = Color(0xFFF8FAFC); // Slate 50
  static const Color lightCardColor = Color(0xFFFFFFFF); // White
  static const Color lightSurfaceColor = Color(0xFFF1F5F9); // Slate 100
  static const Color lightTextPrimary = Color(0xFF0F172A); // Slate 900
  static const Color lightTextSecondary = Color(0xFF64748B); // Slate 500

  // Legacy fallback constants
  static const Color backgroundColor = darkBackgroundColor;
  static const Color cardColor = darkCardColor;
  static const Color surfaceColor = darkSurfaceColor;
  static const Color textPrimary = darkTextPrimary;
  static const Color textSecondary = darkTextSecondary;

  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF059669), Color(0xFF0D9488)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient accentGradient = LinearGradient(
    colors: [Color(0xFF10B981), Color(0xFF14B8A6)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static ThemeData getDarkTheme(TextTheme textTheme) {
    return ThemeData.dark().copyWith(
      scaffoldBackgroundColor: darkBackgroundColor,
      primaryColor: primaryColor,
      colorScheme: const ColorScheme.dark(
        primary: primaryColor,
        secondary: secondaryColor,
        surface: darkCardColor,
        onSurface: darkTextPrimary,
      ),
      cardColor: darkCardColor,
      appBarTheme: const AppBarTheme(
        backgroundColor: darkCardColor,
        foregroundColor: darkTextPrimary,
        elevation: 0,
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: darkCardColor,
        selectedItemColor: primaryColor,
        unselectedItemColor: darkTextSecondary,
      ),
      textTheme: textTheme.apply(
        bodyColor: darkTextPrimary,
        displayColor: darkTextPrimary,
      ),
    );
  }

  static ThemeData getLightTheme(TextTheme textTheme) {
    return ThemeData.light().copyWith(
      scaffoldBackgroundColor: lightBackgroundColor,
      primaryColor: primaryColor,
      colorScheme: const ColorScheme.light(
        primary: primaryColor,
        secondary: secondaryColor,
        surface: lightCardColor,
        onSurface: lightTextPrimary,
      ),
      cardColor: lightCardColor,
      appBarTheme: const AppBarTheme(
        backgroundColor: lightCardColor,
        foregroundColor: lightTextPrimary,
        elevation: 1,
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: lightCardColor,
        selectedItemColor: primaryColor,
        unselectedItemColor: lightTextSecondary,
      ),
      textTheme: textTheme.apply(
        bodyColor: lightTextPrimary,
        displayColor: lightTextPrimary,
      ),
    );
  }
}

extension ThemeContextX on BuildContext {
  bool get isDarkMode => Theme.of(this).brightness == Brightness.dark;
  Color get textPrimary => isDarkMode ? AppConfig.darkTextPrimary : AppConfig.lightTextPrimary;
  Color get textSecondary => isDarkMode ? AppConfig.darkTextSecondary : AppConfig.lightTextSecondary;
  Color get cardColor => Theme.of(this).cardColor;
  Color get surfaceColor => isDarkMode ? AppConfig.darkSurfaceColor : AppConfig.lightSurfaceColor;
  Color get bgColor => Theme.of(this).scaffoldBackgroundColor;
}
