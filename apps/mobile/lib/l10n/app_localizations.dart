import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ru.dart';
import 'app_localizations_uz.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ru'),
    Locale('uz'),
    Locale('zh')
  ];

  /// User-visible product name. Per Project-Decisions §1 the canonical source for this string is the admin panel — this ARB key is the fallback when remote tenant branding is unavailable.
  ///
  /// In en, this message translates to:
  /// **'SilkLens'**
  String get appName;

  /// No description provided for @appTagline.
  ///
  /// In en, this message translates to:
  /// **'See the Silk Road through your lens'**
  String get appTagline;

  /// No description provided for @onboardingTitle.
  ///
  /// In en, this message translates to:
  /// **'Discover heritage with your camera'**
  String get onboardingTitle;

  /// No description provided for @onboardingSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Point at any monument to instantly learn its story.'**
  String get onboardingSubtitle;

  /// No description provided for @onboardingCta.
  ///
  /// In en, this message translates to:
  /// **'Start exploring'**
  String get onboardingCta;

  /// No description provided for @onboardingSkip.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get onboardingSkip;

  /// No description provided for @onboardingSlide1Title.
  ///
  /// In en, this message translates to:
  /// **'Recognize heritage in seconds'**
  String get onboardingSlide1Title;

  /// No description provided for @onboardingSlide1Body.
  ///
  /// In en, this message translates to:
  /// **'Point your camera at any monument and our AI tells you what you are looking at.'**
  String get onboardingSlide1Body;

  /// No description provided for @onboardingSlide2Title.
  ///
  /// In en, this message translates to:
  /// **'Listen to the story'**
  String get onboardingSlide2Title;

  /// No description provided for @onboardingSlide2Body.
  ///
  /// In en, this message translates to:
  /// **'Personalized audio guides — choose your language and your favorite region.'**
  String get onboardingSlide2Body;

  /// No description provided for @onboardingSlide3Title.
  ///
  /// In en, this message translates to:
  /// **'Build your atlas'**
  String get onboardingSlide3Title;

  /// No description provided for @onboardingSlide3Body.
  ///
  /// In en, this message translates to:
  /// **'Save places, share reviews, and earn badges as you explore the Silk Road.'**
  String get onboardingSlide3Body;

  /// No description provided for @onboardingSignIn.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get onboardingSignIn;

  /// No description provided for @onboardingNext.
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get onboardingNext;

  /// No description provided for @navMap.
  ///
  /// In en, this message translates to:
  /// **'Map'**
  String get navMap;

  /// No description provided for @navCamera.
  ///
  /// In en, this message translates to:
  /// **'Camera'**
  String get navCamera;

  /// No description provided for @navProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get navProfile;

  /// No description provided for @navDiscover.
  ///
  /// In en, this message translates to:
  /// **'Discover'**
  String get navDiscover;

  /// No description provided for @navSaved.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get navSaved;

  /// No description provided for @cameraPlaceholderTitle.
  ///
  /// In en, this message translates to:
  /// **'Camera'**
  String get cameraPlaceholderTitle;

  /// No description provided for @cameraPlaceholderBody.
  ///
  /// In en, this message translates to:
  /// **'Vision pipeline ships in FAZA 2 — Hafta 3.'**
  String get cameraPlaceholderBody;

  /// No description provided for @mapPlaceholderTitle.
  ///
  /// In en, this message translates to:
  /// **'Map'**
  String get mapPlaceholderTitle;

  /// No description provided for @mapPlaceholderBody.
  ///
  /// In en, this message translates to:
  /// **'Mapbox / OSM integration ships in FAZA 2 — Hafta 3.'**
  String get mapPlaceholderBody;

  /// No description provided for @profileTitle.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profileTitle;

  /// No description provided for @profileLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get profileLanguage;

  /// No description provided for @profileTheme.
  ///
  /// In en, this message translates to:
  /// **'Theme'**
  String get profileTheme;

  /// No description provided for @profileSignOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get profileSignOut;

  /// No description provided for @profileGuestTitle.
  ///
  /// In en, this message translates to:
  /// **'Guest'**
  String get profileGuestTitle;

  /// No description provided for @profileGuestBody.
  ///
  /// In en, this message translates to:
  /// **'Sign in to sync your saved heritage across devices.'**
  String get profileGuestBody;

  /// No description provided for @authEmailLabel.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get authEmailLabel;

  /// No description provided for @authPasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get authPasswordLabel;

  /// No description provided for @authPasswordConfirmLabel.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get authPasswordConfirmLabel;

  /// No description provided for @authDisplayNameLabel.
  ///
  /// In en, this message translates to:
  /// **'Display name'**
  String get authDisplayNameLabel;

  /// No description provided for @authSignInTitle.
  ///
  /// In en, this message translates to:
  /// **'Welcome back'**
  String get authSignInTitle;

  /// No description provided for @authSignInSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in to continue exploring.'**
  String get authSignInSubtitle;

  /// No description provided for @authSignInCta.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get authSignInCta;

  /// No description provided for @authSignUpTitle.
  ///
  /// In en, this message translates to:
  /// **'Create your account'**
  String get authSignUpTitle;

  /// No description provided for @authSignUpSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Save heritage, share reviews, unlock badges.'**
  String get authSignUpSubtitle;

  /// No description provided for @authSignUpCta.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get authSignUpCta;

  /// No description provided for @authForgotPasswordTitle.
  ///
  /// In en, this message translates to:
  /// **'Forgot password'**
  String get authForgotPasswordTitle;

  /// No description provided for @authForgotPasswordCta.
  ///
  /// In en, this message translates to:
  /// **'Send reset link'**
  String get authForgotPasswordCta;

  /// No description provided for @authForgotPasswordBody.
  ///
  /// In en, this message translates to:
  /// **'Password recovery is coming soon — we will email you instructions.'**
  String get authForgotPasswordBody;

  /// No description provided for @authHaveAccountQ.
  ///
  /// In en, this message translates to:
  /// **'Already have an account?'**
  String get authHaveAccountQ;

  /// No description provided for @authNoAccountQ.
  ///
  /// In en, this message translates to:
  /// **'Don’t have an account?'**
  String get authNoAccountQ;

  /// No description provided for @authForgotLink.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get authForgotLink;

  /// No description provided for @authProvidersDivider.
  ///
  /// In en, this message translates to:
  /// **'Or continue with'**
  String get authProvidersDivider;

  /// No description provided for @authProviderGoogle.
  ///
  /// In en, this message translates to:
  /// **'Continue with Google'**
  String get authProviderGoogle;

  /// No description provided for @authProviderApple.
  ///
  /// In en, this message translates to:
  /// **'Continue with Apple'**
  String get authProviderApple;

  /// No description provided for @authProviderTelegram.
  ///
  /// In en, this message translates to:
  /// **'Continue with Telegram'**
  String get authProviderTelegram;

  /// No description provided for @authComingSoon.
  ///
  /// In en, this message translates to:
  /// **'Coming soon'**
  String get authComingSoon;

  /// No description provided for @authErrorInvalidEmail.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid email address.'**
  String get authErrorInvalidEmail;

  /// No description provided for @authErrorPasswordTooShort.
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 12 characters.'**
  String get authErrorPasswordTooShort;

  /// No description provided for @authErrorPasswordWeak.
  ///
  /// In en, this message translates to:
  /// **'Password must contain upper- and lower-case letters and at least one digit.'**
  String get authErrorPasswordWeak;

  /// No description provided for @authErrorPasswordsDontMatch.
  ///
  /// In en, this message translates to:
  /// **'Passwords don’t match.'**
  String get authErrorPasswordsDontMatch;

  /// No description provided for @authErrorRequired.
  ///
  /// In en, this message translates to:
  /// **'This field is required.'**
  String get authErrorRequired;

  /// No description provided for @authErrorInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'Email or password is incorrect.'**
  String get authErrorInvalidCredentials;

  /// No description provided for @authErrorRateLimited.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Please try again later.'**
  String get authErrorRateLimited;

  /// No description provided for @authErrorEmailTaken.
  ///
  /// In en, this message translates to:
  /// **'That email is already registered.'**
  String get authErrorEmailTaken;

  /// No description provided for @authErrorNetwork.
  ///
  /// In en, this message translates to:
  /// **'Network error. Check your connection.'**
  String get authErrorNetwork;

  /// No description provided for @authErrorUnknown.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Please try again.'**
  String get authErrorUnknown;

  /// No description provided for @heritageListTitle.
  ///
  /// In en, this message translates to:
  /// **'Discover'**
  String get heritageListTitle;

  /// No description provided for @heritageSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search heritage, cities, eras...'**
  String get heritageSearchHint;

  /// No description provided for @heritageFilterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get heritageFilterAll;

  /// No description provided for @heritageFilterKind.
  ///
  /// In en, this message translates to:
  /// **'Kind'**
  String get heritageFilterKind;

  /// No description provided for @heritageFilterCountry.
  ///
  /// In en, this message translates to:
  /// **'Country'**
  String get heritageFilterCountry;

  /// No description provided for @heritageEmpty.
  ///
  /// In en, this message translates to:
  /// **'No heritage matches your filters yet.'**
  String get heritageEmpty;

  /// No description provided for @heritageSearchEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'Nothing here yet'**
  String get heritageSearchEmptyTitle;

  /// No description provided for @heritageSearchEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Try a different keyword or browse all heritage.'**
  String get heritageSearchEmptyBody;

  /// No description provided for @heritageRecentSearches.
  ///
  /// In en, this message translates to:
  /// **'Recent searches'**
  String get heritageRecentSearches;

  /// No description provided for @heritageDetailSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get heritageDetailSave;

  /// No description provided for @heritageDetailUnsave.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get heritageDetailUnsave;

  /// No description provided for @heritageDetailShare.
  ///
  /// In en, this message translates to:
  /// **'Share'**
  String get heritageDetailShare;

  /// No description provided for @heritageDetailAiGuide.
  ///
  /// In en, this message translates to:
  /// **'AI guide'**
  String get heritageDetailAiGuide;

  /// No description provided for @heritageDetailAiGuideTooltip.
  ///
  /// In en, this message translates to:
  /// **'Coming in v2 build'**
  String get heritageDetailAiGuideTooltip;

  /// No description provided for @heritageDetailOpenInMap.
  ///
  /// In en, this message translates to:
  /// **'Open in map'**
  String get heritageDetailOpenInMap;

  /// No description provided for @heritageDetailPeriod.
  ///
  /// In en, this message translates to:
  /// **'Period'**
  String get heritageDetailPeriod;

  /// No description provided for @heritageDetailCountry.
  ///
  /// In en, this message translates to:
  /// **'Country'**
  String get heritageDetailCountry;

  /// No description provided for @heritageDetailUnesco.
  ///
  /// In en, this message translates to:
  /// **'UNESCO inscribed'**
  String get heritageDetailUnesco;

  /// No description provided for @heritageDetailSummary.
  ///
  /// In en, this message translates to:
  /// **'Summary'**
  String get heritageDetailSummary;

  /// No description provided for @heritageDetailAbout.
  ///
  /// In en, this message translates to:
  /// **'About'**
  String get heritageDetailAbout;

  /// No description provided for @heritageDetailLocation.
  ///
  /// In en, this message translates to:
  /// **'Location'**
  String get heritageDetailLocation;

  /// No description provided for @heritageSavedTitle.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get heritageSavedTitle;

  /// No description provided for @heritageSavedEmpty.
  ///
  /// In en, this message translates to:
  /// **'Nothing saved yet. Tap save on any heritage detail page.'**
  String get heritageSavedEmpty;

  /// No description provided for @heritageLoadMoreError.
  ///
  /// In en, this message translates to:
  /// **'Couldn’t load more — tap to retry.'**
  String get heritageLoadMoreError;

  /// No description provided for @commonRetry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get commonRetry;

  /// No description provided for @commonClose.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get commonClose;

  /// No description provided for @commonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get commonCancel;

  /// No description provided for @commonContinue.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get commonContinue;

  /// No description provided for @commonOk.
  ///
  /// In en, this message translates to:
  /// **'OK'**
  String get commonOk;

  /// No description provided for @cameraTorch.
  ///
  /// In en, this message translates to:
  /// **'Torch'**
  String get cameraTorch;

  /// No description provided for @cameraFlip.
  ///
  /// In en, this message translates to:
  /// **'Flip camera'**
  String get cameraFlip;

  /// No description provided for @cameraGallery.
  ///
  /// In en, this message translates to:
  /// **'Pick from gallery'**
  String get cameraGallery;

  /// No description provided for @cameraCapture.
  ///
  /// In en, this message translates to:
  /// **'Capture'**
  String get cameraCapture;

  /// No description provided for @cameraUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Camera unavailable'**
  String get cameraUnavailable;

  /// No description provided for @recognitionUploading.
  ///
  /// In en, this message translates to:
  /// **'Uploading…'**
  String get recognitionUploading;

  /// No description provided for @recognitionRecognising.
  ///
  /// In en, this message translates to:
  /// **'Recognising…'**
  String get recognitionRecognising;

  /// No description provided for @recognitionTitle.
  ///
  /// In en, this message translates to:
  /// **'Recognised'**
  String get recognitionTitle;

  /// No description provided for @recognitionConfidence.
  ///
  /// In en, this message translates to:
  /// **'Confidence'**
  String get recognitionConfidence;

  /// No description provided for @recognitionViewDetails.
  ///
  /// In en, this message translates to:
  /// **'View details'**
  String get recognitionViewDetails;

  /// No description provided for @recognitionAlternatives.
  ///
  /// In en, this message translates to:
  /// **'Other matches'**
  String get recognitionAlternatives;

  /// No description provided for @recognitionFailed.
  ///
  /// In en, this message translates to:
  /// **'Recognition failed'**
  String get recognitionFailed;

  /// No description provided for @mapLocateMe.
  ///
  /// In en, this message translates to:
  /// **'Locate me'**
  String get mapLocateMe;

  /// No description provided for @mapOpen.
  ///
  /// In en, this message translates to:
  /// **'Open'**
  String get mapOpen;

  /// No description provided for @mapLayerHeritage.
  ///
  /// In en, this message translates to:
  /// **'Heritage'**
  String get mapLayerHeritage;

  /// No description provided for @mapLayerUnesco.
  ///
  /// In en, this message translates to:
  /// **'UNESCO'**
  String get mapLayerUnesco;

  /// No description provided for @mapLayerCities.
  ///
  /// In en, this message translates to:
  /// **'Cities'**
  String get mapLayerCities;

  /// No description provided for @chatTitle.
  ///
  /// In en, this message translates to:
  /// **'Ask SilkLens'**
  String get chatTitle;

  /// No description provided for @chatEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'Ask anything about the Silk Road'**
  String get chatEmptyTitle;

  /// No description provided for @chatInputHint.
  ///
  /// In en, this message translates to:
  /// **'Type a message…'**
  String get chatInputHint;

  /// No description provided for @chatTtsHint.
  ///
  /// In en, this message translates to:
  /// **'Play'**
  String get chatTtsHint;

  /// No description provided for @chatSuggestionWhen.
  ///
  /// In en, this message translates to:
  /// **'When was this monument built?'**
  String get chatSuggestionWhen;

  /// No description provided for @chatSuggestionHotels.
  ///
  /// In en, this message translates to:
  /// **'What are the best hotels nearby?'**
  String get chatSuggestionHotels;

  /// No description provided for @chatSuggestionLegends.
  ///
  /// In en, this message translates to:
  /// **'Tell me a legend about this place.'**
  String get chatSuggestionLegends;

  /// No description provided for @profileTabActivity.
  ///
  /// In en, this message translates to:
  /// **'Activity'**
  String get profileTabActivity;

  /// No description provided for @profileTabSaved.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get profileTabSaved;

  /// No description provided for @profileTabReviews.
  ///
  /// In en, this message translates to:
  /// **'Reviews'**
  String get profileTabReviews;

  /// No description provided for @profileTabFriends.
  ///
  /// In en, this message translates to:
  /// **'Friends'**
  String get profileTabFriends;

  /// No description provided for @profileTabSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get profileTabSettings;

  /// No description provided for @profileActivityEmpty.
  ///
  /// In en, this message translates to:
  /// **'No activity yet'**
  String get profileActivityEmpty;

  /// No description provided for @profileSavedEmpty.
  ///
  /// In en, this message translates to:
  /// **'No saved heritage yet'**
  String get profileSavedEmpty;

  /// No description provided for @profileReviewsEmpty.
  ///
  /// In en, this message translates to:
  /// **'Your reviews will appear here'**
  String get profileReviewsEmpty;

  /// No description provided for @profileReviewsNew.
  ///
  /// In en, this message translates to:
  /// **'New review'**
  String get profileReviewsNew;

  /// No description provided for @profileFriendsEmpty.
  ///
  /// In en, this message translates to:
  /// **'Invite friends to join SilkLens'**
  String get profileFriendsEmpty;

  /// No description provided for @profileFriendsInvite.
  ///
  /// In en, this message translates to:
  /// **'Invite'**
  String get profileFriendsInvite;

  /// No description provided for @profileNotifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get profileNotifications;

  /// No description provided for @profileNotificationsHint.
  ///
  /// In en, this message translates to:
  /// **'Configure push & email'**
  String get profileNotificationsHint;

  /// No description provided for @profileLogout.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get profileLogout;

  /// No description provided for @profileFollow.
  ///
  /// In en, this message translates to:
  /// **'Follow'**
  String get profileFollow;

  /// No description provided for @profileFollowing.
  ///
  /// In en, this message translates to:
  /// **'Following'**
  String get profileFollowing;

  /// No description provided for @profileFollowers.
  ///
  /// In en, this message translates to:
  /// **'Followers'**
  String get profileFollowers;

  /// No description provided for @profileUserNotFound.
  ///
  /// In en, this message translates to:
  /// **'User not found'**
  String get profileUserNotFound;

  /// No description provided for @reviewComposerTitle.
  ///
  /// In en, this message translates to:
  /// **'Write a review'**
  String get reviewComposerTitle;

  /// No description provided for @reviewComposerBodyLabel.
  ///
  /// In en, this message translates to:
  /// **'Your review'**
  String get reviewComposerBodyLabel;

  /// No description provided for @reviewComposerLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get reviewComposerLanguage;

  /// No description provided for @reviewComposerSubmit.
  ///
  /// In en, this message translates to:
  /// **'Submit'**
  String get reviewComposerSubmit;

  /// No description provided for @reviewDimHistory.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get reviewDimHistory;

  /// No description provided for @reviewDimPhotos.
  ///
  /// In en, this message translates to:
  /// **'Photos'**
  String get reviewDimPhotos;

  /// No description provided for @reviewDimAccess.
  ///
  /// In en, this message translates to:
  /// **'Access'**
  String get reviewDimAccess;

  /// No description provided for @reviewDimValue.
  ///
  /// In en, this message translates to:
  /// **'Value'**
  String get reviewDimValue;

  /// No description provided for @reviewDimAtmosphere.
  ///
  /// In en, this message translates to:
  /// **'Atmosphere'**
  String get reviewDimAtmosphere;

  /// No description provided for @reviewDimFamilyFriendly.
  ///
  /// In en, this message translates to:
  /// **'Family-friendly'**
  String get reviewDimFamilyFriendly;

  /// No description provided for @gamificationLevel.
  ///
  /// In en, this message translates to:
  /// **'Level'**
  String get gamificationLevel;

  /// No description provided for @gamificationNoData.
  ///
  /// In en, this message translates to:
  /// **'No data'**
  String get gamificationNoData;

  /// No description provided for @gamificationStreakDays.
  ///
  /// In en, this message translates to:
  /// **'day streak'**
  String get gamificationStreakDays;

  /// No description provided for @gamificationBadgesTitle.
  ///
  /// In en, this message translates to:
  /// **'Badges'**
  String get gamificationBadgesTitle;

  /// No description provided for @gamificationBadgesEmpty.
  ///
  /// In en, this message translates to:
  /// **'No badges yet'**
  String get gamificationBadgesEmpty;

  /// No description provided for @leaderboardTitle.
  ///
  /// In en, this message translates to:
  /// **'Leaderboard'**
  String get leaderboardTitle;

  /// No description provided for @leaderboardWeekly.
  ///
  /// In en, this message translates to:
  /// **'Weekly'**
  String get leaderboardWeekly;

  /// No description provided for @leaderboardMonthly.
  ///
  /// In en, this message translates to:
  /// **'Monthly'**
  String get leaderboardMonthly;

  /// No description provided for @leaderboardAllTime.
  ///
  /// In en, this message translates to:
  /// **'All-time'**
  String get leaderboardAllTime;

  /// No description provided for @leaderboardFriends.
  ///
  /// In en, this message translates to:
  /// **'Friends'**
  String get leaderboardFriends;

  /// No description provided for @billingPlansTitle.
  ///
  /// In en, this message translates to:
  /// **'Choose a plan'**
  String get billingPlansTitle;

  /// No description provided for @billingPlansEmpty.
  ///
  /// In en, this message translates to:
  /// **'No plans available'**
  String get billingPlansEmpty;

  /// No description provided for @billingFreeLabel.
  ///
  /// In en, this message translates to:
  /// **'Free'**
  String get billingFreeLabel;

  /// No description provided for @billingPerMonth.
  ///
  /// In en, this message translates to:
  /// **'/month'**
  String get billingPerMonth;

  /// No description provided for @billingPerYear.
  ///
  /// In en, this message translates to:
  /// **'/year'**
  String get billingPerYear;

  /// No description provided for @billingCurrentPlan.
  ///
  /// In en, this message translates to:
  /// **'Current'**
  String get billingCurrentPlan;

  /// No description provided for @billingChoosePlan.
  ///
  /// In en, this message translates to:
  /// **'Choose'**
  String get billingChoosePlan;

  /// No description provided for @billingCheckoutTitle.
  ///
  /// In en, this message translates to:
  /// **'Checkout'**
  String get billingCheckoutTitle;

  /// No description provided for @billingCheckoutSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Enter your payment method to subscribe'**
  String get billingCheckoutSubtitle;

  /// No description provided for @billingCheckoutToken.
  ///
  /// In en, this message translates to:
  /// **'Payment token'**
  String get billingCheckoutToken;

  /// No description provided for @billingCheckoutMock.
  ///
  /// In en, this message translates to:
  /// **'Mock payment (development only)'**
  String get billingCheckoutMock;

  /// No description provided for @billingCheckoutSubmit.
  ///
  /// In en, this message translates to:
  /// **'Subscribe'**
  String get billingCheckoutSubmit;

  /// No description provided for @billingManageTitle.
  ///
  /// In en, this message translates to:
  /// **'Manage subscription'**
  String get billingManageTitle;

  /// No description provided for @billingNoActive.
  ///
  /// In en, this message translates to:
  /// **'No active subscription'**
  String get billingNoActive;

  /// No description provided for @billingRenewsOn.
  ///
  /// In en, this message translates to:
  /// **'Renews on'**
  String get billingRenewsOn;

  /// No description provided for @billingCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get billingCancel;

  /// No description provided for @billingResume.
  ///
  /// In en, this message translates to:
  /// **'Resume'**
  String get billingResume;

  /// No description provided for @billingInvoicesTitle.
  ///
  /// In en, this message translates to:
  /// **'Invoices'**
  String get billingInvoicesTitle;

  /// No description provided for @billingInvoicesEmpty.
  ///
  /// In en, this message translates to:
  /// **'No invoices'**
  String get billingInvoicesEmpty;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ru', 'uz', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ru':
      return AppLocalizationsRu();
    case 'uz':
      return AppLocalizationsUz();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
