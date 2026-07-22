import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../core/config.dart';
import '../providers/auth_provider.dart';
import 'auth/login_screen.dart';
import 'main_screen.dart';

/// A premium animated splash screen with:
/// - Pulsing radial gradient background
/// - Floating particle orbs
/// - Animated icon with shimmer ring
/// - Staggered text reveal
/// - Progress indicator
/// - Smooth fade-out transition
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  // --- Animation Controllers ---
  late final AnimationController _bgPulseController;
  late final AnimationController _logoController;
  late final AnimationController _ringController;
  late final AnimationController _textController;
  late final AnimationController _particleController;
  late final AnimationController _exitController;

  // --- Animations ---
  late final Animation<double> _bgPulse;
  late final Animation<double> _logoScale;
  late final Animation<double> _logoFade;
  late final Animation<double> _ringRotation;
  late final Animation<double> _ringOpacity;
  late final Animation<double> _titleSlide;
  late final Animation<double> _titleFade;
  late final Animation<double> _subtitleSlide;
  late final Animation<double> _subtitleFade;
  late final Animation<double> _progressFade;
  late final Animation<double> _exitFade;

  // Particle data
  final List<_Particle> _particles = [];
  final int _particleCount = 12;

  @override
  void initState() {
    super.initState();
    _generateParticles();
    _setupAnimations();
    _startSequence();
  }

  void _generateParticles() {
    final rng = math.Random(42);
    for (int i = 0; i < _particleCount; i++) {
      _particles.add(_Particle(
        x: rng.nextDouble(),
        y: rng.nextDouble(),
        radius: 2.0 + rng.nextDouble() * 5.0,
        speed: 0.3 + rng.nextDouble() * 0.7,
        phase: rng.nextDouble() * 2 * math.pi,
        opacity: 0.08 + rng.nextDouble() * 0.18,
      ));
    }
  }

  void _setupAnimations() {
    // Background radial pulse (infinite, slow)
    _bgPulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3500),
    )..repeat(reverse: true);
    _bgPulse = CurvedAnimation(
      parent: _bgPulseController,
      curve: Curves.easeInOut,
    );

    // Logo entrance: scale + fade
    _logoController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _logoScale = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.elasticOut),
    );
    _logoFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _logoController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeIn),
      ),
    );

    // Shimmer ring rotation (infinite)
    _ringController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    )..repeat();
    _ringRotation = Tween<double>(begin: 0.0, end: 2 * math.pi).animate(
      CurvedAnimation(parent: _ringController, curve: Curves.linear),
    );
    _ringOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _logoController,
        curve: const Interval(0.4, 1.0, curve: Curves.easeIn),
      ),
    );

    // Particles
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 6),
    )..repeat();

    // Text stagger
    _textController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _titleSlide = Tween<double>(begin: 30.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _textController,
        curve: const Interval(0.0, 0.7, curve: Curves.easeOut),
      ),
    );
    _titleFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _textController,
        curve: const Interval(0.0, 0.6, curve: Curves.easeIn),
      ),
    );
    _subtitleSlide = Tween<double>(begin: 30.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _textController,
        curve: const Interval(0.25, 1.0, curve: Curves.easeOut),
      ),
    );
    _subtitleFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _textController,
        curve: const Interval(0.3, 1.0, curve: Curves.easeIn),
      ),
    );
    _progressFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _textController,
        curve: const Interval(0.6, 1.0, curve: Curves.easeIn),
      ),
    );

    // Exit fade
    _exitController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _exitFade = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(parent: _exitController, curve: Curves.easeIn),
    );
  }

  Future<void> _startSequence() async {
    // Step 1: Logo pops in
    await Future.delayed(const Duration(milliseconds: 200));
    if (!mounted) return;
    _logoController.forward();

    // Step 2: Text slides up
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    _textController.forward();

    // Step 3: Wait for auth to resolve, then navigate
    await Future.delayed(const Duration(milliseconds: 1800));
    if (!mounted) return;

    final auth = Provider.of<AuthProvider>(context, listen: false);
    // Wait until auth finishes initializing
    while (auth.isInitializing) {
      await Future.delayed(const Duration(milliseconds: 100));
      if (!mounted) return;
    }

    // Fade out & navigate
    await _exitController.forward();
    if (!mounted) return;

    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        transitionDuration: Duration.zero,
        pageBuilder: (_, __, ___) =>
            auth.isAuthenticated ? const MainScreen() : const LoginScreen(),
      ),
    );
  }

  @override
  void dispose() {
    _bgPulseController.dispose();
    _logoController.dispose();
    _ringController.dispose();
    _particleController.dispose();
    _textController.dispose();
    _exitController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return FadeTransition(
      opacity: _exitFade,
      child: Scaffold(
        backgroundColor: AppConfig.darkBackgroundColor,
        body: AnimatedBuilder(
          animation: Listenable.merge([
            _bgPulseController,
            _logoController,
            _ringController,
            _particleController,
            _textController,
          ]),
          builder: (context, _) {
            return Stack(
              fit: StackFit.expand,
              children: [
                // ── 1. Pulsing radial gradient background ──
                _buildBackground(size),

                // ── 2. Floating particles ──
                _buildParticles(size),

                // ── 3. Center content ──
                Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Logo with shimmer ring
                      _buildLogoSection(),
                      const SizedBox(height: 36),
                      // App title
                      _buildTitle(),
                      const SizedBox(height: 8),
                      // Subtitle
                      _buildSubtitle(),
                      const SizedBox(height: 48),
                      // Progress indicator
                      _buildProgress(),
                    ],
                  ),
                ),

                // ── 4. Version tag bottom ──
                _buildBottomTag(),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildBackground(Size size) {
    final pulse = _bgPulse.value;
    return CustomPaint(
      size: size,
      painter: _BackgroundPainter(pulse: pulse),
    );
  }

  Widget _buildParticles(Size size) {
    final t = _particleController.value;
    return CustomPaint(
      size: size,
      painter: _ParticlePainter(particles: _particles, t: t),
    );
  }

  Widget _buildLogoSection() {
    return ScaleTransition(
      scale: _logoScale,
      child: FadeTransition(
        opacity: _logoFade,
        child: SizedBox(
          width: 140,
          height: 140,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Outer glow ring
              FadeTransition(
                opacity: _ringOpacity,
                child: Transform.rotate(
                  angle: _ringRotation.value,
                  child: CustomPaint(
                    size: const Size(140, 140),
                    painter: _GlowRingPainter(),
                  ),
                ),
              ),
              // Inner static glow
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      AppConfig.primaryColor.withOpacity(0.15),
                      AppConfig.primaryColor.withOpacity(0.0),
                    ],
                  ),
                ),
              ),
              // Icon container
              Container(
                width: 88,
                height: 88,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: const LinearGradient(
                    colors: [Color(0xFF059669), Color(0xFF0D9488)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppConfig.primaryColor.withOpacity(0.45),
                      blurRadius: 28,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.verified_rounded,
                  color: Colors.white,
                  size: 44,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTitle() {
    return FadeTransition(
      opacity: _titleFade,
      child: Transform.translate(
        offset: Offset(0, _titleSlide.value),
        child: Text(
          AppConfig.appName,
          textAlign: TextAlign.center,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 24,
            fontWeight: FontWeight.w800,
            color: AppConfig.darkTextPrimary,
            letterSpacing: -0.5,
          ),
        ),
      ),
    );
  }

  Widget _buildSubtitle() {
    return FadeTransition(
      opacity: _subtitleFade,
      child: Transform.translate(
        offset: Offset(0, _subtitleSlide.value),
        child: Text(
          'Performance. Growth. Recognition.',
          textAlign: TextAlign.center,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppConfig.accentColor.withOpacity(0.85),
            letterSpacing: 0.8,
          ),
        ),
      ),
    );
  }

  Widget _buildProgress() {
    return FadeTransition(
      opacity: _progressFade,
      child: Column(
        children: [
          SizedBox(
            width: 160,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                backgroundColor: AppConfig.darkSurfaceColor,
                valueColor: const AlwaysStoppedAnimation<Color>(
                  AppConfig.primaryColor,
                ),
                minHeight: 3,
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            'Initializing...',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 12,
              color: AppConfig.darkTextSecondary,
              letterSpacing: 0.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomTag() {
    return Positioned(
      bottom: 36,
      left: 0,
      right: 0,
      child: FadeTransition(
        opacity: _subtitleFade,
        child: Column(
          children: [
            Container(
              width: 40,
              height: 1,
              color: AppConfig.darkTextSecondary.withOpacity(0.3),
            ),
            const SizedBox(height: 10),
            Text(
              'v1.0.0 • Secure & Encrypted',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 11,
                color: AppConfig.darkTextSecondary.withOpacity(0.5),
                letterSpacing: 0.6,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────
// Custom Painters
// ─────────────────────────────────────────────

class _BackgroundPainter extends CustomPainter {
  final double pulse;

  const _BackgroundPainter({required this.pulse});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final baseRadius = size.longestSide * 0.65;
    final pulseRadius = baseRadius * (1.0 + pulse * 0.15);

    // Warm emerald radial glow
    final paint1 = Paint()
      ..shader = RadialGradient(
        center: Alignment.center,
        radius: 1.0,
        colors: [
          const Color(0xFF059669).withOpacity(0.12 + pulse * 0.05),
          const Color(0xFF0D9488).withOpacity(0.06 + pulse * 0.03),
          const Color(0xFF0B0F1A).withOpacity(0.0),
        ],
        stops: const [0.0, 0.45, 1.0],
      ).createShader(Rect.fromCircle(
        center: Offset(cx, cy - size.height * 0.1),
        radius: pulseRadius,
      ));

    canvas.drawCircle(
      Offset(cx, cy - size.height * 0.1),
      pulseRadius,
      paint1,
    );

    // Secondary subtle teal glow (bottom corner)
    final paint2 = Paint()
      ..shader = RadialGradient(
        center: Alignment.center,
        radius: 1.0,
        colors: [
          const Color(0xFF0D9488).withOpacity(0.08 + pulse * 0.04),
          const Color(0xFF0B0F1A).withOpacity(0.0),
        ],
      ).createShader(Rect.fromCircle(
        center: Offset(cx * 1.5, cy * 1.6),
        radius: pulseRadius * 0.6,
      ));

    canvas.drawCircle(
      Offset(cx * 1.5, cy * 1.6),
      pulseRadius * 0.6,
      paint2,
    );
  }

  @override
  bool shouldRepaint(_BackgroundPainter old) => old.pulse != pulse;
}

class _Particle {
  final double x, y, radius, speed, phase, opacity;

  const _Particle({
    required this.x,
    required this.y,
    required this.radius,
    required this.speed,
    required this.phase,
    required this.opacity,
  });
}

class _ParticlePainter extends CustomPainter {
  final List<_Particle> particles;
  final double t;

  const _ParticlePainter({required this.particles, required this.t});

  @override
  void paint(Canvas canvas, Size size) {
    for (final p in particles) {
      final floatY = math.sin(t * 2 * math.pi * p.speed + p.phase) * 18.0;
      final floatX = math.cos(t * 2 * math.pi * p.speed * 0.5 + p.phase) * 10.0;

      final dx = p.x * size.width + floatX;
      final dy = p.y * size.height + floatY;

      final paint = Paint()
        ..color = AppConfig.primaryColor.withOpacity(p.opacity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);

      canvas.drawCircle(Offset(dx, dy), p.radius, paint);
    }
  }

  @override
  bool shouldRepaint(_ParticlePainter old) => old.t != t;
}

class _GlowRingPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2 - 2;

    // Dashed arc segments with gradient color
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        colors: [
          AppConfig.primaryColor.withOpacity(0.0),
          AppConfig.primaryColor,
          AppConfig.secondaryColor,
          AppConfig.primaryColor.withOpacity(0.0),
        ],
        stops: const [0.0, 0.3, 0.7, 1.0],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r));

    // Draw arc (270° sweep)
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r),
      -math.pi / 2,
      2 * math.pi * 0.75,
      false,
      paint,
    );

    // Small bright dot at the head
    final headAngle = -math.pi / 2 + 2 * math.pi * 0.75;
    final dotX = cx + r * math.cos(headAngle);
    final dotY = cy + r * math.sin(headAngle);
    final dotPaint = Paint()
      ..color = AppConfig.accentColor
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
    canvas.drawCircle(Offset(dotX, dotY), 4, dotPaint);
  }

  @override
  bool shouldRepaint(_GlowRingPainter _) => false;
}
