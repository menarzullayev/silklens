/// Static localisation strings for the app.
///
/// Usage:
///   AppStrings.get(LocaleService.instance.locale, 'onb_skip')
class AppStrings {
  AppStrings._();

  /// Returns the translated string for [key] in [locale].
  /// Falls back to English if the key or locale is missing.
  static String get(String locale, String key) {
    final table = _strings[locale] ?? _strings['en']!;
    return table[key] ?? _strings['en']![key] ?? key;
  }

  static const _strings = <String, Map<String, String>>{
    'en': {
      // Auth — Sign In
      'auth_signin_title': 'Welcome Back',
      'auth_signin_sub': 'Sign in to continue exploring',
      'auth_email': 'Email address',
      'auth_password': 'Password',
      'auth_forgot': 'Forgot password?',
      'auth_signin_btn': 'Sign In',
      'auth_no_account': "Don't have an account? ",
      'auth_signup_link': 'Sign Up',
      'auth_guest': 'Continue as Guest',
      'auth_or': 'or',
      'auth_google': 'Continue with Google',
      'auth_google_soon': 'Google OAuth — coming soon!',
      // Auth — Sign Up
      'auth_signup_title': 'Create Account',
      'auth_signup_sub': 'Join the SilkLens community',
      'auth_password_8': 'Password (min 8 chars)',
      'auth_signup_btn': 'Create Account',
      'auth_have_account': 'Already have an account? ',
      'auth_signin_link': 'Sign In',
      'auth_tos_text':
          'I agree to the Terms of Service and Privacy Policy',
      'pwd_weak': 'Weak',
      'pwd_medium': 'Medium',
      'pwd_strong': 'Strong',
      // Auth — Forgot Password
      'auth_forgot_title': 'Reset Password',
      'auth_forgot_sub': 'Enter your email to receive a reset link',
      'auth_forgot_sent_sub': 'Check your email for the reset link',
      'auth_forgot_email': 'Email address',
      'auth_forgot_btn': 'Send Reset Link',
      'auth_forgot_back': 'Back to Sign In',
      'auth_forgot_success': 'Reset link sent to',
      'auth_back_signin': 'Back to Sign In',
      // Validation errors
      'err_email_required': 'Enter your email',
      'err_email_invalid': 'Enter a valid email',
      'err_password_required': 'Enter your password',
      'err_password_8': 'Password must be at least 8 characters',
      'auth_confirm_password': 'Confirm password',
      'err_confirm_password_required': 'Please confirm your password',
      'err_passwords_mismatch': 'Passwords do not match',
      // Splash
      'splash_tagline': 'Cultural Heritage Explorer',
      // Auth Choice
      'auth_choice_sub': 'Choose how to continue',
      // Email Verification
      'email_verify_title': 'Verify your Email',
      'email_verify_sent': 'A 6-digit code was sent to',
      'email_verify_btn': 'Verify',
      'email_resend_loading': 'Sending...',
      'email_resend_countdown': 'Resend code in ({s}s)',
      'email_resend_btn': 'Resend code',
      // Language Selection page (these are locale-aware UI labels
      // shown before locale is known; kept in _Lang model too)
      'lang_select_label': 'Choose language',
      'lang_confirm_label': 'Continue',
      // Onboarding navigation
      'onb_skip': 'Skip',
      'onb_next': 'Next',
      'onb_get_started': 'Get Started',
      'onb_back': 'Back',
      'onb_have_account': 'Sign In',
      // Page 1
      'onb_p1_title': 'Touch a Thousand Years',
      'onb_p1_sub':
          "Journey through the Silk Road's greatest landmarks"
          ' — curated, mapped, and richly told.',
      // Page 2
      'onb_p2_title': 'Point. Discover. Learn.',
      'onb_p2_sub':
          'Aim your camera at any monument and SilkLens'
          ' reveals its story in seconds.',
      // Page 3
      'onb_p3_title': 'Walk Together',
      'onb_p3_sub':
          'Share discoveries, earn badges, and connect'
          ' with heritage enthusiasts worldwide.',
    },
    'uz': {
      // Auth — Sign In
      'auth_signin_title': 'Xush kelibsiz',
      'auth_signin_sub': 'Kashf etishni davom ettirish uchun kiring',
      'auth_email': 'Elektron pochta',
      'auth_password': 'Parol',
      'auth_forgot': 'Parolni unutdingizmi?',
      'auth_signin_btn': 'Kirish',
      'auth_no_account': "Hisobingiz yo'qmi? ",
      'auth_signup_link': "Ro'yxatdan o'tish",
      'auth_guest': 'Mehmon sifatida davom etish',
      'auth_or': 'yoki',
      'auth_google': 'Google orqali davom etish',
      'auth_google_soon': 'Google OAuth — tez orada!',
      // Auth — Sign Up
      'auth_signup_title': 'Hisob yaratish',
      'auth_signup_sub': "SilkLens hamjamiyatiga qo'shiling",
      'auth_password_8': 'Parol (kamida 8 belgi)',
      'auth_signup_btn': 'Hisob yaratish',
      'auth_have_account': 'Hisobingiz bormi? ',
      'auth_signin_link': 'Kirish',
      'auth_tos_text':
          'Foydalanish shartlari va Maxfiylik siyosatiga roziman',
      'pwd_weak': 'Zaif',
      'pwd_medium': "O'rta",
      'pwd_strong': 'Kuchli',
      // Auth — Forgot Password
      'auth_forgot_title': 'Parolni tiklash',
      'auth_forgot_sub':
          'Tiklash havolasini olish uchun emailingizni kiriting',
      'auth_forgot_sent_sub':
          'Tiklash havolasi uchun emailingizni tekshiring',
      'auth_forgot_email': 'Elektron pochta',
      'auth_forgot_btn': 'Tiklash havolasini yuborish',
      'auth_forgot_back': 'Kirishga qaytish',
      'auth_forgot_success': 'Tiklash havolasi yuborildi:',
      'auth_back_signin': 'Kirishga qaytish',
      // Validation errors
      'err_email_required': 'Elektron pochtangizni kiriting',
      'err_email_invalid': "To'g'ri elektron pochta kiriting",
      'err_password_required': 'Parolingizni kiriting',
      'err_password_8': "Parol kamida 8 belgi bo'lishi kerak",
      'auth_confirm_password': 'Parolni tasdiqlang',
      'err_confirm_password_required': 'Iltimos, parolni tasdiqlang',
      'err_passwords_mismatch': 'Parollar mos kelmaydi',
      // Splash
      'splash_tagline': 'Madaniy Meros Tadqiqotchisi',
      // Auth Choice
      'auth_choice_sub': 'Davom etish uchun tanlang',
      // Email Verification
      'email_verify_title': 'Emailni tasdiqlang',
      'email_verify_sent': 'ga 6 raqamli kod yuborildi',
      'email_verify_btn': 'Tasdiqlash',
      'email_resend_loading': 'Yuborilmoqda...',
      'email_resend_countdown': 'Qayta yuborish ({s}s)',
      'email_resend_btn': 'Kodni qayta yuborish',
      // Language Selection
      'lang_select_label': 'Tilni tanlang',
      'lang_confirm_label': 'Davom etish',
      // Onboarding navigation
      'onb_skip': "O'tkazib yuborish",
      'onb_next': 'Keyingi',
      'onb_get_started': 'Boshlash',
      'onb_back': 'Orqaga',
      'onb_have_account': 'Hisobim bor',
      // Page 1
      'onb_p1_title': 'Ming Yilni His Eting',
      'onb_p1_sub':
          "Ipak yo'li buylab eng buyuk yodgorliklarni kashf eting"
          " — tanlangan, xaritada belgilangan va boy ma'lumotli.",
      // Page 2
      'onb_p2_title': "Ko'rsating. Kashf eting.",
      'onb_p2_sub':
          "Kamerangizni istalgan obidaga yo'naltiring —"
          ' SilkLens uning tarixini soniyalar ichida ochib beradi.',
      // Page 3
      'onb_p3_title': 'Birga Yuring',
      'onb_p3_sub':
          'Kashfiyotlarni ulashing, nishonlar qozonib,'
          " madaniy meros sevarlari bilan bog'laning.",
    },
    'ru': {
      // Auth — Sign In
      'auth_signin_title': 'Добро пожаловать',
      'auth_signin_sub': 'Войдите, чтобы продолжить исследование',
      'auth_email': 'Электронная почта',
      'auth_password': 'Пароль',
      'auth_forgot': 'Забыли пароль?',
      'auth_signin_btn': 'Войти',
      'auth_no_account': 'Нет аккаунта? ',
      'auth_signup_link': 'Зарегистрироваться',
      'auth_guest': 'Продолжить как гость',
      'auth_or': 'или',
      'auth_google': 'Продолжить с Google',
      'auth_google_soon': 'Google OAuth — скоро!',
      // Auth — Sign Up
      'auth_signup_title': 'Создать аккаунт',
      'auth_signup_sub': 'Присоединяйтесь к сообществу SilkLens',
      'auth_password_8': 'Пароль (минимум 8 символов)',
      'auth_signup_btn': 'Создать аккаунт',
      'auth_have_account': 'Уже есть аккаунт? ',
      'auth_signin_link': 'Войти',
      'auth_tos_text':
          'Я согласен с Условиями использования и Политикой конфиденциальности',
      'pwd_weak': 'Слабый',
      'pwd_medium': 'Средний',
      'pwd_strong': 'Надёжный',
      // Auth — Forgot Password
      'auth_forgot_title': 'Сброс пароля',
      'auth_forgot_sub': 'Введите email для получения ссылки для сброса',
      'auth_forgot_sent_sub':
          'Проверьте email — туда отправлена ссылка для сброса',
      'auth_forgot_email': 'Электронная почта',
      'auth_forgot_btn': 'Отправить ссылку для сброса',
      'auth_forgot_back': 'Вернуться к входу',
      'auth_forgot_success': 'Ссылка для сброса отправлена на',
      'auth_back_signin': 'Вернуться к входу',
      // Validation errors
      'err_email_required': 'Введите email',
      'err_email_invalid': 'Введите корректный email',
      'err_password_required': 'Введите пароль',
      'err_password_8': 'Пароль должен содержать не менее 8 символов',
      'auth_confirm_password': 'Подтвердите пароль',
      'err_confirm_password_required': 'Пожалуйста, подтвердите пароль',
      'err_passwords_mismatch': 'Пароли не совпадают',
      // Splash
      'splash_tagline': 'Исследователь культурного наследия',
      // Auth Choice
      'auth_choice_sub': 'Выберите способ продолжения',
      // Email Verification
      'email_verify_title': 'Подтвердите email',
      'email_verify_sent': 'На этот адрес отправлен 6-значный код',
      'email_verify_btn': 'Подтвердить',
      'email_resend_loading': 'Отправляем...',
      'email_resend_countdown': 'Отправить повторно ({s}с)',
      'email_resend_btn': 'Отправить код повторно',
      // Language Selection
      'lang_select_label': 'Выберите язык',
      'lang_confirm_label': 'Продолжить',
      // Onboarding navigation
      'onb_skip': 'Пропустить',
      'onb_next': 'Далее',
      'onb_get_started': 'Начать',
      'onb_back': 'Назад',
      'onb_have_account': 'Войти',
      // Page 1
      'onb_p1_title': 'Прикоснитесь к тысячелетиям',
      'onb_p1_sub':
          'Исследуйте величайшие памятники Шёлкового пути'
          ' — с геопривязкой и подробным описанием.',
      // Page 2
      'onb_p2_title': 'Укажи. Открой. Узнай.',
      'onb_p2_sub':
          'Наведите камеру на любой памятник —'
          ' SilkLens раскроет его историю за секунды.',
      // Page 3
      'onb_p3_title': 'Идите вместе',
      'onb_p3_sub':
          'Делитесь открытиями, зарабатывайте значки'
          ' и общайтесь с любителями наследия.',
    },
    'zh': {
      // Auth — Sign In
      'auth_signin_title': '欢迎回来',
      'auth_signin_sub': '登录以继续探索',
      'auth_email': '电子邮件地址',
      'auth_password': '密码',
      'auth_forgot': '忘记密码？',
      'auth_signin_btn': '登录',
      'auth_no_account': '还没有账号？',
      'auth_signup_link': '注册',
      'auth_guest': '以游客身份继续',
      'auth_or': '或',
      'auth_google': '通过 Google 继续',
      'auth_google_soon': 'Google OAuth — 即将推出！',
      // Auth — Sign Up
      'auth_signup_title': '创建账号',
      'auth_signup_sub': '加入 SilkLens 社区',
      'auth_password_8': '密码（至少 8 个字符）',
      'auth_signup_btn': '创建账号',
      'auth_have_account': '已有账号？',
      'auth_signin_link': '登录',
      'auth_tos_text': '我同意服务条款和隐私政策',
      'pwd_weak': '弱',
      'pwd_medium': '中',
      'pwd_strong': '强',
      // Auth — Forgot Password
      'auth_forgot_title': '重置密码',
      'auth_forgot_sub': '输入您的邮箱以接收重置链接',
      'auth_forgot_sent_sub': '请检查您的邮箱以获取重置链接',
      'auth_forgot_email': '电子邮件地址',
      'auth_forgot_btn': '发送重置链接',
      'auth_forgot_back': '返回登录',
      'auth_forgot_success': '重置链接已发送至',
      'auth_back_signin': '返回登录',
      // Validation errors
      'err_email_required': '请输入您的邮箱',
      'err_email_invalid': '请输入有效的邮箱',
      'err_password_required': '请输入密码',
      'err_password_8': '密码至少需要8个字符',
      'auth_confirm_password': '确认密码',
      'err_confirm_password_required': '请确认您的密码',
      'err_passwords_mismatch': '密码不匹配',
      // Splash
      'splash_tagline': '文化遗产探索者',
      // Auth Choice
      'auth_choice_sub': '选择继续方式',
      // Email Verification
      'email_verify_title': '验证您的邮箱',
      'email_verify_sent': '已向此地址发送6位验证码',
      'email_verify_btn': '验证',
      'email_resend_loading': '发送中...',
      'email_resend_countdown': '{s}秒后重新发送',
      'email_resend_btn': '重新发送验证码',
      // Language Selection
      'lang_select_label': '选择语言',
      'lang_confirm_label': '继续',
      // Onboarding navigation
      'onb_skip': '跳过',
      'onb_next': '下一步',
      'onb_get_started': '开始使用',
      'onb_back': '返回',
      'onb_have_account': '已有账号',
      // Page 1
      'onb_p1_title': '触摸千年历史',
      'onb_p1_sub': '探索丝绸之路最伟大的遗址——精心策划、地图标注、内容丰富。',
      // Page 2
      'onb_p2_title': '指向。发现。学习。',
      'onb_p2_sub': '将相机对准任何古迹，SilkLens 即刻揭示其历史故事。',
      // Page 3
      'onb_p3_title': '一起同行',
      'onb_p3_sub': '分享发现、赢取徽章，与全球文化遗产爱好者建立联系。',
    },
  };
}
