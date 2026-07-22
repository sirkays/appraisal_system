import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';

import 'core/config.dart';
import 'providers/auth_provider.dart';
import 'providers/appraisal_provider.dart';
import 'providers/reviewer_provider.dart';
import 'providers/notification_provider.dart';
import 'providers/theme_provider.dart';
import 'providers/hr_provider.dart';

import 'screens/splash_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/main_screen.dart';
import 'screens/appraisal/my_appraisals_screen.dart';
import 'screens/appraisal/self_appraisal_screen.dart';
import 'screens/appraisal/appraisal_detail_screen.dart';
import 'screens/appraisal/review_queue_screen.dart';
import 'screens/appraisal/step_review_screen.dart';
import 'screens/notifications/notifications_screen.dart';
import 'screens/profile/profile_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AppraisalApp());
}

class AppraisalApp extends StatelessWidget {
  const AppraisalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => AuthProvider()..init()),
        ChangeNotifierProvider(create: (_) => AppraisalProvider()),
        ChangeNotifierProvider(create: (_) => ReviewerProvider()),
        ChangeNotifierProvider(create: (_) => NotificationProvider()),
        ChangeNotifierProvider(create: (_) => HrProvider()),
      ],
      child: Consumer2<AuthProvider, ThemeProvider>(
        builder: (context, auth, themeProvider, _) {
          final textTheme = GoogleFonts.plusJakartaSansTextTheme();

          return MaterialApp(
            title: AppConfig.appName,
            debugShowCheckedModeBanner: false,
            themeMode: themeProvider.themeMode,
            theme: AppConfig.getLightTheme(textTheme),
            darkTheme: AppConfig.getDarkTheme(textTheme),
            // SplashScreen is always the home — it handles its own
            // auth check and navigates to LoginScreen or MainScreen.
            home: const SplashScreen(),
            onGenerateRoute: (settings) {
              final name = settings.name;
              final args = settings.arguments;

              switch (name) {
                case '/login':
                  return MaterialPageRoute(builder: (_) => const LoginScreen());
                case '/main':
                case '/dashboard':
                  return MaterialPageRoute(builder: (_) => const MainScreen());
                case '/my_appraisals':
                  return MaterialPageRoute(builder: (_) => const MyAppraisalsScreen());
                case '/self_appraisal':
                  return MaterialPageRoute(
                    builder: (_) => SelfAppraisalScreen(appraisalId: args as int),
                  );
                case '/appraisal_detail':
                  return MaterialPageRoute(
                    builder: (_) => AppraisalDetailScreen(appraisalId: args as int),
                  );
                case '/review_queue':
                  return MaterialPageRoute(builder: (_) => const ReviewQueueScreen());
                case '/step_review':
                  return MaterialPageRoute(
                    builder: (_) => StepReviewScreen(queueItem: args as ReviewQueueItem),
                  );
                case '/notifications':
                  return MaterialPageRoute(builder: (_) => const NotificationsScreen());
                case '/profile':
                  return MaterialPageRoute(builder: (_) => const ProfileScreen());
                default:
                  return MaterialPageRoute(
                    builder: (_) => auth.isAuthenticated ? const MainScreen() : const LoginScreen(),
                  );
              }
            },
          );
        },
      ),
    );
  }
}
