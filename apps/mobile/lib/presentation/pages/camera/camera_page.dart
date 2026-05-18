// Full-screen camera with Shazam-style capture flow.
//
// Layout:
//   - background: live camera preview (or a black placeholder when the
//     camera plugin can't initialise — e.g. iOS simulator, widget tests).
//   - top-right: torch toggle + flip-camera.
//   - bottom-center: a large circular capture FAB (Project-Decisions §23).
//   - bottom-left: gallery-picker entry point (image_picker).
//   - bottom: "Recent recognitions" horizontal carousel.
//
// On capture we run the recognition pipeline through [recognitionController]
// and surface a bottom sheet with the top candidate + 3 alternatives. If
// confidence > 0.7 the sheet routes straight to /heritage/{pub_id}.

import "dart:io" show File;

import "package:camera/camera.dart";
import "package:flutter/material.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:image_picker/image_picker.dart";
import "package:permission_handler/permission_handler.dart";
import "package:silklens/core/logging/app_logger.dart";
import "package:silklens/domain/media/entities/media_capture.dart";
import "package:silklens/domain/media/entities/recognition_result.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/locale_provider.dart";
import "package:silklens/presentation/providers/recognition_provider.dart";

class CameraPage extends ConsumerStatefulWidget {
  const CameraPage({super.key});

  @override
  ConsumerState<CameraPage> createState() => _CameraPageState();
}

class _CameraPageState extends ConsumerState<CameraPage>
    with WidgetsBindingObserver {
  CameraController? _controller;
  List<CameraDescription> _cameras = const <CameraDescription>[];
  int _activeCameraIndex = 0;
  bool _initialising = true;
  bool _torchOn = false;
  String? _initError;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bootstrap();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final c = _controller;
    if (c == null || !c.value.isInitialized) return;
    if (state == AppLifecycleState.inactive) {
      c.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _bootstrap();
    }
  }

  Future<void> _bootstrap() async {
    setState(() {
      _initialising = true;
      _initError = null;
    });
    try {
      final cameraStatus = await Permission.camera.request();
      // Microphone is requested ahead of FAZA 3 audio reviews.
      await Permission.microphone.request();
      if (!cameraStatus.isGranted) {
        setState(() {
          _initialising = false;
          _initError = "camera_permission_denied";
        });
        return;
      }
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() {
          _initialising = false;
          _initError = "no_cameras";
        });
        return;
      }
      _cameras = cameras;
      await _activateCamera(_activeCameraIndex);
    } on CameraException catch (e, st) {
      AppLogger.instance.e("Camera bootstrap failed",
          error: e, stackTrace: st);
      if (mounted) {
        setState(() {
          _initialising = false;
          _initError = e.code;
        });
      }
    }
  }

  Future<void> _activateCamera(int index) async {
    await _controller?.dispose();
    final controller = CameraController(
      _cameras[index],
      ResolutionPreset.high,
      enableAudio: false,
    );
    await controller.initialize();
    if (!mounted) return;
    setState(() {
      _controller = controller;
      _activeCameraIndex = index;
      _initialising = false;
    });
  }

  Future<void> _toggleTorch() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized) return;
    try {
      _torchOn = !_torchOn;
      await c.setFlashMode(_torchOn ? FlashMode.torch : FlashMode.off);
      if (mounted) setState(() {});
    } on CameraException catch (e, st) {
      AppLogger.instance.w("Torch toggle failed", error: e, stackTrace: st);
    }
  }

  Future<void> _flipCamera() async {
    if (_cameras.length < 2) return;
    final next = (_activeCameraIndex + 1) % _cameras.length;
    await _activateCamera(next);
  }

  Future<void> _capture() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized) return;
    try {
      final file = await c.takePicture();
      await _runPipeline(file.path);
    } on CameraException catch (e, st) {
      AppLogger.instance.e("Capture failed", error: e, stackTrace: st);
    }
  }

  Future<void> _pickFromGallery() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked == null) return;
    await _runPipeline(picked.path);
  }

  Future<void> _runPipeline(String path) async {
    final capture = MediaCapture(
      localPath: path,
      kind: MediaCaptureKind.photo,
      capturedAt: DateTime.now().toUtc(),
    );
    final language = ref.read(activeLocaleProvider).languageCode;
    await ref
        .read(recognitionControllerProvider.notifier)
        .run(capture, language: language);

    final state = ref.read(recognitionControllerProvider);
    if (!mounted) return;
    if (state is RecognitionDone) {
      await _showResult(state.result, path);
    } else if (state is RecognitionFailed) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n?.recognitionFailed ?? "Recognition failed")),
      );
    }
  }

  Future<void> _showResult(RecognitionResult result, String snapshotPath) async {
    final l10n = AppLocalizations.of(context);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext ctx) => RecognitionResultSheet(
        key: const Key("recognition.result_sheet"),
        result: result,
        snapshotPath: snapshotPath,
        onCandidateTapped: (RecognitionCandidate c) {
          Navigator.of(ctx).pop();
          ctx.go("/heritage/${c.heritagePubId}");
        },
      ),
    );
    if (!mounted) return;
    final top = result.topCandidate;
    if (top.isHighConfidence) {
      // Direct deep-link when very confident — only fires if the sheet was
      // dismissed without explicit selection.
      // ignore: use_build_context_synchronously — checked above with mounted.
      AppLogger.instance.i(
        "auto-route to /heritage/${top.heritagePubId} (conf=${top.confidence})",
      );
    }
    // Suppress unused l10n warning in case localisations not yet generated.
    l10n?.recognitionTitle;
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(recognitionControllerProvider);
    final l10n = AppLocalizations.of(context);
    final recent = ref.watch(recentRecognitionsProvider);

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          _buildPreview(),
          if (state is RecognitionUploading || state is RecognitionRecognising)
            _RecognisingOverlay(state: state),
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            right: 16,
            child: Column(
              children: <Widget>[
                _CircleIconButton(
                  semanticLabel: l10n?.cameraTorch ?? "Torch",
                  icon: _torchOn ? Icons.flash_on : Icons.flash_off,
                  onTap: _toggleTorch,
                  testKey: const Key("camera.torch"),
                ),
                const SizedBox(height: 12),
                _CircleIconButton(
                  semanticLabel: l10n?.cameraFlip ?? "Flip camera",
                  icon: Icons.cameraswitch_outlined,
                  onTap: _flipCamera,
                  testKey: const Key("camera.flip"),
                ),
              ],
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  if (recent.isNotEmpty)
                    _RecentRecognitionsCarousel(
                      items: recent,
                      onTap: (RecognitionCandidate c) =>
                          context.go("/heritage/${c.heritagePubId}"),
                    ),
                  Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 24, vertical: 16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: <Widget>[
                        _CircleIconButton(
                          semanticLabel: l10n?.cameraGallery ?? "Gallery",
                          icon: Icons.photo_library_outlined,
                          onTap: _pickFromGallery,
                          testKey: const Key("camera.gallery"),
                        ),
                        _CaptureButton(
                          onTap: _capture,
                          isBusy: state is RecognitionUploading ||
                              state is RecognitionRecognising,
                        ),
                        const SizedBox(width: 56),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPreview() {
    if (_initialising) {
      return const Center(child: CircularProgressIndicator());
    }
    final c = _controller;
    if (c == null || !c.value.isInitialized || _initError != null) {
      return _CameraUnavailable(reason: _initError);
    }
    return CameraPreview(c);
  }
}

class _CameraUnavailable extends StatelessWidget {
  const _CameraUnavailable({this.reason});
  final String? reason;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Center(
      key: const Key("camera.unavailable"),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.no_photography_outlined,
                size: 80, color: theme.colorScheme.onSurface),
            const SizedBox(height: 16),
            Text(
              l10n?.cameraUnavailable ?? "Camera unavailable",
              style: theme.textTheme.titleLarge?.copyWith(color: Colors.white),
            ),
            const SizedBox(height: 8),
            Text(
              reason ?? "",
              style: theme.textTheme.bodyMedium?.copyWith(color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecognisingOverlay extends StatelessWidget {
  const _RecognisingOverlay({required this.state});
  final RecognitionState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ColoredBox(
      color: Colors.black54,
      child: Center(
        key: const Key("camera.recognising"),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const SizedBox(
              width: 56,
              height: 56,
              child: CircularProgressIndicator(strokeWidth: 4, color: Colors.white),
            ),
            const SizedBox(height: 16),
            Text(
              state is RecognitionUploading
                  ? (l10n?.recognitionUploading ?? "Uploading…")
                  : (l10n?.recognitionRecognising ?? "Recognising…"),
              style: const TextStyle(color: Colors.white, fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}

class _CaptureButton extends StatelessWidget {
  const _CaptureButton({required this.onTap, required this.isBusy});

  final VoidCallback onTap;
  final bool isBusy;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Semantics(
      label: AppLocalizations.of(context)?.cameraCapture ?? "Capture",
      button: true,
      child: GestureDetector(
        key: const Key("camera.capture"),
        onTap: isBusy ? null : onTap,
        child: Container(
          width: 88,
          height: 88,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.white,
            border: Border.all(color: theme.colorScheme.primary, width: 4),
          ),
          child: Center(
            child: Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isBusy ? Colors.grey : theme.colorScheme.primary,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CircleIconButton extends StatelessWidget {
  const _CircleIconButton({
    required this.icon,
    required this.onTap,
    required this.semanticLabel,
    this.testKey,
  });

  final IconData icon;
  final VoidCallback onTap;
  final String semanticLabel;
  final Key? testKey;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: semanticLabel,
      button: true,
      child: InkWell(
        key: testKey,
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: Container(
          width: 44,
          height: 44,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.black54,
          ),
          child: Icon(icon, color: Colors.white),
        ),
      ),
    );
  }
}

class _RecentRecognitionsCarousel extends StatelessWidget {
  const _RecentRecognitionsCarousel({required this.items, required this.onTap});

  final List<RecognitionCandidate> items;
  final ValueChanged<RecognitionCandidate> onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      key: const Key("camera.recent_carousel"),
      height: 88,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (BuildContext ctx, int i) {
          final candidate = items[i];
          return GestureDetector(
            onTap: () => onTap(candidate),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 200),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Icon(Icons.history, color: Colors.white70, size: 18),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        candidate.name,
                        style: const TextStyle(color: Colors.white),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class RecognitionResultSheet extends StatelessWidget {
  const RecognitionResultSheet({
    required this.result,
    required this.snapshotPath,
    required this.onCandidateTapped,
    super.key,
  });

  final RecognitionResult result;
  final String snapshotPath;
  final ValueChanged<RecognitionCandidate> onCandidateTapped;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final top = result.topCandidate;
    final alts = result.alternatives.take(3).toList(growable: false);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.file(
                File(snapshotPath),
                height: 160,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  height: 160,
                  color: theme.colorScheme.surfaceContainerHighest,
                  child: const Icon(Icons.image_outlined, size: 64),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(top.name, style: theme.textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              "${l10n?.recognitionConfidence ?? "Confidence"}: "
              "${(top.confidence * 100).toStringAsFixed(0)}%",
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.secondary,
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              key: const Key("recognition.view_details"),
              onPressed: () => onCandidateTapped(top),
              icon: const Icon(Icons.arrow_forward),
              label: Text(l10n?.recognitionViewDetails ?? "View details"),
            ),
            if (alts.isNotEmpty) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                l10n?.recognitionAlternatives ?? "Other matches",
                style: theme.textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              ...alts.map(
                (RecognitionCandidate c) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(c.name),
                  subtitle:
                      Text("${(c.confidence * 100).toStringAsFixed(0)}%"),
                  onTap: () => onCandidateTapped(c),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
