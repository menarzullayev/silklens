// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appName => 'SilkLens';

  @override
  String get appTagline => 'Шёлковый путь через объектив';

  @override
  String get onboardingTitle => 'Исследуйте наследие с помощью камеры';

  @override
  String get onboardingSubtitle => 'Наведите камеру на памятник — узнайте его историю мгновенно.';

  @override
  String get onboardingCta => 'Начать исследование';

  @override
  String get onboardingSkip => 'Пропустить';

  @override
  String get onboardingSlide1Title => 'Распознавайте наследие за секунды';

  @override
  String get onboardingSlide1Body => 'Наведите камеру на любой памятник — ИИ расскажет, что это.';

  @override
  String get onboardingSlide2Title => 'Слушайте историю';

  @override
  String get onboardingSlide2Body => 'Персональный аудио-гид — выберите язык и любимый регион.';

  @override
  String get onboardingSlide3Title => 'Создайте свой атлас';

  @override
  String get onboardingSlide3Body => 'Сохраняйте места, делитесь отзывами и зарабатывайте значки.';

  @override
  String get onboardingSignIn => 'Войти';

  @override
  String get onboardingNext => 'Далее';

  @override
  String get navMap => 'Карта';

  @override
  String get navCamera => 'Камера';

  @override
  String get navProfile => 'Профиль';

  @override
  String get navDiscover => 'Поиск';

  @override
  String get navSaved => 'Сохранённое';

  @override
  String get cameraPlaceholderTitle => 'Камера';

  @override
  String get cameraPlaceholderBody => 'Распознавание появится в FAZA 2 — неделя 3.';

  @override
  String get mapPlaceholderTitle => 'Карта';

  @override
  String get mapPlaceholderBody => 'Интеграция Mapbox / OSM появится в FAZA 2 — неделя 3.';

  @override
  String get profileTitle => 'Профиль';

  @override
  String get profileLanguage => 'Язык';

  @override
  String get profileTheme => 'Тема';

  @override
  String get profileSignOut => 'Выйти';

  @override
  String get profileGuestTitle => 'Гость';

  @override
  String get profileGuestBody =>
      'Войдите, чтобы синхронизировать сохранённые объекты между устройствами.';

  @override
  String get authEmailLabel => 'Email';

  @override
  String get authPasswordLabel => 'Пароль';

  @override
  String get authPasswordConfirmLabel => 'Подтвердите пароль';

  @override
  String get authDisplayNameLabel => 'Отображаемое имя';

  @override
  String get authSignInTitle => 'С возвращением';

  @override
  String get authSignInSubtitle => 'Войдите, чтобы продолжить исследование.';

  @override
  String get authSignInCta => 'Войти';

  @override
  String get authSignUpTitle => 'Создать аккаунт';

  @override
  String get authSignUpSubtitle => 'Сохраняйте объекты, делитесь отзывами, получайте значки.';

  @override
  String get authSignUpCta => 'Создать аккаунт';

  @override
  String get authForgotPasswordTitle => 'Забыли пароль';

  @override
  String get authForgotPasswordCta => 'Отправить ссылку для сброса';

  @override
  String get authForgotPasswordBody =>
      'Восстановление пароля скоро — мы вышлем инструкцию на email.';

  @override
  String get authHaveAccountQ => 'Уже есть аккаунт?';

  @override
  String get authNoAccountQ => 'Нет аккаунта?';

  @override
  String get authForgotLink => 'Забыли пароль?';

  @override
  String get authProvidersDivider => 'Или продолжите через';

  @override
  String get authProviderGoogle => 'Войти через Google';

  @override
  String get authProviderApple => 'Войти через Apple';

  @override
  String get authProviderTelegram => 'Войти через Telegram';

  @override
  String get authComingSoon => 'Скоро';

  @override
  String get authErrorInvalidEmail => 'Введите корректный email.';

  @override
  String get authErrorPasswordTooShort => 'Пароль должен быть не короче 12 символов.';

  @override
  String get authErrorPasswordWeak =>
      'Пароль должен содержать заглавные и строчные буквы и хотя бы одну цифру.';

  @override
  String get authErrorPasswordsDontMatch => 'Пароли не совпадают.';

  @override
  String get authErrorRequired => 'Обязательное поле.';

  @override
  String get authErrorInvalidCredentials => 'Неверный email или пароль.';

  @override
  String get authErrorRateLimited => 'Слишком много попыток. Попробуйте позже.';

  @override
  String get authErrorEmailTaken => 'Этот email уже зарегистрирован.';

  @override
  String get authErrorNetwork => 'Ошибка сети. Проверьте подключение.';

  @override
  String get authErrorUnknown => 'Что-то пошло не так. Попробуйте снова.';

  @override
  String get heritageListTitle => 'Поиск';

  @override
  String get heritageSearchHint => 'Памятники, города, эпохи...';

  @override
  String get heritageFilterAll => 'Все';

  @override
  String get heritageFilterKind => 'Тип';

  @override
  String get heritageFilterCountry => 'Страна';

  @override
  String get heritageEmpty => 'Не найдено объектов по вашим фильтрам.';

  @override
  String get heritageSearchEmptyTitle => 'Пусто';

  @override
  String get heritageSearchEmptyBody => 'Попробуйте другой запрос или посмотрите все объекты.';

  @override
  String get heritageRecentSearches => 'Недавние запросы';

  @override
  String get heritageDetailSave => 'Сохранить';

  @override
  String get heritageDetailUnsave => 'Сохранено';

  @override
  String get heritageDetailShare => 'Поделиться';

  @override
  String get heritageDetailAiGuide => 'AI-гид';

  @override
  String get heritageDetailAiGuideTooltip => 'Скоро в v2';

  @override
  String get heritageDetailOpenInMap => 'Открыть на карте';

  @override
  String get heritageDetailPeriod => 'Период';

  @override
  String get heritageDetailCountry => 'Страна';

  @override
  String get heritageDetailUnesco => 'Объект ЮНЕСКО';

  @override
  String get heritageDetailSummary => 'Кратко';

  @override
  String get heritageDetailAbout => 'О месте';

  @override
  String get heritageDetailLocation => 'Местоположение';

  @override
  String get heritageSavedTitle => 'Сохранённое';

  @override
  String get heritageSavedEmpty =>
      'Пока ничего не сохранено. Нажмите “Сохранить” на странице объекта.';

  @override
  String get heritageLoadMoreError => 'Не удалось загрузить — нажмите для повтора.';

  @override
  String get commonRetry => 'Повторить';

  @override
  String get commonClose => 'Закрыть';

  @override
  String get commonCancel => 'Отмена';

  @override
  String get commonContinue => 'Продолжить';

  @override
  String get commonOk => 'OK';

  @override
  String get cameraTorch => 'Вспышка';

  @override
  String get cameraFlip => 'Сменить камеру';

  @override
  String get cameraGallery => 'Из галереи';

  @override
  String get cameraCapture => 'Снимок';

  @override
  String get cameraUnavailable => 'Камера недоступна';

  @override
  String get recognitionUploading => 'Загрузка…';

  @override
  String get recognitionRecognising => 'Распознавание…';

  @override
  String get recognitionTitle => 'Распознано';

  @override
  String get recognitionConfidence => 'Уверенность';

  @override
  String get recognitionViewDetails => 'Подробнее';

  @override
  String get recognitionAlternatives => 'Другие совпадения';

  @override
  String get recognitionFailed => 'Распознавание не удалось';

  @override
  String get mapLocateMe => 'Найти меня';

  @override
  String get mapOpen => 'Открыть';

  @override
  String get mapLayerHeritage => 'Наследие';

  @override
  String get mapLayerUnesco => 'ЮНЕСКО';

  @override
  String get mapLayerCities => 'Города';

  @override
  String get chatTitle => 'Спросите SilkLens';

  @override
  String get chatEmptyTitle => 'Спросите что угодно о Шёлковом пути';

  @override
  String get chatInputHint => 'Введите сообщение…';

  @override
  String get chatTtsHint => 'Воспроизвести';

  @override
  String get chatSuggestionWhen => 'Когда был построен этот памятник?';

  @override
  String get chatSuggestionHotels => 'Лучшие отели поблизости?';

  @override
  String get chatSuggestionLegends => 'Расскажите легенду об этом месте.';

  @override
  String get profileTabActivity => 'Активность';

  @override
  String get profileTabSaved => 'Сохранённые';

  @override
  String get profileTabReviews => 'Отзывы';

  @override
  String get profileTabFriends => 'Друзья';

  @override
  String get profileTabSettings => 'Настройки';

  @override
  String get profileActivityEmpty => 'Пока нет активности';

  @override
  String get profileSavedEmpty => 'Нет сохранённых мест';

  @override
  String get profileReviewsEmpty => 'Ваши отзывы будут здесь';

  @override
  String get profileReviewsNew => 'Новый отзыв';

  @override
  String get profileFriendsEmpty => 'Пригласите друзей в SilkLens';

  @override
  String get profileFriendsInvite => 'Пригласить';

  @override
  String get profileNotifications => 'Уведомления';

  @override
  String get profileNotificationsHint => 'Настройте push и email';

  @override
  String get profileLogout => 'Выйти';

  @override
  String get profileFollow => 'Подписаться';

  @override
  String get profileFollowing => 'Вы подписаны';

  @override
  String get profileFollowers => 'Подписчики';

  @override
  String get profileUserNotFound => 'Пользователь не найден';

  @override
  String get reviewComposerTitle => 'Написать отзыв';

  @override
  String get reviewComposerBodyLabel => 'Ваш отзыв';

  @override
  String get reviewComposerLanguage => 'Язык';

  @override
  String get reviewComposerSubmit => 'Отправить';

  @override
  String get reviewDimHistory => 'История';

  @override
  String get reviewDimPhotos => 'Фото';

  @override
  String get reviewDimAccess => 'Доступ';

  @override
  String get reviewDimValue => 'Цена';

  @override
  String get reviewDimAtmosphere => 'Атмосфера';

  @override
  String get reviewDimFamilyFriendly => 'Для семьи';

  @override
  String get gamificationLevel => 'Уровень';

  @override
  String get gamificationNoData => 'Нет данных';

  @override
  String get gamificationStreakDays => 'дней подряд';

  @override
  String get gamificationBadgesTitle => 'Награды';

  @override
  String get gamificationBadgesEmpty => 'Пока нет наград';

  @override
  String get leaderboardTitle => 'Рейтинг';

  @override
  String get leaderboardWeekly => 'Неделя';

  @override
  String get leaderboardMonthly => 'Месяц';

  @override
  String get leaderboardAllTime => 'Всё время';

  @override
  String get leaderboardFriends => 'Друзья';

  @override
  String get billingPlansTitle => 'Выберите план';

  @override
  String get billingPlansEmpty => 'Нет доступных планов';

  @override
  String get billingFreeLabel => 'Бесплатно';

  @override
  String get billingPerMonth => '/мес';

  @override
  String get billingPerYear => '/год';

  @override
  String get billingCurrentPlan => 'Текущий';

  @override
  String get billingChoosePlan => 'Выбрать';

  @override
  String get billingCheckoutTitle => 'Оплата';

  @override
  String get billingCheckoutSubtitle => 'Введите способ оплаты для подписки';

  @override
  String get billingCheckoutToken => 'Токен оплаты';

  @override
  String get billingCheckoutMock => 'Тестовая оплата (для разработки)';

  @override
  String get billingCheckoutSubmit => 'Подписаться';

  @override
  String get billingManageTitle => 'Управление подпиской';

  @override
  String get billingNoActive => 'Нет активной подписки';

  @override
  String get billingRenewsOn => 'Продлевается';

  @override
  String get billingCancel => 'Отменить';

  @override
  String get billingResume => 'Возобновить';

  @override
  String get billingInvoicesTitle => 'Счета';

  @override
  String get billingInvoicesEmpty => 'Нет счетов';

  @override
  String get emailVerifyTitle => 'Подтвердите email';

  @override
  String get emailVerifyCodeSentTo => 'Код из 6 цифр отправлен на';

  @override
  String get emailVerifyConfirm => 'Подтвердить';

  @override
  String get emailVerifyInvalidCode => 'Код неверный или истёк.';

  @override
  String get emailVerifyResendError => 'Не удалось отправить email. Попробуйте снова.';

  @override
  String get emailVerifyResending => 'Отправка...';

  @override
  String emailVerifyResendCountdown(int seconds) {
    return 'Повторить через $secondsс';
  }

  @override
  String get emailVerifyResendNow => 'Отправить код повторно';
}
