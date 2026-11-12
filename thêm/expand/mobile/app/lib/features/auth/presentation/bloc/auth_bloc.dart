import 'package:flutter_bloc/flutter_bloc.dart';
import '../../domain/usecases/login_usecase.dart';
import '../../domain/usecases/logout_usecase.dart';
import '../../domain/usecases/get_current_user_usecase.dart';
import 'auth_event.dart';
import 'auth_state.dart';

class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final LoginUseCase loginUseCase;
  final LogoutUseCase logoutUseCase;
  final GetCurrentUserUseCase getCurrentUserUseCase;

  AuthBloc({
    required this.loginUseCase,
    required this.logoutUseCase,
    required this.getCurrentUserUseCase,
  }) : super(AuthInitial()) {
    on<AppStarted>(_onAppStarted);
    on<LoginRequested>(_onLoginRequested);
    on<LogoutRequested>(_onLogoutRequested);
  }

  /// Khi app khởi động — kiểm tra session hiện tại
  Future<void> _onAppStarted(
    AppStarted event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    final result = await getCurrentUserUseCase();
    result.fold(
      (failure) => emit(Unauthenticated()),
      (user) => user != null
          ? emit(Authenticated(user))
          : emit(Unauthenticated()),
    );
  }

  /// Xử lý login
  Future<void> _onLoginRequested(
    LoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    final result = await loginUseCase(
      LoginParams(email: event.email, password: event.password),
    );
    result.fold(
      (failure) => emit(AuthError(failure.message)),
      (user)    => emit(Authenticated(user)),
    );
  }

  /// Xử lý logout
  Future<void> _onLogoutRequested(
    LogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    await logoutUseCase();
    emit(Unauthenticated());
  }
}
