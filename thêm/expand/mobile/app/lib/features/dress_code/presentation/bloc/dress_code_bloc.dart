import 'package:flutter_bloc/flutter_bloc.dart';
import '../../domain/usecases/check_dress_code_usecase.dart';
import 'dress_code_event.dart';
import 'dress_code_state.dart';

class DressCodeBloc extends Bloc<DressCodeEvent, DressCodeState> {
  final CheckDressCodeUseCase checkDressCodeUseCase;

  DressCodeBloc({required this.checkDressCodeUseCase}) : super(DressCodeInitial()) {
    on<DressCodeCheckRequested>(_onCheckRequested);
    on<DressCodeReset>((_, emit) => emit(DressCodeInitial()));
  }

  Future<void> _onCheckRequested(
    DressCodeCheckRequested event,
    Emitter<DressCodeState> emit,
  ) async {
    emit(DressCodeLoading());
    final result = await checkDressCodeUseCase(event.image);
    result.fold(
      (failure) => emit(DressCodeError(failure.message)),
      (dressResult) => emit(DressCodeChecked(dressResult)),
    );
  }
}
