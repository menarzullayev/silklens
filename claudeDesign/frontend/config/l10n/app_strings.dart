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
      // Auth — Sign Up
      'auth_signup_title': 'Create Account',
      'auth_signup_sub': 'Join the SilkLens community',
      'auth_password_8': 'Password (min 8 chars)',
      'auth_signup_btn': 'Create Account',
      'auth_have_account': 'Already have an account? ',
      'auth_signin_link': 'Sign In',
      'auth_tos_text':
          'I agree to the Terms of Service and Privacy Policy',
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
      // Onboarding navigation
      'onb_skip': 'Skip',
      'onb_next': 'Next',
      'onb_get_started': 'Get Started',
      'onb_have_account': 'I already have an account',
      // Page 1
      'onb_p1_title': 'Discover Heritage Sites',
      'onb_p1_sub':
          'Explore thousands of cultural landmarks across the Silk Road'
          ' and beyond — curated, geolocated, and richly documented.',
      // Page 2
      'onb_p2_title': 'AI-Powered Recognition',
      'onb_p2_sub':
          'Point your camera at any monument or artifact and let'
          ' SilkLens identify it instantly with on-device AI.',
      // Page 3
      'onb_p3_title': 'Join the Community',
      'onb_p3_sub':
          'Share discoveries, write reviews, earn XP badges, and'
          ' connect with heritage enthusiasts worldwide.',
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
      // Auth — Sign Up
      'auth_signup_title': 'Hisob yaratish',
      'auth_signup_sub': "SilkLens hamjamiyatiga qo'shiling",
      'auth_password_8': 'Parol (kamida 8 belgi)',
      'auth_signup_btn': 'Hisob yaratish',
      'auth_have_account': 'Hisobingiz bormi? ',
      'auth_signin_link': 'Kirish',
      'auth_tos_text':
          'Foydalanish shartlari va Maxfiylik siyosatiga roziman',
      // Auth — Forgot Password
      'auth_forgot_title': 'Parolni tiklash',
      'auth_forgot_sub': 'Tiklash havolasini olish uchun emailingizni kiriting',
      'auth_forgot_sent_sub': 'Tiklash havolasi uchun emailingizni tekshiring',
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
      // Onboarding navigation
      'onb_skip': "O'tkazib yuborish",
      'onb_next': 'Keyingi',
      'onb_get_started': 'Boshlash',
      'onb_have_account': 'Menda allaqachon hisob mavjud',
      'onb_p1_title': 'Meros joylarini kashf eting',
      'onb_p1_sub':
          "Ipak yo'li bo'ylab minglab madaniy yodgorliklarni "
          "o'rganing — saralangan, geolokatsiyalangan va boy ma'lumotli.",
      'onb_p2_title': 'AI yordamida tanish',
      'onb_p2_sub':
          "Kamerangizni istalgan obida yoki artefaktga yo'naltiring —"
          ' SilkLens uni qurilmadagi AI yordamida darhol aniqlab beradi.',
      'onb_p3_title': "Hamjamiyatga qo'shiling",
      'onb_p3_sub':
          'Kashfiyotlaringizni ulashing, sharhlar yozing, XP nishonlari'
          " qozonib, meros ishqibozlari bilan bog'laning.",
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
      // Auth — Sign Up
      'auth_signup_title': 'Создать аккаунт',
      'auth_signup_sub': 'Присоединяйтесь к сообществу SilkLens',
      'auth_password_8': 'Пароль (минимум 8 символов)',
      'auth_signup_btn': 'Создать аккаунт',
      'auth_have_account': 'Уже есть аккаунт? ',
      'auth_signin_link': 'Войти',
      'auth_tos_text':
          'Я согласен с Условиями использования и Политикой конфиденциальности',
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
      // Onboarding navigation
      'onb_skip': 'Пропустить',
      'onb_next': 'Далее',
      'onb_get_started': 'Начать',
      'onb_have_account': 'У меня уже есть аккаунт',
      'onb_p1_title': 'Откройте памятники наследия',
      'onb_p1_sub':
          'Исследуйте тысячи культурных объектов вдоль Шёлкового пути —'
          ' отобранных, геолоцированных и подробно задокументированных.',
      'onb_p2_title': 'Распознавание с помощью ИИ',
      'onb_p2_sub':
          'Наведите камеру на любой памятник или артефакт —'
          ' SilkLens мгновенно идентифицирует его на устройстве.',
      'onb_p3_title': 'Присоединяйтесь к сообществу',
      'onb_p3_sub':
          'Делитесь открытиями, пишите отзывы, зарабатывайте XP-значки'
          ' и общайтесь с любителями наследия по всему миру.',
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
      // Auth — Sign Up
      'auth_signup_title': '创建账号',
      'auth_signup_sub': '加入 SilkLens 社区',
      'auth_password_8': '密码（至少 8 个字符）',
      'auth_signup_btn': '创建账号',
      'auth_have_account': '已有账号？',
      'auth_signin_link': '登录',
      'auth_tos_text': '我同意服务条款和隐私政策',
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
      // Onboarding navigation
      'onb_skip': '跳过',
      'onb_next': '下一步',
      'onb_get_started': '开始使用',
      'onb_have_account': '我已有账号',
      'onb_p1_title': '探索文化遗址',
      'onb_p1_sub': '探索丝绸之路沿线数千处文化地标——精心策划、地理定位、内容详尽。',
      'onb_p2_title': 'AI 智能识别',
      'onb_p2_sub': '将相机对准任何遗迹或文物，SilkLens 将通过设备端 AI 即时为您识别。',
      'onb_p3_title': '加入社区',
      'onb_p3_sub': '分享发现、撰写评论、赢取 XP 徽章，与全球文化遗产爱好者建立联系。',
    },
  };
}
