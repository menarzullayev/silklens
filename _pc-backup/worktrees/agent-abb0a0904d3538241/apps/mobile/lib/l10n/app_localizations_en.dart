// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'SilkLens';

  @override
  String get appTagline => 'See the Silk Road through your lens';

  @override
  String get onboardingTitle => 'Discover heritage with your camera';

  @override
  String get onboardingSubtitle =>
      'Point at any monument to instantly learn its story.';

  @override
  String get onboardingCta => 'Start exploring';

  @override
  String get onboardingSkip => 'Skip';

  @override
  String get onboardingSlide1Title => 'Recognize heritage in seconds';

  @override
  String get onboardingSlide1Body =>
      'Point your camera at any monument and our AI tells you what you are looking at.';

  @override
  String get onboardingSlide2Title => 'Listen to the story';

  @override
  String get onboardingSlide2Body =>
      'Personalized audio guides — choose your language and your favorite region.';

  @override
  String get onboardingSlide3Title => 'Build your atlas';

  @override
  String get onboardingSlide3Body =>
      'Save places, share reviews, and earn badges as you explore the Silk Road.';

  @override
  String get onboardingSignIn => 'Sign in';

  @override
  String get onboardingNext => 'Next';

  @override
  String get navMap => 'Map';

  @override
  String get navCamera => 'Camera';

  @override
  String get navProfile => 'Profile';

  @override
  String get navDiscover => 'Discover';

  @override
  String get navSaved => 'Saved';

  @override
  String get cameraPlaceholderTitle => 'Camera';

  @override
  String get cameraPlaceholderBody =>
      'Vision pipeline ships in FAZA 2 — Hafta 3.';

  @override
  String get mapPlaceholderTitle => 'Map';

  @override
  String get mapPlaceholderBody =>
      'Mapbox / OSM integration ships in FAZA 2 — Hafta 3.';

  @override
  String get profileTitle => 'Profile';

  @override
  String get profileLanguage => 'Language';

  @override
  String get profileTheme => 'Theme';

  @override
  String get profileSignOut => 'Sign out';

  @override
  String get profileGuestTitle => 'Guest';

  @override
  String get profileGuestBody =>
      'Sign in to sync your saved heritage across devices.';

  @override
  String get authEmailLabel => 'Email';

  @override
  String get authPasswordLabel => 'Password';

  @override
  String get authPasswordConfirmLabel => 'Confirm password';

  @override
  String get authDisplayNameLabel => 'Display name';

  @override
  String get authSignInTitle => 'Welcome back';

  @override
  String get authSignInSubtitle => 'Sign in to continue exploring.';

  @override
  String get authSignInCta => 'Sign in';

  @override
  String get authSignUpTitle => 'Create your account';

  @override
  String get authSignUpSubtitle =>
      'Save heritage, share reviews, unlock badges.';

  @override
  String get authSignUpCta => 'Create account';

  @override
  String get authForgotPasswordTitle => 'Forgot password';

  @override
  String get authForgotPasswordCta => 'Send reset link';

  @override
  String get authForgotPasswordBody =>
      'Password recovery is coming soon — we will email you instructions.';

  @override
  String get authHaveAccountQ => 'Already have an account?';

  @override
  String get authNoAccountQ => 'Don’t have an account?';

  @override
  String get authForgotLink => 'Forgot password?';

  @override
  String get authProvidersDivider => 'Or continue with';

  @override
  String get authProviderGoogle => 'Continue with Google';

  @override
  String get authProviderApple => 'Continue with Apple';

  @override
  String get authProviderTelegram => 'Continue with Telegram';

  @override
  String get authComingSoon => 'Coming soon';

  @override
  String get authErrorInvalidEmail => 'Enter a valid email address.';

  @override
  String get authErrorPasswordTooShort =>
      'Password must be at least 12 characters.';

  @override
  String get authErrorPasswordWeak =>
      'Password must contain upper- and lower-case letters and at least one digit.';

  @override
  String get authErrorPasswordsDontMatch => 'Passwords don’t match.';

  @override
  String get authErrorRequired => 'This field is required.';

  @override
  String get authErrorInvalidCredentials => 'Email or password is incorrect.';

  @override
  String get authErrorRateLimited =>
      'Too many attempts. Please try again later.';

  @override
  String get authErrorEmailTaken => 'That email is already registered.';

  @override
  String get authErrorNetwork => 'Network error. Check your connection.';

  @override
  String get authErrorUnknown => 'Something went wrong. Please try again.';

  @override
  String get heritageListTitle => 'Discover';

  @override
  String get heritageSearchHint => 'Search heritage, cities, eras...';

  @override
  String get heritageFilterAll => 'All';

  @override
  String get heritageFilterKind => 'Kind';

  @override
  String get heritageFilterCountry => 'Country';

  @override
  String get heritageEmpty => 'No heritage matches your filters yet.';

  @override
  String get heritageSearchEmptyTitle => 'Nothing here yet';

  @override
  String get heritageSearchEmptyBody =>
      'Try a different keyword or browse all heritage.';

  @override
  String get heritageRecentSearches => 'Recent searches';

  @override
  String get heritageDetailSave => 'Save';

  @override
  String get heritageDetailUnsave => 'Saved';

  @override
  String get heritageDetailShare => 'Share';

  @override
  String get heritageDetailAiGuide => 'AI guide';

  @override
  String get heritageDetailAiGuideTooltip => 'Coming in v2 build';

  @override
  String get heritageDetailOpenInMap => 'Open in map';

  @override
  String get heritageDetailPeriod => 'Period';

  @override
  String get heritageDetailCountry => 'Country';

  @override
  String get heritageDetailUnesco => 'UNESCO inscribed';

  @override
  String get heritageDetailSummary => 'Summary';

  @override
  String get heritageDetailAbout => 'About';

  @override
  String get heritageDetailLocation => 'Location';

  @override
  String get heritageSavedTitle => 'Saved';

  @override
  String get heritageSavedEmpty =>
      'Nothing saved yet. Tap save on any heritage detail page.';

  @override
  String get heritageLoadMoreError => 'Couldn’t load more — tap to retry.';

  @override
  String get commonRetry => 'Retry';

  @override
  String get commonClose => 'Close';

  @override
  String get commonCancel => 'Cancel';

  @override
  String get commonContinue => 'Continue';

  @override
  String get commonOk => 'OK';

  @override
  String get cameraTorch => 'Torch';

  @override
  String get cameraFlip => 'Flip camera';

  @override
  String get cameraGallery => 'Pick from gallery';

  @override
  String get cameraCapture => 'Capture';

  @override
  String get cameraUnavailable => 'Camera unavailable';

  @override
  String get recognitionUploading => 'Uploading…';

  @override
  String get recognitionRecognising => 'Recognising…';

  @override
  String get recognitionTitle => 'Recognised';

  @override
  String get recognitionConfidence => 'Confidence';

  @override
  String get recognitionViewDetails => 'View details';

  @override
  String get recognitionAlternatives => 'Other matches';

  @override
  String get recognitionFailed => 'Recognition failed';

  @override
  String get mapLocateMe => 'Locate me';

  @override
  String get mapOpen => 'Open';

  @override
  String get mapLayerHeritage => 'Heritage';

  @override
  String get mapLayerUnesco => 'UNESCO';

  @override
  String get mapLayerCities => 'Cities';

  @override
  String get chatTitle => 'Ask SilkLens';

  @override
  String get chatEmptyTitle => 'Ask anything about the Silk Road';

  @override
  String get chatInputHint => 'Type a message…';

  @override
  String get chatTtsHint => 'Play';

  @override
  String get chatSuggestionWhen => 'When was this monument built?';

  @override
  String get chatSuggestionHotels => 'What are the best hotels nearby?';

  @override
  String get chatSuggestionLegends => 'Tell me a legend about this place.';

  @override
  String get profileTabActivity => 'Activity';

  @override
  String get profileTabSaved => 'Saved';

  @override
  String get profileTabReviews => 'Reviews';

  @override
  String get profileTabFriends => 'Friends';

  @override
  String get profileTabSettings => 'Settings';

  @override
  String get profileActivityEmpty => 'No activity yet';

  @override
  String get profileSavedEmpty => 'No saved heritage yet';

  @override
  String get profileReviewsEmpty => 'Your reviews will appear here';

  @override
  String get profileReviewsNew => 'New review';

  @override
  String get profileFriendsEmpty => 'Invite friends to join SilkLens';

  @override
  String get profileFriendsInvite => 'Invite';

  @override
  String get profileNotifications => 'Notifications';

  @override
  String get profileNotificationsHint => 'Configure push & email';

  @override
  String get profileLogout => 'Log out';

  @override
  String get profileFollow => 'Follow';

  @override
  String get profileFollowing => 'Following';

  @override
  String get profileFollowers => 'Followers';

  @override
  String get profileUserNotFound => 'User not found';

  @override
  String get reviewComposerTitle => 'Write a review';

  @override
  String get reviewComposerBodyLabel => 'Your review';

  @override
  String get reviewComposerLanguage => 'Language';

  @override
  String get reviewComposerSubmit => 'Submit';

  @override
  String get reviewDimHistory => 'History';

  @override
  String get reviewDimPhotos => 'Photos';

  @override
  String get reviewDimAccess => 'Access';

  @override
  String get reviewDimValue => 'Value';

  @override
  String get reviewDimAtmosphere => 'Atmosphere';

  @override
  String get reviewDimFamilyFriendly => 'Family-friendly';

  @override
  String get gamificationLevel => 'Level';

  @override
  String get gamificationNoData => 'No data';

  @override
  String get gamificationStreakDays => 'day streak';

  @override
  String get gamificationBadgesTitle => 'Badges';

  @override
  String get gamificationBadgesEmpty => 'No badges yet';

  @override
  String get leaderboardTitle => 'Leaderboard';

  @override
  String get leaderboardWeekly => 'Weekly';

  @override
  String get leaderboardMonthly => 'Monthly';

  @override
  String get leaderboardAllTime => 'All-time';

  @override
  String get leaderboardFriends => 'Friends';

  @override
  String get billingPlansTitle => 'Choose a plan';

  @override
  String get billingPlansEmpty => 'No plans available';

  @override
  String get billingFreeLabel => 'Free';

  @override
  String get billingPerMonth => '/month';

  @override
  String get billingPerYear => '/year';

  @override
  String get billingCurrentPlan => 'Current';

  @override
  String get billingChoosePlan => 'Choose';

  @override
  String get billingCheckoutTitle => 'Checkout';

  @override
  String get billingCheckoutSubtitle =>
      'Enter your payment method to subscribe';

  @override
  String get billingCheckoutToken => 'Payment token';

  @override
  String get billingCheckoutMock => 'Mock payment (development only)';

  @override
  String get billingCheckoutSubmit => 'Subscribe';

  @override
  String get billingManageTitle => 'Manage subscription';

  @override
  String get billingNoActive => 'No active subscription';

  @override
  String get billingRenewsOn => 'Renews on';

  @override
  String get billingCancel => 'Cancel';

  @override
  String get billingResume => 'Resume';

  @override
  String get billingInvoicesTitle => 'Invoices';

  @override
  String get billingInvoicesEmpty => 'No invoices';
}
