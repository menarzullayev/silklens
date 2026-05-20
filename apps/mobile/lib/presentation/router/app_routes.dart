abstract final class AppRoutes {
  static const splash = '/';
  static const onboarding = '/onboarding';
  static const signIn = '/auth/sign-in';
  static const signUp = '/auth/sign-up';
  static const home = '/home';
  static const map = '/map';
  static const camera = '/camera';
  
  static String heritageDetail(String pubId) => '/home/heritage/$pubId';
}
