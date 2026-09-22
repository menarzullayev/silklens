// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Korean (`ko`).
class AppLocalizationsKo extends AppLocalizations {
  AppLocalizationsKo([String locale = 'ko']) : super(locale);

  @override
  String get appName => 'SilkLens';

  @override
  String get appTagline => '당신의 렌즈로 실크로드를 바라보세요';

  @override
  String get onboardingTitle => '카메라로 문화유산을 발견하세요';

  @override
  String get onboardingSubtitle => '어떤 기념물이든 가리키면 즉시 그 이야기를 알 수 있습니다.';

  @override
  String get onboardingCta => '탐험 시작';

  @override
  String get onboardingSkip => '건너뛰기';

  @override
  String get onboardingSlide1Title => '몇 초 만에 문화유산 인식';

  @override
  String get onboardingSlide1Body => '카메라를 어떤 기념물에든 향하면 AI가 무엇인지 알려줍니다.';

  @override
  String get onboardingSlide2Title => '이야기 듣기';

  @override
  String get onboardingSlide2Body => '개인화된 오디오 가이드 — 언어와 즐겨 찾는 지역을 선택하세요.';

  @override
  String get onboardingSlide3Title => '나만의 지도 만들기';

  @override
  String get onboardingSlide3Body =>
      '장소를 저장하고, 리뷰를 공유하며, 실크로드를 탐험하면서 배지를 획득하세요.';

  @override
  String get onboardingSignIn => '로그인';

  @override
  String get onboardingNext => '다음';

  @override
  String get navMap => '지도';

  @override
  String get navCamera => '카메라';

  @override
  String get navProfile => '프로필';

  @override
  String get navDiscover => '발견';

  @override
  String get navSaved => '저장됨';

  @override
  String get cameraPlaceholderTitle => '카메라';

  @override
  String get cameraPlaceholderBody => '비전 파이프라인은 FAZA 2 — 3주차에 출시됩니다.';

  @override
  String get mapPlaceholderTitle => '지도';

  @override
  String get mapPlaceholderBody => 'Mapbox/OSM 통합은 FAZA 2 — 3주차에 출시됩니다.';

  @override
  String get profileTitle => '프로필';

  @override
  String get profileLanguage => '언어';

  @override
  String get profileTheme => '테마';

  @override
  String get profileSignOut => '로그아웃';

  @override
  String get profileGuestTitle => '게스트';

  @override
  String get profileGuestBody => '로그인하여 저장된 문화유산을 기기 간에 동기화하세요.';

  @override
  String get authEmailLabel => '이메일';

  @override
  String get authPasswordLabel => '비밀번호';

  @override
  String get authPasswordConfirmLabel => '비밀번호 확인';

  @override
  String get authDisplayNameLabel => '표시 이름';

  @override
  String get authSignInTitle => '다시 오신 것을 환영합니다';

  @override
  String get authSignInSubtitle => '탐험을 계속하려면 로그인하세요.';

  @override
  String get authSignInCta => '로그인';

  @override
  String get authSignUpTitle => '계정 만들기';

  @override
  String get authSignUpSubtitle => '문화유산 저장, 리뷰 공유, 배지 잠금 해제.';

  @override
  String get authSignUpCta => '계정 만들기';

  @override
  String get authForgotPasswordTitle => '비밀번호 찾기';

  @override
  String get authForgotPasswordCta => '재설정 링크 보내기';

  @override
  String get authForgotPasswordBody => '비밀번호 복구는 곧 제공됩니다 — 이메일로 안내를 보내드립니다.';

  @override
  String get authHaveAccountQ => '이미 계정이 있으신가요?';

  @override
  String get authNoAccountQ => '계정이 없으신가요?';

  @override
  String get authForgotLink => '비밀번호를 잊으셨나요?';

  @override
  String get authProvidersDivider => '또는 다음으로 계속';

  @override
  String get authProviderGoogle => 'Google로 계속';

  @override
  String get authProviderApple => 'Apple로 계속';

  @override
  String get authProviderTelegram => 'Telegram으로 계속';

  @override
  String get authComingSoon => '출시 예정';

  @override
  String get authErrorInvalidEmail => '유효한 이메일 주소를 입력하세요.';

  @override
  String get authErrorPasswordTooShort => '비밀번호는 최소 12자 이상이어야 합니다.';

  @override
  String get authErrorPasswordWeak => '비밀번호에는 대소문자와 숫자가 최소 하나씩 포함되어야 합니다.';

  @override
  String get authErrorPasswordsDontMatch => '비밀번호가 일치하지 않습니다.';

  @override
  String get authErrorRequired => '이 필드는 필수입니다.';

  @override
  String get authErrorInvalidCredentials => '이메일 또는 비밀번호가 올바르지 않습니다.';

  @override
  String get authErrorRateLimited => '시도 횟수가 너무 많습니다. 나중에 다시 시도하세요.';

  @override
  String get authErrorEmailTaken => '해당 이메일은 이미 등록되어 있습니다.';

  @override
  String get authErrorNetwork => '네트워크 오류. 연결을 확인하세요.';

  @override
  String get authErrorUnknown => '문제가 발생했습니다. 다시 시도하세요.';

  @override
  String get heritageListTitle => '발견';

  @override
  String get heritageSearchHint => '문화유산, 도시, 시대 검색...';

  @override
  String get heritageFilterAll => '전체';

  @override
  String get heritageFilterKind => '종류';

  @override
  String get heritageFilterCountry => '국가';

  @override
  String get heritageEmpty => '필터에 맞는 문화유산이 없습니다.';

  @override
  String get heritageSearchEmptyTitle => '아직 결과 없음';

  @override
  String get heritageSearchEmptyBody => '다른 키워드를 시도하거나 모든 문화유산을 탐색하세요.';

  @override
  String get heritageRecentSearches => '최근 검색';

  @override
  String get heritageDetailSave => '저장';

  @override
  String get heritageDetailUnsave => '저장됨';

  @override
  String get heritageDetailShare => '공유';

  @override
  String get heritageDetailAiGuide => 'AI 가이드';

  @override
  String get heritageDetailAiGuideTooltip => 'v2 빌드에서 제공 예정';

  @override
  String get heritageDetailOpenInMap => '지도에서 열기';

  @override
  String get heritageDetailPeriod => '시대';

  @override
  String get heritageDetailCountry => '국가';

  @override
  String get heritageDetailUnesco => 'UNESCO 등재';

  @override
  String get heritageDetailSummary => '요약';

  @override
  String get heritageDetailAbout => '소개';

  @override
  String get heritageDetailLocation => '위치';

  @override
  String get heritageSavedTitle => '저장됨';

  @override
  String get heritageSavedEmpty => '아직 저장된 항목이 없습니다. 문화유산 상세 페이지에서 저장을 탭하세요.';

  @override
  String get heritageLoadMoreError => '더 불러오지 못했습니다 — 탭하여 재시도하세요.';

  @override
  String get commonRetry => '재시도';

  @override
  String get commonClose => '닫기';

  @override
  String get commonCancel => '취소';

  @override
  String get commonContinue => '계속';

  @override
  String get commonOk => '확인';

  @override
  String get cameraTorch => '손전등';

  @override
  String get cameraFlip => '카메라 전환';

  @override
  String get cameraGallery => '갤러리에서 선택';

  @override
  String get cameraCapture => '촬영';

  @override
  String get cameraUnavailable => '카메라를 사용할 수 없습니다';

  @override
  String get recognitionUploading => '업로드 중…';

  @override
  String get recognitionRecognising => '인식 중…';

  @override
  String get recognitionTitle => '인식됨';

  @override
  String get recognitionConfidence => '신뢰도';

  @override
  String get recognitionViewDetails => '상세 보기';

  @override
  String get recognitionAlternatives => '다른 결과';

  @override
  String get recognitionFailed => '인식 실패';

  @override
  String get mapLocateMe => '내 위치 찾기';

  @override
  String get mapOpen => '열기';

  @override
  String get mapLayerHeritage => '문화유산';

  @override
  String get mapLayerUnesco => 'UNESCO';

  @override
  String get mapLayerCities => '도시';

  @override
  String get chatTitle => 'SilkLens에 질문하기';

  @override
  String get chatEmptyTitle => '실크로드에 대해 무엇이든 물어보세요';

  @override
  String get chatInputHint => '메시지 입력…';

  @override
  String get chatTtsHint => '재생';

  @override
  String get chatSuggestionWhen => '이 기념물은 언제 지어졌나요?';

  @override
  String get chatSuggestionHotels => '근처의 최고 호텔은 어디인가요?';

  @override
  String get chatSuggestionLegends => '이 장소에 대한 전설을 알려주세요.';

  @override
  String get profileTabActivity => '활동';

  @override
  String get profileTabSaved => '저장됨';

  @override
  String get profileTabReviews => '리뷰';

  @override
  String get profileTabFriends => '친구';

  @override
  String get profileTabSettings => '설정';

  @override
  String get profileActivityEmpty => '아직 활동 없음';

  @override
  String get profileSavedEmpty => '저장된 문화유산 없음';

  @override
  String get profileReviewsEmpty => '리뷰가 여기에 표시됩니다';

  @override
  String get profileReviewsNew => '새 리뷰';

  @override
  String get profileFriendsEmpty => '친구를 SilkLens에 초대하세요';

  @override
  String get profileFriendsInvite => '초대';

  @override
  String get profileNotifications => '알림';

  @override
  String get profileNotificationsHint => '푸시 및 이메일 설정';

  @override
  String get profileLogout => '로그아웃';

  @override
  String get profileFollow => '팔로우';

  @override
  String get profileFollowing => '팔로잉';

  @override
  String get profileFollowers => '팔로워';

  @override
  String get profileUserNotFound => '사용자를 찾을 수 없습니다';

  @override
  String get reviewComposerTitle => '리뷰 작성';

  @override
  String get reviewComposerBodyLabel => '리뷰 내용';

  @override
  String get reviewComposerLanguage => '언어';

  @override
  String get reviewComposerSubmit => '제출';

  @override
  String get reviewDimHistory => '역사';

  @override
  String get reviewDimPhotos => '사진';

  @override
  String get reviewDimAccess => '접근성';

  @override
  String get reviewDimValue => '가치';

  @override
  String get reviewDimAtmosphere => '분위기';

  @override
  String get reviewDimFamilyFriendly => '가족 친화적';

  @override
  String get gamificationLevel => '레벨';

  @override
  String get gamificationNoData => '데이터 없음';

  @override
  String get gamificationStreakDays => '일 연속';

  @override
  String get gamificationBadgesTitle => '배지';

  @override
  String get gamificationBadgesEmpty => '아직 배지 없음';

  @override
  String get leaderboardTitle => '리더보드';

  @override
  String get leaderboardWeekly => '주간';

  @override
  String get leaderboardMonthly => '월간';

  @override
  String get leaderboardAllTime => '전체';

  @override
  String get leaderboardFriends => '친구';

  @override
  String get billingPlansTitle => '플랜 선택';

  @override
  String get billingPlansEmpty => '이용 가능한 플랜 없음';

  @override
  String get billingFreeLabel => '무료';

  @override
  String get billingPerMonth => '/월';

  @override
  String get billingPerYear => '/년';

  @override
  String get billingCurrentPlan => '현재';

  @override
  String get billingChoosePlan => '선택';

  @override
  String get billingCheckoutTitle => '결제';

  @override
  String get billingCheckoutSubtitle => '구독을 위해 결제 방법을 입력하세요';

  @override
  String get billingCheckoutToken => '결제 토큰';

  @override
  String get billingCheckoutMock => '테스트 결제 (개발 전용)';

  @override
  String get billingCheckoutSubmit => '구독하기';

  @override
  String get billingManageTitle => '구독 관리';

  @override
  String get billingNoActive => '활성 구독 없음';

  @override
  String get billingRenewsOn => '갱신일';

  @override
  String get billingCancel => '취소';

  @override
  String get billingResume => '재개';

  @override
  String get billingInvoicesTitle => '청구서';

  @override
  String get billingInvoicesEmpty => '청구서 없음';

  @override
  String get emailVerifyTitle => '이메일 인증';

  @override
  String get emailVerifyCodeSentTo => '6자리 코드가 다음으로 발송되었습니다';

  @override
  String get emailVerifyConfirm => '확인';

  @override
  String get emailVerifyInvalidCode => '코드가 올바르지 않거나 만료되었습니다.';

  @override
  String get emailVerifyResendError => '이메일 발송에 실패했습니다. 다시 시도하세요.';

  @override
  String get emailVerifyResending => '발송 중...';

  @override
  String emailVerifyResendCountdown(int seconds) {
    return '$seconds초 후 재발송';
  }

  @override
  String get emailVerifyResendNow => '코드 재발송';
}
