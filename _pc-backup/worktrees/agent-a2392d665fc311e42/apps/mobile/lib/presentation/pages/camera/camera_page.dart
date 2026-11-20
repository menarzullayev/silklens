// SILK-0099 — CameraPage: live viewfinder + heritage recognition
//
// Flow: camera preview → capture/pick → upload → recognizeImage → show result
// State goes through RecognitionNotifier; no Dio in this file.

import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/recognition_provider.dart';

// ---------------------------------------------------------------------------
// CameraPage
// ---------------------------------------------------------------------------

class CameraPage extends ConsumerStatefulWidget {
  const CameraPage({super.key});

  @override
  ConsumerState<CameraPage> createState() => _CameraPageState();
}

class _CameraPageState extends ConsumerState<CameraPage> with WidgetsBindingObserver {
  // ---- state ----
  List<CameraDescription> _cameras = [];
  CameraController? _ctrl;
  bool _initialized = false;
  bool _busy = false; // upload+recognize in flight

  // ---- helpers ----
  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  // ---- lifecycle ----

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Colors.black,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final ctrl = _ctrl;
    if (ctrl == null || !ctrl.value.isInitialized) return;
    if (state == AppLifecycleState.inactive) {
      ctrl.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _initCamera();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ctrl?.dispose();
    super.dispose();
  }

  // ---- camera init ----

  Future<void> _initCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras.isEmpty) return;

      final ctrl = CameraController(
        _cameras.first,
        ResolutionPreset.high,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await ctrl.initialize();
      if (!mounted) return;
      setState(() {
        _ctrl = ctrl;
        _initialized = true;
      });
    } catch (e) {
      debugPrint('CameraPage init error: $e');
    }
  }

  // ---- actions ----

  Future<void> _captureAndRecognize() async {
    final ctrl = _ctrl;
    if (ctrl == null || !ctrl.value.isInitialized || _busy) return;

    setState(() => _busy = true);
    ref.read(recognitionProvider.notifier).reset();

    try {
      final photo = await ctrl.takePicture();
      final bytes = await File(photo.path).readAsBytes();
      await ref.read(recognitionProvider.notifier).analyzeBytes(
            bytes: bytes,
            filename: 'capture.jpg',
            mimeType: 'image/jpeg',
            language: LocaleService.instance.locale,
          );
    } catch (e) {
      debugPrint('Capture error: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickFromGallery() async {
    if (_busy) return;
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (image == null) return;

    setState(() => _busy = true);
    ref.read(recognitionProvider.notifier).reset();

    try {
      final bytes = await File(image.path).readAsBytes();
      await ref.read(recognitionProvider.notifier).analyzeBytes(
            bytes: bytes,
            filename: 'gallery.jpg',
            mimeType: 'image/jpeg',
            language: LocaleService.instance.locale,
          );
    } catch (e) {
      debugPrint('Gallery pick error: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _navigateToDetail(String heritagePubId) {
    if (!mounted) return;
    context.push('/home/heritage/$heritagePubId');
  }

  // ---- build ----

  @override
  Widget build(BuildContext context) {
    final recState = ref.watch(recognitionProvider);

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // ── Camera preview ───────────────────────────────────────────
          _buildPreview(),

          // ── Top bar ──────────────────────────────────────────────────
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    _iconBtn(
                      icon: Icons.close,
                      onTap: () => context.pop(),
                      semanticLabel: _s('camera_close'),
                    ),
                    const Spacer(),
                    Text(
                      _s('camera_title'),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.3,
                      ),
                    ),
                    const Spacer(),
                    _iconBtn(
                      icon: Icons.photo_library_outlined,
                      onTap: _pickFromGallery,
                      semanticLabel: _s('camera_gallery'),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // ── Viewfinder frame ─────────────────────────────────────────
          Center(
            child: IgnorePointer(
              child: Container(
                width: 272,
                height: 272,
                decoration: BoxDecoration(
                  border: Border.all(
                    color: const Color(0xFFB78628),
                    width: 2,
                  ),
                  borderRadius: BorderRadius.circular(20),
                ),
                alignment: Alignment.bottomCenter,
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    _s('camera_frame_hint'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white60,
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
            ),
          ),

          // ── Bottom area ───────────────────────────────────────────────
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Result card
                  _buildResultCard(recState),
                  const SizedBox(height: 24),
                  // Capture button
                  _buildCaptureButton(),
                  const SizedBox(height: 8),
                  // Voice assistant shortcut
                  TextButton.icon(
                    onPressed: () => context.push('/voice-assistant'),
                    icon: const Icon(
                      Icons.mic_none,
                      color: Color(0xFFB78628),
                      size: 18,
                    ),
                    label: Text(
                      _s('camera_voice_btn'),
                      style: const TextStyle(
                        color: Color(0xFFB78628),
                        fontSize: 13,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---- sub-widgets ----

  Widget _buildPreview() {
    if (_initialized && _ctrl != null) {
      return CameraPreview(_ctrl!);
    }
    return ColoredBox(
      color: Colors.black,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.camera_alt_outlined,
            size: 64,
            color: Colors.white24,
          ),
          const SizedBox(height: 12),
          Text(
            _s('camera_loading'),
            style: const TextStyle(color: Colors.white38, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildCaptureButton() {
    return GestureDetector(
      onTap: _captureAndRecognize,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: 72,
        height: 72,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _busy ? Colors.grey.shade700 : const Color(0xFFB78628),
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: _busy
              ? null
              : [
                  BoxShadow(
                    color: const Color(0xFFB78628).withAlpha(100),
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ],
        ),
        child: _busy
            ? const Center(
                child: SizedBox(
                  width: 28,
                  height: 28,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2.5,
                  ),
                ),
              )
            : const Icon(Icons.camera_alt, color: Colors.white, size: 32),
      ),
    );
  }

  Widget _buildResultCard(RecognitionState state) {
    if (state is RecognitionIdle) return const SizedBox.shrink();

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Container(
        key: ValueKey(state.runtimeType),
        margin: const EdgeInsets.symmetric(horizontal: 24),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.black.withAlpha(210),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: const Color(0xFFB78628).withAlpha(120),
          ),
        ),
        child: switch (state) {
          RecognitionLoading() => Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Color(0xFFB78628),
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  _s('camera_analyzing'),
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          RecognitionError() => Row(
              children: [
                const Icon(
                  Icons.error_outline,
                  color: Colors.redAccent,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _s('camera_error'),
                    style: const TextStyle(
                      color: Colors.redAccent,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
          RecognitionSuccess(result: final result) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.auto_awesome,
                      color: Color(0xFFB78628),
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        result.topLabel.isNotEmpty ? result.topLabel : _s('camera_unknown'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${_s('camera_confidence')}: '
                  '${(result.confidence * 100).toStringAsFixed(0)}%',
                  style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 12,
                  ),
                ),
                if (result.candidates.isNotEmpty &&
                    result.candidates.first.heritagePubId.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  GestureDetector(
                    onTap: () => _navigateToDetail(
                      result.candidates.first.heritagePubId,
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFFB78628),
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: Text(
                        _s('camera_view_detail'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          RecognitionIdle() => const SizedBox.shrink(),
        },
      ),
    );
  }

  Widget _iconBtn({
    required IconData icon,
    required VoidCallback onTap,
    required String semanticLabel,
  }) {
    return Semantics(
      label: semanticLabel,
      button: true,
      child: Material(
        color: Colors.white.withAlpha(26),
        borderRadius: BorderRadius.circular(24),
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Icon(icon, color: Colors.white, size: 24),
          ),
        ),
      ),
    );
  }
}
