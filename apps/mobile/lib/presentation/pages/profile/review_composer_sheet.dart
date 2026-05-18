// Modal for composing a multi-dimension review. Each dimension is a 1–5 star
// row. The body is a free-form text field with a language selector.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/social/entities/review_dimensions.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/locale_provider.dart";
import "package:silklens/presentation/providers/social_provider.dart";

class ReviewComposerSheet extends ConsumerStatefulWidget {
  const ReviewComposerSheet({required this.heritagePubId, super.key});

  final String heritagePubId;

  @override
  ConsumerState<ReviewComposerSheet> createState() =>
      _ReviewComposerSheetState();
}

class _ReviewComposerSheetState extends ConsumerState<ReviewComposerSheet> {
  int? _history;
  int? _photos;
  int? _access;
  int? _value;
  int? _atmosphere;
  int? _family;
  late String _language = ref.read(activeLocaleProvider).languageCode;
  final TextEditingController _body = TextEditingController();

  @override
  void dispose() {
    _body.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final draft = ReviewDraft(
      heritagePubId: widget.heritagePubId,
      dimensions: ReviewDimensions(
        history: _history,
        photos: _photos,
        access: _access,
        value: _value,
        atmosphere: _atmosphere,
        familyFriendly: _family,
      ),
      body: _body.text.trim().isEmpty ? null : _body.text.trim(),
      language: _language,
    );
    await ref.read(reviewSubmissionControllerProvider.notifier).submit(draft);
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final submitState = ref.watch(reviewSubmissionControllerProvider);

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(context).viewInsets.bottom + 20,
        ),
        child: SingleChildScrollView(
          key: const Key("review_composer.scroll"),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Text(
                l10n?.reviewComposerTitle ?? "Write a review",
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              _StarRow(
                label: l10n?.reviewDimHistory ?? "History",
                value: _history,
                onChanged: (int v) => setState(() => _history = v),
                semanticPrefix: "history",
              ),
              _StarRow(
                label: l10n?.reviewDimPhotos ?? "Photos",
                value: _photos,
                onChanged: (int v) => setState(() => _photos = v),
                semanticPrefix: "photos",
              ),
              _StarRow(
                label: l10n?.reviewDimAccess ?? "Access",
                value: _access,
                onChanged: (int v) => setState(() => _access = v),
                semanticPrefix: "access",
              ),
              _StarRow(
                label: l10n?.reviewDimValue ?? "Value",
                value: _value,
                onChanged: (int v) => setState(() => _value = v),
                semanticPrefix: "value",
              ),
              _StarRow(
                label: l10n?.reviewDimAtmosphere ?? "Atmosphere",
                value: _atmosphere,
                onChanged: (int v) => setState(() => _atmosphere = v),
                semanticPrefix: "atmosphere",
              ),
              _StarRow(
                label: l10n?.reviewDimFamilyFriendly ?? "Family-friendly",
                value: _family,
                onChanged: (int v) => setState(() => _family = v),
                semanticPrefix: "family",
              ),
              const SizedBox(height: 16),
              TextField(
                key: const Key("review_composer.body"),
                controller: _body,
                minLines: 3,
                maxLines: 8,
                decoration: InputDecoration(
                  border: const OutlineInputBorder(),
                  labelText: l10n?.reviewComposerBodyLabel ?? "Your review",
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _language,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(value: "uz", child: Text("O'zbek")),
                  DropdownMenuItem<String>(value: "en", child: Text("English")),
                  DropdownMenuItem<String>(value: "ru", child: Text("Русский")),
                  DropdownMenuItem<String>(value: "zh", child: Text("中文")),
                ],
                onChanged: (String? v) {
                  if (v != null) setState(() => _language = v);
                },
                decoration: InputDecoration(
                  border: const OutlineInputBorder(),
                  labelText: l10n?.reviewComposerLanguage ?? "Language",
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                key: const Key("review_composer.submit"),
                onPressed: submitState.isLoading ? null : _submit,
                child: submitState.isLoading
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(l10n?.reviewComposerSubmit ?? "Submit"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StarRow extends StatelessWidget {
  const _StarRow({
    required this.label,
    required this.value,
    required this.onChanged,
    required this.semanticPrefix,
  });

  final String label;
  final int? value;
  final ValueChanged<int> onChanged;
  final String semanticPrefix;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: <Widget>[
          Expanded(child: Text(label)),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: List<Widget>.generate(
              5,
              (int i) => IconButton(
                key: Key("review_composer.$semanticPrefix.${i + 1}"),
                iconSize: 24,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: () => onChanged(i + 1),
                icon: Icon(
                  (value ?? 0) > i ? Icons.star : Icons.star_outline,
                  color: Colors.amber,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
